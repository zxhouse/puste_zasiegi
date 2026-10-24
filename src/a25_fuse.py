"""Fuzja dopasowań (v3) -> analysis/alignment.json (poprzednia wersja zachowana jako analysis/alignment_v2.json).
Źródła: Omnilingual CTC (a23, kto śpiewa które słowo + czasy znaków), MFA (a22, czasy słów i fonemów),
obwiednia stemów (koniec trzymanych nut, głośność sylaby).
Zasady:
* słowo śpiewa Henio, jeśli jest w stemie wokalu prowadzącego z pewnością >= -0,9/znak (albo >= -1,5, gdy chór go nie ma);
  chór - jeśli jest w stemie chórków z pewnością >= -1,5; oba -> dubel (śpiewają razem).
* początek słowa: MFA, jeśli różni się od (CTC - 45 ms) o < 150 ms; inaczej CTC - 45 ms (CTC „strzela” po początku dźwięku -
  średnio 35-110 ms później niż MFA / Parakeet / Whisper, a2 4_crosscheck).
* sylaby: z fonemów MFA (grupy wokół samogłosek), gdy liczba samogłosek = liczba sylab; inaczej ze znaczników znaków CTC.
* koniec sylaby: koniec samogłoski (MFA) lub następna sylaba, przycięty, gdy obwiednia stemu spadnie o 18 dB od szczytu sylaby.
* otwarcie ust 0..1 dla sylaby: samogłoska x głośność x długość x akcent (półotwarcia dla krótkich / nieakcentowanych)."""
import os, sys, json, re, shutil, numpy as np, soundfile as sf, librosa
sys.path.insert(0, os.path.dirname(__file__))
from a23_ctc_skip import script
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.join(ROOT, 'build/asr'); AN = os.path.join(ROOT, 'analysis')
VOW_PH = {'a', 'ɛ', 'i', 'ɨ', 'ɔ', 'u', 'ɔ̃', 'ɛ̃'}
VOW = set('aąeęioóuy')
BASE = {'a': 1.0, 'o': 0.86, 'ą': 0.8, 'e': 0.74, 'ę': 0.72, 'y': 0.58, 'u': 0.52, 'ó': 0.52, 'i': 0.48}
FUNC = {'i', 'w', 'z', 'a', 'na', 'tu', 'się', 'że', 'to', 'o', 'do', 'ja', 'po', 'za', 'nie', 'jak', 'bez', 'tej', 'tych', 'cię', 'mnie', 'mam', 'był', 'bym'}
def norm(w): return re.sub(r'[^a-ząćęłńóśźż]', '', w.lower())

def env(stem):
    x, sr = sf.read(os.path.join(ROOT, 'build/wav', stem), always_2d=True); x = x.mean(1)
    hop = int(0.01*sr); r = librosa.feature.rms(y=x, frame_length=4*hop, hop_length=hop)[0]
    return 20*np.log10(r + 1e-9)
ENV = {'lead': env('0_lead_vocals.wav'), 'back': env('1_backing_vocals.wav')}
def db_at(stem, a, b):
    e = ENV[stem]; i0, i1 = int(a*100), max(int(b*100), int(a*100) + 1)
    return e[i0:i1]

def vowel_of(s):
    t = s.lower()
    for k, ch in enumerate(t):
        if ch in VOW and not (ch == 'i' and k + 1 < len(t) and t[k+1] in VOW): return ch
    return 'e'

def mfa_words(stem):
    m = json.load(open(os.path.join(A, f'mfa_{stem}.json')))
    out = {}
    for s in m['segments']:
        if s.get('failed'): continue
        ph = s['phones']
        for w in s['words']:
            w = dict(w); w['phones'] = [p for p in ph if p['t0'] >= w['t0'] - 1e-6 and p['t1'] <= w['t1'] + 1e-6]
            out.setdefault(s['seg'], []).append(w)
    return out

def syl_groups(phones, n):
    """Fonemy słowa -> n grup sylab (spółgłoski przed samogłoską należą do jej sylaby, końcowe do ostatniej)."""
    vi = [i for i, p in enumerate(phones) if p['p'] in VOW_PH]
    if len(vi) != n or n == 0: return None
    groups = []
    for k, v in enumerate(vi):
        a = 0 if k == 0 else groups[-1]['_end'] + 1
        # spółgłoski między samogłoskami: ostatnia idzie do następnej sylaby
        if k + 1 < len(vi):
            nxt = vi[k+1]; cons = nxt - v - 1; end = v + max(cons - 1, 0) if cons > 1 else v
        else: end = len(phones) - 1
        groups.append(dict(t_on=phones[a]['t0'], t_vowel=phones[v]['t0'], t_vowel_end=phones[v]['t1'], t_off=phones[end]['t1'], _end=end))
    return groups

def fuse_stem(stem, words_ctc, mfa):
    """Czasy słów i sylab dla jednego stemu."""
    seg_words = {}
    for w in words_ctc:
        if w.get('present') and w['conf'] > -1.5: seg_words.setdefault(f"l{w['sec']:02d}_{w['line']}_{w['occ']}", []).append(w)
    res = {}
    for seg, ws in seg_words.items():
        mw = mfa.get(seg, [])
        # dopasowanie sekwencyjne słów CTC <-> MFA po pisowni
        j = 0
        for w in ws:
            m = None
            for k in range(j, min(j + 3, len(mw))):
                if norm(mw[k]['w']) == norm(w['sung']): m = mw[k]; j = k + 1; break
            ctc_on = w['t0'] - 0.045
            use_mfa = m is not None and abs(m['t0'] - ctc_on) < 0.15
            t0 = m['t0'] if use_mfa else ctc_on
            t1 = m['t1'] if use_mfa else w['t1']
            n = len(w['syl'])
            if n == 0:                                   # przyimek bez samogłoski (w, z) - wymawiany z następnym słowem
                res[(w['sec'], w['line'], w['occ'], w['wi_glob'])] = dict(t0=round(t0, 3), t1=round(t1, 3), conf=w['conf'], syl=[], src='mfa' if use_mfa else 'ctc')
                continue
            G = syl_groups(m['phones'], n) if use_mfa else None
            src = 'mfa' if G else 'ctc'
            if not G:
                # znaczniki znaków CTC: początek sylaby = znak początkowy sylaby, samogłoska = pierwszy znak samogłoski
                ct = w['char_t']; pos = 0; G = []
                for s in w['syl']:
                    idx = list(range(pos, pos + len(s))); pos += len(s)
                    times = [ct[i] for i in idx if i < len(ct) and ct[i] is not None]
                    vt = [ct[i] for i in idx if i < len(ct) and ct[i] is not None and s[i - idx[0]].lower() in VOW]
                    on = (min(times) if times else (G[-1]['t_on'] + 0.1 if G else t0)) - 0.045
                    G.append(dict(t_on=on, t_vowel=(vt[0] - 0.03) if vt else on + 0.04))
                for k in range(n):
                    G[k]['t_off'] = G[k+1]['t_on'] if k + 1 < n else t1
                    G[k]['t_vowel_end'] = G[k]['t_off']
                G[0]['t_on'] = min(G[0]['t_on'], t0); t0 = G[0]['t_on']
            sy = []
            for k, (s, g) in enumerate(zip(w['syl'], G)):
                on = g['t_on']; off = max(g['t_off'], on + 0.05)
                # koniec trzymanej nuty z obwiedni: spadek o 18 dB od szczytu sylaby
                e = db_at(stem, on, off + 0.4); pk = e[:max(int((off - on)*100), 1)].max() if len(e) else -60
                drop = np.where(e[int(max(g['t_vowel'] - on, 0)*100):] < pk - 18)[0]
                env_off = on + (int(max(g['t_vowel'] - on, 0)*100) + drop[0])/100 if len(drop) else off
                if k + 1 == n: off = max(min(max(off, env_off), off + 0.4), on + 0.06)
                loud = float(np.clip((pk + 42)/30, 0.35, 1.0))
                sy.append(dict(text=s, t_on=round(on, 3), t_peak=round(max(g['t_vowel'], on), 3), t_off=round(off, 3), vowel=vowel_of(s),
                               loud=round(loud, 2), src=src))
            res[(w['sec'], w['line'], w['occ'], w['wi_glob'])] = dict(t0=round(t0, 3), t1=round(max(t1, sy[-1]['t_off']), 3), conf=w['conf'], syl=sy, src=src)
    return res

def mouth_open(word, syls):
    """Otwarcie ust dla każdej sylaby słowa: samogłoska x głośność x długość x akcent."""
    n = len(syls); out = []
    for k, s in enumerate(syls):
        d = s['t_off'] - s['t_on']
        dur = float(np.clip(0.5 + d*1.6, 0.55, 1.0))
        stress = 1.08 if (n >= 2 and k == n - 2) else (0.92 if n >= 2 else 1.0)
        if n == 1 and norm(word) in FUNC: stress = 0.74
        op = BASE.get(s['vowel'], 0.7)*(0.55 + 0.45*s['loud'])*dur*stress
        out.append(round(float(np.clip(op*1.15, 0.22, 1.0)), 3))
    return out

if __name__ == '__main__':
    if not os.path.exists(os.path.join(AN, 'alignment_v2.json')):
        shutil.copy(os.path.join(AN, 'alignment.json'), os.path.join(AN, 'alignment_v2.json'))
    old = json.load(open(os.path.join(AN, 'alignment_v2.json')))
    S = json.load(open(os.path.join(AN, 'lyrics_struct.json')))
    CT = {st: json.load(open(os.path.join(A, f'ctc2_{st}.json'))) for st in ('lead', 'back')}
    for st in CT:
        for i, w in enumerate(CT[st]['words']): w['wi_glob'] = None
    # wspólny klucz słowa: (sec, line, occ, indeks słowa w wersie bez nawiasów / w nawiasie)
    for st in CT:
        cnt = {}
        for w in CT[st]['words']:
            k = (w['sec'], w['line'], w['occ'], w['paren']); w['wi_glob'] = (w['paren'], cnt.get(k, 0)); cnt[k] = cnt.get(k, 0) + 1
    MF = {st: mfa_words(st) for st in ('lead', 'back')}
    # pierwsze dopasowanie (bez pomijania słów) jako zapas dla słów nierozpoznanych
    FB = {}; cnt = {}
    for w in json.load(open(os.path.join(A, 'ctc_lead.json')))['words']:
        k = (w['sec'], w['line']); FB[(w['sec'], w['line'], cnt.get(k, 0))] = w; cnt[k] = cnt.get(k, 0) + 1
    F = {st: fuse_stem(st, CT[st]['words'], MF[st]) for st in ('lead', 'back')}
    # poprawki tekstu wykryte akustycznie (np. refren 1, wers 6: śpiewane "Puste", w tekście "Wielkie")
    changes = CT['lead']['changes'] + CT['back']['changes']
    fix = {(c['sec'], c['line'], c['occ']): c for c in changes}
    lines = []; repeats = []
    for L in script():
        key3 = (L['sec'], L['line'], L['occ'])
        words = []; ci = {False: 0, True: 0}
        for w in L['words']:
            k = (L['sec'], L['line'], L['occ'], (w['paren'], ci[w['paren']])); ci[w['paren']] += 1
            lw = F['lead'].get(k); cw = F['back'].get(k)
            lead_ok = lw is not None and (lw['conf'] >= -0.9 or (cw is None and lw['conf'] >= -1.5))
            choir_ok = cw is not None
            if not lead_ok and not choir_ok:
                # słowo śpiewane, ale nierozpoznane pewnie (np. angielskie "case", "cringe"): pozycja z pierwszego,
                # wymuszonego dopasowania bez pomijania (a21), sylaby po równo; śpiewa ten sam głos co sąsiedzi
                if w['paren']: continue
                fb = FB.get((L['sec'], L['line'], ci[False] - 1)) if L['occ'] == 0 else None
                words.append(dict(w=w['w'], singers=None, paren=False, fb=fb, nsyl=len(w['syl']), sylt=w['syl']))
                continue
            disp = w['w']
            cc = [c for c in changes if (c['sec'], c['line'], c['occ']) == key3 and c['written'].lower() == w['w'].lower()]
            if cc: disp = cc[0]['sung'].capitalize() if w['w'][0].isupper() else cc[0]['sung']
            main = lw if lead_ok else cw
            ent = dict(w=disp, singers=(['lead'] if lead_ok else []) + (['choir'] if choir_ok else []), paren=w['paren'],
                       t0=min(x['t0'] for x in (lw if lead_ok else None, cw) if x), t1=max(x['t1'] for x in (lw if lead_ok else None, cw) if x),
                       syl=main['syl'], src=main['src'])
            ent['open'] = mouth_open(disp, main['syl'])
            if lead_ok and choir_ok: ent['syl_choir'] = cw['syl']; ent['open_choir'] = mouth_open(disp, cw['syl'])
            words.append(ent)
        # uzupełnienie słów nierozpoznanych
        for k, w in enumerate(words):
            if w is None or w.get('singers') is not None: continue
            prv = next((words[j] for j in range(k - 1, -1, -1) if words[j] and words[j].get('singers')), None)
            nxt = next((words[j] for j in range(k + 1, len(words)) if words[j] and words[j].get('singers')), None)
            lo = prv['t1'] if prv else (nxt['t0'] - 0.6 if nxt else None); hi = nxt['t0'] if nxt else (prv['t1'] + 0.6 if prv else None)
            if lo is None: words[k] = None; continue
            fb = w['fb']
            if fb and lo - 0.05 <= fb['t0'] - 0.045 < hi: t0 = fb['t0'] - 0.045; t1 = min(fb['t1'], hi)
            else: t0 = lo + 0.02; t1 = hi - 0.02 if hi - lo < 0.9 else lo + 0.12*max(w['nsyl'], 1) + 0.1
            t1 = max(t1, t0 + 0.08); n = max(w['nsyl'], 0)
            sy = [dict(text=w['sylt'][i], t_on=round(t0 + (t1 - t0)*i/n, 3), t_peak=round(t0 + (t1 - t0)*i/n + 0.03, 3),
                       t_off=round(t0 + (t1 - t0)*(i + 1)/n - 0.01, 3), vowel=vowel_of(w['sylt'][i]), loud=0.7, src='interp') for i in range(n)]
            sing = (prv or nxt)['singers']
            ent = dict(w=w['w'], singers=sing, paren=False, t0=round(t0, 3), t1=round(t1, 3), syl=sy, src='interp' if not fb else 'ctc-forced')
            ent['open'] = mouth_open(w['w'], sy)
            if 'choir' in sing and 'lead' in sing: ent['syl_choir'] = sy; ent['open_choir'] = ent['open']
            words[k] = ent
        words = [w for w in words if w]
        if not words: continue
        text = S[L['sec']]['lines'][L['line']]['text']
        if key3 in fix or any(c['sec'] == L['sec'] and c['line'] == L['line'] for c in changes):
            for c in changes:
                if c['sec'] == L['sec'] and c['line'] == L['line']: text = re.sub(c['written'], c['sung'].capitalize(), text, count=1)
        lead_words = [w for w in words if 'lead' in w['singers'] and not w['paren']]
        ent = dict(sec=L['sec'], line=L['line'], occ=L['occ'], section=S[L['sec']]['name'], text=text, spoken=L['spoken'],
                   singer='lead' if lead_words else 'choir', t0=min(w['t0'] for w in words), t1=max(w['t1'] for w in words), words=words)
        if any((l['sec'], l['line']) == (L['sec'], L['line']) for l in lines): repeats.append(ent)
        else: lines.append(ent)
    # chór: "hej" (tylko tam, gdzie stem chórków ma okrzyk), wokalizy bez słów, finał
    hej = []
    for l in lines:
        for w in l['words']:
            if w['w'].lower() == 'hej' and 'choir' in w['singers']: hej.append(dict(after_line=[l['sec'], l['line']], t_on=w['t0']))
    for l in lines: l['words'] = [w for w in l['words'] if w['w'].lower() != 'hej']
    e = ENV['back']; t = np.arange(len(e))/100; act = e > e.max() - 35
    cov = np.zeros(len(t), bool)
    for l in lines + repeats:
        for w in l['words']:
            if 'choir' in w['singers']: cov[(t >= w['t0'] - 0.15) & (t <= w['t1'] + 0.25)] = True
    for h in hej: cov[(t >= h['t_on'] - 0.1) & (t <= h['t_on'] + 0.6)] = True
    wordless = []; i = 0
    while i < len(t):
        if act[i] and not cov[i]:
            j = i
            while j < len(t) and act[j] and not cov[j]: j += 1
            if (j - i) >= 25: wordless.append(dict(t0=round(t[i], 2), t1=round(t[j-1], 2), peak_db=round(float(e[i:j].max()), 1)))
            i = j
        else: i += 1
    # zdarzenia (początki fraz) we wokalizach: przyrosty obwiedni stemu chórków
    x, sr = sf.read(os.path.join(ROOT, 'build/wav/1_backing_vocals.wav'), always_2d=True)
    on = librosa.onset.onset_detect(y=x.mean(1), sr=sr, hop_length=441, units='time', backtrack=True, delta=0.08)
    events = [dict(t_on=round(float(o), 3), t_peak=round(float(o) + 0.06, 3), level=0.0) for o in on if any(s['t0'] - 0.05 <= o <= s['t1'] for s in wordless)]
    # finał: okrzyk Henia (201,5 s) i końcowe "HEJ" - początek z obwiedni stemu wokalu
    def onset_near(stem, a, b):
        ee = ENV[stem][int(a*100):int(b*100)]; k = int(np.argmax(np.diff(ee))) + 1; return round(a + k/100, 2)
    fin_shout = onset_near('lead', 201.2, 201.9); fin_hej = onset_near('lead', 209.6, 210.0)
    finale = [dict(text='hej', t_on=fin_shout, t_off=round(fin_shout + 0.8, 2)), dict(text='HEJ', t_on=fin_hej, t_off=round(fin_hej + 1.8, 2))]
    rep = [r for r in repeats if r['sec'] == 12 and 'lead' in r['words'][0]['singers'] and r['t0'] > 205]
    reprise = [dict(text=s['text'], t_on=s['t_on'], t_off=s['t_off']) for r in rep for w in r['words'] if 'lead' in w['singers'] for s in w['syl']]
    out = dict(method='v3: Omnilingual ASR CTC 1B (wymuszone dopasowanie z pomijaniem słów, osobno stem prowadzący i chórki) + '
                      'Montreal Forced Aligner polish_mfa (fonemy) + obwiednia stemów; sprawdzone: Whisper small, Parakeet TDT v3, Silero VAD',
               lines=lines, repeats=repeats, text_changes=changes,
               choir=dict(events=events, wordless=wordless, hej=hej, finale=finale, reprise=reprise))
    json.dump(out, open(os.path.join(AN, 'alignment.json'), 'w'), ensure_ascii=False, indent=1)
    # podsumowanie
    nl = sum(1 for l in lines for w in l['words'] if 'lead' in w['singers'] for s in w['syl'])
    nc = sum(1 for l in lines + repeats for w in l['words'] if 'choir' in w['singers'] for s in (w.get('syl_choir') or w['syl']))
    print('wersów', len(lines), 'powtórzeń', len(repeats), 'sylab Henia', nl, 'sylab chóru', nc)
    print('hej chóru:', hej); print('finał:', finale); print('wokalizy chóru bez słów:', len(wordless), 'zdarzeń:', len(events))
    print('zmiany tekstu:', [(c['sec'], c['line'], c['written'], '->', c['sung']) for c in changes])
    for l in lines + repeats:
        print(f"[{l['sec']},{l['line']},{l['occ']}] {l['t0']:.2f} {l['singer']:5s} " + ' '.join(
            f"{w['w']}{'' if w['singers'] == ['lead'] else ('*' if w['singers'] == ['choir'] else '+')}" for w in l['words']))

"""Dopasowanie CTC z możliwością pominięcia słowa (kara SKIP) - osobno dla stemu wokalu prowadzącego i stemu chórków.
Tekst „jak śpiewany” (SCRIPT): wersy z tekstu w kolejności + powtórzenia finału; dla każdego stemu Viterbi sam rozstrzyga,
które słowa w nim są (słowo nieobecne w stemie -> pominięte), więc wychodzi też podział: kto śpiewa który wers.
Warianty przymiotników w refrenach (puste / wielkie / mocne) rozstrzygane akustycznie (lokalny wynik Viterbiego w oknie słowa).
Wynik: build/asr/ctc2_<stem>.json"""
import os, sys, json, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from lyrics import syllables, tokenize
from a21_ctc_align import load, viterbi, PHON, PHON_SYL
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.join(ROOT, 'build/asr')
SKIP_CH = -1.6        # koszt pominięcia słowa na znak (log-prawdopodobieństwo); słowo nieobecne w stemie wypada drożej niż -1,6/znak
ADJ = ('puste', 'wielkie', 'mocne')

def script():
    """Wersy w kolejności śpiewania. Każde słowo: tekst, pisownia jak śpiewana, sylaby, czy z nawiasu (chórek)."""
    S = json.load(open(os.path.join(ROOT, 'analysis/lyrics_struct.json')))
    lines = []
    for si, sec in enumerate(S):
        for li, L in enumerate(sec['lines']):
            occs = 3 if (si, li) == (len(S) - 1, 1) else 1          # finał: "Puste zasięgi" śpiewane kilka razy
            for occ in range(occs):
                ws = []
                for part, paren in ((L['lead'], False), (L['choir'], True)):
                    if occ < occs - 1 and paren: continue           # "hej" tylko po ostatnim powtórzeniu
                    for w in tokenize(part):
                        low = w.lower(); sung = PHON.get(low, low)
                        ws.append(dict(w=w, sung=sung, syl=PHON_SYL.get(sung) or [s.lower() for s in syllables(w)], paren=paren))
                lines.append(dict(sec=si, line=li, occ=occ, text=L['text'], spoken=L['spoken'], words=ws))
    return lines

def viterbi_skip(lp, blank, ids, word_of, nwords, skip=None):
    """Viterbi CTC z krawędziami 'pomiń słowo'. Zwraca pierwszą/ostatnią klatkę każdego znaku (-1 = słowo pominięte)."""
    T = lp.shape[0]; N = len(ids); S = 2*N + 1
    emit = np.empty((T, S)); emit[:, 0::2] = blank[:, None]; emit[:, 1::2] = lp[:, ids]
    lab = np.full(S, -1); lab[1::2] = ids
    can_skip = np.zeros(S, bool); can_skip[3::2] = lab[3::2] != lab[1:-2:2]
    # granice słów w indeksach znaków
    first_c = np.array([np.where(word_of == k)[0][0] for k in range(nwords)]); last_c = np.array([np.where(word_of == k)[0][-1] for k in range(nwords)])
    src_b = 2*first_c; dst = 2*(last_c + 1)                   # blank przed słowem -> blank po słowie
    src_c = np.where(first_c > 0, 2*first_c - 1, 0)           # ostatni znak poprzedniego słowa -> blank po słowie
    skip = np.minimum(SKIP_CH*(last_c - first_c + 1), -3.0)   # kara zależna od długości słowa
    NEG = -1e18
    dp = np.full(S, NEG); dp[0] = emit[0, 0]; dp[1] = emit[0, 1]
    # słowo 0 można pominąć od razu
    bp = np.zeros((T, S), np.int8)
    for t in range(1, T):
        a = dp; b = np.concatenate(([NEG], dp[:-1])); c = np.concatenate(([NEG, NEG], dp[:-2])); c = np.where(can_skip, c, NEG)
        d = np.full(S, NEG); e = np.full(S, NEG)
        d[dst] = dp[src_b] + skip
        e[dst] = np.where(first_c > 0, dp[src_c] + skip, NEG)
        stack = np.vstack([a, b, c, d, e]); k = stack.argmax(0)
        dp = stack[k, np.arange(S)] + emit[t]; bp[t] = k
    s = int(S - 1 if dp[S - 1] >= dp[S - 2] else S - 2)
    # mapy dst -> src dla krawędzi pomijania
    m_b = dict(zip(dst.tolist(), src_b.tolist())); m_c = dict(zip(dst.tolist(), src_c.tolist()))
    path = np.empty(T, np.int32)
    for t in range(T - 1, -1, -1):
        path[t] = s; k = int(bp[t, s])
        s = s - k if k <= 2 else (m_b[s] if k == 3 else m_c[s])
    first = np.full(N, -1); last = np.full(N, -1)
    for t in range(T):
        st = path[t]
        if st % 2 == 1:
            j = st//2
            if first[j] < 0: first[j] = t
            last[j] = t
    return first, last, float(dp.max())

def local_score(lp, blank, cidx, word, a, b):
    """Średni log-prob na klatkę najlepszego dopasowania słowa w oknie [a, b) (blank dozwolony na brzegach)."""
    ids = np.array([cidx[c] for c in word if c in cidx])
    f, l, path, emit = viterbi(lp[a:b], blank[a:b], ids)
    sc = sum(emit[t, path[t]] for t in range(b - a))
    return sc/(b - a)

def run(stem, include_paren, lead_words=None):
    chars, lp, blank, FR = load(stem); cidx = {c: i for i, c in enumerate(chars)}
    L = script()
    words = []
    for li, l in enumerate(L):
        for w in l['words']:
            if w['paren'] and not include_paren: continue
            words.append(dict(w, li=li, sec=l['sec'], line=l['line'], occ=l['occ']))
    def align(group, f0, f1):
        ids, owner = [], []
        for k, w in enumerate(group):
            for ch in w['sung']:
                if ch in cidx: ids.append(cidx[ch]); owner.append(k)
        owner = np.array(owner)
        first, last, score = viterbi_skip(lp[f0:f1], blank[f0:f1], np.array(ids), owner, len(group))
        first = np.where(first >= 0, first + f0, -1); last = np.where(last >= 0, last + f0, -1)
        for k, w in enumerate(group):
            m = np.where(owner == k)[0]; f, l = first[m], last[m]
            if (f < 0).all():
                w['present'] = False; w.pop('t0', None); w.pop('t1', None); w.pop('char_t', None); continue
            w['present'] = True
            w['char_t'] = [round(float(x)*FR, 3) if x >= 0 else None for x in f]
            w['t0'] = round(float(f[f >= 0].min())*FR, 3); w['t1'] = round(float(l[l >= 0].max() + 1)*FR, 3)
            w['conf'] = round(float(np.mean([lp[f[i], ids[m[i]]] for i in range(len(m)) if f[i] >= 0])), 3)
    # grupy i okna: wokal prowadzący - cała piosenka naraz; chórki - każda część osobno, w oknie czasu tej części
    # wyznaczonym z wokalu prowadzącego (powtarzane frazy refrenów nie mogą przeskoczyć do innego refrenu)
    if lead_words is None:
        groups = [(words, 0, lp.shape[0])]
    else:
        nsec = max(w['sec'] for w in words) + 1
        st = {}; en = {}
        for w in lead_words:
            if w['present']:
                st[w['sec']] = min(st.get(w['sec'], 1e9), w['t0']); en[w['sec']] = max(en.get(w['sec'], 0), w['t1'])
        groups = []
        for sec in range(nsec):
            g = [w for w in words if w['sec'] == sec]
            if not g: continue
            prev_end = max([en[s] for s in en if s < sec] + [0.0])
            nxt = min([st[s] for s in st if s > sec] + [lp.shape[0]*FR])
            a = st.get(sec, prev_end) - 1.0 if sec in st else prev_end - 0.3
            b = nxt + 0.3
            groups.append((g, max(int(a/FR), 0), min(int(b/FR), lp.shape[0])))
    for g, f0, f1 in groups: align(g, f0, f1)
    # warianty przymiotników przed "zasięgi" w refrenach i finale: wybór akustyczny
    changes = []
    for k, w in enumerate(words):
        if w['sung'] in ADJ and k + 1 < len(words) and words[k+1]['sung'].startswith('zasi') and (w['present'] or words[k+1]['present']):
            if w['present']: a = max(int(w['t0']/FR) - 4, 0); b = min(int(w['t1']/FR) + 4, lp.shape[0])
            else: b = int(words[k+1]['t0']/FR) + 1; a = max(b - int(0.9/FR), 0)      # przymiotnik pominięty: okno tuż przed "zasięgi"

            sc = {v: local_score(lp, blank, cidx, v, a, b) for v in ADJ}
            best = max(sc, key=sc.get)
            w['variant_scores'] = {v: round(s, 3) for v, s in sc.items()}
            if best != w['sung'] and sc[best] - sc[w['sung']] > 0.15 and sc[best] > -0.6:
                changes.append(dict(sec=w['sec'], line=w['line'], occ=w['occ'], written=w['w'], sung=best, t=w.get('t0', words[k+1]['t0']), scores=w['variant_scores']))
                w['written'] = w['w']; w['w'] = best.capitalize() if w['w'][0].isupper() else best; w['sung'] = best
                w['syl'] = [s.lower() for s in syllables(best)]
    if changes:                                                   # ponowne dopasowanie z poprawionym tekstem
        for g, f0, f1 in groups: align(g, f0, f1)
    return words, changes, FR

if __name__ == '__main__':
    R = {}
    for stem, paren in (('lead', False), ('back', True)):
        words, changes, FR = run(stem, paren, R['lead']['words'] if stem == 'back' else None)
        R[stem] = dict(words=words, changes=changes)
        json.dump(dict(frame=FR, words=words, changes=changes), open(os.path.join(A, f'ctc2_{stem}.json'), 'w'), ensure_ascii=False, indent=0)
        print(f'== {stem}: słów {len(words)}, obecnych {sum(w["present"] for w in words)}, zmiany tekstu: {changes}')
        cur = None
        for w in words:
            key = (w['sec'], w['line'], w['occ'])
            if key != cur: cur = key; print(f"\n[{key[0]},{key[1]},{key[2]}]", end=' ')
            print(f"{w['w']}@{w['t0']:.2f}({w['conf']:.1f})" if w['present'] else f"-{w['w']}-", end=' ')
        print('\n')

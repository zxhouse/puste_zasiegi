"""Wymuszone dopasowanie CTC (Viterbi) znanego tekstu do prawdopodobieństw znaków z modelu Omnilingual (a20_omni_ctc.py).
Cały tekst wokalu prowadzącego naraz (kotwice same wynikają z akustyki), spacja traktowana jak cisza (blank).
Wynik: build/asr/ctc_<stem>.json - dla każdego słowa: czasy znaków, początek/koniec, pewność;
       porównanie z niezależną transkrypcją zachłanną tego samego modelu (czy słowo rozpoznane w pobliżu)."""
import os, sys, json, re, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from lyrics import syllables
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.join(ROOT, 'build/asr')
# pisownia "jak śpiewane" dla słów obcych (model zapisuje je fonetycznie po polsku)
PHON = {'case': 'kejs', 'study': 'stadi', 'cringe': 'krindż', 'scrollowania': 'skrolowania', 'linkedinie': 'linkedinie'}
PHON_SYL = {'kejs': ['kejs'], 'stadi': ['sta', 'di'], 'krindż': ['krindż'], 'skrolowania': ['skro', 'lo', 'wa', 'nia'], 'linkedinie': ['lin', 'ke', 'di', 'nie']}

def load(stem):
    d = np.load(os.path.join(A, f'omni_{stem}.npz'))
    chars = [str(c) for c in d['chars']]
    lp = d['logp'].astype(np.float64)
    filled = d['filled'] if 'filled' in d.files else np.ones(len(lp), bool)
    for j in np.where(~filled)[0]:                   # pojedyncze klatki na styku okien: kopia sąsiedniej
        k = j - 1 if j > 0 and filled[j - 1] else min(j + 1, len(lp) - 1)
        lp[j] = lp[k]
    sp = chars.index(' ')
    blank = np.logaddexp(lp[:, 0], lp[:, sp])           # spacja = przerwa
    return chars, lp, blank, float(d['fr'])

def viterbi(lp, blank, ids):
    """Klasyczne dopasowanie CTC: stany = blank,c1,blank,c2,...,blank. Zwraca dla każdego znaku (pierwsza, ostatnia klatka)."""
    T = lp.shape[0]; N = len(ids); S = 2*N + 1
    emit = np.empty((T, S)); emit[:, 0::2] = blank[:, None]; emit[:, 1::2] = lp[:, ids]
    lab = np.full(S, -1); lab[1::2] = ids
    can_skip = np.zeros(S, bool)
    can_skip[3::2] = lab[3::2] != lab[1:-2:2]            # przeskok blanku między różnymi znakami
    NEG = -1e18
    dp = np.full(S, NEG); dp[0] = emit[0, 0]; dp[1] = emit[0, 1]
    bp = np.zeros((T, S), np.int8)
    for t in range(1, T):
        a = dp
        b = np.concatenate(([NEG], dp[:-1]))
        c = np.concatenate(([NEG, NEG], dp[:-2])); c = np.where(can_skip, c, NEG)
        stack = np.vstack([a, b, c]); k = stack.argmax(0)
        dp = stack[k, np.arange(S)] + emit[t]; bp[t] = k
    s = int(S - 1 if dp[S - 1] >= dp[S - 2] else S - 2)
    path = np.empty(T, np.int32)
    for t in range(T - 1, -1, -1):
        path[t] = s; s = int(s) - int(bp[t, s])
    first = np.full(N, -1); last = np.full(N, -1)
    for t in range(T):
        st = path[t]
        if st % 2 == 1:
            j = st//2
            if first[j] < 0: first[j] = t
            last[j] = t
    return first, last, path, emit

def words_of_lyrics(singer='lead'):
    S = json.load(open(os.path.join(ROOT, 'analysis/lyrics_struct.json')))
    out = []
    for si, sec in enumerate(S):
        for li, L in enumerate(sec['lines']):
            ws = L['lead_words'] if singer == 'lead' else L['choir_words']
            for wi, w in enumerate(ws):
                orig = w['w']; low = orig.lower(); sung = PHON.get(low, low)
                syl = PHON_SYL.get(sung) or [s.lower() for s in syllables(orig)]
                out.append(dict(sec=si, line=li, wi=wi, w=orig, sung=sung, syl=syl))
    return out

def run(stem='lead', singer='lead', words=None):
    chars, lp, blank, FR = load(stem)
    cidx = {c: i for i, c in enumerate(chars)}
    words = words or words_of_lyrics(singer)
    ids, owner = [], []
    for k, w in enumerate(words):
        for ch in w['sung']:
            if ch in cidx: ids.append(cidx[ch]); owner.append(k)
    first, last, path, emit = viterbi(lp, blank, np.array(ids))
    owner = np.array(owner)
    for k, w in enumerate(words):
        m = np.where(owner == k)[0]
        f, l = first[m], last[m]
        w['char_t'] = [round(float(x)*FR, 3) for x in f]
        w['t0'] = round(float(f.min())*FR, 3); w['t1'] = round(float(l.max() + 1)*FR, 3)
        w['conf'] = round(float(np.mean([lp[f[i], ids[m[i]]] for i in range(len(m))])), 3)
    return words, FR

def greedy_words(stem):
    out = []
    for l in open(os.path.join(A, f'omni_{stem}_greedy.txt'), encoding='utf-8'):
        t, w = l.split(None, 1); out.append((float(t), w.strip()))
    return out

if __name__ == '__main__':
    words, FR = run('lead', 'lead')
    G = greedy_words('lead')
    # niezależny test: czy w transkrypcji zachłannej to samo słowo (lub jego początek) pojawia się w +-0,3 s od początku z dopasowania
    ok = 0; rows = []
    for w in words:
        cand = [g for g in G if abs(g[0] - w['t0']) < 0.3 and (w['sung'][:3] in g[1] or g[1][:3] in w['sung'])]
        w['greedy_match'] = bool(cand)
        if cand: w['greedy_dt'] = round(min(cand, key=lambda g: abs(g[0] - w['t0']))[0] - w['t0'], 3); ok += 1
    json.dump(dict(frame=FR, words=words), open(os.path.join(A, 'ctc_lead.json'), 'w'), ensure_ascii=False, indent=0)
    print('słów', len(words), 'potwierdzonych przez transkrypcję (±0,3 s):', ok)
    cur = None
    for w in words:
        if (w['sec'], w['line']) != cur:
            cur = (w['sec'], w['line']); print(f"\n[{cur[0]},{cur[1]}]", end=' ')
        print(f"{w['w']}@{w['t0']:.2f}{'' if w['greedy_match'] else '?'}({w['conf']:.1f})", end=' ')
    print()

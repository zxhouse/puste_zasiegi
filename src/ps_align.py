"""Wymuszone dopasowanie (forced alignment) pocketsphinx: model akustyczny en-us z paczki pip, słownik z g2p_pl."""
import numpy as np, os, librosa, json
from pocketsphinx import Decoder, get_model_path
from analysis_common import load, ROOT
from g2p_pl import g2p
import re
_audio = {}
def audio16(name='0_lead_vocals'):
    if name not in _audio:
        x, sr = load(name); y = librosa.resample(x, orig_sr=sr, target_sr=16000)
        y = y/np.abs(y).max()*0.9
        _audio[name] = (y*32767).astype(np.int16)
    return _audio[name]

def norm_word(w): return re.sub(r'[^a-ząćęłńóśźż]', '', w.lower())

def align(words, t0, t1, stem='0_lead_vocals', beam=1e-60):
    """words: lista słów; zwraca listę (słowo, start, koniec, [(fonem, start, koniec)]) w sekundach bezwzględnych."""
    y = audio16(stem)[int(t0*16000):int(t1*16000)]
    vocab = {}
    for w in words:
        nw = norm_word(w)
        if nw: vocab[nw] = g2p(nw)
    dpath = os.path.join(ROOT, 'build', 'ps_dict.txt')
    with open(dpath, 'w') as f:
        for k, v in vocab.items(): f.write(f'{k} {v}\n')
    d = Decoder(hmm=os.path.join(get_model_path(), 'en-us', 'en-us'), dict=dpath, lm=None, samprate=16000,
                loglevel='FATAL', beam=beam, wbeam=beam, pbeam=beam, frate=100)
    d.set_align_text(' '.join(norm_word(w) for w in words if norm_word(w)))
    try:
        d.start_utt(); d.process_raw(y.tobytes(), full_utt=True); d.end_utt()
        if d.hyp() is None: return None
        d.set_alignment()                     # drugi przebieg: dopasowanie fonemów
        d.start_utt(); d.process_raw(y.tobytes(), full_utt=True); d.end_utt()
        al = d.get_alignment()
    except RuntimeError:
        return None
    if al is None: return None
    out = []
    for wseg in al:
        ph = [(p.name, t0 + p.start/100, t0 + (p.start + p.duration)/100) for p in wseg]
        out.append((wseg.name, t0 + wseg.start/100, t0 + (wseg.start + wseg.duration)/100, ph))
    return out

if __name__ == '__main__':
    import sys
    words = 'Poranna kawa wielki plan Wkładam garnitur choć mam luźny stan Piszę o synergiach choć boli mnie szczęka Z przyjemnością dzielę się i już mnie skręca Tak tak wszyscy się strasznie cieszą'.split()
    r = align(words, 13.5, 33.0)
    for w, a, b, ph in r:
        print(f'{a:7.2f} {b:7.2f} {w}  ' + ' '.join(f'{p}' for p, _, _ in ph))

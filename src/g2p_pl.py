"""Uproszczona polska transkrypcja grafem->fonem na fonemy ARPAbet (model akustyczny en-us pocketsphinx)."""
import re
SPECIAL = {'linkedinie': 'L IH NG K D IH N Y EH', 'case': 'K EY S', 'study': 'S T AH D IY', 'cringe': 'K R IH N JH',
           'scrollowania': 'S K R OW L OW V AA N Y AA'}
MULTI = [('dzi', 'JH'), ('drz', 'JH'), ('dż', 'JH'), ('dź', 'JH'), ('dz', 'D Z'), ('ci', 'CH'), ('si', 'SH'), ('zi', 'ZH'), ('ni', 'N Y'),
         ('cz', 'CH'), ('sz', 'SH'), ('rz', 'ZH'), ('ch', 'HH')]
SINGLE = {'a': 'AA', 'ą': 'AO N', 'b': 'B', 'c': 'T S', 'ć': 'CH', 'd': 'D', 'e': 'EH', 'ę': 'EH N', 'f': 'F', 'g': 'G', 'h': 'HH',
          'i': 'IY', 'j': 'Y', 'k': 'K', 'l': 'L', 'ł': 'W', 'm': 'M', 'n': 'N', 'ń': 'N Y', 'o': 'AO', 'ó': 'UW', 'p': 'P', 'r': 'R',
          's': 'S', 'ś': 'SH', 't': 'T', 'u': 'UW', 'w': 'V', 'y': 'IH', 'z': 'Z', 'ź': 'ZH', 'ż': 'ZH', 'q': 'K', 'v': 'V', 'x': 'K S'}
VOW = set('aąeęioóuy')
def g2p(word):
    w = word.lower()
    if w in SPECIAL: return SPECIAL[w]
    out, i = [], 0
    while i < len(w):
        for g, p in MULTI:
            if w.startswith(g, i):
                # 'ci','si','zi','ni','dzi' przed samogłoską: i to tylko zmiękczenie; przed spółgłoską/na końcu: + IY
                if g.endswith('i') and not (i+len(g) < len(w) and w[i+len(g)] in VOW):
                    out.append(p + (' IY' if g != 'ni' else ' IY')); 
                else:
                    out.append(p)
                i += len(g); break
        else:
            c = w[i]
            if c == 'i' and i+1 < len(w) and w[i+1] in VOW and i > 0: out.append('Y')
            elif c in SINGLE: out.append(SINGLE[c])
            i += 1
    ph = ' '.join(out).split()
    # ubezdźwięcznienie wygłosowe
    dev = {'B': 'P', 'D': 'T', 'G': 'K', 'V': 'F', 'Z': 'S', 'ZH': 'SH', 'JH': 'CH'}
    if ph and ph[-1] in dev: ph[-1] = dev[ph[-1]]
    # ę na końcu wyrazu ~ e
    if w.endswith('ę') and ph[-2:] == ['EH', 'N']: ph = ph[:-1]
    return ' '.join(ph)
if __name__ == '__main__':
    for w in 'Poranna kawa wielki plan wkładam garnitur choć mam luźny stan piszę synergiach szczęka przyjemnością dzielę się skręca zdjęcie konferencji łaskawca dziś mgły łez wywalili wdzięczność'.split():
        print(w, '->', g2p(w))

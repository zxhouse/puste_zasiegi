"""Parsowanie tekstu (analysis/lyrics.txt) na części, wersy, słowa i sylaby.
Polskie sylaby: jądro = samogłoska (a ą e ę i o ó u y); 'i' przed samogłoską to tylko zmiękczenie."""
import re, json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V = set('aąeęioóuyAĄEĘIOÓUY')
# wymowa słów obcych / nietypowych (jak śpiewane): pisownia fonetyczna dla syntezy i liczby sylab
SPECIAL = {'linkedinie': ('linkedinie', ['lin', 'ke', 'di', 'nie']),
           'case': ('kejs', ['kejs']), 'study': ('stadi', ['sta', 'di']), 'cringe': ('krindż', ['krindż']),
           'scrollowania': ('skrolowania', ['skro', 'lo', 'wa', 'nia'])}

def syllables(word):
    w = word.lower()
    if w in SPECIAL: return SPECIAL[w][1]
    nuclei = []
    i = 0
    while i < len(w):
        c = w[i]
        if c in V:
            if c == 'i' and i+1 < len(w) and w[i+1] in V and i > 0:   # zmiękczenie: sie, nia, cie...
                i += 1; continue
            # dyftongi 'au','eu' w tym tekście nie występują jako jedna sylaba -> każda samogłoska osobno
            nuclei.append(i)
        i += 1
    if not nuclei: return []          # przyimki bez samogłoski (w, z) - doklejane do następnego słowa
    # granice: dzielimy spółgłoski między jądrami (ostatnia spółgłoska idzie do następnej sylaby)
    parts, start = [], 0
    for k in range(len(nuclei) - 1):
        a, b = nuclei[k], nuclei[k+1]
        # 'i' zmiękczające przed b należy do następnej sylaby
        bb = b - 1 if (b - 1 > a and w[b-1] == 'i') else b
        cons = bb - a - 1
        cut = a + 1 + max(cons - 1, 0) if cons > 0 else a + 1
        # dwuznaki cz sz rz ch dz dż dź nie rozrywamy
        if cut - 1 >= 0 and w[cut-1:cut+1] in ('cz', 'sz', 'rz', 'ch', 'dz', 'dż', 'dź') and cut - 1 > a: cut -= 1
        parts.append(word[start:cut]); start = cut
    parts.append(word[start:])
    return parts

def tokenize(line):
    return re.findall(r"[A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż]+", line)

def parse():
    txt = open(os.path.join(ROOT, 'analysis/lyrics.txt'), encoding='utf-8').read()
    sections, cur, voice = [], None, None
    for raw in txt.splitlines():
        s = raw.strip()
        if not s: continue
        m = re.match(r'^\[(.+)\]$', s)
        if m:
            tag = m.group(1)
            if re.match(r'(Intro|Verse|Pre-Chorus|Chorus|Bridge|Outro|Choir Interjection)', tag):
                cur = dict(name=tag, lines=[]); sections.append(cur)
                voice = 'choir' if tag.startswith('Choir') else None
            else:
                voice = tag
            continue
        spoken = s.startswith('"')
        # część w nawiasie = chórek (choir), reszta = główny wokal
        lead_txt = re.sub(r'\(.*?\)', '', s).strip()
        choir_txt = ' '.join(re.findall(r'\((.*?)\)', s))
        if cur['name'].startswith('Choir'):
            lead_txt, choir_txt = '', choir_txt or s
        line = dict(text=s, spoken=spoken, voice=voice or '', lead=lead_txt, choir=choir_txt,
                    lead_words=[dict(w=w, syl=syllables(w)) for w in tokenize(lead_txt)],
                    choir_words=[dict(w=w, syl=syllables(w)) for w in tokenize(choir_txt)])
        cur['lines'].append(line)
    return sections

if __name__ == '__main__':
    S = parse()
    json.dump(S, open(os.path.join(ROOT, 'analysis/lyrics_struct.json'), 'w'), ensure_ascii=False, indent=1)
    nl = ns = 0
    for sec in S:
        print(f"== {sec['name']}")
        for l in sec['lines']:
            sy = sum(len(w['syl']) for w in l['lead_words']); nl += 1; ns += sy
            print(f"  [{'M' if l['spoken'] else 'Ś'}] {sy:2d} syl | " + ' '.join('-'.join(w['syl']) for w in l['lead_words']) + (f"   || chór: {l['choir']}" if l['choir'] else ''))
    print('lines', nl, 'lead syllables', ns)

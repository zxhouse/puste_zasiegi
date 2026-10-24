"""Scenariusz w kodzie: role, gra aktorska przy konkretnych słowach, rekwizyty, dekoracje, kurtyna, światła, ujęcia.
Wszystkie czasy pochodzą z analizy (alignment.json / beats.json), nie z 'oka'."""
import math, numpy as np
import engine as E, stage as S, props as P, cast as C
from engine import Track, Cam, smoothstep
from roles import Role
from signs import LINES, Sign

# ------------------------------------------------------------------ czasy z dopasowania
def lt(s, l): return LINES[(s, l)]['t0']
def le(s, l): return LINES[(s, l)]['t1']
def wt(s, l, i): return LINES[(s, l)]['words'][i]['t0']
INTRO, V1, V1B, PRE1, CH1, V2, CHOIRI, V2B, PRE2, CH2, BR, CH3, OUT = range(13)
HEJ = sorted([h['t_on'] for h in E.AL['choir']['hej']])
FIN_HEJ = E.AL['choir']['finale'][0]['t_on']; FINAL_HEJ = E.AL['choir']['finale'][-1]['t_on']
REPRISE = E.AL['choir']['reprise'][0]['t_on'] if E.AL['choir']['reprise'] else 208.2
def bar_at_or_before(t): i = np.searchsorted(E.BARS, t + 0.02) - 1; return float(E.BARS[max(i, 0)])
def bar_at_or_after(t): i = np.searchsorted(E.BARS, t - 0.02); return float(E.BARS[min(i, len(E.BARS) - 1)])
def snap_bar(t, tol=0.15):
    b = float(E.BARS[np.argmin(np.abs(E.BARS - t))]); return b if abs(b - t) <= tol else t
def hit_bars(a, b):
    """'Raz' taktów w [a,b] dociągnięte do najbliższego prawdziwego uderzenia stopy (±80 ms), jeśli jest."""
    out = []
    for bb in E.BARS[(E.BARS > a) & (E.BARS < b)]:
        k = E.KICK[np.argmin(np.abs(E.KICK - bb))] if len(E.KICK) else bb
        out.append(float(k) if abs(k - bb) < 0.08 else float(bb))
    return out
def snares_between(a, b): return [s for s in E.SNARE if a <= s <= b]
def kicks_between(a, b): return [s for s in E.KICK if a <= s <= b]

# ------------------------------------------------------------------ gesty (relatywnie do wymiarów lalki)
def G(ch, name):
    w1, h, hy, hw, hh = ch.torso_w[1], ch.torso_h, ch.head_y, ch.head_w, ch.head_h
    g = {'rest': ((-(w1 + 30), -20), ((w1 + 30), -20)),
         'hips': ((-(w1 - 5), -h*0.5), ((w1 - 5), -h*0.5)),
         'up': ((-(w1 + 70), hy - 130), ((w1 + 70), hy - 130)),
         'wide': ((-(w1 + 175), hy + 30), ((w1 + 175), hy + 30)),
         'shrug': ((-(w1 + 95), -h*0.72), ((w1 + 95), -h*0.72)),
         'type': ((-w1*0.55, -34), (w1*0.55, -34)),
         'present_L': ((-(w1 + 190), hy + 70), ((w1 + 30), -20)),
         'present_R': ((-(w1 + 30), -20), ((w1 + 190), hy + 70)),
         'jaw': ((-(w1 + 30), -20), (hw*0.92, hy + hh*0.62)),
         'forehead': ((-(w1 + 30), -20), (hw*0.58, hy - hh*0.85)),
         'chin': ((-(w1 - 10), -h*0.42), (hw*0.28, hy + hh*1.05)),
         'chest': ((-(w1 + 30), -20), (w1*0.18, -h*0.62)),
         'facepalm': ((-(w1 + 30), -20), (hw*0.15, hy - hh*0.1)),
         'hold_R': ((-(w1 + 30), -20), ((w1 + 60), -h*0.62)),
         'hold_L': ((-(w1 + 60), -h*0.62), ((w1 + 30), -20)),
         'holdup_R': ((-(w1 + 30), -20), ((w1 + 95), hy + 10)),
         'holdup_L': ((-(w1 + 95), hy + 10), ((w1 + 30), -20)),
         'sip': ((-(w1 + 30), -20), (hw*0.38, hy + hh*0.75)),
         'mug': ((-(w1 + 30), -20), ((w1 - 20), -h*0.68)),
         'push_down': ((-(w1 + 30), -20), ((w1 + 120), -h*0.25)),
         'bow': ((-(w1 + 10), -h*0.3), ((w1 + 10), -h*0.3)),
         'phone': ((-w1*0.35, -h*0.85), (w1*0.5, -h*0.7)),
         'write': ((-(w1 + 30), -20), ((w1 + 70), -h*0.95)),
         }[name]
    return g
def gest(role, t, name, **kw):
    L, R = G(role.ch, name); role.key(t, hL=L, hR=R, **kw); return role
def gest_hold(role, t0, t1, name, **kw):
    gest(role, t0, name, **kw); gest(role, t1, name, **kw); return role

# ================================================================== OBSADA
HENIO = Role(C.HENIO, 'lead')
GRAZ = Role(C.GRAZYNA); PREZ = Role(C.PREZES); TADEK = Role(C.TADEK); MIREK = Role(C.MIREK); KASIA = Role(C.KASIA)
CHOIR = [Role(C.CHOIR[i], 'choir', member=i, base=dict(scale=0.8)) for i in range(8)]
ROLES = [HENIO, GRAZ, PREZ, TADEK, MIREK, KASIA] + CHOIR

D_APRON_ACT = -95.0          # lalki przed kurtyną (na przedscenie)
CHOIR_X = [-720, -320, 320, 720, -920, -520, 520, 920]
MEN = [0, 1, 2, 3]; WOMEN = [4, 5, 6, 7]       # lalki 0-3 to panowie (krawaty) na ±320, ±720; panie 4-7 dochodzą na ±520, ±920
CHOIR_Y, CHOIR_D = -400.0, 140.0

# ------------------------------------------------------------------ HENIO
H = HENIO
H.costume(0, jacket='#7fa3c6', lapels=False, tie=None, shirt='#f1efe8', buttons=None)      # piżama/sweter rano
H.costume(18.85, jacket='#6f7480', lapels=True, tie='#c0392b', buttons='#2f3238')           # garnitur zjechał z góry
H.costume(149.2, tie=None)                                                                   # bridge: zdejmuje krawat
# intro na przedscenie
H.on(3.0, 10.35, 'rise', 'sink', 0.6, 0.45)
H.key(0, x=0.0, depth=D_APRON_ACT)
gest(H, 3.3, 'phone', gaze=(0.0, 0.1), brow=0.3, lid=0.3)
H.hold(3.0, 10.8, 'R', lambda cv, t: P.phone(cv))
gest(H, wt(INTRO, 0, 7), 'phone', gaze=(-0.3, 0.6))             # 'dzisiaj' - zerka w telefon
gest(H, wt(INTRO, 0, 8), 'present_L', gaze=(0.0, 0.0), brow=0.6)  # 'kochani' - do widzów
gest(H, wt(INTRO, 0, 9), 'shrug', brow=0.9, lid=0.15)             # 'Kolejny sukces?'
gest(H, wt(INTRO, 0, 11) - 0.2, 'phone', gaze=(0.2, 0.7), brow=0.2, lid=0.3)   # 'Zobaczmy...' - przesuwa palcem
# kuchnia: wynurza się z kubkiem kawy
H.on(13.0, lt(PRE1, 0), 'rise', 'none', 0.65)
H.key(12.4, x=-80.0, depth=0.0)
H.hold(12.4, 17.4, 'R', lambda cv, t: P.mug(cv, '#e05d5d', 1.0, t))
gest(H, 13.0, 'mug', gaze=(0.3, 0.2), lid=0.55, brow=-0.1)
gest(H, wt(V1, 0, 1) - 0.15, 'sip', gaze=(0.0, 0.5), lid=0.7)      # 'kawa' - łyk
gest(H, wt(V1, 0, 2) - 0.1, 'mug', gaze=(-0.8, -0.1), lid=0.25, turn=-0.4)  # 'wielki plan' - na sztalugę
H.key(wt(V1, 0, 2), hL=(-330.0, -260.0))
H.key(wt(V1, 0, 3) + 0.4, hL=(-320.0, -250.0), turn=-0.3)
# 'Wkładam garnitur' - marynarka zjeżdża, Henio się wciska
gest(H, lt(V1, 1), 'up', gaze=(0.0, -0.8), turn=0.0, lid=0.2, brow=0.6)
gest(H, wt(V1, 1, 2), 'hips', gaze=(0.2, 0.2), lid=0.3, brow=-0.2)
gest(H, wt(V1, 1, 4), 'shrug', gaze=(0.0, 0.1), lean=-6.0)   # 'luźny stan'
H.key(wt(V1, 1, 5), lean=6.0); H.key(le(V1, 1), lean=0.0)
# 'Piszę o synergiach' - laptop
gest(H, lt(V1, 2) - 0.1, 'type', gaze=(0.0, 0.9), lid=0.45, brow=0.0)
gest(H, wt(V1, 2, 6) - 0.15, 'jaw', gaze=(0.3, 0.3), brow=-0.8, lid=0.5)   # 'szczęka'
# 'Z przyjemnością dzielę się' - plansza-post + wyuczony uśmiech, potem 'skręca'
gest(H, lt(V1, 3), 'holdup_R', smile=1.0, gaze=(0.0, 0.0), brow=0.8, lid=0.1)
H.hold(lt(V1, 3) - 0.1, wt(V1, 3, 4) + 0.3, 'R', lambda cv, t: P.linkedin_card(cv, 'Z przyjemnością dzielę się…', 470, 210, side=1))
gest(H, wt(V1, 3, 4), 'facepalm', smile=0.0, brow=-0.6, lid=0.6, lean=-10.0, turn=-0.5)
H.key(wt(V1, 3, 6), lean=12.0, turn=0.5); H.key(wt(V1, 3, 7) + 0.3, lean=-8.0, turn=-0.3)
gest(H, le(V1, 3) + 0.2, 'hips', lean=0.0, turn=0.0, brow=0.0, lid=0.35)
gest(H, 29.5, 'rest', gaze=(0.0, 0.2))
# biuro (30.4-39.3)
H.key(30.6, x=-80.0); H.key(31.6, x=0.0)
gest(H, lt(V1B, 0), 'hips', gaze=(-0.4, -0.5), brow=0.5, lid=0.2)   # 'w tle awans' - zerka w górę na baner
gest(H, wt(V1B, 0, 4), 'facepalm', gaze=(0.0, 0.3), brow=-0.7, lid=0.55)   # 'w głowie stres'
gest(H, lt(V1B, 1), 'chin', gaze=(0.5, 0.0), brow=0.2, lid=0.35, smile=0.0)   # 'strategiczny gest'
gest(H, wt(V1B, 1, 4) + 0.3, 'present_R', gaze=(0.8, 0.0))
# konferencja: z boku
H.key(lt(V1B, 2) - 0.01, x=0.0); H.key(lt(V1B, 2), x=-780.0)
gest(H, lt(V1B, 2), 'hips', gaze=(0.9, 0.0), turn=0.45, lid=0.5, brow=-0.2)
gest(H, wt(V1B, 2, 3), 'present_R', gaze=(0.9, -0.1), brow=0.5)    # 'mina jak z plakatu'
gest(H, lt(V1B, 3), 'chin', gaze=(1.0, 0.1), lid=0.55, brow=-0.4)
gest(H, wt(V1B, 3, 7), 'facepalm', lid=0.7, brow=-0.6)               # 'łaskawca'
# show: przedrefren 1
H.on(lt(PRE1, 0) + 0.57, 69.9, 'rise', 'none', 0.57)
H.key(lt(PRE1, 0) - 0.01, x=-780.0); H.key(lt(PRE1, 0), x=0.0)
gest(H, lt(PRE1, 0), 'present_L', turn=0.0, gaze=(-0.6, -0.3), lid=0.3, brow=0.3)
gest(H, wt(PRE1, 0, 5), 'present_R', gaze=(0.6, -0.3))
gest(H, lt(PRE1, 1), 'hips', smile=1.0, gaze=(0.0, 0.0), brow=0.8, lid=0.05)      # 'uśmiech wyuczony'
gest(H, wt(PRE1, 1, 2) - 0.1, 'forehead', smile=1.0)                                # 'rzut na czoło'
gest(H, lt(PRE1, 2), 'hips', smile=0.0, brow=-0.3, lid=0.4, gaze=(-0.4, 0.1))
H.key(wt(PRE1, 2, 2), gaze=(0.6, 0.1)); H.key(wt(PRE1, 2, 3), gaze=(-0.6, 0.1))     # 'za dużo' - rozgląda się
gest(H, lt(PRE1, 3), 'shrug', gaze=(0.0, 0.0), brow=0.5, lid=0.2)
gest(H, wt(PRE1, 3, 5) - 0.1, 'wide', brow=1.0, lid=0.0, smile=0.6)                # 'wielki gest'
# refren 1
gest(H, lt(CH1, 0), 'wide', smile=0.3, brow=0.6, lid=0.1)
gest(H, wt(CH1, 0, 2), 'present_L', smile=0.2); gest(H, wt(CH1, 0, 3), 'present_R')
gest(H, lt(CH1, 1), 'up', brow=0.8)                                                  # 'błyszczy'
gest(H, wt(CH1, 1, 5), 'shrug', brow=-0.5, lid=0.4)                                  # 'pęka'
gest(H, lt(CH1, 2), 'present_L', brow=0.4, lid=0.2); gest(H, wt(CH1, 2, 2), 'wide')
gest(H, lt(CH1, 3), 'rest', brow=-0.3, lid=0.5, gaze=(0.0, 0.8))                   # 'pod spodem cisza'
H.on(73.0, lt(V2, 0), 'rise', 'none', 0.5)
gest(H, lt(CH1, 4), 'up', brow=1.0, lid=0.0, gaze=(0.0, -0.2))
gest(H, lt(CH1, 5), 'wide', brow=0.8); gest(H, 78.4, 'up')
# studio Grażyny: zagląda z boku
H.on(83.0, lt(CHOIRI, 0), 'left', 'none', 0.7)
H.key(lt(V2, 1) - 0.01, x=0.0); H.key(lt(V2, 1), x=-830.0)
gest(H, lt(V2, 1), 'chin', gaze=(1.0, 0.0), turn=0.5, lid=0.5, brow=0.2)
gest(H, wt(V2, 1, 3), 'facepalm', brow=-0.8, lid=0.65, lean=-8.0)                 # 'brzmi jak cringe'
H.key(wt(V2, 1, 5), lean=10.0, turn=-0.4); H.key(le(V2, 1), lean=0.0, turn=0.5)
gest(H, lt(V2, 2), 'present_R', gaze=(1.0, -0.3), lid=0.3, brow=0.4)                # 'pięć scenek'
gest(H, wt(V2, 2, 7), 'shrug', gaze=(0.6, 0.0), brow=0.9)                          # 'długi wywód'
# droga: Henio czyta (bez tchu)
H.key(lt(V2, 3) - 0.01, x=-830.0); H.key(lt(V2, 3), x=-760.0)
gest(H, lt(V2, 3), 'hold_L', gaze=(0.0, 0.6), lid=0.35, turn=0.2)
H.hold(lt(V2, 3), le(V2, 4), 'L', lambda cv, t: P.phone(cv))
gest(H, wt(V2, 3, 5), 'chest', gaze=(0.0, 0.6), brow=0.6, lid=0.1)              # 'czytam bez tchu'
gest(H, lt(V2, 4), 'hold_L', gaze=(0.9, 0.0), brow=-0.2)
gest(H, wt(V2, 4, 5) - 0.1, 'present_R', gaze=(0.9, 0.2), brow=0.9, lid=0.0)       # 'wywalili cię na bruk!'
gest(H, 98.4, 'rest', brow=0.0)
# raj korporacyjny: na chmurce z boku
H.on(lt(V2B, 0) + 0.43, lt(PRE2, 0), 'rise', 'none', 0.43)
H.key(lt(V2B, 0) - 0.01, x=-760.0); H.key(lt(V2B, 0), x=-880.0, y=-40.0)
gest(H, lt(V2B, 0), 'present_R', gaze=(0.9, 0.0), turn=0.4, lid=0.4)
gest(H, lt(V2B, 1), 'shrug', gaze=(0.9, -0.1), brow=0.5)
gest(H, lt(V2B, 2), 'chin', gaze=(1.0, 0.0), lid=0.55)
gest(H, lt(V2B, 3), 'up', gaze=(0.6, -0.8), brow=0.9, lid=0.0)                      # 'świętym'
# studio w drewnie
H.on(lt(PRE2, 0) + 0.56, 147.6, 'rise', 'sink', 0.56, 0.4)
H.key(lt(PRE2, 0) - 0.01, x=-880.0, y=-40.0); H.key(lt(PRE2, 0), x=0.0, y=0.0)
gest(H, lt(PRE2, 0), 'present_L', gaze=(-0.6, -0.3), lid=0.3, turn=0.0)
gest(H, wt(PRE2, 0, 5), 'present_R', gaze=(0.6, -0.3))
gest(H, lt(PRE2, 1), 'hips', smile=1.0, brow=0.8, lid=0.05, gaze=(0.0, 0.0))
gest(H, wt(PRE2, 1, 2) - 0.1, 'present_L', smile=1.0, gaze=(-0.9, -0.2))           # 'studio w drewnie'
gest(H, lt(PRE2, 2), 'hips', smile=0.0, brow=-0.3, lid=0.4, gaze=(-0.4, 0.1))
H.key(wt(PRE2, 2, 2), gaze=(0.6, 0.1)); H.key(wt(PRE2, 2, 3), gaze=(-0.6, 0.1))
gest(H, lt(PRE2, 3), 'shrug', gaze=(0.0, 0.0), brow=0.5, lid=0.2)
gest(H, wt(PRE2, 3, 5) - 0.1, 'wide', brow=1.0, lid=0.0, smile=0.6)
# refren 2
gest(H, lt(CH2, 0), 'wide', smile=0.3, brow=0.6, lid=0.1)
gest(H, lt(CH2, 1), 'up', brow=0.8); gest(H, wt(CH2, 1, 5), 'shrug', brow=-0.5, lid=0.4)
gest(H, lt(CH2, 2), 'present_R', brow=0.4); gest(H, wt(CH2, 2, 2), 'wide')
gest(H, lt(CH2, 3), 'rest', brow=-0.3, lid=0.5, gaze=(0.0, 0.7))
gest(H, lt(CH2, 4), 'up', brow=1.0, lid=0.0); gest(H, lt(CH2, 5), 'wide', brow=0.8)
# bridge: przed kurtyną, jeden reflektor
H.on(148.3, 164.3, 'rise', 'sink', 0.5, 0.45)
H.key(148.0, x=0.0, depth=D_APRON_ACT)
gest(H, 148.4, 'rest', smile=0.0, brow=0.0, lid=0.45, gaze=(0.0, 0.2), jitter=0.6)
gest(H, wt(BR, 0, 2) - 0.1, 'jaw', gaze=(0.0, 0.0), lid=0.4)                       # 'szczerze' - luzuje krawat
H.key(wt(BR, 0, 2) + 0.4, hR=(70.0, -175.0))
gest(H, lt(BR, 1), 'write', gaze=(0.6, -0.1), lid=0.3, turn=0.3)                    # 'napisać prosto'
gest(H, lt(BR, 2), 'hips', gaze=(0.0, -0.7), lid=0.2, turn=0.0, brow=0.3)           # ozdoby opadają
gest(H, wt(BR, 2, 5), 'rest', gaze=(0.0, 0.0), brow=0.0)
gest(H, lt(BR, 3), 'present_R', gaze=(0.6, -0.1), lid=0.25, smile=0.25)             # pokazuje 'Robię swoje.'
gest(H, wt(BR, 3, 6), 'chest', gaze=(0.0, 0.0), smile=0.35)
gest(H, lt(BR, 4), 'rest', gaze=(0.4, 0.4), smile=0.0)
gest(H, wt(BR, 4, 3) - 0.25, 'push_down', gaze=(0.7, 0.6), brow=-0.2)              # 'fanfar' - spycha trąbkę
gest(H, wt(BR, 4, 4) + 0.1, 'rest', gaze=(0.0, 0.2))
gest(H, wt(BR, 4, 5) - 0.25, 'push_down', gaze=(0.7, 0.6))                         # 'łez' - spycha łzę
gest(H, le(BR, 4) + 0.2, 'rest', gaze=(0.0, 0.0), smile=0.3, jitter=1.0)
# refren 3 (zespół)
H.on(166.9, 202.5, 'rise', 'sink', 0.6, 0.5)
H.key(166.0, x=0.0, depth=0.0)
gest(H, lt(CH3, 0), 'wide', smile=0.4, brow=0.6, lid=0.1)
gest(H, lt(CH3, 1), 'up', brow=0.8); gest(H, wt(CH3, 1, 5), 'present_L', brow=0.3)
gest(H, lt(CH3, 2), 'present_R', gaze=(-0.7, 0.0), turn=-0.3)                       # do Tadka
gest(H, lt(CH3, 3), 'chest', brow=-0.1, lid=0.4, gaze=(-0.5, 0.2), turn=-0.2, smile=0.2)
gest(H, lt(CH3, 4), 'up', brow=1.0, lid=0.0, turn=0.0)
gest(H, lt(CH3, 5), 'wide', brow=0.8)
# outro: ukłon do kamery
gest(H, lt(OUT, 0) - 0.2, 'bow', gaze=(0.0, 0.0), lean=0.0, smile=0.2, lid=0.3)
H.key(wt(OUT, 0, 1), lean=0.0); H.key(wt(OUT, 0, 2), tilt=14.0); H.key(wt(OUT, 0, 2) + 0.5, tilt=0.0)
gest(H, wt(OUT, 0, 3), 'present_R', gaze=(0.4, 0.4))                                # 'miłego scrollowania'
gest(H, 194.2, 'wide', smile=0.4, brow=0.8); gest(H, FIN_HEJ - 0.1, 'up', brow=1.0)
H.on(bar_at_or_before(REPRISE) + 0.35, 212.5, 'rise', 'none', 0.35)
gest(H, REPRISE, 'wide', smile=0.6, brow=0.9); gest(H, FINAL_HEJ - 0.08, 'up', brow=1.0, lid=0.0)

# ------------------------------------------------------------------ GRAŻYNA
g = GRAZ
g.on(lt(V1B, 2) + 0.4, 46.2, 'rise', 'sink', 0.4, 0.45)            # konferencja: pozuje do zdjęcia
g.key(0, x=-170.0, depth=0.0)
gest(g, lt(V1B, 2), 'holdup_L', smile=1.0, gaze=(0.0, 0.0), brow=0.9, lid=0.0, turn=0.25)
gest(g, wt(V1B, 2, 3), 'hips', smile=1.0, turn=0.3)
gest(g, lt(V1B, 3), 'hips', smile=0.6, gaze=(0.8, 0.0), turn=0.3)
g.on(lt(V2, 1) - 0.4, lt(V2, 3), 'rise', 'none', 0.5, 0.45)                # jej studio
g.key(lt(V2, 1) - 1.0, x=120.0)
g.hold(lt(V2, 1) - 0.4, le(V2, 1) + 0.2, 'L', lambda cv, t: P.linkedin_card(cv, 'Z pokorą informuję…', 450, 200, 'Grażyna Gratka', side=-1))
gest(g, lt(V2, 1) - 0.4, 'holdup_L', smile=1.0, brow=0.7, lid=0.2, gaze=(-0.2, -0.2))
gest(g, wt(V2, 1, 3), 'holdup_L', smile=1.0, lid=0.5, gaze=(0.3, -0.6))          # 'z pokorą' - przymknięte oczy
gest(g, lt(V2, 2), 'present_L', smile=1.0, gaze=(-0.4, -0.6), brow=0.6)          # pokazuje kadry 'scenek'
for i in range(5): g.key(wt(V2, 2, 2) + i*0.41, hL=(-300.0 + i*30, -360.0 - 30*(i % 2)))
gest(g, wt(V2, 2, 7), 'wide', smile=1.0, brow=0.9)                               # 'długi wywód'
g.on(lt(V2B, 2) - 0.5, 115.0, 'rise', 'sink', 0.5, 0.5)               # raj: wdzięczność, aureola
g.key(lt(V2B, 2) - 1.0, x=600.0, y=-30.0)
g.hold(lt(V2B, 2) - 0.5, le(V2B, 3), 'R', lambda cv, t: P.scroll(cv, min(520, max(60, (t - lt(V2B, 2) + 0.3)*260))))
gest(g, lt(V2B, 2) - 0.5, 'hold_R', smile=0.8, gaze=(0.2, 0.6), brow=0.6)
gest(g, wt(V2B, 2, 2), 'hold_R', gaze=(0.6, 0.3), smile=1.0)
gest(g, lt(V2B, 3), 'hold_R', gaze=(0.0, -0.9), smile=1.0, brow=1.0, lid=0.0)
g.on(166.9, 202.5, 'rise', 'sink', 0.6, 0.5)                          # refren 3 i finał
g.key(166.0, x=-610.0, y=0.0)
gest(g, 167.0, 'up', smile=0.8, brow=0.7); gest(g, lt(CH3, 2), 'wide', smile=0.5); gest(g, lt(CH3, 3), 'rest', smile=0.0, lid=0.4)
gest(g, lt(CH3, 4), 'up', smile=0.7); gest(g, 194.2, 'wide'); gest(g, FIN_HEJ - 0.1, 'up')
g.on(bar_at_or_before(REPRISE) + 0.4, 212.5, 'rise', 'none', 0.35); gest(g, REPRISE, 'wide', smile=0.8); gest(g, FINAL_HEJ - 0.08, 'up')

# ------------------------------------------------------------------ PREZES
p = PREZ
p.on(lt(V1B, 2) + 0.55, 46.2, 'rise', 'sink', 0.5, 0.45)
p.key(0, x=240.0, depth=0.0)
gest(p, lt(V1B, 2) + 0.2, 'holdup_R', smile=1.0, brow=0.6, lid=0.25, turn=-0.25)
gest(p, wt(V1B, 2, 3), 'hips', smile=1.0, turn=-0.3)
gest(p, lt(V1B, 3), 'hips', smile=0.5, gaze=(0.7, 0.0), turn=0.2, lid=0.4)
gest(p, wt(V1B, 3, 4), 'chest', smile=0.9, lid=0.55, gaze=(0.9, 0.1))            # przyjmuje 'szacun' z łaskawością
p.key(wt(V1B, 3, 7), tilt=-12.0); p.key(wt(V1B, 3, 7) + 0.5, tilt=0.0)
p.on(lt(V2, 4) - 0.3, 99.2, 'right', 'sink', 0.6, 0.45)               # stempel 'restrukturyzacja'
p.key(lt(V2, 4) - 1.0, x=640.0)
p.hold(lt(V2, 4) - 0.3, 99.0, 'R', lambda cv, t: P.stamp(cv))
gest(p, lt(V2, 4), 'hold_R', gaze=(-0.8, 0.2), turn=-0.5, brow=-0.6, lid=0.4)
gest(p, wt(V2, 4, 5), 'holdup_R', gaze=(-0.8, 0.4), brow=-0.8)
gest(p, wt(V2, 4, 8) - 0.12, 'hold_R', gaze=(-0.8, 0.6))                         # 'bruk' - stempel w dół
p.on(166.9, 202.5, 'rise', 'sink', 0.6, 0.5)
p.key(166.0, x=600.0)
gest(p, 167.0, 'wide', smile=0.8, turn=0.0, lid=0.25, brow=0.4); gest(p, lt(CH3, 3), 'chest', smile=0.0, lid=0.5)
gest(p, lt(CH3, 4), 'up', smile=0.8); gest(p, FIN_HEJ - 0.1, 'up')
p.on(bar_at_or_before(REPRISE) + 0.4, 212.5, 'rise', 'none', 0.35); gest(p, REPRISE, 'wide', smile=0.8); gest(p, FINAL_HEJ - 0.08, 'up')

# ------------------------------------------------------------------ TADEK
td = TADEK
td.on(lt(V2, 3) + 0.5, wt(V2, 4, 8) + 0.05, 'rise', 'sink', 0.5, 0.35)   # 'nowa droga' -> na bruk (zjeżdża w dół)
td.key(0, x=180.0, depth=0.0)
td.hold(lt(V2, 3) - 0.3, 97.2, 'L', lambda cv, t: P.box_of_stuff(cv))
td.hold(lt(V2, 3) - 0.3, 97.2, 'R', lambda cv, t: P.placard(cv, 'Cieszę się z nowej drogi! :)', size=36, side=1))
gest(td, lt(V2, 3) - 0.3, 'hold_L', smile=1.0, brow=0.9, lid=0.0, gaze=(0.0, 0.0))
td.key(lt(V2, 3) - 0.3, hR=(230.0, -330.0))
td.key(lt(V2, 4), smile=0.6, gaze=(0.6, 0.0), brow=0.3)
td.key(wt(V2, 4, 5), smile=0.0, gaze=(0.8, -0.4), brow=-0.8, lid=0.0)             # 'wywalili' - widzi stempel
td.on(166.9, 202.5, 'rise', 'sink', 0.6, 0.5)
td.key(166.0, x=-300.0)
gest(td, 167.0, 'up', smile=0.8, brow=0.6, lid=0.1); gest(td, lt(CH3, 2), 'present_R', gaze=(0.8, 0.0), turn=0.3, smile=0.6)
gest(td, lt(CH3, 3), 'chest', gaze=(0.7, 0.1), turn=0.2, smile=0.3); gest(td, lt(CH3, 4), 'up', turn=0.0); gest(td, FIN_HEJ - 0.1, 'up')
td.on(bar_at_or_before(REPRISE) + 0.4, 212.5, 'rise', 'none', 0.35); gest(td, REPRISE, 'wide', smile=0.8); gest(td, FINAL_HEJ - 0.08, 'up')

# ------------------------------------------------------------------ MIREK ('Ogromny szacun!')
m = MIREK
m.on(wt(V1B, 3, 3) - 0.35, 46.3, 'rise', 'sink', 0.3, 0.35)
m.key(0, x=640.0, depth=-10.0)
m.hold(wt(V1B, 3, 3) - 0.35, 46.3, 'R', lambda cv, t: P.placard(cv, 'Ogromny szacun!', size=40, color='#ffffff', ink='#0a66c2', side=-1))
gest(m, wt(V1B, 3, 3) - 0.35, 'holdup_R', smile=1.0, brow=1.0, gaze=(-0.9, 0.0), turn=-0.6, lid=0.0)
m.key(wt(V1B, 3, 3) - 0.35, mouth_extra=0.0)
for k, tk in enumerate(snares_between(wt(V1B, 3, 3), 46.0)):
    m.key(tk - 0.05, hR=(150.0, -260.0)); m.key(tk + 0.12, hR=(150.0, -300.0))
m.on(166.9, 202.5, 'rise', 'sink', 0.6, 0.5)
m.key(166.0, x=280.0, depth=0.0)
gest(m, 167.0, 'up', smile=1.0); gest(m, FIN_HEJ - 0.1, 'up')
m.on(bar_at_or_before(REPRISE) + 0.4, 212.5, 'rise', 'none', 0.35); gest(m, FINAL_HEJ - 0.08, 'up')

# ------------------------------------------------------------------ KASIA ('case study')
k_ = KASIA
k_.on(lt(V2B, 0) + 0.45, 115.0, 'rise', 'sink', 0.45, 0.5)
k_.key(0, x=-400.0, depth=0.0, y=-30.0)
gest(k_, lt(V2B, 0) - 0.4, 'present_L', smile=1.0, brow=0.8, gaze=(-0.7, -0.2), turn=-0.3, lid=0.1)
gest(k_, wt(V2B, 0, 4), 'present_L', gaze=(0.0, 0.0), turn=0.0)
gest(k_, lt(V2B, 1), 'hips', smile=0.6, gaze=(0.8, 0.0)); gest(k_, lt(V2B, 3), 'up', gaze=(0.6, -0.8), smile=1.0)
k_.on(166.9, 202.5, 'rise', 'sink', 0.6, 0.5)
k_.key(166.0, x=-900.0, y=0.0)
gest(k_, 167.0, 'up', smile=0.8); gest(k_, lt(CH3, 3), 'rest', smile=0.0); gest(k_, lt(CH3, 4), 'up'); gest(k_, FIN_HEJ - 0.1, 'up')
k_.on(bar_at_or_before(REPRISE) + 0.4, 212.5, 'rise', 'none', 0.35); gest(k_, FINAL_HEJ - 0.08, 'up')

# ------------------------------------------------------------------ CHÓR (8): 4 panów od przedrefrenu 1, panie od refrenu 1
REACT = ['like', 'heart', 'clap', 'idea', 'like', 'support', 'heart', 'laugh']
for i, r in enumerate(CHOIR):
    r.key(0, x=float(CHOIR_X[i]), y=CHOIR_Y, depth=CHOIR_D)
    turn_in = 0.25 if CHOIR_X[i] < 0 else -0.25
    r.key(0, turn=turn_in)
    if i in MEN:
        # biuro: zza ścianek boksów (patrz set office)
        ox = {0: -820.0, 1: -330.0, 2: 330.0, 3: 820.0}[i]
        r.on(30.9 + 0.12*MEN.index(i), lt(V1B, 2), 'rise', 'none', 0.45)
        r.key(30.0, x=ox, y=-230.0, depth=175.0); r.key(39.24, x=ox, y=-230.0, depth=175.0)
        gest(r, 31.0, 'rest', gaze=(0.0, 0.2))
        gest(r, wt(V1B, 1, 3) - 0.2, 'chin', gaze=(0.6 if ox < 0 else -0.6, -0.2), brow=0.6, lid=0.3)   # 'strategiczny gest'
        gest(r, le(V1B, 1) + 0.3, 'rest', brow=0.0, lid=0.2)
        # przedrefren 1 -> refren 1
        r.on(lt(PRE1, 0) + 0.5 + 0.15*MEN.index(i), lt(V2, 0), 'rise', 'none', 0.5)
        r.key(lt(PRE1, 0), x=float(CHOIR_X[i]), y=CHOIR_Y, depth=CHOIR_D, scale=0.8)
    else:
        r.on(59.45 + 0.1*WOMEN.index(i), lt(V2, 0), 'rise', 'none', 0.45)
    start = lt(PRE1, 0) if i in MEN else 59.4
    gest(r, start, 'rest', gaze=(0.0, 0.0))
    if i in MEN:
        gest(r, lt(PRE1, 1), 'rest', smile=1.0, brow=0.8, lid=0.0)
        r.hold(lt(PRE1, 1) - 0.2, le(PRE1, 1) + 0.2, 'L', lambda cv, t: P.smile_mask(cv, 0.0))
        gest(r, lt(PRE1, 1), 'hold_L', smile=1.0)
        gest(r, wt(PRE1, 1, 2) - 0.1, 'forehead', smile=1.0)                     # 'rzut na czoło' - wszyscy naraz
        gest(r, lt(PRE1, 2), 'rest', smile=0.0, gaze=(-1.0 if CHOIR_X[i] > 0 else 1.0, 0.3), brow=-0.4)   # patrzą na Henia
        gest(r, lt(PRE1, 3), 'rest', gaze=(0.0, 0.0), brow=0.3)
    # refren 1: reakcje na patykach w górę na mocnych bitach
    r.hold(59.6, 79.3, 'R', lambda cv, t, kind=REACT[i]: P.reaction_paddle(cv, kind, 0.85))
    gest(r, 59.7, 'hold_R', brow=0.6, lid=0.1)
    for b in hit_bars(60.0, 69.5):
        r.key(b - 0.06, hR=(110.0, -150.0)); r.key(b + 0.2, hR=(120.0, -330.0)); r.key(b + 0.65, hR=(110.0, -170.0))
    gest(r, lt(CH1, 3), 'rest', brow=-0.2, lid=0.4)
    for hj in [h for h in HEJ if 72 < h < 80]:
        gest(r, hj - 0.12, 'up', brow=1.0, lid=0.0); gest(r, hj + 0.5, 'hold_R')
    # wtrącenie 'Wywalili na bruk!' (cały chór na drodze, z kostkami bruku)
    r.on(lt(CHOIRI, 0) - 0.35, lt(V2B, 0) - 0.47, 'rise', 'sink', 0.3, 0.45)
    r.key(lt(CHOIRI, 0) - 0.4, x=float(CHOIR_X[i])*1.05, y=-40.0, depth=40.0, scale=0.95)
    r.hold(lt(CHOIRI, 0) - 0.4, le(CHOIRI, 0) + 0.8, 'R', lambda cv, t, k=i: P.cobble(cv, k))
    gest(r, lt(CHOIRI, 0) - 0.35, 'holdup_R', brow=-0.9, lid=0.0, gaze=(0.0, 0.0), turn=0.0)
    r.key(le(CHOIRI, 0) + 0.31, x=float(CHOIR_X[i])*1.05, y=-40.0, depth=40.0, scale=0.95)
    if i == 2:
        r.on(lt(V2B, 1) - 0.45, 115.0, 'rise', 'sink', 0.45, 0.5)
        r.key(lt(V2B, 1) - 0.5, x=150.0, y=-30.0, depth=0.0, scale=1.05)
        r.key(114.99, x=150.0, y=-30.0, depth=0.0, scale=1.05)
        r.hold(lt(V2B, 1) - 0.45, 115.0, 'L', lambda cv, t: P.price_tag(cv))
        gest(r, lt(V2B, 1) - 0.45, 'hold_L', smile=1.0, brow=0.8, lid=0.0, gaze=(0.0, 0.0), turn=0.0)
        gest(r, wt(V2B, 1, 3), 'holdup_R', smile=1.0, gaze=(0.3, -0.7))
        gest(r, lt(V2B, 2), 'hold_L', smile=0.6, gaze=(0.8, 0.0))
        gest(r, lt(V2B, 3), 'up', smile=1.0, gaze=(0.5, -0.8))
    # przedrefren 2 (panowie) + refren 2 (wszyscy) w studiu w drewnie -> show
    if i in MEN:
        r.on(lt(PRE2, 0) + 0.5 + 0.15*MEN.index(i), 148.95, 'rise', 'none', 0.5)
        r.key(lt(PRE2, 0) - 0.5, x=float(CHOIR_X[i]), y=CHOIR_Y, depth=CHOIR_D, scale=0.8)
        gest(r, lt(PRE2, 0), 'rest', gaze=(0.0, 0.0), brow=0.0, smile=0.0, turn=turn_in)
        r.hold(lt(PRE2, 1) - 0.2, le(CH2, 1), 'L', lambda cv, t: P.smile_mask(cv, smoothstep((t - wt(CH2, 1, 5) + 0.05)/0.3)))
        gest(r, lt(PRE2, 1), 'hold_L', smile=1.0, brow=0.8, lid=0.0)
        gest(r, wt(PRE2, 1, 2) - 0.1, 'hold_L', smile=1.0, gaze=(-0.8, 0.0))
        gest(r, lt(PRE2, 2), 'hold_L', smile=0.0, gaze=(-1.0 if CHOIR_X[i] > 0 else 1.0, 0.3), brow=-0.4)
        gest(r, lt(PRE2, 3), 'hold_L', gaze=(0.0, 0.0), brow=0.3)
    else:
        r.on(127.7 + 0.1*WOMEN.index(i), 148.95, 'rise', 'none', 0.45)
        r.key(127.0, x=float(CHOIR_X[i]), y=CHOIR_Y, depth=CHOIR_D, scale=0.8)
    r.hold(128.0, 147.9, 'R', lambda cv, t, kind=REACT[i]: P.reaction_paddle(cv, kind, 0.85))
    gest(r, 128.1, 'hold_R', brow=0.6, lid=0.1, turn=turn_in)
    for b in hit_bars(128.3, 138.0):
        r.key(b - 0.06, hR=(110.0, -150.0)); r.key(b + 0.2, hR=(120.0, -330.0)); r.key(b + 0.65, hR=(110.0, -170.0))
    gest(r, lt(CH2, 3), 'rest', brow=-0.2, lid=0.4)
    for hj in [h for h in HEJ if 140 < h < 148]:
        gest(r, hj - 0.12, 'up', brow=1.0, lid=0.0); gest(r, hj + 0.5, 'hold_R')
    # refren 3 + finał: wszyscy
    r.on(167.0 + 0.06*i, 202.5, 'rise', 'sink', 0.5, 0.5)
    r.key(166.5, x=float(CHOIR_X[i]), y=CHOIR_Y, depth=CHOIR_D, scale=0.8)
    r.hold(167.0, 202.5, 'R', lambda cv, t, kind=REACT[i]: P.reaction_paddle(cv, kind, 0.85))
    gest(r, 167.2, 'hold_R', brow=0.7, lid=0.1)
    for b in hit_bars(167.5, 177.0):
        r.key(b - 0.06, hR=(110.0, -150.0)); r.key(b + 0.2, hR=(120.0, -330.0)); r.key(b + 0.65, hR=(110.0, -170.0))
    gest(r, lt(CH3, 3), 'rest', brow=-0.2, lid=0.4)
    for hj in [h for h in HEJ if 180 < h < 190] + [FIN_HEJ]:
        gest(r, hj - 0.12, 'up', brow=1.0, lid=0.0); gest(r, hj + 0.5, 'hold_R')
    r.on(bar_at_or_before(REPRISE) + 0.4 + 0.03*i, 212.5, 'rise', 'none', 0.35)
    gest(r, REPRISE, 'hold_R'); gest(r, FINAL_HEJ - 0.08, 'up', brow=1.0)

for r in ROLES: r.build()

# ================================================================== DEKORACJE, KURTYNA
SETS = [(0.0, 'kitchen', False), (29.9, 'office', True), (lt(V1B, 2), 'conf', False), (lt(PRE1, 0), 'show', False),
        (80.6, 'studio_g', True), (lt(V2, 3), 'road', False), (102.6, 'heaven', False), (lt(PRE2, 0), 'wood', False),
        (127.55, 'show', True)]
FLY = 0.9
def sets_at(t):
    cur = None; prev = None; tsw = None; fly = False
    for ts, name, fl in SETS:
        if t >= ts: prev, cur, tsw, fly = cur, name, ts, fl
    if fly and prev is not None and t < tsw + FLY:
        a = smoothstep((t - tsw)/FLY)
        return [(prev, -1700*a), (cur, -1700*(1 - a))]
    return [(cur, 0.0)]
CURTAIN = Track([(0, 0.0), (10.85, 0.0), (13.2, 1.0), (147.5, 1.0), (148.9, 0.0), (166.3, 0.0), (167.85, 1.0), (300, 1.0)])

# ================================================================== REKWIZYTY SCENICZNE (poza dłońmi)
def stage_props(t):
    """Zwraca (props[(depth, fn)], back_props[(set, fn)], front_props, curtain_props)."""
    pr, front, cprops = [], [], []
    # kuchnia: laptop na krawędzi sceny (pisanie), marynarka zjeżdża na sznurkach
    if lt(V1, 2) - 0.6 <= t <= lt(V1, 3) + 0.3:
        a = min(smoothstep((t - (lt(V1, 2) - 0.6))/0.4), smoothstep((lt(V1, 3) + 0.3 - t)/0.3))
        pr.append((-15.0, lambda cv, t, a=a: (cv.translate(-80, 60*(1 - a)), P.laptop(cv, 0.8, t))))
    if lt(V1, 1) - 0.4 <= t <= 19.8:
        if t < 18.85: y = -1500 + (1500 - 230)*smoothstep((t - (lt(V1, 1) - 0.4))/1.5)
        else: y = -230 - 1400*smoothstep((t - 18.85)/0.9)
        empty = t >= 18.85
        def jacket(cv, t, y=y, empty=empty):
            cv.translate(-80, y)
            if empty:
                p_ = __import__('skia').Paint(AntiAlias=True, StrokeWidth=7, Color4f=P.col('#8b5a2b')); cv.drawLine(-110, 0, 0, -40, p_); cv.drawLine(110, 0, 0, -40, p_); cv.drawLine(-110, 0, 110, 0, p_)
                p2 = __import__('skia').Paint(AntiAlias=True, StrokeWidth=3, Color4f=P.col('#dddddd')); cv.drawLine(-60, -1400, -60, -20, p2); cv.drawLine(60, -1400, 60, -20, p2)
            else: P.hanger_jacket(cv)
        pr.append((-5.0, jacket))
    # biuro: baner AWANS + chmurka nad głową Henia
    if wt(V1B, 0, 2) - 0.5 <= t <= lt(V1B, 2):
        y = -640 - 1400*(1 - smoothstep((t - (wt(V1B, 0, 2) - 0.5))/0.8))
        pr.append((260.0, lambda cv, t, y=y: (cv.translate(0, y), P.banner(cv, 'AWANS!', 1000))))
    if wt(V1B, 0, 4) - 0.3 <= t <= lt(V1B, 2):
        a = smoothstep((t - (wt(V1B, 0, 4) - 0.3))/0.5); lg = max([math.exp(-(t - s)/0.12) for s in snares_between(wt(V1B, 0, 4), t)] + [0])
        pr.append((-8.0, lambda cv, t, a=a, lg=lg: (cv.translate(150, -560 - 300*(1 - a)), P.cloud(cv, 0.9, 0.7, lg))))
    # przedrefreny/refreny: podest chóru (front ukrywa nogi... tzn. pręty chóru)
    for name, dy in sets_at(t):
        if name == 'show' or name == 'wood':
            pr.append((125.0, lambda cv, t, dy=dy: (cv.translate(0, dy*0.6), riser(cv, t))))
    # refren 1: balon-serce u chórzystki (pęka na 'pęka'), iskry na 'błyszczy'
    if 59.6 <= t <= wt(CH1, 1, 5) + 1.0:
        pp = smoothstep((t - wt(CH1, 1, 5))/0.7) if t > wt(CH1, 1, 5) else 0.0
        pr.append((CHOIR_D - 5, lambda cv, t, pp=pp: (cv.translate(-620, CHOIR_Y - 120), P.balloon_heart(cv, pp, t))))
    for (a_, b_) in [(wt(CH1, 1, 2), wt(CH1, 1, 2) + 1.4), (wt(CH2, 1, 2), wt(CH2, 1, 2) + 1.4), (wt(CH3, 1, 2), wt(CH3, 1, 2) + 1.4)]:
        if a_ - 0.1 <= t <= b_: pr.append((-6.0, lambda cv, t, a_=a_: sparkles(cv, t, a_)))
    # studio Grażyny: ring light, kadry 'scenek', zwój 'wywodu'
    if 80.6 <= t <= lt(V2, 3):
        pr.append((60.0, lambda cv, t: ringlight(cv, t)))
    if wt(V2, 2, 2) - 0.1 <= t <= lt(V2, 3):
        def panels(cv, t):
            for i in range(5):
                t0 = wt(V2, 2, 2) + i*0.41
                if t < t0: continue
                a = smoothstep((t - t0)/0.18)
                px = [-940, -660, -380, 560, 840][i]
                cv.save(); cv.translate(px, -520 + 120*(1 - a)); s = 0.6 + 0.4*a; cv.scale(s, s); cv.rotate((i - 2)*3)
                P.comic_panel(cv, i); cv.restore()
        pr.append((200.0, panels))
    if wt(V2, 2, 8) - 0.2 <= t <= lt(V2, 3):
        L_ = 700*smoothstep((t - (wt(V2, 2, 8) - 0.2))/1.0)
        pr.append((100.0, lambda cv, t, L_=L_: (cv.translate(820, -980), P.scroll(cv, L_, 'i dlatego…'))))
    # droga: pieczątka RESTRUKTURYZACJA na tle po 'bruk'
    if wt(V2, 4, 8) - 0.05 <= t <= 102.6:
        a = smoothstep((t - wt(V2, 4, 8))/0.08)
        pr.append((300.0, lambda cv, t, a=a: (cv.translate(180, -620), P.stamp_mark(cv, a))))
    # raj: flipchart Kasi, gwiazdki 'trzy opinie', aureola
    if lt(V2B, 0) - 0.5 <= t <= 115.0:
        pr.append((40.0, lambda cv, t: (cv.translate(-130, 40), P.flipchart(cv))))
    if wt(V2B, 1, 3) - 0.2 <= t <= 115.0:
        def stars(cv, t):
            for i in range(3):
                t0 = wt(V2B, 1, 3) + i*0.2
                if t < t0: continue
                a = smoothstep((t - t0)/0.15)
                cv.save(); cv.translate(-20 + i*170, -470 - 40*a); cv.scale(0.8*a, 0.8*a); P.star_card(cv); cv.restore()
        pr.append((-5.0, stars))
    if wt(V2B, 3, 2) - 0.6 <= t <= 115.0:
        y = -1500 + (1500 - 520)*smoothstep((t - (wt(V2B, 3, 2) - 0.6))/0.9)
        pr.append((-4.0, lambda cv, t, y=y: (cv.translate(600, y + 30*math.sin(t*2)), P.halo(cv, 1.0))))
    # studio w drewnie: mikrofon podcastowy, ON AIR
    if lt(PRE2, 0) - 0.5 <= t <= 128.0:
        pr.append((-20.0, lambda cv, t: (cv.translate(300, 0), P.desk_mic(cv))))
    # bridge: tabliczka 'Robię swoje.', ozdoby, mgła, trąbka, łza
    if 148.5 <= t <= 164.5:
        rev = smoothstep((t - wt(BR, 1, 4))/(wt(BR, 1, 6) + 0.4 - wt(BR, 1, 4)))
        front.append((-110.0, lambda cv, t, rev=rev: (cv.translate(470, -170 + 18*math.sin(t*0.8)), P.marker_sign(cv, 'Robię swoje.', rev, 440, 200))))
        fall = smoothstep((t - wt(BR, 2, 2))/1.3)
        def ornaments(cv, t, fall=fall):
            for k in range(9):
                x = -900 + k*225; y0 = -720 + 60*math.sin(k*1.3)
                cv.save(); cv.translate(x, y0 + 1400*fall**1.6*(0.8 + 0.05*k))
                cv.drawLine(0, -900, 0, 0, __import__('skia').Paint(AntiAlias=True, StrokeWidth=2, Color4f=P.col('#cccccc', 1 - fall)))
                P.ornament(cv, k, t); cv.restore()
        front.append((-112.0, ornaments))
        fog = 1 - smoothstep((t - wt(BR, 2, 5))/1.6)
        if fog > 0.01: front.append((-115.0, lambda cv, t, fog=fog: haze(cv, t, fog)))
        tr_up = smoothstep((t - 161.4)/0.5) * (1 - smoothstep((t - wt(BR, 4, 3))/0.5))
        if tr_up > 0.001: front.append((-108.0, lambda cv, t, a=tr_up: (cv.translate(330, 420 - 520*a), P.trumpet(cv))))
        te_up = smoothstep((t - 163.0)/0.4) * (1 - smoothstep((t - wt(BR, 4, 5))/0.45))
        if te_up > 0.001: front.append((-108.0, lambda cv, t, a=te_up: (cv.translate(330, 300 - 420*a), P.tear(cv))))
    # przedscenie (fartuch) gdy lalka stoi przed kurtyną
    if 2.5 <= t <= 11.0 or 147.9 <= t <= 165.0:
        front.append((-100.0, apron))
    # konfetti
    for t0 in [lt(CH3, 0) - 0.2, HEJ[-1] if HEJ else 185, FIN_HEJ, FINAL_HEJ]:
        if t0 <= t <= t0 + 6: front.append((-60.0, lambda cv, t, t0=t0: P.confetti(cv, t, t0, 120, seed=int(t0))))
    return pr, front, cprops

def star(cv, x, y, r, color):
    import skia
    pts = [(x + (r if k % 2 == 0 else r*0.45)*math.cos(-math.pi/2 + k*math.pi/5), y + (r if k % 2 == 0 else r*0.45)*math.sin(-math.pi/2 + k*math.pi/5)) for k in range(10)]
    cv.drawPath(P.poly_path(pts, True, False), skia.Paint(AntiAlias=True, Color4f=P.col(color)))
def riser(cv, t):
    from gfx import card, bulb
    card(cv, (-1100, CHOIR_Y + 4, 1100, 60), '#4a1f6e', 14, 'card', 81, 0.6)
    on = 0.5 + 0.5*math.cos(2*math.pi*E.beat_pos(t)/2)
    for k, x in enumerate(np.linspace(-1060, 1060, 30)):
        bulb(cv, x, CHOIR_Y + 34, 10, 1.0 if (k + int(E.beat_pos(t))) % 2 == 0 else 0.3)
    for k in range(5):
        y = CHOIR_Y + 80 + k*70
        cv.drawLine(-1100, y, 1100, y, __import__('skia').Paint(AntiAlias=True, StrokeWidth=3, Color4f=P.col('#2c0f45')))
def sparkles(cv, t, t0):
    import skia
    rng = np.random.default_rng(int(t0*10))
    for k in range(40):
        x = rng.uniform(-1000, 1000); y = rng.uniform(-750, -150); ph = rng.uniform(0, 1)
        a = max(0.0, math.sin(math.pi*min(max((t - t0 - ph*0.5)/0.6, 0), 1)))
        if a <= 0: continue
        s = 10 + 18*a
        p_ = skia.Paint(AntiAlias=True, Color4f=skia.Color4f(1, 0.95, 0.7, a))
        cv.drawPath(P.poly_path([(x, y - s), (x + s*0.25, y - s*0.25), (x + s, y), (x + s*0.25, y + s*0.25), (x, y + s), (x - s*0.25, y + s*0.25), (x - s, y), (x - s*0.25, y - s*0.25)], True, False), p_)
def ringlight(cv, t):
    import skia
    from gfx import light_pool
    cv.drawLine(-430, -320, -430, 60, skia.Paint(AntiAlias=True, StrokeWidth=10, Color4f=P.col('#333333')))
    cv.drawCircle(-430, -420, 120, skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=26, Color4f=P.col('#f3eee4')))
    light_pool(cv, -430, -420, 170, 170, (1, 0.97, 0.9), 0.14)
def haze(cv, t, a):
    import skia
    g = skia.GradientShader.MakeLinear([skia.Point(0, -700), skia.Point(0, 400)], [skia.Color4f(1, 1, 1, 0).toColor(), skia.Color4f(0.9, 0.92, 1, 0.55*a).toColor()])
    p_ = skia.Paint(); p_.setShader(g); cv.drawRect(skia.Rect(-1600, -800, 1600, 500), p_)
    for k in range(6):
        x = -1200 + k*500 + 120*math.sin(t*0.4 + k)
        p2 = skia.Paint(AntiAlias=True, Color4f=skia.Color4f(1, 1, 1, 0.12*a)); p2.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 60))
        cv.drawOval(skia.Rect(x - 400, -120, x + 400, 260), p2)
def apron(cv, t):
    from puppet import Material, fill
    import skia
    r = skia.Path(); r.addRect(skia.Rect(-1300, 0, 1300, 470))
    fill(cv, r, Material('#3a2340', 'felt', 0.9, light=1.1, dark=0.75, seed=9))
    cv.drawRect(skia.Rect(-1300, 0, 1300, 16), skia.Paint(Color4f=P.col('#c99a3a')))
    from gfx import draw_text
    draw_text(cv, 'Puste zasięgi', 0, 360, 'script', 80, '#c99a3a')
    for sx in (-1, 1): star(cv, sx*380, 332, 26, '#c99a3a')

# ================================================================== UJĘCIA
def C_(x, y, d, roll=0.0): return Cam(float(x), float(y), float(d), 1700.0, roll)
# (t0, t1, tryb, klucze kamery [(tau, Cam)] albo parametry przebitki)
SHOTS = [
    (0.0, lt(INTRO, 0), 'feed', dict(kind='open')),
    (lt(INTRO, 0), wt(INTRO, 0, 9), 'stage', [(0, C_(-30, -300, 1500)), (1, C_(20, -300, 1250))]),
    (wt(INTRO, 0, 9), wt(INTRO, 0, 11), 'stage', [(0, C_(-170, -320, 1100, -1.2)), (1, C_(-110, -330, 950, 0.0))]),
    (wt(INTRO, 0, 11), lt(V1, 0), 'stage', [(0, C_(0, -360, 1600)), (0.35, C_(0, -400, 2200)), (1, C_(-40, -430, 2700))]),
    (lt(V1, 0), lt(V1, 1), 'stage', [(0, C_(60, -290, 1350)), (0.45, C_(0, -300, 1300)), (1, C_(-300, -330, 1550))]),
    (lt(V1, 1), lt(V1, 2), 'stage', [(0, C_(-80, -440, 1800)), (1, C_(-80, -350, 1450))]),
    (lt(V1, 2), lt(V1, 3), 'stage', [(0, C_(-240, -260, 1300)), (1, C_(-130, -280, 1100))]),
    (lt(V1, 3), lt(V1, 4), 'stage', [(0, C_(60, -260, 1180)), (1, C_(40, -250, 1060))]),
    (lt(V1, 4), bar_at_or_before(30.41), 'feed', dict(kind='henio_post')),
    (bar_at_or_before(30.41), lt(V1B, 0), 'stage', [(0, C_(-300, -400, 2300)), (1, C_(150, -390, 1900))]),
    (lt(V1B, 0), lt(V1B, 1), 'stage', [(0, C_(0, -460, 1550)), (1, C_(0, -370, 1400))]),
    (lt(V1B, 1), lt(V1B, 2), 'stage', [(0, C_(-450, -360, 1750)), (1, C_(450, -360, 1750))]),
    (lt(V1B, 2), lt(V1B, 3), 'stage', [(0, C_(-100, -400, 2300)), (1, C_(20, -340, 1600))]),
    (lt(V1B, 3), lt(PRE1, 0), 'stage', [(0, C_(330, -330, 1550)), (1, C_(420, -310, 1350))]),
    (lt(PRE1, 0), lt(PRE1, 1), 'stage', [(0, C_(0, -700, 2500)), (1, C_(0, -450, 2700))]),
    (lt(PRE1, 1), lt(PRE1, 2), 'stage', [(0, C_(-650, -440, 1500)), (1, C_(650, -440, 1500))]),
    (lt(PRE1, 2), lt(PRE1, 3), 'stage', [(0, C_(0, -260, 1250)), (1, C_(0, -245, 1030))]),
    (lt(PRE1, 3), lt(CH1, 0), 'stage', [(0, C_(0, -245, 1030)), (1, C_(0, -450, 2750))]),
    # refren 1: plan ogólny z żurawiem, z prawej, Henio z lewej, zjazd pod scenę, ogólny, żuraw
    (lt(CH1, 0), lt(CH1, 1), 'stage', [(0, C_(0, -380, 2600)), (1, C_(0, -500, 2850))]),
    (lt(CH1, 1), lt(CH1, 2), 'stage', [(0, C_(450, -460, 2000)), (1, C_(250, -460, 1900))]),
    (lt(CH1, 2), lt(CH1, 3), 'stage', [(0, C_(-300, -380, 1500)), (0.72, C_(-160, -380, 1360)), (1, C_(-120, -120, 1420))]),
    (lt(CH1, 3), lt(CH1, 4), 'under', [(0, C_(-350, -170, 1800)), (1, C_(120, -90, 1500))]),
    (lt(CH1, 4), lt(CH1, 5), 'stage', [(0, C_(0, -430, 2750)), (1, C_(0, -450, 2500))]),
    (lt(CH1, 5), lt(V2, 0), 'stage', [(0, C_(-300, -520, 2050)), (1, C_(300, -440, 2250))]),
    (lt(V2, 0), lt(V2, 1), 'feed', dict(kind='to_grazyna')),
    (lt(V2, 1), lt(V2, 2), 'stage', [(0, C_(120, -330, 1350)), (0.7, C_(-150, -330, 1450)), (1, C_(-480, -330, 1500))]),
    (lt(V2, 2), lt(V2, 3), 'stage', [(0, C_(0, -500, 2500)), (1, C_(100, -470, 2300))]),
    (lt(V2, 3), lt(V2, 4), 'stage', [(0, C_(-250, -380, 1900)), (1, C_(-100, -360, 1700))]),
    (lt(V2, 4), snap_bar(wt(V2, 4, 8)), 'stage', [(0, C_(380, -330, 1500)), (1, C_(380, -330, 1330))]),
    (snap_bar(wt(V2, 4, 8)), lt(CHOIRI, 0), 'stage', [(0, C_(250, -460, 2050)), (1, C_(250, -460, 2300))]),
    (lt(CHOIRI, 0), lt(V2B, 0), 'stage', [(0, C_(0, -420, 2650)), (1, C_(0, -400, 2200))]),
    (lt(V2B, 0), lt(V2B, 1), 'stage', [(0, C_(-420, -380, 1500)), (1, C_(-320, -360, 1400))]),
    (lt(V2B, 1), lt(V2B, 2), 'stage', [(0, C_(0, -420, 1750)), (1, C_(180, -400, 1650))]),
    (lt(V2B, 2), lt(V2B, 3), 'stage', [(0, C_(560, -360, 1450)), (1, C_(600, -340, 1300))]),
    (lt(V2B, 3), lt(PRE2, 0), 'stage', [(0, C_(300, -420, 2300)), (1, C_(150, -520, 2500))]),
    (lt(PRE2, 0), lt(PRE2, 1), 'stage', [(0, C_(0, -440, 2650)), (1, C_(0, -430, 2300))]),
    (lt(PRE2, 1), lt(PRE2, 2), 'stage', [(0, C_(-350, -420, 1650)), (1, C_(350, -420, 1650))]),
    (lt(PRE2, 2), lt(PRE2, 3), 'stage', [(0, C_(0, -255, 1150)), (1, C_(0, -240, 990))]),
    (lt(PRE2, 3), lt(CH2, 0), 'stage', [(0, C_(0, -240, 1050)), (1, C_(0, -450, 2800))]),
    # refren 2: żuraw z góry, maski pękają, przebitki: analityka i puste komentarze
    (lt(CH2, 0), lt(CH2, 1), 'stage', [(0, C_(0, -820, 2500)), (1, C_(0, -460, 2650))]),
    (lt(CH2, 1), lt(CH2, 2), 'stage', [(0, C_(-560, -330, 1450)), (1, C_(-420, -310, 1350))]),
    (lt(CH2, 2), lt(CH2, 4), 'feed', dict(kind='analytics')),
    (lt(CH2, 4), lt(CH2, 5), 'stage', [(0, C_(0, -430, 2750)), (1, C_(0, -420, 2400))]),
    (lt(CH2, 5), lt(BR, 0), 'stage', [(0, C_(520, -430, 2000)), (1, C_(0, -430, 2600))]),
    # bridge: wyciszenie
    (lt(BR, 0), lt(BR, 1), 'stage', [(0, C_(0, -330, 1300)), (1, C_(0, -320, 1150))]),
    (lt(BR, 1), lt(BR, 2), 'stage', [(0, C_(160, -300, 1450)), (1, C_(200, -300, 1300))]),
    (lt(BR, 2), lt(BR, 3), 'stage', [(0, C_(0, -430, 1950)), (1, C_(0, -390, 1750))]),
    (lt(BR, 3), lt(BR, 4), 'stage', [(0, C_(140, -300, 1350)), (1, C_(100, -300, 1220))]),
    (lt(BR, 4), le(BR, 4) + 0.05, 'stage', [(0, C_(120, -270, 1350)), (1, C_(100, -260, 1250))]),
    (le(BR, 4) + 0.05, lt(CH3, 0), 'feed', dict(kind='simple_post')),
    # refren 3: majestatyczny - studio z daleka, przejazd, Henio i Tadek, cisza, ogólny, żuraw
    (lt(CH3, 0), lt(CH3, 1), 'stage', [(0, C_(0, -580, 3800)), (1, C_(0, -470, 2900))]),
    (lt(CH3, 1), lt(CH3, 2), 'stage', [(0, C_(-620, -460, 2050)), (1, C_(620, -460, 2050))]),
    (lt(CH3, 2), lt(CH3, 3), 'stage', [(0, C_(-170, -280, 1550)), (1, C_(-150, -270, 1400))]),
    (lt(CH3, 3), lt(CH3, 4), 'stage', [(0, C_(0, -440, 2650)), (1, C_(-90, -390, 1900))]),
    (lt(CH3, 4), lt(CH3, 5), 'stage', [(0, C_(0, -450, 2700)), (1, C_(0, -470, 2600))]),
    (lt(CH3, 5), lt(OUT, 0), 'stage', [(0, C_(0, -440, 2600)), (1, C_(0, -660, 3050))]),
    (lt(OUT, 0), bar_at_or_before(lt(OUT, 1)), 'feed', dict(kind='outro')),
    (bar_at_or_before(lt(OUT, 1)), bar_at_or_after(202.3), 'stage', [(0, C_(0, -470, 2900)), (0.25, C_(0, -450, 2650)), (1, C_(150, -660, 3150))]),
    (bar_at_or_after(202.3), bar_at_or_before(REPRISE), 'feed', dict(kind='stats')),
    (bar_at_or_before(REPRISE), E.SONG_DUR, 'stage', [(0, C_(0, -440, 2650)), (1, C_(0, -430, 2350))]),
    (E.SONG_DUR, E.SONG_DUR + E.TAIL + 1, 'credits', None),
]
def shot_at(t):
    for s in SHOTS:
        if s[0] <= t < s[1]: return s
    return SHOTS[-1]
def cam_at(t, s=None):
    s = s or shot_at(t)
    if s[2] not in ('stage', 'under'): return None
    cam = E.shot_cam(t, s[0], s[1], s[3], 0.3)
    # drobny 'oddech' operatora + mikro-akcent na mocnych uderzeniach
    cam.x += 3*math.sin(t*0.9) ; cam.y += 2*math.sin(t*1.3)
    cam.d *= 1 - 0.006*E.kick(t, decay=0.1)*ENERGY_CAM(t)
    return cam
from roles import ENERGY as ENERGY_CAM

# ================================================================== ŚWIATŁA
def lights_at(t, actors):
    L = dict(ambient=1.0, wash_col=(1.0, 0.96, 0.9), edge_col=(0.42, 0.38, 0.5), wash_r=1500, spots=[], beams=[], flash=0.0, key_x=-400.0)
    hen = next((a for a in actors if a.name == C.HENIO.name), None)
    sets = [n for n, _ in sets_at(t)]
    show = 'show' in sets or 'wood' in sets
    chorus = any(lt(s, 0) - 0.3 <= t <= le(s, 5) + 0.6 for s in (CH1, CH2, CH3))
    if t < 10.9:
        L.update(ambient=0.55, wash_col=(0.8, 0.55, 0.6), dim=0.0)
    if 147.6 <= t <= 166.8:
        k = smoothstep((t - 147.6)/1.2)*(1 - smoothstep((t - 166.0)/0.8))
        L.update(ambient=1 - 0.55*k, wash_col=(1.0, 0.85, 0.7))
    for a in actors:
        if a.depth <= 10 and abs(a.y) < 200:
            r = 330*a.scale*a.ch.scale
            L['spots'].append((a.x, -300*a.scale + a.y, r, (1.0, 0.92, 0.78), 0.22 if a.name != C.HENIO.name else 0.30))
    if chorus or (show and t > lt(PRE1, 3)):
        e = 1.0
        for i, x0 in enumerate((-900, -300, 300, 900)):
            sw = math.sin(2*math.pi*(E.beat_pos(t)/8 + i*0.25))
            c = [(1.0, 0.35, 0.7), (0.4, 0.75, 1.0), (1.0, 0.75, 0.3), (0.6, 0.4, 1.0)][i]
            L['beams'].append((x0*1.1, -1250, x0 + 500*sw, 300, 30, 220, c, 0.16*e))
        L['flash'] = 0.18*E.snare(t, decay=0.09) + 0.0
    # flesz na konferencji (na prawdziwych uderzeniach werbla)
    if lt(V1B, 2) <= t <= lt(V1B, 3):
        L['flash'] = max(L['flash'], 0.65*max([math.exp(-(t - s)/0.07) for s in snares_between(lt(V1B, 2), t)] + [0]))
    # 'pęka', 'bruk', 'hej': błysk
    for tb in [wt(CH1, 1, 5), wt(CH2, 1, 5), wt(V2, 4, 8)] + HEJ + [FIN_HEJ, FINAL_HEJ]:
        if 0 <= t - tb < 0.6: L['flash'] = max(L['flash'], 0.5*math.exp(-(t - tb)/0.1))
    if hen is not None: L['key_x'] = hen.x - 500
    if t > 210.6: L['dim'] = 0.92*smoothstep((t - 210.6)/1.4)          # wyciemnienie przed napisami
    return L

def portal_at(t):
    chase = E.beat_pos(t)/2.0
    on = 1.0
    if 147.6 <= t <= 166.6: on = 0.15
    if t < 10.9: on = 0.5
    return dict(chase=chase, bulbs=on)

# ================================================================== NAPISY (stałe miejsce wersu, dobór bez kolizji)
FEED_LINES = {(V1, 4): 'chat', (V2, 0): 'chat', (CH2, 2): 'comment', (CH2, 3): 'comment', (OUT, 0): 'comment'}
UNDER_LINES = {(CH1, 3)}
def actors_at(t):
    return [a for r in ROLES if (a := r.actor(t)) is not None]
def actor_rect(a):
    """Prostokąt lalki w świecie (z dłońmi i trzymanymi rekwizytami), do kontroli kolizji z napisami."""
    ch = a.ch; s = a.scale*ch.scale
    xs = [-(ch.torso_w[1] + 15), ch.torso_w[1] + 15, -ch.head_w*1.2, ch.head_w*1.2]
    ys = [ch.head_y - ch.head_h - max(ch.eye_r, 30) - 25, -a.y/s if a.y > 0 else 0.0]   # poniżej krawędzi sceny lalka jest niewidoczna
    for side in ('L', 'R'):
        hx, hy = a.pose['hands'][side]
        xs.append(hx + (25 if hx > 0 else -25)); ys.append(hy - 30)
        if a.pose['props'][side]:
            xs += [hx - 260, hx + 260]; ys.append(hy - 300)
    top, bot = a.y + min(ys)*s, a.y + max(ys)*s
    if top >= 0: return (a.x, 0.0, a.x, 0.0)          # lalka całkiem schowana za krawędzią sceny
    return (a.x + min(xs)*s, top, a.x + max(xs)*s, min(bot, 0.0))
def project_rect(cam, r, depth):
    (x0, y0), (x1, y1) = cam.to_screen(r[0], r[1], depth), cam.to_screen(r[2], r[3], depth)
    return (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
def inter(a, b):
    w = min(a[2], b[2]) - max(a[0], b[0]); h = min(a[3], b[3]) - max(a[1], b[1])
    return max(w, 0)*max(h, 0)
def area(a): return max(a[2] - a[0], 0)*max(a[3] - a[1], 0)
FRAME = (0, 0, E.W, E.H)

def _extra_tokens(key):
    sec, li = key
    if sec in (CH1, CH2, CH3) and li in (4, 5):
        hs = [h['t_on'] for h in E.AL['choir']['hej'] if tuple(h['after_line']) == key]
        if hs: return [('(hej!)', hs[0])]
    return []

def _candidates(key, t_mid):
    sec, li = key
    L = LINES[key]
    cam = cam_at(t_mid)
    cx = cam.x if cam else 0.0
    def sz(depth, px=58, lo=34, hi=150):
        return float(np.clip(px/cam.scale(depth), lo, hi)) if cam else 60.0
    def mw(depth): return 0.78*E.W/cam.scale(depth) if cam else 1500
    spoken = L['spoken']
    sets = [n for n, _ in sets_at(t_mid)]
    cands = []
    if spoken:
        hen = HENIO.actor(t_mid)
        hx = hen.x if hen else 0.0; hd = hen.depth if hen else 0.0
        for dx, y in [(560, -640), (-560, -640), (600, -470), (-600, -470), (0, -760), (520, -560), (-520, -560), (430, -560), (-430, -560), (400, -660), (-400, -660)]:
            for k in (1.0, 0.8):
                cands.append(('bubble', hx + dx, y, hd - 20, sz(hd - 20, 46*k), dict(tail=(-1 if dx > 0 else 1, 1), maxw=0.55*mw(hd - 20))))
        return cands
    if sec == BR:
        for dx, y in [(-520, -560), (-560, -330), (560, -600), (-480, -700), (-600, -450)]:
            for k in (1.0, 0.8):
                cands.append(('marker', dx, y, -118.0, sz(-118, 50*k), dict(maxw=0.45*mw(-118))))
        if cam:
            for px in (50, 42):
                s_ = cam.scale(-100.5); ytxt = min(110.0, cam.y + (0.93*E.H - E.H/2)/s_)
                cands.append(('playboard', cam.x, max(ytxt, 45.0), -100.5, px/s_, dict(maxw=0.86*E.W/s_)))
        return cands
    if 'show' in sets or 'wood' in sets:
        cands.append(('marquee', 0.0, -935.0, S.D_PORTAL, 74, {}))
    # front krawędzi sceny (albo przedscenia, gdy lalka stoi przed kurtyną)
    if cam:
        apr = (2.5 <= t_mid <= 11.0) or (147.9 <= t_mid <= 165.0)
        dp = -100.5 if apr else S.D_PLAY - 0.5
        for px in (52, 44, 38):
            s_ = cam.scale(dp)
            ytxt = min(110.0, cam.y + (0.93*E.H - E.H/2)/s_)
            cands.append(('playboard', cam.x, max(ytxt, 45.0), dp, px/s_, dict(maxw=0.86*E.W/s_)))
    # kandydaci zakotwiczeni w kadrze ujęcia (w połowie wersu), przeliczeni na stałe położenie w świecie
    D = 60.0
    for (u, v, mwf) in [(0.5, 0.11, 0.80), (0.5, 0.16, 0.80), (0.27, 0.12, 0.44), (0.73, 0.12, 0.44), (0.22, 0.30, 0.40), (0.78, 0.30, 0.40),
                        (0.30, 0.20, 0.50), (0.70, 0.20, 0.50), (0.5, 0.24, 0.6)]:
        for px in (54, 46, 38):
            s_ = cam.scale(D)
            wx = cam.x + (u*E.W - E.W/2)/s_; wy = cam.y + (v*E.H - E.H/2)/s_
            cands.append(('board', wx, wy, D, px/s_, dict(maxw=mwf*E.W/s_ - 1.4*px/s_)))
    return cands

def _score(sg, ts):
    vis, ov = [], []
    for t in ts:
        s = shot_at(t)
        if s[2] != 'stage': continue
        cam = cam_at(t, s)
        r = project_rect(cam, sg.rect(), sg.depth)
        if sg.kind not in ('marquee', 'playboard'):
            op = project_rect(cam, (S.OPEN_L + 20, S.OPEN_T + 30, S.OPEN_R - 20, 0), S.D_PORTAL)
            fr = (max(op[0], 0), max(op[1], 0), min(op[2], E.W), min(op[3], E.H))
        else: fr = FRAME
        vis.append(inter(r, fr)/max(area(r), 1))
        o = 0.0
        for a in actors_at(t):
            ar = project_rect(cam, actor_rect(a), a.depth)
            o = max(o, inter(r, ar)/max(area(r), 1))
        ov.append(o)
    if not vis: return -1e9, 0, 0
    return np.mean(vis) - 6*max(ov), np.mean(vis), max(ov)

SIGNS = []
SIGN_REPORT = []
def _layout_signs():
    for key, L in sorted(LINES.items(), key=lambda kv: kv[1]['t0']):
        if key in FEED_LINES or key in UNDER_LINES: continue
        if key == (OUT, 1):      # finał: neon na portalu (+ powtórka na końcu)
            sg = Sign(key, 'marquee', 0.0, -935.0, S.D_PORTAL, 90, t_out=202.3)
            SIGNS.append(sg); SIGN_REPORT.append((key, 'marquee', 1.0, 0.0)); continue
        # napis znika najpóźniej przy najbliższym cięciu po końcu wersu (nie przechodzi do innego ujęcia)
        cut = min([s[0] for s in SHOTS if s[0] >= L['t1'] - 0.05] + [L['t1'] + 0.55])
        t_out = min(L['t1'] + 0.55, cut)
        # ...i nie pojawia się w ujęciu przed cięciem, jeśli pierwsze słowo pada dopiero po cięciu
        cin = [s[0] for s in SHOTS if L['t0'] - 0.75 < s[0] <= L['t0'] + 0.05]
        cut_in = max(cin) if cin else None
        ts = np.linspace(L['t0'], min(L['t1'], cut - 0.01), 7)
        best = None
        for kind, x, y, d, size, kw in _candidates(key, (L['t0'] + L['t1'])/2):
            kw = dict(kw); maxw = kw.pop('maxw', 1500)
            sg = Sign(key, kind, x, y, d, size, maxw=maxw, t_out=t_out, cut_in=cut_in, **kw)
            sg.tokens += _extra_tokens(key); sg.rows = __import__('signs')._fit_lines(sg.tokens, sg.fname, sg.size, sg.maxw)
            if kind == 'board' and cam_at((L['t0'] + L['t1'])/2) is not None:
                cm = cam_at((L['t0'] + L['t1'])/2); top_world = cm.y + (0.035*E.H - E.H/2)/cm.scale(d)
                if sg.y - sg.h/2 < top_world: sg.y = top_world + sg.h/2
            sc, v, o = _score(sg, ts)
            if kind == 'marquee': sc += 0.08
            if kind == 'playboard': sc -= 0.03
            sc += 0.004*size*(cam_at((L['t0'] + L['t1'])/2) or Cam()).scale(d)/50
            if best is None or sc > best[0]: best = (sc, sg, v, o)
        SIGNS.append(best[1]); SIGN_REPORT.append((key, best[1].kind, round(best[2], 2), round(best[3], 3)))
    # powtórka 'Pus-te za-się-gi! HEJ!' na końcu
    rep = Sign((OUT, 1), 'marquee', 0.0, -935.0, S.D_PORTAL, 90, t_in=REPRISE - 0.3, t_out=E.SONG_DUR + 1)
    rep.tokens = [('Puste', REPRISE), ('zasięgi!', REPRISE + 0.46), ('HEJ!', FINAL_HEJ)]
    rep.rows = [rep.tokens]; SIGNS.append(rep)
_layout_signs()

# ================================================================== SCENA W CHWILI t
def stage_scene(t, cam=None):
    actors = actors_at(t)
    pr, front, cprops = stage_props(t)
    for sg in SIGNS:
        if sg.active(t) and sg.kind == 'playboard':
            front.append((sg.depth, lambda cv, t, sg=sg: sg.draw(cv, t)))
        elif sg.active(t) and sg.kind in ('board',):
            pr.append((sg.depth, lambda cv, t, sg=sg: sg.draw(cv, t)))
        elif sg.active(t) and sg.kind in ('bubble', 'marker'):
            front.append((sg.depth, lambda cv, t, sg=sg: sg.draw(cv, t)))
    marq = [sg for sg in SIGNS if sg.kind == 'marquee' and sg.active(t)]
    def marquee(cv, marq=marq):
        from gfx import draw_text
        if marq:
            for sg in marq: sg.draw(cv, t)
        else:
            draw_text(cv, 'PUSTE ZASIĘGI', 0, -910, 'marquee', 70, '#e8b85a', stroke=('#6b3a12', 3), alpha=0.75)
            for sx in (-1, 1): star(cv, sx*400, -935, 26, '#e8b85a')
    portal = portal_at(t); portal['marquee'] = marquee
    sc = dict(mode='stage', cam=cam or cam_at(t), sets=sets_at(t), curtain=CURTAIN(t), curtain_sway=0.4,
              actors=actors, props=pr, front_props=front, curtain_props=cprops, lights=lights_at(t, actors), portal=portal)
    return sc

def scene_at(t):
    s = shot_at(t)
    if s[2] == 'credits': return dict(mode='credits', t0=s[0])
    if s[2] == 'feed': return dict(mode='feed', kind=s[3]['kind'], t0=s[0], t1=s[1])
    if s[2] == 'under': return dict(mode='under', cam=cam_at(t, s), t0=s[0], t1=s[1])
    return stage_scene(t, cam_at(t, s))

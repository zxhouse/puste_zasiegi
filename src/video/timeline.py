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
         'phone': ((-w1*0.2, -h*0.62), (w1 + 55, -h*0.55)),
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
H.costume(wt(V1, 1, 1) + 0.85, jacket='#6f7480', lapels=True, tie='#c0392b', buttons='#2f3238')           # garnitur zjechał z góry
H.costume(wt(BR, 0, 2) + 0.1, tie=None)                                                                   # bridge: zdejmuje krawat
# intro na przedscenie
H.on(3.0, le(INTRO, 0) + 0.05, 'rise', 'sink', 0.6, 0.45)
H.key(0, x=0.0, y=0.0, depth=D_APRON_ACT)
gest(H, 3.3, 'phone', gaze=(0.0, 0.1), brow=0.3, lid=0.3)
H.hold(3.0, le(INTRO, 0) + 0.5, 'R', lambda cv, t: P.phone(cv))
gest(H, wt(INTRO, 0, 7), 'phone', gaze=(-0.3, 0.6))             # 'dzisiaj' - zerka w telefon
gest(H, wt(INTRO, 0, 8), 'present_L', gaze=(0.0, 0.0), brow=0.6)  # 'kochani' - do widzów
gest(H, wt(INTRO, 0, 9), 'shrug', brow=0.9, lid=0.15)             # 'Kolejny sukces?'
gest(H, wt(INTRO, 0, 11) - 0.2, 'phone', gaze=(0.2, 0.7), brow=0.2, lid=0.3)   # 'Zobaczmy...' - przesuwa palcem
# kuchnia: wynurza się z kubkiem kawy
H.on(13.0, lt(PRE1, 0), 'rise', 'none', 0.65)
H.key(12.4, x=-80.0, depth=0.0)
H.hold(12.4, lt(V1, 1) - 0.05, 'R', lambda cv, t: P.mug(cv, '#e05d5d', 1.0, t))
gest(H, 13.0, 'mug', gaze=(0.3, 0.2), lid=0.55, brow=-0.1)
gest(H, 13.55, 'sip', gaze=(0.0, 0.5), lid=0.7)                     # łyk przed wersem (nie śpiewa z kubkiem przy ustach)
gest(H, lt(V1, 0) - 0.12, 'mug', gaze=(0.1, 0.1), lid=0.45)
gest(H, wt(V1, 0, 1) - 0.1, 'holdup_R', gaze=(0.5, -0.3), lid=0.3, brow=0.4)   # 'kawa' - kubek w górę
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
H.hold(lt(V1, 3), wt(V1, 3, 4) + 0.3, 'R', lambda cv, t: P.linkedin_card(cv, 'Z przyjemnością dzielę się…', 470, 210, side=1), grip=True)
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
H.on(lt(PRE1, 0) + 0.57, lt(CH1, 3) + 0.3, 'rise', 'none', 0.57)
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
H.on(lt(CH1, 4) - 0.05, lt(V2, 0) + 0.35, 'rise', 'sink', 0.5, 0.45)
gest(H, lt(CH1, 4), 'up', brow=1.0, lid=0.0, gaze=(0.0, -0.2))
gest(H, lt(CH1, 5), 'wide', brow=0.8); gest(H, le(CH1, 5) + 0.15, 'up')
# studio Grażyny: zagląda z boku
H.on(lt(V2, 1) - 0.35, lt(CHOIRI, 0), 'left', 'none', 0.7)
H.key(lt(V2, 1) - 0.01, x=0.0); H.key(lt(V2, 1), x=-830.0)
gest(H, lt(V2, 1), 'chin', gaze=(1.0, 0.0), turn=0.5, lid=0.5, brow=0.2)
gest(H, wt(V2, 1, 3), 'facepalm', brow=-0.8, lid=0.65, lean=-8.0)                 # 'brzmi jak cringe'
H.key(wt(V2, 1, 5), lean=10.0, turn=-0.4); H.key(le(V2, 1), lean=0.0, turn=0.5)
gest(H, lt(V2, 2), 'present_R', gaze=(1.0, -0.3), lid=0.3, brow=0.4)                # 'pięć scenek'
gest(H, wt(V2, 2, 7), 'shrug', gaze=(0.6, 0.0), brow=0.9)                          # 'długi wywód'
# droga: Henio czyta (bez tchu)
H.key(lt(V2, 3) - 0.01, x=-830.0); H.key(lt(V2, 3), x=-600.0)
gest(H, lt(V2, 3), 'hold_L', gaze=(0.0, 0.6), lid=0.35, turn=0.2)
H.hold(lt(V2, 3), le(V2, 4), 'L', lambda cv, t: P.phone(cv))
gest(H, wt(V2, 3, 5), 'chest', gaze=(0.0, 0.6), brow=0.6, lid=0.1)              # 'czytam bez tchu'
gest(H, lt(V2, 4), 'hold_L', gaze=(0.9, 0.0), brow=-0.2)
gest(H, wt(V2, 4, 5) - 0.1, 'present_R', gaze=(0.9, 0.2), brow=0.9, lid=0.0)       # 'wywalili cię na bruk!'
gest(H, le(V2, 4) + 0.3, 'rest', brow=0.0)
# raj korporacyjny: na chmurce z boku
H.on(lt(V2B, 0) + 0.43, lt(PRE2, 0), 'rise', 'none', 0.43)
H.key(lt(V2B, 0) - 0.01, x=-600.0); H.key(lt(V2B, 0), x=-880.0, y=-40.0)
gest(H, lt(V2B, 0), 'present_R', gaze=(0.9, 0.0), turn=0.4, lid=0.4)
gest(H, lt(V2B, 1), 'shrug', gaze=(0.9, -0.1), brow=0.5)
gest(H, lt(V2B, 2), 'chin', gaze=(1.0, 0.0), lid=0.55)
gest(H, lt(V2B, 3), 'up', gaze=(0.6, -0.8), brow=0.9, lid=0.0)                      # 'świętym'
# studio w drewnie
H.on(lt(PRE2, 0) + 0.56, le(CH2, 5) + 1.5, 'rise', 'sink', 0.56, 0.4)
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
H.on(lt(BR, 0) - 0.65, le(BR, 4) + 0.4, 'rise', 'sink', 0.5, 0.45)
H.key(lt(BR, 0) - 0.03, x=0.0, depth=D_APRON_ACT)
gest(H, lt(BR, 0) - 0.55, 'rest', smile=0.0, brow=0.0, lid=0.45, gaze=(0.0, 0.2), jitter=0.6)
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
H.on(lt(CH3, 0) - 0.87, FIN_HEJ + 1.0, 'rise', 'sink', 0.6, 0.5)
H.key(lt(CH3, 0) - 1.8, x=0.0, depth=0.0)
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
gest(H, lt(OUT, 1) - 0.45, 'wide', smile=0.4, brow=0.8); gest(H, FIN_HEJ - 0.1, 'up', brow=1.0)
H.on(bar_at_or_before(REPRISE) + 0.35, 212.5, 'rise', 'none', 0.35)
gest(H, REPRISE, 'wide', smile=0.6, brow=0.9); gest(H, FINAL_HEJ - 0.08, 'up', brow=1.0, lid=0.0)

# ------------------------------------------------------------------ GRAŻYNA
g = GRAZ
g.on(lt(V1B, 2), lt(PRE1, 0), 'none', 'none')            # konferencja: pozuje do zdjęcia
g.key(0, x=-170.0, y=0.0, depth=0.0)
gest(g, lt(V1B, 2), 'holdup_L', smile=1.0, gaze=(0.0, 0.0), brow=0.9, lid=0.0, turn=0.25)
gest(g, wt(V1B, 2, 3), 'hips', smile=1.0, turn=0.3)
gest(g, lt(V1B, 3), 'hips', smile=0.6, gaze=(0.8, 0.0), turn=0.3)
g.on(lt(V2, 1) - 0.4, lt(V2, 3), 'rise', 'none', 0.5, 0.45)                # jej studio
g.key(lt(V2, 1) - 1.0, x=120.0)
g.hold(lt(V2, 1) - 0.4, le(V2, 1) + 0.2, 'L', lambda cv, t: P.linkedin_card(cv, 'Z pokorą informuję…', 450, 200, 'Grażyna Gratka', side=-1), grip=True)
gest(g, lt(V2, 1) - 0.4, 'holdup_L', smile=1.0, brow=0.7, lid=0.2, gaze=(-0.2, -0.2))
gest(g, wt(V2, 1, 3), 'holdup_L', smile=1.0, lid=0.5, gaze=(0.3, -0.6))          # 'z pokorą' - przymknięte oczy
gest(g, lt(V2, 2), 'present_L', smile=1.0, gaze=(-0.4, -0.6), brow=0.6)          # pokazuje kadry 'scenek'
for i in range(5): g.key(wt(V2, 2, 2) + i*0.41, hL=(-250.0 + i*55, -440.0 - 25*(i % 2)))      # wskazuje kolejne kadry nad głową
gest(g, wt(V2, 2, 7), 'wide', smile=1.0, brow=0.9)                               # 'długi wywód'
g.on(lt(V2B, 2) - 0.5, lt(PRE2, 0), 'rise', 'none', 0.5)               # raj: wdzięczność, aureola
g.key(lt(V2B, 2) - 1.0, x=600.0, y=-30.0)
g.hold(lt(V2B, 2) - 0.5, le(V2B, 3), 'R', lambda cv, t: P.scroll(cv, min(520, max(60, (t - lt(V2B, 2) + 0.3)*260))))
gest(g, lt(V2B, 2) - 0.5, 'hold_R', smile=0.8, gaze=(0.2, 0.6), brow=0.6)
gest(g, wt(V2B, 2, 2), 'hold_R', gaze=(0.6, 0.3), smile=1.0)
gest(g, lt(V2B, 3), 'hold_R', gaze=(0.0, -0.9), smile=1.0, brow=1.0, lid=0.0)
g.on(lt(CH3, 0) - 0.87, FIN_HEJ + 1.0, 'rise', 'sink', 0.6, 0.5)                          # refren 3 i finał
g.key(lt(CH3, 0) - 1.8, x=-655.0, y=0.0, depth=18.0)
gest(g, lt(CH3, 0) - 0.77, 'up', smile=0.8, brow=0.7); gest(g, lt(CH3, 2), 'wide', smile=0.5); gest(g, lt(CH3, 3), 'rest', smile=0.0, lid=0.4)
gest(g, lt(CH3, 4), 'up', smile=0.7); gest(g, lt(OUT, 1) - 0.45, 'wide'); gest(g, FIN_HEJ - 0.1, 'up')
g.on(bar_at_or_before(REPRISE) + 0.4, 212.5, 'rise', 'none', 0.35); gest(g, REPRISE, 'wide', smile=0.8); gest(g, FINAL_HEJ - 0.08, 'up')

# ------------------------------------------------------------------ PREZES
p = PREZ
p.on(lt(V1B, 2), lt(PRE1, 0), 'none', 'none')
p.key(0, x=240.0, y=0.0, depth=0.0)
gest(p, lt(V1B, 2) + 0.2, 'holdup_R', smile=1.0, brow=0.6, lid=0.25, turn=-0.25)
gest(p, wt(V1B, 2, 3), 'hips', smile=1.0, turn=-0.3)
gest(p, lt(V1B, 3), 'hips', smile=0.5, gaze=(0.7, 0.0), turn=0.2, lid=0.4)
gest(p, wt(V1B, 3, 5) + 0.05, 'chest', smile=0.9, lid=0.55, gaze=(0.9, 0.1))       # przyjmuje 'szacun' z łaskawością (po powrocie z serwisu)
p.key(wt(V1B, 3, 7), tilt=-12.0); p.key(wt(V1B, 3, 7) + 0.5, tilt=0.0)
p.on(lt(V2, 4) - 0.3, lt(V2B, 0) - 0.5, 'right', 'sink', 0.6, 0.45)               # stempel 'restrukturyzacja'
p.key(lt(V2, 4) - 1.0, x=640.0)
p.hold(lt(V2, 4) - 0.3, lt(V2B, 0) - 0.7, 'R', lambda cv, t: P.stamp(cv))
gest(p, lt(V2, 4), 'hold_R', gaze=(-0.8, 0.2), turn=-0.5, brow=-0.6, lid=0.4)
gest(p, wt(V2, 4, 5), 'holdup_R', gaze=(-0.8, 0.4), brow=-0.8)
gest(p, wt(V2, 4, 8) - 0.12, 'hold_R', gaze=(-0.8, 0.6))                         # 'bruk' - stempel w dół
p.on(lt(CH3, 0) - 0.87, FIN_HEJ + 1.0, 'rise', 'sink', 0.6, 0.5)
p.key(lt(CH3, 0) - 1.8, x=655.0, depth=18.0)
gest(p, lt(CH3, 0) - 0.77, 'wide', smile=0.8, turn=0.0, lid=0.25, brow=0.4); gest(p, lt(CH3, 3), 'chest', smile=0.0, lid=0.5)
gest(p, lt(CH3, 4), 'up', smile=0.8); gest(p, FIN_HEJ - 0.1, 'up')
p.on(bar_at_or_before(REPRISE) + 0.4, 212.5, 'rise', 'none', 0.35); gest(p, REPRISE, 'wide', smile=0.8); gest(p, FINAL_HEJ - 0.08, 'up')

# ------------------------------------------------------------------ TADEK
td = TADEK
td.on(lt(V2, 3) + 0.5, wt(V2, 4, 8) + 0.05, 'rise', 'sink', 0.5, 0.35)   # 'nowa droga' -> na bruk (zjeżdża w dół)
td.key(0, x=180.0, y=0.0, depth=0.0)
td.hold(lt(V2, 3) - 0.3, wt(V2, 4, 8) + 0.3, 'L', lambda cv, t: P.box_of_stuff(cv))
td.hold(lt(V2, 3) - 0.3, wt(V2, 4, 8) + 0.3, 'R', lambda cv, t: P.placard(cv, 'Cieszę się z nowej drogi! :)', size=36, side=1), grip=True)
gest(td, lt(V2, 3) - 0.3, 'hold_L', smile=1.0, brow=0.9, lid=0.0, gaze=(0.0, 0.0))
td.key(lt(V2, 3) - 0.3, hR=(230.0, -330.0))
td.key(lt(V2, 4), smile=0.6, gaze=(0.6, 0.0), brow=0.3)
td.key(wt(V2, 4, 5), smile=0.0, gaze=(0.8, -0.4), brow=-0.8, lid=0.0)             # 'wywalili' - widzi stempel
td.on(lt(CH3, 0) - 0.87, FIN_HEJ + 1.0, 'rise', 'sink', 0.6, 0.5)
td.key(lt(CH3, 0) - 1.8, x=-330.0, depth=-8.0)
gest(td, lt(CH3, 0) - 0.77, 'up', smile=0.8, brow=0.6, lid=0.1); gest(td, lt(CH3, 2), 'present_R', gaze=(0.8, 0.0), turn=0.3, smile=0.6)
gest(td, lt(CH3, 3), 'chest', gaze=(0.7, 0.1), turn=0.2, smile=0.3); gest(td, lt(CH3, 4), 'up', turn=0.0); gest(td, FIN_HEJ - 0.1, 'up')
td.on(bar_at_or_before(REPRISE) + 0.4, 212.5, 'rise', 'none', 0.35); gest(td, REPRISE, 'wide', smile=0.8); gest(td, FINAL_HEJ - 0.08, 'up')

# ------------------------------------------------------------------ MIREK ('Ogromny szacun!')
m = MIREK
m.on(wt(V1B, 3, 5) - 0.5, lt(PRE1, 0), 'rise', 'none', 0.3)
m.key(0, x=640.0, y=0.0, depth=-10.0)
m.hold(wt(V1B, 3, 5) - 0.5, lt(PRE1, 0), 'R', lambda cv, t: P.placard(cv, 'Ogromny szacun!', size=40, color='#ffffff', ink='#0a66c2', side=-1), grip=True)
gest(m, wt(V1B, 3, 5) - 0.5, 'holdup_R', smile=1.0, brow=1.0, gaze=(-0.9, 0.0), turn=-0.6, lid=0.0)
m.key(wt(V1B, 3, 5) - 0.5, mouth_extra=0.0)
for k, tk in enumerate(snares_between(wt(V1B, 3, 5), lt(PRE1, 0) - 0.2)):
    m.key(tk - 0.05, hR=(150.0, -260.0)); m.key(tk + 0.12, hR=(150.0, -300.0))
m.on(lt(CH3, 0) - 0.87, FIN_HEJ + 1.0, 'rise', 'sink', 0.6, 0.5)
m.key(lt(CH3, 0) - 1.8, x=325.0, depth=-8.0)
gest(m, lt(CH3, 0) - 0.77, 'up', smile=1.0); gest(m, FIN_HEJ - 0.1, 'up')
m.on(bar_at_or_before(REPRISE) + 0.4, 212.5, 'rise', 'none', 0.35); gest(m, FINAL_HEJ - 0.08, 'up')

# ------------------------------------------------------------------ KASIA ('case study')
k_ = KASIA
k_.on(lt(V2B, 0) + 0.3, lt(PRE2, 0), 'rise', 'none', 0.45)
k_.key(0, x=-400.0, depth=0.0, y=-30.0)
gest(k_, lt(V2B, 0) - 0.4, 'present_L', smile=1.0, brow=0.8, gaze=(-0.7, -0.2), turn=-0.3, lid=0.1)
gest(k_, wt(V2B, 0, 4), 'present_L', gaze=(0.0, 0.0), turn=0.0)
gest(k_, lt(V2B, 1), 'hips', smile=0.6, gaze=(0.8, 0.0)); gest(k_, lt(V2B, 3), 'up', gaze=(0.6, -0.8), smile=1.0)
k_.on(lt(CH3, 0) - 0.87, FIN_HEJ + 1.0, 'rise', 'sink', 0.6, 0.5)
k_.key(lt(CH3, 0) - 1.8, x=-975.0, y=0.0, depth=22.0)
gest(k_, lt(CH3, 0) - 0.77, 'up', smile=0.8); gest(k_, lt(CH3, 3), 'rest', smile=0.0); gest(k_, lt(CH3, 4), 'up'); gest(k_, FIN_HEJ - 0.1, 'up')
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
        r.key(30.0, x=ox, y=-230.0, depth=175.0); r.key(lt(V1B, 2) - 0.4, x=ox, y=-230.0, depth=175.0)
        gest(r, 31.0, 'rest', gaze=(0.0, 0.2))
        gest(r, wt(V1B, 1, 3) - 0.2, 'chin', gaze=(0.6 if ox < 0 else -0.6, -0.2), brow=0.6, lid=0.3)   # 'strategiczny gest'
        gest(r, le(V1B, 1) + 0.3, 'rest', brow=0.0, lid=0.2)
        # przedrefren 1 -> refren 1
        r.on(lt(PRE1, 0) + 0.5 + 0.15*MEN.index(i), lt(V2, 0) + 0.35, 'rise', 'sink', 0.5, 0.45)
        r.key(lt(PRE1, 0), x=float(CHOIR_X[i]), y=CHOIR_Y, depth=CHOIR_D, scale=0.8)
    else:
        r.on(lt(CH1, 0) - 0.66 + 0.1*WOMEN.index(i), lt(V2, 0) + 0.35, 'rise', 'sink', 0.45, 0.45)
    start = lt(PRE1, 0) if i in MEN else lt(CH1, 0) - 0.7
    gest(r, start, 'rest', gaze=(0.0, 0.0))
    if i in MEN:
        gest(r, lt(PRE1, 1), 'rest', smile=1.0, brow=0.8, lid=0.0)
        r.hold(lt(PRE1, 1) - 0.2, le(PRE1, 1) + 0.2, 'L', lambda cv, t: P.smile_mask(cv, 0.0), grip=True)
        gest(r, lt(PRE1, 1), 'hold_L', smile=1.0)
        gest(r, wt(PRE1, 1, 2) - 0.1, 'forehead', smile=1.0)                     # 'rzut na czoło' - wszyscy naraz
        gest(r, lt(PRE1, 2), 'rest', smile=0.0, gaze=(-1.0 if CHOIR_X[i] > 0 else 1.0, 0.3), brow=-0.4)   # patrzą na Henia
        gest(r, lt(PRE1, 3), 'rest', gaze=(0.0, 0.0), brow=0.3)
    # refren 1: reakcje na patykach w górę na mocnych bitach
    r.hold(lt(CH1, 0) - 0.5, le(CH1, 5) + 1.1, 'R', lambda cv, t, kind=REACT[i]: P.reaction_paddle(cv, kind, 0.85), grip=True)
    gest(r, lt(CH1, 0) - 0.4, 'hold_R', brow=0.6, lid=0.1)
    for b in hit_bars(lt(CH1, 0) - 0.1, lt(CH1, 3) - 0.1):
        r.key(b - 0.06, hR=(110.0, -150.0)); r.key(b + 0.2, hR=(120.0, -330.0)); r.key(b + 0.65, hR=(110.0, -170.0))
    gest(r, lt(CH1, 3), 'rest', brow=-0.2, lid=0.4)
    for hj in [h for h in HEJ if 72 < h < 80]:
        gest(r, hj - 0.12, 'up', brow=1.0, lid=0.0); gest(r, hj + 0.5, 'hold_R')
    # wtrącenie 'Wywalili na bruk!' (cały chór na drodze, z kostkami bruku)
    r.on(lt(CHOIRI, 0) + 0.22, lt(V2B, 0) - 0.28, 'rise', 'sink', 0.24, 0.45)      # wyskakują na cięciu, z okrzykiem
    r.key(lt(CHOIRI, 0) - 0.4, x=float(CHOIR_X[i])*1.05, y=-40.0, depth=40.0, scale=0.95)
    r.hold(lt(CHOIRI, 0) - 0.4, le(CHOIRI, 0) + 0.8, 'R', lambda cv, t, k=i: P.cobble(cv, k), grip=True)
    gest(r, lt(CHOIRI, 0) - 0.35, 'holdup_R', brow=-0.9, lid=0.0, gaze=(0.0, 0.0), turn=0.0)
    r.key(le(CHOIRI, 0) + 0.31, x=float(CHOIR_X[i])*1.05, y=-40.0, depth=40.0, scale=0.95)
    if i == 2:
        r.on(lt(V2B, 1) - 0.45, lt(PRE2, 0), 'rise', 'none', 0.45)
        r.key(lt(V2B, 1) - 0.5, x=150.0, y=-30.0, depth=0.0, scale=1.05)
        r.key(lt(PRE2, 0) - 0.03, x=150.0, y=-30.0, depth=0.0, scale=1.05)
        r.hold(lt(V2B, 1) - 0.45, lt(PRE2, 0), 'L', lambda cv, t: P.rec_tag(cv), grip=True)
        gest(r, lt(V2B, 1) - 0.45, 'hold_L', smile=1.0, brow=0.8, lid=0.0, gaze=(0.0, 0.0), turn=0.0)
        gest(r, wt(V2B, 1, 3), 'holdup_R', smile=1.0, gaze=(0.3, -0.7))
        gest(r, lt(V2B, 2), 'hold_L', smile=0.6, gaze=(0.8, 0.0))
        gest(r, lt(V2B, 3), 'up', smile=1.0, gaze=(0.5, -0.8))
    # przedrefren 2 (panowie) + refren 2 (wszyscy) w studiu w drewnie -> show
    if i in (2, 3):
        px_ = -480.0 if i == 2 else 480.0; tg = 0.3 if i == 2 else -0.3
        r.on(lt(PRE2, 0) + 0.45 + 0.12*(i - 2), lt(CH2, 0) - 1.05, 'rise', 'sink', 0.45, 0.3)
        r.key(lt(PRE2, 0) - 0.01, x=px_, y=0.0, depth=8.0, scale=1.12)
        r.key(lt(CH2, 0) - 0.62, x=px_, y=0.0, depth=8.0, scale=1.12)
        r.key(lt(CH2, 0) - 0.6, x=float(CHOIR_X[i]), y=CHOIR_Y, depth=CHOIR_D, scale=0.8)
        r.on(lt(CH2, 0) - 0.25, lt(BR, 0), 'rise', 'none', 0.3)
        gest(r, lt(PRE2, 0), 'rest', gaze=(0.0, 0.0), brow=0.0, smile=0.0, turn=tg)
    if i in MEN:
        if i in (0, 1):
            r.on(lt(CH2, 0) - 0.7 + 0.1*i, lt(BR, 0), 'rise', 'none', 0.45)
            r.key(lt(CH2, 0) - 1.4, x=float(CHOIR_X[i]), y=CHOIR_Y, depth=CHOIR_D, scale=0.8)
        r.hold(lt(PRE2, 1) - 0.2, le(CH2, 1), 'L', lambda cv, t: P.smile_mask(cv, smoothstep((t - wt(CH2, 1, 5) + 0.05)/0.3)), grip=True)
        gest(r, lt(PRE2, 1), 'hold_L', smile=1.0, brow=0.8, lid=0.0)
        gest(r, wt(PRE2, 1, 2) - 0.1, 'hold_L', smile=1.0, gaze=(-0.8, 0.0))
        gest(r, lt(PRE2, 2), 'hold_L', smile=0.0, gaze=((1.0 if i == 2 else -1.0) if i in (2, 3) else (-1.0 if CHOIR_X[i] > 0 else 1.0), 0.3), brow=-0.4)   # patrzą na Henia
        gest(r, lt(PRE2, 3), 'hold_L', gaze=(0.0, 0.0), brow=0.3)
    else:
        r.on(lt(CH2, 0) - 0.7 + 0.1*WOMEN.index(i), lt(BR, 0), 'rise', 'none', 0.45)
        r.key(lt(CH2, 0) - 1.4, x=float(CHOIR_X[i]), y=CHOIR_Y, depth=CHOIR_D, scale=0.8)
    r.hold(lt(CH2, 0) - 0.4, lt(BR, 0) - 1.0, 'R', lambda cv, t, kind=REACT[i]: P.reaction_paddle(cv, kind, 0.85), grip=True)
    gest(r, lt(CH2, 0) - 0.3, 'hold_R', brow=0.6, lid=0.1, turn=turn_in)
    for b in hit_bars(lt(CH2, 0) - 0.1, lt(CH2, 3)):
        r.key(b - 0.06, hR=(110.0, -150.0)); r.key(b + 0.2, hR=(120.0, -330.0)); r.key(b + 0.65, hR=(110.0, -170.0))
    gest(r, lt(CH2, 3), 'rest', brow=-0.2, lid=0.4)
    for hj in [h for h in HEJ if 140 < h < 148]:
        gest(r, hj - 0.12, 'up', brow=1.0, lid=0.0); gest(r, hj + 0.5, 'hold_R')
    # refren 3 + finał: wszyscy
    r.on(lt(CH3, 0) - 0.77 + 0.06*i, FIN_HEJ + 1.0, 'rise', 'sink', 0.5, 0.5)
    r.key(lt(CH3, 0) - 1.3, x=float(CHOIR_X[i]), y=CHOIR_Y, depth=CHOIR_D, scale=0.8)
    r.hold(lt(CH3, 0) - 0.77, FIN_HEJ + 1.0, 'R', lambda cv, t, kind=REACT[i]: P.reaction_paddle(cv, kind, 0.85), grip=True)
    gest(r, lt(CH3, 0) - 0.57, 'hold_R', brow=0.7, lid=0.1)
    for b in hit_bars(lt(CH3, 0) - 0.3, lt(CH3, 3) - 0.4):
        r.key(b - 0.06, hR=(110.0, -150.0)); r.key(b + 0.2, hR=(120.0, -330.0)); r.key(b + 0.65, hR=(110.0, -170.0))
    gest(r, lt(CH3, 3), 'rest', brow=-0.2, lid=0.4)
    for hj in [h for h in HEJ if 180 < h < 190] + [FIN_HEJ]:
        gest(r, hj - 0.12, 'up', brow=1.0, lid=0.0); gest(r, hj + 0.5, 'hold_R')
    r.on(bar_at_or_before(REPRISE) + 0.4 + 0.03*i, 212.5, 'rise', 'none', 0.35)
    gest(r, REPRISE, 'hold_R'); gest(r, FINAL_HEJ - 0.08, 'up', brow=1.0)

for r in ROLES: r.build()

# ================================================================== DEKORACJE, KURTYNA
SETS = [(0.0, 'kitchen', False), (29.9, 'office', True), (lt(V1B, 2), 'conf', False), (lt(PRE1, 0), 'show', False),
        (lt(V2, 0) + 0.1, 'studio_g', True), (lt(V2, 3), 'road', False), (lt(V2B, 0) - 0.02, 'heaven', False), (lt(PRE2, 0), 'podcast', False),
        (lt(CH2, 0) - 0.85, 'show', True)]
FLY = 0.9
def sets_at(t):
    cur = None; prev = None; tsw = None; fly = False
    for ts, name, fl in SETS:
        if t >= ts: prev, cur, tsw, fly = cur, name, ts, fl
    if fly and prev is not None and t < tsw + FLY:
        a = smoothstep((t - tsw)/FLY)
        return [(prev, -1700*a), (cur, -1700*(1 - a))]
    return [(cur, 0.0)]
CURTAIN = Track([(0, 0.0), (10.85, 0.0), (13.2, 1.0), (lt(BR, 0) - 1.45, 1.0), (lt(BR, 0) - 0.05, 0.0), (lt(CH3, 0) - 1.5, 0.0), (lt(CH3, 0) + 0.05, 1.0), (300, 1.0)])

# ================================================================== REKWIZYTY SCENICZNE (poza dłońmi)
def stage_props(t):
    """Zwraca (props[(depth, fn)], back_props[(set, fn)], front_props, curtain_props)."""
    pr, front, cprops = [], [], []
    # kuchnia: laptop na krawędzi sceny (pisanie), marynarka zjeżdża na sznurkach
    if lt(V1, 2) - 0.6 <= t <= lt(V1, 3) + 0.3:
        a = min(smoothstep((t - (lt(V1, 2) - 0.6))/0.4), smoothstep((lt(V1, 3) + 0.3 - t)/0.3))
        pr.append((-15.0, lambda cv, t, a=a: (cv.translate(-80, 60*(1 - a)), P.laptop(cv, 0.8, t))))
    JON = wt(V1, 1, 1) + 0.85
    if lt(V1, 1) - 0.4 <= t <= JON + 0.95:
        if t < JON: y = -1500 + (1500 - 230)*smoothstep((t - (lt(V1, 1) - 0.4))/1.5)
        else: y = -230 - 1400*smoothstep((t - JON)/0.9)
        empty = t >= JON
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
        if name == 'show':
            pr.append((125.0, lambda cv, t, dy=dy: (cv.translate(0, dy*0.6), riser(cv, t))))
    # refren 1: balon-serce u chórzystki (pęka na 'pęka'), iskry na 'błyszczy'
    if lt(CH1, 0) - 0.5 <= t <= wt(CH1, 1, 5) + 1.0:
        pp = smoothstep((t - wt(CH1, 1, 5))/0.7) if t > wt(CH1, 1, 5) else 0.0
        pr.append((CHOIR_D - 5, lambda cv, t, pp=pp: (cv.translate(-620, CHOIR_Y - 120), P.balloon_heart(cv, pp, t))))
    for (a_, b_) in [(wt(CH1, 1, 2), wt(CH1, 1, 2) + 1.4), (wt(CH2, 1, 2), wt(CH2, 1, 2) + 1.4), (wt(CH3, 1, 2), wt(CH3, 1, 2) + 1.4)]:
        if a_ - 0.1 <= t <= b_: pr.append((-6.0, lambda cv, t, a_=a_: sparkles(cv, t, a_)))
    # studio Grażyny: ring light, kadry 'scenek', zwój 'wywodu'
    if lt(V2, 0) + 0.1 <= t <= lt(V2, 3):
        pr.append((60.0, lambda cv, t: ringlight(cv, t)))
    if wt(V2, 2, 2) - 0.1 <= t <= lt(V2, 3):
        def panels(cv, t):
            for i in range(5):
                t0 = wt(V2, 2, 2) + i*0.41
                if t < t0: continue
                a = smoothstep((t - t0)/0.18)
                px, py = PANEL_POS[i]
                cv.save(); cv.translate(px, py + 120*(1 - a)); s = 0.6 + 0.4*a; cv.scale(s, s); cv.rotate((i - 2)*3)
                P.comic_panel(cv, i); cv.restore()
        pr.append((60.0, panels))
    if wt(V2, 2, 8) - 0.2 <= t <= lt(V2, 3):
        L_ = 700*smoothstep((t - (wt(V2, 2, 8) - 0.2))/1.0)
        pr.append((100.0, lambda cv, t, L_=L_: (cv.translate(SCROLL_X, SCROLL_Y), P.scroll(cv, L_, 'i dlatego…'))))
    # droga: pieczątka RESTRUKTURYZACJA na tle po 'bruk'
    if wt(V2, 4, 8) - 0.05 <= t <= lt(V2B, 0) - 0.02:
        a = smoothstep((t - wt(V2, 4, 8))/0.08)
        pr.append((300.0, lambda cv, t, a=a: (cv.translate(180, -620), P.stamp_mark(cv, a))))
    # raj: flipchart Kasi, gwiazdki 'trzy opinie', aureola
    if lt(V2B, 0) - 0.02 <= t <= lt(PRE2, 0):
        pr.append((40.0, lambda cv, t: (cv.translate(-130, 40), P.flipchart(cv))))
    if wt(V2B, 1, 3) - 0.2 <= t <= lt(PRE2, 0):
        def stars(cv, t):
            for i in range(3):
                t0 = wt(V2B, 1, 3) + i*0.2
                if t < t0: continue
                a = smoothstep((t - t0)/0.15)
                cv.save(); cv.translate(-60 + i*170, -470 - 40*a); cv.scale(0.8*a, 0.8*a); P.rec_card(cv, i); cv.restore()
        pr.append((-5.0, stars))
    if wt(V2B, 3, 2) - 0.6 <= t <= lt(PRE2, 0):
        y = -1500 + (1500 - 520)*smoothstep((t - (wt(V2B, 3, 2) - 0.6))/0.9)
        pr.append((-4.0, lambda cv, t, y=y: (cv.translate(600, y + 30*math.sin(t*2)), P.halo(cv, 1.0))))
    # studio podcastowe: stół z mikrofonami na ramionach (prowadzący + dwóch gości)
    for name, dy in sets_at(t):
        if name == 'podcast':
            seats = [(0.0, -253.0, 1, 1.0), (-480.0, -178.0, -1, 0.85), (480.0, -178.0, 1, 0.85)]
            pr.append((-14.0, lambda cv, t, dy=dy, seats=seats: (cv.translate(0, dy*0.6), P.podcast_desk(cv, seats))))
    # bridge: tabliczka 'Robię swoje.', ozdoby, mgła, trąbka, łza
    if lt(BR, 0) - 0.5 <= t <= le(BR, 4) + 0.6:
        rev = smoothstep((t - wt(BR, 1, 4))/(wt(BR, 1, 6) + 0.4 - wt(BR, 1, 4)))
        drop = 1 - smoothstep((t - (lt(BR, 1) - 0.4))/0.5)
        if drop < 0.999: front.append((-110.0, lambda cv, t, rev=rev, drop=drop: (cv.translate(470, -170 + 18*math.sin(t*0.8) - 900*drop**1.5), P.marker_sign(cv, 'Robię swoje.', rev, 440, 200))))
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
        tr_up = smoothstep((t - (wt(BR, 4, 3) - 0.85))/0.5) * (1 - smoothstep((t - wt(BR, 4, 3))/0.5))
        if tr_up > 0.001: front.append((-108.0, lambda cv, t, a=tr_up: (cv.translate(330, 420 - 520*a), P.trumpet(cv))))
        te_up = smoothstep((t - (wt(BR, 4, 5) - 0.3))/0.4) * (1 - smoothstep((t - wt(BR, 4, 5))/0.45))
        if te_up > 0.001: front.append((-108.0, lambda cv, t, a=te_up: (cv.translate(330, 300 - 420*a), P.tear(cv))))
    # przedscenie (fartuch) gdy lalka stoi przed kurtyną
    if 2.5 <= t <= 11.0 or lt(BR, 0) - 1.1 <= t <= le(BR, 4) + 1.1:
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
    cv.drawLine(RING_X, -320, RING_X, 60, skia.Paint(AntiAlias=True, StrokeWidth=10, Color4f=P.col('#333333')))
    cv.drawCircle(RING_X, -420, 120, skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=26, Color4f=P.col('#f3eee4')))
    light_pool(cv, RING_X, -420, 170, 170, (1, 0.97, 0.9), 0.14)
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
# Kadrowanie względem postaci (jak operator w studiu TV): klucz ujęcia = wielkość planu + kto w kadrze + przesunięcia.
# Kamera liczy się z położenia postaci w danej chwili (śledzi je), a między kluczami płynnie zmienia plan.
# v4: kadr obejmuje nie tylko postaci, ale wszystko, co w danej chwili opowiada historię - trzymane tablice i karty,
# rekwizyty sceny (POI: scenki z życia, zwój, baner, flipchart...) oraz napis wersu (tablica/dymek stoi obok postaci
# i kamera kadruje postać razem z nim). Głowy innych lalek nie są ucinane krawędzią kadru: albo cała, albo wcale.
ROLE_BY = {'H': HENIO, 'G': GRAZ, 'P': PREZ, 'T': TADEK, 'M': MIREK, 'K': KASIA}
for _i, _r in enumerate(CHOIR): ROLE_BY['c%d' % _i] = _r
SIZE = {  # (udział głowy w wysokości kadru lub None, dół kadru względem linii pasa [x wysokość korpusu], górny margines)
    'CU': (0.50, None, 0.06), 'MCU': (None, -0.30, 0.10), 'MS': (None, 0.05, 0.12), 'MLS': (None, 0.55, 0.14),
    'LS': (None, 1.25, 0.16), 'WS': (None, 2.4, 0.18)}
def F(size, subj, dx=0.0, dy=0.0, roll=0.0, w=1.25, poi=(), props=True, heads=True):
    return dict(size=size, subj=subj, dx=dx, dy=dy, roll=roll, w=w, poi=list(poi), props=props, heads=heads, _boxes=[], _shift=0.0)
def _subj_list(subj, t, win=None):
    """Postaci w kadrze. Skład grupy (chór) ustalany dla całego ujęcia (win), żeby kadr nie skakał, gdy ktoś się wynurza."""
    out = []
    a, b = win if win else (t, t)
    for n in (subj if isinstance(subj, (list, tuple)) else [subj]):
        rs = CHOIR if n == 'C' else ([CHOIR[i] for i in MEN] if n == 'Cm' else ([CHOIR[i] for i in WOMEN] if n == 'Cw' else [ROLE_BY[n]]))
        for r in rs:
            vis = any(sp[0] - sp[4] <= b and a <= sp[1] + sp[5] for sp in r.spans)
            if vis or n not in ('C', 'Cm', 'Cw'): out.append(r)
    return out
def _subj_geom(r, t):
    ch = r.ch; s = r.g('scale', t)*ch.scale; x = r.g('x', t); y = r.g('y', t); d = r.g('depth', t)
    top = y + (ch.head_y + min(-ch.head_h, ch.eye_y - ch.eye_r) - (34 if ch.hair is not None else 14))*s
    return x, top, y, d, 2*ch.head_h*s, ch.head_w*1.15*s, ch.torso_h*s

# ------------------------------------------------------------------ rekwizyty sceny ważne dla kadru (POI): okno czasu, prostokąt w świecie, głębokość
JON = wt(V1, 1, 1) + 0.85
PANEL_POS = [(-400, -548), (-140, -560), (120, -548), (380, -560), (640, -548)]   # 'pięć scenek z życia': rząd jak storyboard nad Grażyną
SCROLL_X, SCROLL_Y = 900.0, -930.0
RING_X = -800.0
POI = {
    'easel': ((12.4, 29.9), (-1030, -630, -570, -280), S.D_MID),
    'jacket': ((lt(V1, 1) - 0.4, JON + 0.95), (-240, -300, 80, 20), -5.0),
    'laptop': ((lt(V1, 2) - 0.6, lt(V1, 3) + 0.3), (-272, -170, 110, 0), -15.0),
    'banner': ((wt(V1B, 0, 2) - 0.5, lt(V1B, 2)), (-505, -860, 505, -590), 260.0),
    'cloud': ((wt(V1B, 0, 4) - 0.3, lt(V1B, 2)), (0, -670, 290, -480), -8.0),
    'panels': ((wt(V2, 2, 2) - 0.1, lt(V2, 3)), (min(p[0] for p in PANEL_POS) - 115, min(p[1] for p in PANEL_POS) - 180,
                                                 max(p[0] for p in PANEL_POS) + 115, max(p[1] for p in PANEL_POS) + 10), 60.0),
    'scroll': ((wt(V2, 2, 8) - 0.2, lt(V2, 3)), (SCROLL_X - 155, S.OPEN_T, SCROLL_X + 155, SCROLL_Y + 560), 100.0),
    'stamp_mark': ((wt(V2, 4, 8) - 0.05, lt(V2B, 0)), (-230, -755, 580, -520), 300.0),
    'flipchart': ((lt(V2B, 0) - 0.02, lt(PRE2, 0)), (-335, -590, 75, 40), 40.0),
    'recs_cards': ((wt(V2B, 1, 3) - 0.2, lt(PRE2, 0)), (-160, -715, 380, -560), -5.0),
    'ringlight': ((lt(V2, 0) + 0.1, lt(V2, 3)), (RING_X - 150, -560, RING_X + 150, -280), 60.0),
    'halo': ((wt(V2B, 3, 2) - 0.6, lt(PRE2, 0)), (390, -630, 810, -410), -4.0),
    'robie': ((lt(BR, 1) - 0.4, le(BR, 4) + 0.6), (235, -375, 705, -160), -110.0),
    'trumpet': ((wt(BR, 4, 3) - 0.85, wt(BR, 4, 5) + 0.45), (255, -490, 405, -60), -108.0),
}
def poi_box(name, win):
    (a, b), rect, d = POI[name]
    if b < win[0] or a > win[1]: return None
    return (*rect, d)

# ------------------------------------------------------------------ obrys rekwizytów trzymanych w dłoniach (raster, raz na rekwizyt)
_PB = {}
def _prop_bounds(fn, t, key):
    if key in _PB: return _PB[key]
    import skia
    k = 0.25; Wp = 700
    s_ = skia.Surface(Wp, Wp); c = s_.getCanvas(); c.clear(skia.Color4f(0, 0, 0, 0)); c.translate(Wp/2, Wp*0.62); c.scale(k, k)
    try: fn(c, t)
    except Exception: pass
    a = s_.makeImageSnapshot().toarray()[..., 3]
    ys, xs = np.nonzero(a > 10)
    if len(xs) == 0: _PB[key] = None; return None
    b = ((xs.min() - Wp/2)/k, (ys.min() - Wp*0.62)/k, (xs.max() - Wp/2)/k, (ys.max() - Wp*0.62)/k)
    b = (max(b[0], -900), max(b[1], -900), min(b[2], 900), min(b[3], 300))
    _PB[key] = b; return b
_ENV = {}
def prop_env(r, win):
    """Obwiednia trzymanych rekwizytów względem (x, y) lalki w oknie ujęcia: lista prostokątów (lokalnie, już w skali)."""
    key = (id(r), round(win[0], 3), round(win[1], 3))
    if key in _ENV: return _ENV[key]
    out = []
    for hi, (a, b, side, fn, grip) in enumerate(r.holds):
        lo, hi_t = max(a, win[0]), min(b, win[1])
        if hi_t - lo < 0.15: continue
        pb = None
        for tt in (lo + 0.1, (lo + hi_t)/2, hi_t - 0.05):
            bb = _prop_bounds(fn, tt, (id(r), hi, round(tt, 1)))
            if bb: pb = bb if pb is None else (min(pb[0], bb[0]), min(pb[1], bb[1]), max(pb[2], bb[2]), max(pb[3], bb[3]))
        if pb is None or (pb[2] - pb[0])*(pb[3] - pb[1]) < 60*60: continue          # drobiazgi (telefon, kubek) nie zmieniają kadru
        env = None
        for tt in np.linspace(lo + 0.05, hi_t - 0.05, 7):
            a_ = r.actor(tt)
            if a_ is None: continue
            gx, gy = r.g('x', tt), r.g('y', tt)
            if abs(a_.y - gy) > 5 or abs(a_.x - gx) > 40: continue     # wynurzanie/chowanie, wejście z boku - nie poszerza kadru
            s_ = a_.scale*a_.ch.scale; hx, hy = a_.pose['hands'][side]
            ox, oy = a_.x - gx, a_.y - gy
            bx = (ox + (hx + pb[0])*s_*1.04, oy + (hy + pb[1])*s_*1.04, ox + (hx + pb[2])*s_*1.04, min(oy + (hy + pb[3])*s_, -gy))   # nie niżej niż krawędź sceny
            env = bx if env is None else (min(env[0], bx[0]), min(env[1], bx[1]), max(env[2], bx[2]), max(env[3], bx[3]))
        if env and env[3] > env[1]: out.append(env)
    _ENV[key] = out
    return out

def _fit(cx, cy, Hw, D, boxes, m=0.035):
    """Powiększa kadr (proporcje 16:9) tak, by objął wszystkie prostokąty (każdy na swojej głębokości) z marginesem.
    Kadr postaci jest minimum; górna krawędź zostaje (zapas nad głowami), dodatkowe miejsce idzie w dół i na boki."""
    R0 = (cx - Hw*E.W/E.H/2, cy - Hw/2, cx + Hw*E.W/E.H/2, cy + Hw/2)
    c = (cx, cy, Hw)
    for _ in range(4):
        cxx, cyy, H_ = c
        dcam = 1700.0*H_/E.H - D
        R = list(R0); mm = m*H_
        for (x0, y0, x1, y1, dp) in boxes:
            k = (dcam + D)/max(dcam + dp, 60.0)
            R = [min(R[0], cxx + (x0 - cxx)*k - mm), min(R[1], cyy + (y0 - cyy)*k - mm), max(R[2], cxx + (x1 - cxx)*k + mm), max(R[3], cyy + (y1 - cyy)*k + mm)]
        Hn = max(R[3] - R[1], (R[2] - R[0])*E.H/E.W)
        c = ((R[0] + R[2])/2, R[1] + Hn/2, Hn)
    return c
def frame_cam(spec, t, win=None, extras=True):
    rs = _subj_list(spec['subj'], t, win)
    if not rs: return None
    G_ = [_subj_geom(r, t) for r in rs]
    xl = min(g[0] - g[5] for g in G_); xr = max(g[0] + g[5] for g in G_)
    top = min(g[1] for g in G_); base = max(g[2] for g in G_); D = float(np.mean([g[3] for g in G_]))
    hh = max(g[4] for g in G_); th = max(g[6] for g in G_)
    fh, bot_k, ft = SIZE[spec['size']]
    Hh = hh/fh if fh else (base + bot_k*th - top)/(1 - ft)
    Hw = max(Hh, (xr - xl)*spec.get('w', 1.25)*E.H/E.W)
    # grupa szersza niż plan: nadmiar wysokości po połowie nad i pod grupą (nad nią zwykle chór/dekoracja, pod nią pusty
    # front sceny), ale górna krawędź kadru nie wyżej niż górna krawędź otworu sceny
    y_top = max(top - ft*Hh - 0.5*(Hw - Hh), min(top - ft*Hh, S.OPEN_T + 20.0))
    cx = (xl + xr)/2 - spec.get('dx', 0.0)*Hw*E.W/E.H
    cy = y_top + Hw/2 + spec.get('dy', 0.0)*Hw
    if extras:
        boxes = [((*b.rect(), b.depth) if hasattr(b, 'rect') else b) for b in spec.get('_boxes', [])]
        win_ = win or (t, t)
        for n in spec.get('poi', []):
            b = poi_box(n, win_)
            if b: boxes.append(b)
        if spec.get('props', True):
            for r in rs:
                x_, y_ = r.g('x', t), r.g('y', t); d_ = r.g('depth', t)
                for e in prop_env(r, win_): boxes.append((x_ + e[0], y_ + e[1], x_ + e[2], y_ + e[3], d_))
        cl, cr = xl, xr
        if boxes:
            cx, cy, Hw = _fit(cx, cy, Hw, D, boxes)
            dcam = 1700.0*Hw/E.H - D
            for (x0, y0, x1, y1, dp) in boxes:
                k = (dcam + D)/max(dcam + dp, 60.0); cl = min(cl, cx + (x0 - cx)*k); cr = max(cr, cx + (x1 - cx)*k)
        dcam = 1700.0*Hw/E.H - D; k = (dcam + D)/max(dcam + S.D_PORTAL, 60.0)
        oL, oR = cx + (S.OPEN_L - cx)*k, cx + (S.OPEN_R - cx)*k
        fw = Hw*E.W/E.H; fL, fR = cx - fw/2, cx + fw/2; mg = 0.03*fw
        if fR > oR and fL > oL: cx -= max(0.0, min(fR - oR, fL - oL, cl - mg - fL))
        elif fL < oL and fR < oR: cx += max(0.0, min(oL - fL, oR - fR, fR - mg - cr))
        cx += spec.get('_shift', 0.0)*Hw*E.W/E.H
    d = 1700.0*Hw/E.H - D
    return Cam(cx, cy, max(d, 380.0), 1700.0, spec.get('roll', 0.0))
_STATIC = {}
def _is_static(s):
    """Ujęcie, w którym kadry kluczowe (z napisem i rekwizytami) wyszły prawie takie same - dostaje powolny najazd."""
    if s[0] in _STATIC: return _STATIC[s[0]]
    if not all(isinstance(k[1], dict) for k in s[3]): _STATIC[s[0]] = False; return False
    tm = (s[0] + s[1])/2; cs = [frame_cam(k[1], tm, (s[0], s[1])) for k in s[3]]
    st = all(c is not None for c in cs) and max(abs(a.x - b.x) + abs(a.y - b.y) + abs(a.d - b.d) for a in cs for b in cs) < 60
    _STATIC[s[0]] = st; return st
def _shot_cam(t, s, extras=True):
    keys = s[3]
    if not any(isinstance(k[1], dict) for k in keys): return E.shot_cam(t, s[0], s[1], keys, 0.3)
    tau = E.ease((t - s[0])/max(s[1] - s[0], 1e-6), 0.45)
    cams = []
    for u, spec in keys:
        if not isinstance(spec, dict): cams.append((u, spec)); continue
        c = frame_cam(spec, t, (s[0], s[1]), extras) or frame_cam(spec, s[0] + 0.5*(s[1] - s[0]), (s[0], s[1]), extras)
        cams.append((u, c))
    cam = cams[-1][1]
    for (a, ca), (b, cb) in zip(cams[:-1], cams[1:]):
        if tau <= b: cam = ca.lerp(cb, (tau - a)/max(b - a, 1e-6)); break
    if extras and _is_static(s): cam = Cam(cam.x, cam.y, cam.d*(1 - 0.05*tau), cam.f, cam.roll)     # powolny najazd (5%)
    return cam

SHOTS = [
    (0.0, lt(INTRO, 0), 'feed', dict(kind='open')),
    # intro: Henio przed kurtyną, z telefonem (dymek obok - kamera kadruje oba)
    (lt(INTRO, 0), wt(INTRO, 0, 9), 'stage', [(0, F('MS', 'H')), (1, F('MCU', 'H'))]),
    (wt(INTRO, 0, 9), wt(INTRO, 0, 11), 'stage', [(0, F('MCU', 'H', roll=-1.2)), (1, F('MCU', 'H', dx=0.02))]),
    (wt(INTRO, 0, 11), lt(V1, 0), 'stage', [(0, C_(0, -380, 1500)), (0.35, C_(0, -400, 2200)), (1, C_(-40, -430, 2700))]),
    # zwrotka 1: kuchnia ('wielki plan' - sztaluga w kadrze; marynarka zjeżdża; laptop; karta-post)
    (lt(V1, 0), lt(V1, 1), 'stage', [(0, F('MS', 'H')), (0.35, F('MS', 'H', poi=['easel'])), (1, F('MS', 'H', poi=['easel']))]),
    (lt(V1, 1), lt(V1, 2), 'stage', [(0, F('MS', 'H', poi=['jacket'])), (1, F('MS', 'H', dx=-0.04))]),
    (lt(V1, 2), lt(V1, 3), 'stage', [(0, F('MS', 'H', poi=['laptop'])), (1, F('MCU', 'H', poi=['laptop']))]),
    (lt(V1, 3), lt(V1, 4), 'stage', [(0, F('MS', 'H')), (1, F('MS', 'H', dx=-0.04))]),
    (lt(V1, 4), bar_at_or_before(30.41), 'feed', dict(kind='henio_post')),
    # biuro: baner AWANS i chmurka w kadrze
    (bar_at_or_before(30.41), lt(V1B, 0), 'stage', [(0, C_(-300, -400, 2300)), (1, C_(150, -390, 1900))]),
    (lt(V1B, 0), lt(V1B, 1), 'stage', [(0, F('MS', 'H', poi=['cloud'])), (1, F('MS', 'H', poi=['banner', 'cloud']))]),
    (lt(V1B, 1), lt(V1B, 2), 'stage', [(0, F('LS', ['Cm', 'H'], w=1.08, poi=['banner'])), (1, F('MLS', ['Cm', 'H'], w=1.04, poi=['banner']))]),
    # konferencja: ścianka, flesze -> wpis prezesa z komentarzem Mirka -> z powrotem: prezes przyjmuje 'szacun'
    (lt(V1B, 2), lt(V1B, 3), 'stage', [(0, F('MLS', ['G', 'P'], w=1.4)), (1, F('MS', ['G', 'P'], w=1.3))]),
    (lt(V1B, 3), wt(V1B, 3, 5), 'feed', dict(kind='szacun')),
    (wt(V1B, 3, 5), lt(PRE1, 0), 'stage', [(0, F('MS', ['P', 'M'], w=1.2)), (1, F('MS', ['P', 'M'], w=1.15, dx=-0.02))]),
    # przedrefren 1: wielkie show
    (lt(PRE1, 0), lt(PRE1, 1), 'stage', [(0, C_(0, -700, 2500)), (1, C_(0, -450, 2700))]),
    (lt(PRE1, 1), lt(PRE1, 2), 'stage', [(0, F('LS', ['Cm', 'H'], w=1.06)), (1, F('MLS', ['Cm', 'H'], w=1.03))]),
    (lt(PRE1, 2), lt(PRE1, 3), 'stage', [(0, F('MCU', 'H')), (1, F('MCU', 'H', dx=0.02))]),
    (lt(PRE1, 3), lt(CH1, 0), 'stage', [(0, F('MS', 'H', dy=-0.12)), (1, F('MLS', 'H', dy=-0.12))]),
    # refren 1
    (lt(CH1, 0), lt(CH1, 1), 'stage', [(0, C_(0, -380, 2600)), (1, C_(0, -500, 2850))]),
    (lt(CH1, 1), lt(CH1, 2), 'stage', [(0, F('MLS', ['c2', 'c6', 'c3', 'c7'], w=1.2)), (1, F('MLS', ['c6', 'c3', 'c7'], w=1.2))]),
    (lt(CH1, 2), lt(CH1, 3), 'stage', [(0, F('MS', 'H', dx=0.05)), (1, F('MS', 'H'))]),
    (lt(CH1, 3), lt(CH1, 4), 'under', [(0, C_(-350, -170, 1800)), (1, C_(120, -90, 1500))]),
    (lt(CH1, 4), lt(CH1, 5), 'stage', [(0, F('WS', ['H', 'C'], w=1.06)), (1, F('LS', ['H', 'C'], w=1.03))]),
    (lt(CH1, 5), lt(V2, 0), 'stage', [(0, F('MLS', ['c4', 'c0', 'c5', 'c1'], w=1.2)), (1, F('MLS', ['c0', 'c5', 'c1'], w=1.2))]),
    (lt(V2, 0), lt(V2, 1), 'feed', dict(kind='to_grazyna')),
    # zwrotka 2: studio Grażyny ('pięć scenek z życia' + zwój w kadrze) -> wpis Tadka -> droga, bruk
    (lt(V2, 1), lt(V2, 2), 'stage', [(0, F('MS', 'G')), (1, F('MS', 'G', dx=0.03))]),
    (lt(V2, 2), lt(V2, 3), 'stage', [(0, F('MS', 'G', poi=['panels'])), (1, F('MS', 'G', poi=['panels', 'scroll']))]),
    (lt(V2, 3), lt(V2, 4), 'feed', dict(kind='tadek')),
    (lt(V2, 4), snap_bar(wt(V2, 4, 8)), 'stage', [(0, F('MLS', ['H', 'T', 'P'], w=1.1)), (1, F('MS', ['H', 'T', 'P'], w=1.08))]),
    (snap_bar(wt(V2, 4, 8)), lt(CHOIRI, 0), 'stage', [(0, F('MS', ['T', 'P'], w=1.15, poi=['stamp_mark'])), (1, F('MLS', ['T', 'P'], w=1.25, poi=['stamp_mark']))]),
    (lt(CHOIRI, 0), lt(V2B, 0), 'stage', [(0, F('LS', 'C', w=1.06, poi=['stamp_mark'])), (1, F('MLS', 'C', w=1.02, poi=['stamp_mark']))]),
    # zwrotka 2b: korporacyjny raj (flipchart 'case study', rekomendacje w serwisie, aureola)
    (lt(V2B, 0), lt(V2B, 1), 'stage', [(0, F('MS', 'K', poi=['flipchart'])), (1, F('MS', 'K', poi=['flipchart'], dx=0.03))]),
    (lt(V2B, 1), lt(V2B, 2), 'feed', dict(kind='recs')),
    (lt(V2B, 2), lt(V2B, 3), 'stage', [(0, F('MS', 'G', poi=['recs_cards'])), (1, F('MS', 'G', poi=['recs_cards'], dx=0.03))]),
    (lt(V2B, 3), lt(PRE2, 0), 'stage', [(0, F('MLS', ['H', 'G'], w=1.15, poi=['halo'])), (1, C_(150, -520, 2500))]),
    # przedrefren 2: studio podcastowe ('studio w drewnie') - na słowach 'studio w drewnie' odjazd na całą dekorację
    (lt(PRE2, 0), lt(PRE2, 1), 'stage', [(0, F('LS', ['c2', 'H', 'c3'], w=1.08)), (1, F('MLS', ['c2', 'H', 'c3'], w=1.04))]),
    (lt(PRE2, 1), lt(PRE2, 2), 'stage', [(0, F('MS', 'H')), (0.42, F('MS', 'H')), (1, C_(0, -470, 2650))]),
    (lt(PRE2, 2), lt(PRE2, 3), 'stage', [(0, F('MLS', ['H', 'c3'], w=1.12)), (1, F('MS', ['H', 'c3'], w=1.1))]),
    (lt(PRE2, 3), lt(CH2, 0), 'stage', [(0, F('MS', 'H')), (1, F('MLS', 'H'))]),
    # refren 2
    (lt(CH2, 0), lt(CH2, 1), 'stage', [(0, C_(0, -820, 2500)), (1, C_(0, -460, 2650))]),
    (lt(CH2, 1), lt(CH2, 2), 'stage', [(0, F('MLS', ['c4', 'c0', 'c5', 'c1'], w=1.2)), (1, F('MLS', ['c0', 'c5', 'c1'], w=1.2))]),
    (lt(CH2, 2), lt(CH2, 4), 'feed', dict(kind='analytics')),
    (lt(CH2, 4), lt(CH2, 5), 'stage', [(0, F('WS', ['H', 'C'], w=1.06)), (1, F('LS', ['H', 'C'], w=1.03))]),
    (lt(CH2, 5), lt(BR, 0), 'stage', [(0, F('MS', 'H')), (0.4, F('MLS', 'H')), (1, C_(0, -430, 2750))]),     # odjazd: kurtyna się zamyka
    # bridge: przed kurtyną, jeden reflektor; karta 'Robię swoje.' zawsze w kadrze
    (lt(BR, 0), lt(BR, 1), 'stage', [(0, F('MCU', 'H')), (1, F('MCU', 'H', dx=0.02))]),
    (lt(BR, 1), lt(BR, 2), 'stage', [(0, F('MS', 'H', poi=['robie'])), (1, F('MS', 'H', poi=['robie'], dx=0.02))]),
    (lt(BR, 2), lt(BR, 3), 'stage', [(0, F('MLS', 'H', poi=['robie'])), (1, F('MS', 'H', poi=['robie']))]),
    (lt(BR, 3), lt(BR, 4), 'stage', [(0, F('MS', 'H', poi=['robie'])), (1, F('MS', 'H', poi=['robie'], dx=-0.02))]),
    (lt(BR, 4), le(BR, 4) + 0.05, 'stage', [(0, F('MS', 'H', poi=['robie', 'trumpet'])), (1, F('MS', 'H', poi=['robie', 'trumpet']))]),
    (le(BR, 4) + 0.05, lt(CH3, 0), 'feed', dict(kind='simple_post')),
    # refren 3: majestatyczny
    (lt(CH3, 0), lt(CH3, 1), 'stage', [(0, C_(0, -580, 3800)), (1, C_(0, -470, 2900))]),
    (lt(CH3, 1), lt(CH3, 2), 'stage', [(0, F('LS', ['K', 'G', 'T', 'H', 'M', 'P'], w=1.04)), (1, F('LS', ['G', 'T', 'H', 'M'], w=1.06))]),
    (lt(CH3, 2), lt(CH3, 3), 'stage', [(0, F('MLS', ['G', 'T', 'H', 'M'], w=1.04)), (1, F('MS', ['G', 'T', 'H', 'M'], w=1.03))]),
    (lt(CH3, 3), lt(CH3, 4), 'stage', [(0, F('LS', ['H', 'C'], w=1.06)), (1, F('LS', ['H', 'C'], w=1.02))]),
    (lt(CH3, 4), lt(CH3, 5), 'stage', [(0, F('WS', ['H', 'C', 'G', 'P', 'K', 'M', 'T'], w=1.05)), (1, F('LS', ['H', 'C', 'G', 'P', 'K', 'M', 'T'], w=1.02))]),
    (lt(CH3, 5), lt(OUT, 0), 'stage', [(0, F('LS', ['H', 'T', 'M'], w=1.3)), (0.5, F('LS', ['H', 'T', 'M', 'G', 'P'], w=1.15)), (1, C_(0, -660, 3050))]),
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
def cam_at(t, s=None, extras=True):
    s = s or shot_at(t)
    if s[2] not in ('stage', 'under'): return None
    cam = _shot_cam(t, s, extras)
    # drobny 'oddech' operatora + mikro-akcent na mocnych uderzeniach
    cam.x += 3*math.sin(t*0.9) ; cam.y += 2*math.sin(t*1.3)
    cam.d *= 1 - 0.006*E.kick(t, decay=0.1)*ENERGY_CAM(t)
    return cam
from roles import ENERGY as ENERGY_CAM

# ================================================================== ŚWIATŁA
def lights_at(t, actors):
    L = dict(ambient=1.0, wash_col=(0.86, 0.82, 0.78), edge_col=(0.36, 0.32, 0.43), wash_r=1500, spots=[], beams=[], flash=0.0, key_x=-400.0)
    hen = next((a for a in actors if a.name == C.HENIO.name), None)
    sets = [n for n, _ in sets_at(t)]
    show = 'show' in sets
    if 'podcast' in sets:     # studio podcastowe: ciepłe lampy, ciemniejsze brzegi
        L.update(wash_col=(0.92, 0.82, 0.68), edge_col=(0.34, 0.27, 0.24), wash_r=1800)
    chorus = any(lt(s, 0) - 0.3 <= t <= le(s, 5) + 0.6 for s in (CH1, CH2, CH3))
    if t < 10.9:
        L.update(ambient=0.55, wash_col=(0.8, 0.55, 0.6), dim=0.0)
    if 147.6 <= t <= 166.8:
        k = smoothstep((t - 147.6)/1.2)*(1 - smoothstep((t - 166.0)/0.8))
        L.update(ambient=1 - 0.55*k, wash_col=(0.88, 0.74, 0.62))
    for a in actors:
        if a.depth <= 10 and abs(a.y) < 200:
            r = 330*a.scale*a.ch.scale
            L['spots'].append((a.x, -300*a.scale + a.y, r, (1.0, 0.92, 0.78), 0.16 if a.name != C.HENIO.name else 0.2))
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

# ================================================================== NAPISY (stałe miejsce wersu przy postaci; kamera je obejmuje)
FEED_LINES = {(V1, 4): 'chat', (V2, 0): 'chat', (V2, 3): 'chat', (V2B, 1): 'chat', (CH2, 2): 'comment', (CH2, 3): 'comment', (OUT, 0): 'comment'}
UNDER_LINES = {(CH1, 3)}
def actors_at(t):
    return [a for r in ROLES if (a := r.actor(t)) is not None]
def actor_rects(a):
    """Prostokąty lalki w świecie: głowa (z oczami i włosami), korpus nad krawędzią, każda dłoń z trzymanym rekwizytem."""
    ch = a.ch; s = a.scale*ch.scale; P_ = a.pose; out = []
    hy = ch.head_y + P_.get('nod', 0.0)
    top = hy + min(-ch.head_h, ch.eye_y - ch.eye_r) - 40
    bot = hy + ch.head_h*ch.jaw_squash + P_.get('mouth', 0.0)*ch.jaw_drop + 10
    out.append((-ch.head_w*1.15, top, ch.head_w*1.15, bot))
    out.append((-(ch.torso_w[1] + 10), -ch.torso_h - 10, ch.torso_w[1] + 10, 40))
    for side in ('L', 'R'):
        hx, hy_ = P_['hands'][side]
        out.append((hx - 45, hy_ - 45, hx + 45, hy_ + 45))
        for pr in P_['props'][side]:
            grip = pr[1] if isinstance(pr, tuple) else False
            hb = hold_bounds(*pr[2]) if isinstance(pr, tuple) and len(pr) > 2 else None
            if hb: out.append((hx + hb[0], hy_ + hb[1], hx + hb[2], hy_ + hb[3]))
            elif grip: out.append((hx - 150, hy_ - P.GRIP - 230, hx + 150, hy_))
            else: out.append((hx - 90, hy_ - 150, hx + 90, hy_ + 60))
    res = []
    for (x0, y0, x1, y1) in out:
        Y0, Y1 = a.y + y0*s, min(a.y + y1*s, 0.0)
        if Y1 <= Y0: continue
        res.append((a.x + x0*s, Y0, a.x + x1*s, Y1))
    return res
_HB = {}
def hold_bounds(r, hi):
    """Rzeczywisty obrys rekwizytu trzymanego w dłoni (z rastra, kilka chwil okna trzymania), względem dłoni."""
    if (id(r), hi) in _HB: return _HB[(id(r), hi)]
    a, b, side, fn, grip = r.holds[hi]
    pb = None
    for tt in (a + 0.1, (a + b)/2, b - 0.05):
        bb = _prop_bounds(fn, tt, (id(r), hi, round(tt, 1)))
        if bb: pb = bb if pb is None else (min(pb[0], bb[0]), min(pb[1], bb[1]), max(pb[2], bb[2]), max(pb[3], bb[3]))
    _HB[(id(r), hi)] = pb
    return pb
def head_rect(a):
    """Głowa lalki w świecie (z włosami i opadniętą szczęką), None gdy schowana pod krawędzią sceny."""
    ch = a.ch; s = a.scale*ch.scale; P_ = a.pose
    hy = ch.head_y + P_.get('nod', 0.0)
    top = hy + min(-ch.head_h, ch.eye_y - ch.eye_r) - 40
    bot = hy + ch.head_h*ch.jaw_squash + P_.get('mouth', 0.0)*ch.jaw_drop + 10
    Y0, Y1 = a.y + top*s, min(a.y + bot*s, 0.0)
    if Y1 <= Y0 + 20: return None
    return (a.x - ch.head_w*1.15*s, Y0, a.x + ch.head_w*1.15*s, Y1)
def actor_rect(a):
    """Prostokąt obejmujący (do zgrubnej kontroli)."""
    rs = actor_rects(a)
    if not rs: return (a.x, 0.0, a.x, 0.0)
    return (min(r[0] for r in rs), min(r[1] for r in rs), max(r[2] for r in rs), max(r[3] for r in rs))
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
def obstacles_at(t):
    """Rekwizyty sceniczne, których napis nie może zasłonić: (prostokąt w świecie, głębokość)."""
    ob = []
    for n, ((a, b), rect, d) in POI.items():
        if a <= t <= b and n not in ('jacket',): ob.append((rect, d))
    return ob

_SAMPLE_CACHE = {}
_OTHER = [[]]
def _sample(t):
    """Kamera, kadr i przeszkody (prostokąty postaci i ważnych rekwizytów na ekranie) w chwili t - liczone raz."""
    if t in _SAMPLE_CACHE: return _SAMPLE_CACHE[t]
    s = shot_at(t)
    if s[2] != 'stage': _SAMPLE_CACHE[t] = None; return None
    cam = cam_at(t, s)
    op = project_rect(cam, (S.OPEN_L + 20, S.OPEN_T + 30, S.OPEN_R - 20, 0), S.D_PORTAL)
    fr_in = (max(op[0], 0), max(op[1], 0), min(op[2], E.W), min(op[3], E.H))
    obs = []
    for a in actors_at(t):
        for rr in actor_rects(a): obs.append((project_rect(cam, rr, a.depth), a.depth))
    for rr, dd in obstacles_at(t): obs.append((project_rect(cam, rr, dd), -1e9))
    _SAMPLE_CACHE[t] = (cam, fr_in, obs)
    return _SAMPLE_CACHE[t]
def _score(sg, ts, vis_w=6.0):
    """Widoczność w kadrze (średnia i najgorsza chwila) i największe zasłonięcie postaci / rekwizytu / innego napisu."""
    vis, ov = [], []
    for t in ts:
        smp = _sample(t)
        if smp is None: continue
        cam, fr_in, obs = smp
        r = project_rect(cam, sg.rect(), sg.depth)
        fr = FRAME if sg.kind in ('marquee', 'playboard', 'riser') else fr_in
        vis.append(inter(r, fr)/max(area(r), 1))
        o = 0.0; ar_ = max(area(r), 1)
        for rr, dd in obs:
            # napis na zasłaniającym panelu (front sceny / podestu): lalki za panelem są w tym miejscu i tak zasłonięte
            if sg.kind in ('playboard', 'riser') and dd > sg.depth: continue
            o = max(o, inter(r, rr)/ar_)
        st_ = sg.cut_in if sg.cut_in is not None else sg.t0 - 0.4
        for og in _OTHER[0]:                                      # inny napis widoczny w tej samej chwili (poza właśnie gasnącym)
            if og.active(t) and og is not sg and og.t1 > st_ + 0.15:
                o = max(o, inter(r, project_rect(cam, og.rect(), og.depth))/ar_)
        ov.append(o)
    if not vis: return -1e9, 0, 0
    return np.mean(vis) - vis_w*(1 - min(vis)) - 20*max(ov), np.mean(vis), max(ov)

def _set_candidates(key, t_mid):
    """Ujęcia o stałej kamerze (plany ogólne show): napis jako element dekoracji - neon portalu, front podestu chóru, front sceny."""
    cam = cam_at(t_mid)
    sets = [n for n, _ in sets_at(t_mid)]
    cands = []
    if 'show' in sets:
        cands.append(('marquee', 0.0, -935.0, S.D_PORTAL, 74, {}))
        for px in (56, 48, 42):
            s_ = cam.scale(124.0)
            for yy in (CHOIR_Y + 70, CHOIR_Y + 100, CHOIR_Y + 130):
                for wf in (0.8, 0.5):
                    cands.append(('riser', cam.x, yy, 124.0, px/s_, dict(maxw=min(wf*E.W/s_, 2000))))
    apr = (2.5 <= t_mid <= 11.0) or (lt(BR, 0) - 1.0 <= t_mid <= le(BR, 4) + 1.0)
    dp = -100.5 if apr else S.D_PLAY - 0.5
    for px in (56, 48, 42):
        s_ = cam.scale(dp)
        ytxt = min(110.0, cam.y + (0.92*E.H - E.H/2)/s_)
        for wf in (0.8, 0.5):
            cands.append(('playboard', cam.x, max(ytxt, 45.0), dp, px/s_, dict(maxw=wf*E.W/s_)))
    return cands

SIGN_PX = {'CU': 62, 'MCU': 62, 'MS': 60, 'MLS': 56, 'LS': 52, 'WS': 50}
BOARD_LOOK = {'kitchen': ('#f3e5c2', '#2b1d14'), 'office': ('#e8eef4', '#1d2a44'), 'conf': ('#ffffff', '#14213d'), 'show': ('#f6e7c8', '#3a1450'),
              'studio_g': ('#fff3f7', '#7a1f4c'), 'road': ('#f3e5c2', '#3b2414'), 'heaven': ('#ffffff', '#6b5212'), 'podcast': ('#efe2cc', '#3b2a1e')}
def _line_window(key, L):
    """Od kiedy do kiedy napis wersu wisi: znika najpóźniej na cięciu po końcu wersu / przy następnym wersie,
    nie wjeżdża w ujęciu przed cięciem, nie przechodzi do przebitek (serwis, pod sceną)."""
    cut = min([s[0] for s in SHOTS if s[0] >= L['t1'] - 0.05] + [L['t1'] + 0.55])
    t_out = min(L['t1'] + 0.55, cut)
    nxt0 = min([M['t0'] for kk, M in LINES.items() if M['t0'] > L['t0'] + 0.3 and kk not in FEED_LINES and kk not in UNDER_LINES] + [1e9])
    t_out = min(t_out, max(nxt0 + 0.1, L['words'][-1]['t0'] + 0.6))
    bnd = [s_[0] for s_ in SHOTS if L['t0'] + 0.3 < s_[0] <= t_out and s_[0] >= nxt0 - 0.05]
    if bnd: t_out = min(bnd)
    cin = [s[0] for s in SHOTS if L['t0'] - 0.75 < s[0] <= L['t0'] + 0.05]
    cut_in = max(cin) if cin else None
    s0 = shot_at(L['t0'] + 0.01)
    if s0[2] != 'stage':                     # wers zaczyna się w przebitce, kończy na scenie: napis dopiero od cięcia
        cut_in = s0[1]
    t_first = cut_in + 0.02 if cut_in is not None else L['t0'] - 0.3
    t_out = min([t_out] + [s[0] for s in SHOTS if s[2] != 'stage' and t_first < s[0] < t_out])
    return t_first, t_out, cut_in

def _hosts(a, b): return [s for s in SHOTS if s[2] == 'stage' and min(s[1], b) - max(s[0], a) > 0.05]
def _frame_world(cam, depth):
    s = cam.scale(depth); return (cam.x - E.W/2/s, cam.y - E.H/2/s, cam.x + E.W/2/s, cam.y + E.H/2/s)
def _expansion(cam, rect, depth):
    """Ile razy kadr musiałby urosnąć, żeby objąć prostokąt (z marginesem)."""
    fr = _frame_world(cam, depth); m = 0.04*(fr[3] - fr[1])
    R = (min(fr[0], rect[0] - m), min(fr[1], rect[1] - m), max(fr[2], rect[2] + m), max(fr[3], rect[3] + m))
    return max((R[3] - R[1])/(fr[3] - fr[1]), (R[2] - R[0])/(fr[2] - fr[0]))
def _attach(sg, s):
    for u, spec in s[3]:
        if isinstance(spec, dict) and sg not in spec['_boxes']: spec['_boxes'].append(sg)

SIGNS = []
SIGN_REPORT = []
COMPOSED = []          # (napis, ujęcie główne, docelowa wielkość tekstu w px)
def _composed(key, L, prim, t_first, t_out, cut_in, ts):
    sec = key[0]
    win = (prim[0], prim[1])
    specs = [spec for u, spec in prim[3] if isinstance(spec, dict)]
    tmid = min(max((max(L['t0'], t_first) + min(L['t1'], t_out))/2, prim[0] + 0.05), prim[1] - 0.05)
    subj = []
    for spec in specs:
        for r in _subj_list(spec['subj'], tmid, win):
            if r not in subj: subj.append(r)
    sets = [n for n, _ in sets_at(tmid)]
    lead = any('lead' in w['singers'] for w in L['words'])
    choir_only = all(r in CHOIR for r in subj)
    if L['spoken']: kind = 'bubble'
    elif sec == BR: kind = 'marker'
    elif 'show' in sets and choir_only: kind = 'riser'
    elif 'show' in sets and len(subj) >= 2: kind = 'playboard'
    else: kind = 'board'
    anchor = [HENIO] if (HENIO in subj and lead and kind in ('bubble', 'board', 'marker')) else subj
    G_ = [(r, _subj_geom(r, tmid)) for r in anchor]
    xl = min(g[0] - g[5] for r, g in G_); xr = max(g[0] + g[5] for r, g in G_); top = min(g[1] for r, g in G_)
    D = float(np.mean([g[3] for r, g in G_])); hh = float(np.mean([g[4] for r, g in G_]))
    hc = float(np.mean([g[2] + r.ch.head_y*r.g('scale', tmid)*r.ch.scale for r, g in G_]))
    cam1 = _shot_cam(tmid, prim)
    tight = max(specs, key=lambda sp: list(SIZE).index(sp['size']) * -1)
    px = SIGN_PX[tight['size']]
    sd = {'board': D - 25, 'bubble': D - 25, 'marker': D - 25, 'riser': 124.0, 'playboard': S.D_PLAY - 0.5}[kind]
    s_ = cam1.scale(sd)
    maxw = {'board': 0.40, 'bubble': 0.46, 'marker': 0.40, 'riser': 0.8, 'playboard': 0.8}[kind]*E.W/s_
    look = BOARD_LOOK.get(sets[-1], ('#f3e5c2', '#2b1d14'))
    kw = dict(color=look[0], ink=look[1]) if kind == 'board' else {}
    if kind == 'bubble':
        r0, g0 = G_[0]
        kw['tail_to'] = (g0[0], g0[2] + (r0.ch.head_y + 0.5*r0.ch.head_h)*r0.g('scale', tmid)*r0.ch.scale)
    toks = None
    cands = []
    def mk(x, y, size=px/s_):
        sg = Sign(key, kind, x, y, sd, size, maxw=maxw, t_out=t_out, cut_in=cut_in, **kw)
        sg.layout(sg.size, tokens=sg.tokens + _extra_tokens(key))
        return sg
    proto = mk(0.0, 0.0); w, h = proto.w, proto.h
    groups = [(xl, xr, top, hc, hh)]
    if kind in ('board', 'marker') and len(anchor) < len(subj):       # napis przy całej grupie (np. wpis Grażyny, o którym śpiewa Henio)
        Gs = [(r, _subj_geom(r, tmid)) for r in subj]
        groups.append((min(g[0] - g[5] for r, g in Gs), max(g[0] + g[5] for r, g in Gs), min(g[1] for r, g in Gs),
                       float(np.mean([g[2] + r.ch.head_y*r.g('scale', tmid)*r.ch.scale for r, g in Gs])), float(np.mean([g[4] for r, g in Gs]))))
    if kind in ('board', 'bubble', 'marker'):
        for (gl, gr, gt, gc, gh) in groups:
            for side in (-1, 1):
                for g in (0.18, 0.5, 0.9):
                    x = (gl - g*gh - w/2) if side < 0 else (gr + g*gh + w/2)
                    for vy in (-0.75, -0.3, 0.15, 0.6):
                        cands.append(mk(x, gc + vy*gh))
            for fx in (-0.6, -0.3, 0.0, 0.3, 0.6):
                cands.append(mk((gl + gr)/2 + fx*w, gt - 0.12*gh - h/2))
    elif kind == 'riser':
        for yy in (CHOIR_Y + 72, CHOIR_Y + 100):
            cands.append(mk((xl + xr)/2, yy))
    else:
        for yy in (50.0, 70.0):
            cands.append(mk((xl + xr)/2, yy))
    if kind == 'bubble':
        for c in cands: c.kw['tail_to'] = kw['tail_to']
    best = None
    for sg in cands:
        sc, v, o = _score(sg, ts, vis_w=0.0)
        ex = max(_expansion(cam1, sg.rect(), sg.depth), 1.0)
        sc -= 1.6*(ex - 1.0)
        r_ = sg.rect()
        if kind in ('board', 'bubble', 'marker') and (r_[0] < S.OPEN_L + 50 or r_[2] > S.OPEN_R - 50 or r_[1] < S.OPEN_T + 25): sc -= 5.0
        if kind in ('board', 'marker') and sg.y + sg.h/2 < top: sc -= 0.03           # nad głową: tylko gdy z boku ciasno
        if best is None or sc > best[0]: best = (sc, sg, v, o)
    sg = best[1]
    return sg, px, best[3]

def _layout_signs():
    global SIGNS
    for key, L in sorted(LINES.items(), key=lambda kv: kv[1]['t0']):
        if key in FEED_LINES or key in UNDER_LINES: continue
        if key == (OUT, 1):      # finał: neon na portalu (+ powtórka na końcu)
            sg = Sign(key, 'marquee', 0.0, -935.0, S.D_PORTAL, 90, t_out=202.3)
            SIGNS.append(sg); SIGN_REPORT.append((key, 'marquee', 1.0, 0.0)); continue
        t_first, t_out, cut_in = _line_window(key, L)
        hosts = _hosts(t_first, t_out)
        if not hosts: continue
        a_, b_ = max(L['t0'], t_first), min(L['t1'], t_out)
        prim = max(hosts, key=lambda s: min(s[1], b_) - max(s[0], a_))
        ts = np.unique(np.r_[np.arange(t_first, t_out - 0.02, 0.2), [t_out - 0.03], [s[0] + 0.02 for s in SHOTS if t_first < s[0] < t_out - 0.05]])
        _OTHER[0] = [sg for sg in SIGNS if sg.t1 > L['t0'] - 0.4 and sg.kind != 'marquee']
        if any(isinstance(k[1], dict) for k in prim[3]):
            sg, px, ov = _composed(key, L, prim, t_first, t_out, cut_in, ts)
            # ujęcia poboczne (wers przechodzi przez cięcie w środku): napis zostaje tylko, jeśli jest blisko ich kadru
            for s in hosts:
                if s is prim: continue
                if any(isinstance(k[1], dict) for k in s[3]):
                    tm = (max(s[0], t_first) + min(s[1], t_out))/2
                    if _expansion(_shot_cam(tm, s), sg.rect(), sg.depth) > 1.3:
                        if s[0] > prim[0]: sg.t1 = min(sg.t1, s[0])
                        else: sg.cut_in = max(sg.cut_in or 0, s[1])
                        continue
                    _attach(sg, s)
            _attach(sg, prim)
            sg.hard_out = any(abs(s[0] - sg.t1) < 0.03 for s in SHOTS)
            COMPOSED.append((sg, prim, px))
            SIGNS.append(sg); SIGN_REPORT.append((key, sg.kind, 1.0, round(ov, 3)))
            _SAMPLE_CACHE.clear()
        else:
            best = None
            for kind, x, y, d, size, kw in _set_candidates(key, (L['t0'] + L['t1'])/2):
                kw = dict(kw); maxw = kw.pop('maxw', 1500)
                sg = Sign(key, kind, x, y, d, size, maxw=maxw, t_out=t_out, cut_in=cut_in, **kw)
                sg.layout(sg.size, tokens=sg.tokens + _extra_tokens(key))
                sc, v, o = _score(sg, ts)
                if kind == 'marquee': sc += 0.03
                if best is None or sc > best[0]: best = (sc, sg, v, o)
            best[1].hard_out = any(abs(s[0] - best[1].t1) < 0.03 for s in SHOTS)
            SIGNS.append(best[1]); SIGN_REPORT.append((key, best[1].kind, round(best[2], 2), round(best[3], 3)))
    # powtórka 'Pus-te za-się-gi! HEJ!' na końcu
    rep = Sign((OUT, 1), 'marquee', 0.0, -935.0, S.D_PORTAL, 90, t_in=REPRISE - 0.3, t_out=E.SONG_DUR + 1)
    rep.tokens = [('Puste', REPRISE), ('zasięgi!', REPRISE + 0.46), ('HEJ!', FINAL_HEJ)]
    rep.rows = [rep.tokens]; SIGNS.append(rep)
    _resize_signs()
def _resize_signs():
    """Wielkość tekstu po kadrowaniu z napisem: jeśli kamera musiała się oddalić, napis rośnie (od postaci w bok)."""
    for _ in range(2):
        for sg, prim, px in COMPOSED:
            tm = min(max((sg.t0 + sg.t1)/2, prim[0] + 0.05), prim[1] - 0.05)
            eff = sg.size*_shot_cam(tm, prim).scale(sg.depth)
            if eff < 0.85*px:
                k = min(px/eff, 1.3); w0, h0 = sg.w, sg.h
                sg.layout(sg.size*k, sg.maxw*k)
                subj = [r for u, sp in prim[3] if isinstance(sp, dict) for r in _subj_list(sp['subj'], tm, (prim[0], prim[1]))]
                if subj:
                    gx = float(np.mean([r.g('x', tm) for r in subj]))
                    sg.x += math.copysign((sg.w - w0)/2, sg.x - gx)
_layout_signs()

def _fix_heads():
    """Głowy lalek spoza kadrowanej grupy nie mogą być ucięte krawędzią (z boku/u dołu): kadr obejmuje głowę w całości
    (gdy wystarczy niewielkie oddalenie) albo przesuwa się tak, by była całkiem poza kadrem."""
    report = []
    for s in SHOTS:
        if s[2] != 'stage': continue
        win = (s[0], s[1])
        for u, spec in s[3]:
            if not isinstance(spec, dict) or not spec.get('heads', True): continue
            subj = _subj_list(spec['subj'], (s[0] + s[1])/2, win)
            D = float(np.mean([r.g('depth', (s[0] + s[1])/2) for r in subj]))
            def offenders():
                bad = {}
                for tt in np.linspace(s[0] + 0.05, s[1] - 0.05, 7):
                    cam = frame_cam(spec, tt, win)
                    if cam is None: continue
                    for r in ROLES:
                        if r in subj: continue
                        a = r.actor(tt)
                        if a is None: continue
                        hr = head_rect(a)
                        if hr is None: continue
                        pr = project_rect(cam, hr, a.depth)
                        f = inter(pr, FRAME)/max(area(pr), 1)
                        if 0.04 < f < 0.93:
                            if a.depth > D + 60: continue          # tło (statyści za kadrowaną grupą) - ucięcie krawędzią naturalne
                            bad.setdefault(r, []).append((hr, a.depth, pr, cam))
                return bad
            for it in range(3):
                bad = offenders()
                if not bad: break
                tm = (s[0] + s[1])/2
                H0 = frame_cam(spec, tm, win).d
                # 1) objąć całe głowy, jeśli kadr urośnie niewiele
                add = [(min(b[0][0] for b in v), min(b[0][1] for b in v), max(b[0][2] for b in v), max(b[0][3] for b in v), v[0][1]) for v in bad.values()]
                spec['_boxes'] += add
                H1 = frame_cam(spec, tm, win).d
                if (H1 + D)/(H0 + D) <= 1.3: report.append((round(s[0], 2), 'include', [r.ch.name for r in bad])); continue
                for b in add: spec['_boxes'].remove(b)
                # 2) wypchnąć głowy za boczną krawędź (przesunięcie kadru <= 15% szerokości)
                need = 0.0
                for r, v in bad.items():
                    for hr, dp, pr, cam in v:
                        k = cam.scale(D)/cam.scale(dp)
                        if (pr[0] + pr[2])/2 < E.W/2: need = max(need, (pr[2] + 8)/E.W*k) if need >= 0 else need
                        else: need = min(need, -(E.W - pr[0] + 8)/E.W*k) if need <= 0 else need
                if 0 < abs(need) <= 0.15:
                    spec['_shift'] += need; report.append((round(s[0], 2), 'shift', round(need, 3))); continue
                report.append((round(s[0], 2), 'left', [r.ch.name for r in bad])); break
    return report
HEADS_REPORT = _fix_heads()
_resize_signs()
_STATIC.clear(); _SAMPLE_CACHE.clear()

# ================================================================== SCENA W CHWILI t
def stage_scene(t, cam=None, signs=True):
    actors = actors_at(t)
    pr, front, cprops = stage_props(t)
    for sg in (SIGNS if signs else []):
        if sg.active(t) and sg.kind in ('playboard', 'riser'):
            front.append((sg.depth, lambda cv, t, sg=sg: sg.draw(cv, t)))
        elif sg.active(t) and sg.kind in ('board',):
            pr.append((sg.depth, lambda cv, t, sg=sg: sg.draw(cv, t)))
        elif sg.active(t) and sg.kind in ('bubble', 'marker'):
            front.append((sg.depth, lambda cv, t, sg=sg: sg.draw(cv, t)))
    marq = [sg for sg in SIGNS if signs and sg.kind == 'marquee' and sg.active(t) and t >= sg.tokens[0][1] - 0.05]   # do pierwszego słowa - tytuł show
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

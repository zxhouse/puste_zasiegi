"""Napisy końcowe po ostatnim dźwięku (wyciszenie obrazu)."""
import skia, math
import engine as E
from engine import smoothstep
from gfx import draw_text, light_pool
def render_credits(cv, t, sc):
    cv.clear(skia.Color4f(0.03, 0.02, 0.04, 1))
    u = t - E.SONG_DUR
    a = smoothstep(u/0.8)*(1 - smoothstep((u - (E.TAIL - 0.9))/0.8))
    if a <= 0.001: return
    light_pool(cv, E.W/2, E.H/2 - 40, 700, 300, (0.7, 0.35, 0.5), 0.12*a)
    draw_text(cv, 'Puste zasięgi', E.W/2, 470, 'script', 120, '#f6d47a', alpha=a)
    draw_text(cv, 'słowa i muzyka: Paweł Kuraś', E.W/2, 580, 'credits2', 40, '#efe6da', alpha=a)
    draw_text(cv, 'teledysk: Paweł Kuraś', E.W/2, 640, 'credits2', 40, '#efe6da', alpha=a)
    draw_text(cv, 'Lalki, scenografia i serwis w kadrze są fikcyjne', E.W/2, 760, 'credits2', 26, '#a89c8f', alpha=a*0.9)

"""Reakcje serwisu (Lubię to, Gratulacje, Wsparcie, Uwielbiam, Wnikliwe, Zabawne) jako jeden zestaw ikon SVG (24×24):
te same pliki są w klonie serwisu (linkedin_clone/assets/r_*.svg) i na wachlarzach, które trzymają lalki.
Kształty narysowane od nowa na wzór wyglądu reakcji w serwisie: kolorowe koło, jasny symbol, ciemniejszy detal."""
import os, skia
ICONS = {
    # nazwa: (kolor koła, elementy SVG symbolu)
    'like': ('#378fe9', '''
      <path d="M5.2 10.6h2.9v8H5.2z" fill="#0a4d93"/>
      <path d="M8.6 10.9 11.7 6.4c.6-.9 2-.5 2 .6l-.4 3.1h3.9c1.1 0 1.9 1 1.6 2.1l-1.2 4.8c-.2.9-1 1.5-1.9 1.5H8.6z" fill="#e8f3ff"/>
      <path d="M8.6 10.9h1v7.7h-1z" fill="#b9d8fb"/>'''),
    'clap': ('#6dae4f', '''
      <path d="M9.3 19 6 13.2c-.4-.7.5-1.4 1.1-.8l2 2-2.3-5.6c-.3-.8.8-1.3 1.2-.6l2.4 4.4-1.2-5.4c-.2-.9 1-1.2 1.3-.4l1.8 5.1.1-3.4c0-.9 1.2-1 1.4-.1l.6 5.4c.3 2.6-1.3 4.6-3.8 5.1z" fill="#d6ecc9"/>
      <path d="M11.6 18.6 9.3 12.9c-.3-.8.7-1.3 1.2-.6l1.5 2.2-1.4-5.8c-.2-.9 1-1.2 1.3-.4l1.9 5-.6-5.6c-.1-.9 1.2-1.1 1.4-.2l1.3 5.1.6-3.2c.2-.9 1.4-.8 1.4.1l-.2 5.6c-.1 2.6-2.2 4.4-4.7 4.5z" fill="#f1f9ec"/>
      <path d="M8.6 4.9 8 3.3M11.3 4.4V2.7M13.9 4.9l.7-1.5" stroke="#f1f9ec" stroke-width="1.1" stroke-linecap="round" fill="none"/>'''),
    'support': ('#a872e8', '''
      <path d="M12 12.4c-1.6-1.4-3.3-2.6-3.3-4.2 0-1 .8-1.8 1.8-1.8.6 0 1.2.3 1.5.8.3-.5.9-.8 1.5-.8 1 0 1.8.8 1.8 1.8 0 1.6-1.7 2.8-3.3 4.2z" fill="#ffd1e8"/>
      <path d="M4.8 13.9c.8-.6 1.8-.5 2.5.1l1.8 1.5h3.8c.8 0 1.2.8.8 1.4l-.3.2h-3.2l4 .2 3.2-2.2c.6-.4 1.5 0 1.4.8-.1.4-.3.7-.6.9l-3.6 2.5c-.6.4-1.3.6-2 .6H8.4l-3.6-2z" fill="#f2e9fd"/>'''),
    'heart': ('#df704d', '''
      <path d="M12 18.7c-3.7-3.1-6.3-5.4-6.3-8.4 0-2 1.5-3.5 3.5-3.5 1.2 0 2.2.6 2.8 1.5.6-.9 1.6-1.5 2.8-1.5 2 0 3.5 1.5 3.5 3.5 0 3-2.6 5.3-6.3 8.4z" fill="#fff1ec"/>
      <path d="M8.3 9.4c.2-.8.8-1.3 1.5-1.4" stroke="#df704d" stroke-width="1" stroke-linecap="round" fill="none" opacity=".55"/>'''),
    'idea': ('#f5bb5c', '''
      <path d="M12 5.2c-2.7 0-4.8 2.1-4.8 4.7 0 1.6.8 3 2 3.9.5.4.8 1 .8 1.6v.6h4v-.6c0-.6.3-1.2.8-1.6 1.2-.9 2-2.3 2-3.9 0-2.6-2.1-4.7-4.8-4.7z" fill="#fff8e6"/>
      <path d="M10 16.6h4v1.1h-4zM10.5 18.3h3c0 .7-.7 1.2-1.5 1.2s-1.5-.5-1.5-1.2z" fill="#9a6412"/>
      <path d="M12 15.9v-3.6l-1.2-1.4M12 12.3l1.2-1.4" stroke="#e3a33a" stroke-width=".9" stroke-linecap="round" fill="none"/>'''),
    'laugh': ('#44bfd3', '''
      <circle cx="12" cy="12.2" r="6.6" fill="#fff6d6"/>
      <path d="M9 10.6c.4-.6 1.2-.6 1.6 0M13.4 10.6c.4-.6 1.2-.6 1.6 0" stroke="#7a4b12" stroke-width="1" stroke-linecap="round" fill="none"/>
      <path d="M8.7 12.6h6.6c0 2-1.5 3.6-3.3 3.6s-3.3-1.6-3.3-3.6z" fill="#7a4b12"/>
      <path d="M10.2 15.4c.5-.6 1.1-.9 1.8-.9s1.3.3 1.8.9c-.5.5-1.1.8-1.8.8s-1.3-.3-1.8-.8z" fill="#ef6f6c"/>'''),
}
NAMES = {'like': 'Lubię to', 'clap': 'Gratulacje', 'support': 'Wsparcie', 'heart': 'Uwielbiam', 'idea': 'Wnikliwe', 'laugh': 'Zabawne'}
def svg(kind):
    bg, inner = ICONS[kind]
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24"><circle cx="12" cy="12" r="12" fill="{bg}"/>{inner}</svg>'
_DOM = {}
def draw(cv, kind, cx, cy, r):
    """Ikona reakcji wpisana w koło o środku (cx, cy) i promieniu r."""
    if kind not in _DOM:
        _DOM[kind] = skia.SVGDOM.MakeFromStream(skia.MemoryStream(svg(kind).encode()))
        _DOM[kind].setContainerSize(skia.Size(24, 24))
    cv.save(); cv.translate(cx - r, cy - r); cv.scale(r/12, r/12); _DOM[kind].render(cv); cv.restore()
def write_assets(out):
    os.makedirs(out, exist_ok=True)
    for k in ICONS: open(os.path.join(out, f'r_{k}.svg'), 'w').write(svg(k))
if __name__ == '__main__':
    write_assets(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'linkedin_clone', 'assets'))

"""Monta um GIF de prévia a partir de quadros PNG (fundo cinza, ampliação por vizinho mais próximo).

Uso: python ferramentas/montar_gif.py SAIDA.gif QUADRO1.png QUADRO2.png ... [--escala 2] [--ms 110]
"""
import argparse
from PIL import Image


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('saida'); ap.add_argument('quadros', nargs='+')
    ap.add_argument('--escala', type=int, default=2); ap.add_argument('--ms', type=int, default=110)
    ap.add_argument('--fundo', default='#a5b0b6')
    a = ap.parse_args()
    fundo = tuple(int(a.fundo.lstrip('#')[i:i + 2], 16) for i in (0, 2, 4)) + (255,)
    fs = []
    for q in a.quadros:
        im = Image.open(q).convert('RGBA')
        bg = Image.new('RGBA', im.size, fundo); bg.alpha_composite(im)
        fs.append(bg.resize((im.width * a.escala, im.height * a.escala), Image.NEAREST).convert('RGB'))
    pal = fs[0].quantize(colors=128, method=Image.MEDIANCUT)
    q = [f.quantize(palette=pal, dither=Image.NONE) for f in fs]
    q[0].save(a.saida, save_all=True, append_images=q[1:], duration=a.ms, loop=0, optimize=True)
    print('gif', a.saida, len(q), 'quadros')


if __name__ == '__main__':
    main()

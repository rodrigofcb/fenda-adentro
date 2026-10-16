"""GIF de avaliação: o personagem atravessa a tela andando para a direita, vira e volta para a esquerda.

Uso: python ferramentas/previa_passeio.py SAIDA.gif PASTA_DIREITA PASTA_ESQUERDA [--escala 2] [--ms 110] [--passo 14]
--passo: deslocamento horizontal por quadro, em pixels nativos (ajusta ao tamanho da passada para o pé não escorregar).
"""
import argparse, glob, os
from PIL import Image, ImageDraw


def carregar(pasta):
    fs = sorted(glob.glob(os.path.join(pasta, '*.png')))
    return [Image.open(f).convert('RGBA') for f in fs if not os.path.basename(f).startswith('_')]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('saida'); ap.add_argument('direita'); ap.add_argument('esquerda')
    ap.add_argument('--escala', type=int, default=2); ap.add_argument('--ms', type=int, default=110)
    ap.add_argument('--passo', type=float, default=14.0)
    a = ap.parse_args()
    dir_ = carregar(a.direita); esq = carregar(a.esquerda)
    k = a.escala
    fw, fh = dir_[0].size
    larg_nat = 720
    W, H = larg_nat * k, (fh + 40) * k
    chao = (fh + 2) * k
    quadros = []
    x = -fw
    i = 0
    while x < larg_nat:
        quadros.append(('d', dir_[i % len(dir_)], x)); x += a.passo; i += 1
    x = larg_nat; i = 0
    while x > -fw:
        quadros.append(('e', esq[i % len(esq)], x)); x -= a.passo; i += 1
    ims = []
    for lado, spr, x in quadros:
        bg = Image.new('RGBA', (W, H), (160, 172, 178, 255))
        d = ImageDraw.Draw(bg)
        d.rectangle([0, chao, W, H], fill=(110, 118, 112, 255))
        d.line([0, chao, W, chao], fill=(70, 76, 72, 255), width=k)
        for gx in range(0, W, 40 * k):
            d.line([gx, chao, gx, H], fill=(100, 108, 102, 255), width=1)
        bg.alpha_composite(spr.resize((fw * k, fh * k), Image.NEAREST), (int(round(x * k)), 20 * k))
        ims.append(bg.convert('RGB'))
    pal = ims[len(ims) // 4].quantize(colors=128, method=Image.MEDIANCUT)
    q = [im.quantize(palette=pal, dither=Image.NONE) for im in ims]
    q[0].save(a.saida, save_all=True, append_images=q[1:], duration=a.ms, loop=0, optimize=True)
    print('gif', a.saida, len(q), 'quadros', W, 'x', H)


if __name__ == '__main__':
    main()

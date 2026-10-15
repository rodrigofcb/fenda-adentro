"""Alinha quadros de uma animação num canvas comum: pés na mesma linha de base e cabeça na mesma coluna.

Uso: python ferramentas/alinhar_quadros.py PASTA_SAIDA PREFIXO QUADRO1.png QUADRO2.png ... [--linhas-cabeca 10,50]
A âncora horizontal é a mediana das colunas opacas nas linhas da cabeça (relativas ao topo do personagem).
"""
import argparse, os
import numpy as np
from PIL import Image


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('saida'); ap.add_argument('prefixo'); ap.add_argument('quadros', nargs='+')
    ap.add_argument('--linhas-cabeca', default='10,50')
    a = ap.parse_args()
    y0, y1 = map(int, a.linhas_cabeca.split(','))
    ims = [np.array(Image.open(q).convert('RGBA')) for q in a.quadros]
    info = []
    for im in ims:
        op = im[..., 3] > 0
        ys, xs = np.nonzero(op)
        topo, base = ys.min(), ys.max()
        faixa = op[topo + y0: topo + y1]
        cx = int(np.median(np.nonzero(faixa)[1]))
        info.append((topo, base, cx, xs.min(), xs.max()))
    esq = max(cx - xmin for _, _, cx, xmin, _ in info)
    dir_ = max(xmax - cx for _, _, cx, _, xmax in info)
    alt = max(base - topo for topo, base, _, _, _ in info) + 1
    W, H = esq + dir_ + 1 + 2, alt + 2
    os.makedirs(a.saida, exist_ok=True)
    for i, (im, (topo, base, cx, xmin, xmax)) in enumerate(zip(ims, info)):
        canvas = np.zeros((H, W, 4), np.uint8)
        dx = esq + 1 - cx
        dy = H - 2 - base
        sub = im[topo:base + 1, xmin:xmax + 1]
        canvas[dy + topo - topo: dy + topo - topo + sub.shape[0], dx + xmin: dx + xmin + sub.shape[1]] = sub
        Image.fromarray(canvas).save(os.path.join(a.saida, '%s_%02d.png' % (a.prefixo, i)))
    print('canvas', W, 'x', H, 'quadros', len(ims))


if __name__ == '__main__':
    main()

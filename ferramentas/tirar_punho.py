"""Apaga o punho da espada que o Gemini insiste em desenhar no quadril da vista direita.

Uso:
  python ferramentas/tirar_punho.py QUADRO.png GUIA.png SAIDA.png [--banda 92,142] [--folga 4]

GUIA é um quadro sem o punho (ex.: o quadro do boneco v3 que serviu de referência de pose). O guia é alinhado ao quadro
pelos pés e pela cabeça. Na banda do quadril, do lado da frente:
  1. o que estiver à direita da borda do guia (com folga) e não for pele da mão é apagado;
  2. junto à borda, tudo que não for túnica nem pele/creme (componentes grandes) nem cinto (corrida horizontal longa)
     é preenchido com a túnica da linha de cima/baixo.
"""
import argparse
import numpy as np
from PIL import Image
from scipy import ndimage


def hsv(rgb):
    r, g, b = [rgb[..., i] / 255.0 for i in range(3)]
    mx = np.max(rgb, 2) / 255.0; mn = np.min(rgb, 2) / 255.0
    d = mx - mn
    h = np.zeros_like(mx)
    m = d > 1e-6
    dd = np.where(m, d, 1)
    rc = (mx - r) / dd; gc = (mx - g) / dd; bc = (mx - b) / dd
    h = np.where(m & (mx == r), bc - gc, h); h = np.where(m & (mx == g), 2 + rc - bc, h); h = np.where(m & (mx == b), 4 + gc - rc, h)
    h = (h * 60) % 360
    s = np.where(mx > 0, d / np.where(mx > 0, mx, 1), 0)
    return h, s, mx


def ancora(a):
    ys, xs = np.nonzero(a)
    cab = np.nonzero(a[10:50])[1]
    return float(np.median(cab)), ys.max()


def preencher(out, alvo, fonte, H):
    for y, x in zip(*np.nonzero(alvo)):
        ok = False
        for k in range(1, 40):
            for yk in (y - k, y + k):
                if 0 <= yk < H and fonte[yk, x] and not alvo[yk, x]:
                    out[y, x] = out[yk, x]; ok = True; break
            if ok:
                break
        if not ok:
            out[y, x] = 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('quadro'); ap.add_argument('guia'); ap.add_argument('saida')
    ap.add_argument('--banda', default='92,142'); ap.add_argument('--folga', type=int, default=4)
    a = ap.parse_args()
    y0, y1 = map(int, a.banda.split(','))
    im = np.array(Image.open(a.quadro).convert('RGBA')); H, W = im.shape[:2]
    g = np.array(Image.open(a.guia).convert('RGBA'))
    op = im[..., 3] > 0; go = g[..., 3] > 0
    cx, by = ancora(op); gx, gy = ancora(go)
    dx, dy = int(round(cx - gx)), int(by - gy)
    crua = np.zeros((H, W), bool)
    ys = slice(max(0, dy), min(H, g.shape[0] + dy)); xs = slice(max(0, dx), min(W, g.shape[1] + dx))
    crua[ys, xs] = go[max(0, -dy):max(0, -dy) + (ys.stop - ys.start), max(0, -dx):max(0, -dx) + (xs.stop - xs.start)]
    crua = ndimage.binary_fill_holes(crua)
    mask = ndimage.binary_dilation(crua, iterations=a.folga)

    h, s, v = hsv(im[..., :3].astype(float))
    yy, xx = np.mgrid[0:H, 0:W]
    banda = (yy >= y0) & (yy <= y1) & (xx > cx)
    claro = (v > 0.6) & (s < 0.65) & op                       # pele, creme, aço, brilhos
    lab, n = ndimage.label(claro, structure=np.ones((3, 3)))
    grande = np.zeros_like(claro)
    if n:
        tam = ndimage.sum(claro, lab, range(1, n + 1))
        grande = np.isin(lab, np.nonzero(np.array(tam) >= 25)[0] + 1)
    tunica = (h >= 280) & (h <= 345) & (s > 0.3) & op
    # 1. fora da borda do guia
    fora = np.zeros((H, W), bool)
    for y in range(y0, y1 + 1):
        m = np.nonzero(mask[y])[0]
        if len(m):
            fora[y, m.max() + 1:] = op[y, m.max() + 1:] & banda[y, m.max() + 1:] & ~grande[y, m.max() + 1:]
    out = im.copy(); out[fora] = 0
    # 2. junto à borda: tudo que não é túnica, nem claro grande, nem cinto
    borda = mask & ~ndimage.binary_erosion(crua, iterations=2)
    cand = banda & op & borda & ~tunica & ~grande & ~fora
    fam = ((h >= 10) & (h <= 52) & (s > 0.35)) | (v < 0.3)      # marrom/dourado/escuro: família do cinto
    sobre = np.zeros((H, W), bool)
    for y, x in zip(*np.nonzero(cand)):
        l = x
        while l - 1 >= 0 and fam[y, l - 1] and op[y, l - 1]:
            l -= 1
        r = x
        while r + 1 < W and fam[y, r + 1] and op[y, r + 1]:
            r += 1
        if r - l + 1 < 12:
            sobre[y, x] = True
    preencher(out, sobre, tunica, H)
    Image.fromarray(out).save(a.saida)
    print('apagados', int(fora.sum()), 'preenchidos', int(sobre.sum()))


if __name__ == '__main__':
    main()

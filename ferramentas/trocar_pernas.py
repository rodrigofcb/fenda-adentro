"""Gera a fase oposta de uma caminhada lateral trocando o sombreado das duas pernas.

Na vista lateral, a perna próxima é desenhada com tons claros e a distante com tons escuros.
Trocar os tons entre as duas pernas faz a perna "da frente" passar a ler como a distante.

Uso: python ferramentas/trocar_pernas.py ENTRADA.png SAIDA.png [--hem 160] [--debug prefixo]
--hem: linha (a partir do topo do personagem) abaixo da qual ficam as pernas.
"""
import argparse
import numpy as np
from PIL import Image
from scipy import ndimage


def hsv(rgb):
    r, g, b = rgb[..., 0] / 255.0, rgb[..., 1] / 255.0, rgb[..., 2] / 255.0
    mx = np.maximum(np.maximum(r, g), b); mn = np.minimum(np.minimum(r, g), b); d = mx - mn + 1e-9
    h = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    s = d / (mx + 1e-9)
    return h, s, mx


def mascara_pernas(rgb, op):
    h, s, v = hsv(rgb)
    bota = ((h >= 350) | (h <= 40)) & (s > 0.58) & (v > 0.1) & (v < 0.62)
    calca = ((h >= 315) | (h <= 5)) & (s >= 0.25) & (s <= 0.58) & (v > 0.12) & (v < 0.46)
    return op & (bota | calca), bota, calca


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('entrada'); ap.add_argument('saida')
    ap.add_argument('--hem', type=int, default=160)
    ap.add_argument('--debug', default=None)
    a = ap.parse_args()
    im = np.array(Image.open(a.entrada).convert('RGBA')).astype(int)
    rgb = im[..., :3]; op = im[..., 3] > 0
    ys = np.nonzero(op.any(1))[0]; topo = ys.min()
    H, W = op.shape
    zona = np.zeros((H, W), bool); zona[topo + a.hem:] = True
    pernas, bota, calca = mascara_pernas(rgb, op)
    pernas &= zona
    # separa as duas pernas: sementes = dois maiores blocos de bota, crescidos por watershed na zona das pernas
    lab, n = ndimage.label(bota & zona, structure=np.ones((3, 3)))
    if n < 2:
        raise SystemExit('não achei duas botas')
    sz = ndimage.sum(np.ones_like(lab), lab, range(1, n + 1))
    ids = [i + 1 for i in np.argsort(sz)[::-1][:2]]
    from skimage.segmentation import watershed
    marc = np.zeros((H, W), int)
    marc[lab == ids[0]] = 1; marc[lab == ids[1]] = 2
    dist = ndimage.distance_transform_edt(~(marc > 0))
    seg = watershed(dist, marc, mask=pernas)
    # qual perna é a próxima (mais clara)
    _, _, v = hsv(rgb)
    lum = [v[seg == k].mean() for k in (1, 2)]
    perto, longe = (1, 2) if lum[0] > lum[1] else (2, 1)
    # mapeamento de tons por família (bota, calça): ordena as cores de cada perna por luminância e casa por quantil
    out = rgb.copy()
    for fam in (bota, calca):
        cp = rgb[(seg == perto) & fam]; cl = rgb[(seg == longe) & fam]
        if len(cp) < 20 or len(cl) < 20:
            continue
        def tabela(cores):
            u, cnt = np.unique(cores, axis=0, return_counts=True)
            l = u @ [0.3, 0.59, 0.11]; o = np.argsort(l); return u[o], np.cumsum(cnt[o]) / cnt.sum()
        up, qp = tabela(cp); ul, ql = tabela(cl)
        def mapear(origem_u, origem_q, destino_u, destino_q, pixels):
            # cada cor de origem vai para a cor de destino no mesmo quantil de luminância
            idx = {tuple(c): i for i, c in enumerate(origem_u)}
            res = pixels.copy()
            for i, c in enumerate(origem_u):
                j = np.searchsorted(destino_q, origem_q[i] - 1e-9); j = min(j, len(destino_u) - 1)
                res[(pixels == c).all(1)] = destino_u[j]
            return res
        m1 = (seg == perto) & fam; out[m1] = mapear(up, qp, ul, ql, rgb[m1])
        m2 = (seg == longe) & fam; out[m2] = mapear(ul, ql, up, qp, rgb[m2])
    res = im.copy(); res[..., :3] = out
    Image.fromarray(res.astype(np.uint8)).save(a.saida)
    if a.debug:
        dbg = np.zeros((H, W, 3), np.uint8) + 120; dbg[seg == perto] = (80, 200, 80); dbg[seg == longe] = (200, 80, 80)
        Image.fromarray(dbg).save(a.debug + '_seg.png')
    print('ok', a.saida, 'perna próxima=%d' % perto)


if __name__ == '__main__':
    main()

"""Transforma os passes do Blender (cor, id, profundidade) em um quadro de pixel art.

Uso: python ferramentas/pixelar.py PASTA_ENTRADA PASTA_SAIDA [--prefixo nome] [--caixa x0,y0,x1,y1]

Regras:
- contorno escuro de 1 px em volta da silhueta;
- linha interna onde muda o material (id) ou onde a profundidade dá um salto (> limiar),
  desenhada no pixel que está mais longe da câmera, em tom escuro da própria cor;
- recorte comum a todos os quadros (a caixa é a união das silhuetas), para a animação não tremer.
"""
import argparse
import os
import numpy as np
from PIL import Image

CONTORNO = np.array([0x1c, 0x10, 0x16])


def hex2rgb(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)])


def srgb_to_linear(v):
    v = v.astype(np.float64)
    return np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)


def ler_quadro(pasta, i):
    cor = np.array(Image.open(os.path.join(pasta, '%03d.png' % i)).convert('RGBA'))
    idm = np.array(Image.open(os.path.join(pasta, '%03d_id.png' % i)).convert('RGBA'))[..., 0]
    d16 = np.array(Image.open(os.path.join(pasta, '%03d_depth.png' % i)), dtype=np.float64)
    prof = srgb_to_linear(d16 / 65535.0) * 8.0          # metros (ver MapRange no material)
    return cor, idm, prof


def pixelar(cor, idm, prof, limiar_prof=0.035, forca_linha=0.62):
    rgb = cor[..., :3].astype(int)
    sil = cor[..., 3] > 127
    H, W = sil.shape
    out = rgb.copy()
    linha = np.zeros((H, W), bool)
    # linhas internas: compara cada pixel com o da direita e o de baixo
    for dy, dx in ((0, 1), (1, 0)):
        a = sil[:H - dy, :W - dx] & sil[dy:, dx:]
        muda = (idm[:H - dy, :W - dx] != idm[dy:, dx:]) | (np.abs(prof[:H - dy, :W - dx] - prof[dy:, dx:]) > limiar_prof)
        m = a & muda
        longe_e_segundo = prof[dy:, dx:] >= prof[:H - dy, :W - dx]
        l1 = np.zeros((H, W), bool); l1[dy:, dx:] = m & longe_e_segundo
        l2 = np.zeros((H, W), bool); l2[:H - dy, :W - dx] = m & ~longe_e_segundo
        linha |= l1 | l2
    out[linha] = (rgb[linha] * (1 - forca_linha) + CONTORNO * forca_linha).astype(int)
    # contorno da silhueta
    borda = sil.copy()
    borda[1:, :] &= sil[:-1, :]; borda[:-1, :] &= sil[1:, :]
    borda[:, 1:] &= sil[:, :-1]; borda[:, :-1] &= sil[:, 1:]
    borda = sil & ~borda
    out[borda] = CONTORNO
    res = np.zeros((H, W, 4), np.uint8)
    res[..., :3] = np.clip(out, 0, 255)
    res[..., 3] = sil * 255
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('entrada'); ap.add_argument('saida')
    ap.add_argument('--prefixo', default='quadro')
    ap.add_argument('--caixa', default=None, help='x0,y0,x1,y1 para forçar o recorte')
    ap.add_argument('--margem', type=int, default=1)
    a = ap.parse_args()
    os.makedirs(a.saida, exist_ok=True)
    idx = sorted(int(f[:3]) for f in os.listdir(a.entrada) if f.endswith('.png') and f[3:] == '.png')
    quadros = [pixelar(*ler_quadro(a.entrada, i)) for i in idx]
    if a.caixa:
        x0, y0, x1, y1 = map(int, a.caixa.split(','))
    else:
        uni = np.zeros(quadros[0].shape[:2], bool)
        for q in quadros:
            uni |= q[..., 3] > 0
        ys, xs = np.nonzero(uni)
        x0, x1 = max(0, xs.min() - a.margem), xs.max() + 1 + a.margem
        y0, y1 = max(0, ys.min() - a.margem), ys.max() + 1 + a.margem
    for i, q in zip(idx, quadros):
        Image.fromarray(q[y0:y1, x0:x1]).save(os.path.join(a.saida, '%s_%02d.png' % (a.prefixo, i)))
    print('quadros:', len(quadros), 'caixa:', (x0, y0, x1, y1), 'tamanho:', (x1 - x0, y1 - y0))


if __name__ == '__main__':
    main()

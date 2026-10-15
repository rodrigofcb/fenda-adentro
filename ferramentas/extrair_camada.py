"""Extrai a camada de acessórios comparando duas folhas na mesma grade.

Uso: python ferramentas/extrair_camada.py COM_ACESSORIOS SEM_ACESSORIOS PASTA_SAIDA --bloco 5.3665

As duas folhas precisam ter sido geradas a partir da mesma referência (mesma posição
dos personagens). Gera, para cada vista: o corpo sem acessórios, a camada de acessórios
(só o que difere) e uma prévia do corpo com a camada por cima.
"""
import argparse, sys, os
import numpy as np
from PIL import Image
from scipy import ndimage
sys.path.insert(0, os.path.dirname(__file__))
from snap_grid import detectar_fase, amostrar

NOMES = ['frente', 'perfil_direita', 'costas', 'perfil_esquerda']


def nativo(f, b):
    rgb = np.array(Image.open(f).convert('RGB')).astype(int)
    fx, fy = detectar_fase(rgb, b)
    return amostrar(rgb, b, fx, fy).astype(int)


def magenta(X):
    r, g, b = X[..., 0], X[..., 1], X[..., 2]
    return ((r > 200) & (g < 80) & (b > 200)) | ((r - g > 70) & (b - g > 60) & (r > 150) & (b > 120))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('com'); ap.add_argument('sem'); ap.add_argument('saida')
    ap.add_argument('--bloco', type=float, default=5.3665)
    ap.add_argument('--limiar', type=int, default=120)
    a = ap.parse_args()
    B = nativo(a.com, a.bloco); A = nativo(a.sem, a.bloco)
    h = min(A.shape[0], B.shape[0]); w = min(A.shape[1], B.shape[1]); A = A[:h, :w]; B = B[:h, :w]
    corpo = ~magenta(A)
    corpo = ndimage.binary_opening(corpo, iterations=1) | (corpo & ndimage.binary_erosion(corpo))
    lab, n = ndimage.label(corpo)
    sz = ndimage.sum(corpo, lab, range(1, n + 1))
    corpo = np.isin(lab, 1 + np.nonzero(sz > 200)[0])
    dif = (np.abs(A - B).sum(2) > a.limiar) & ~magenta(B)
    dif = ndimage.binary_opening(dif, iterations=1)
    dif = ndimage.binary_closing(dif, iterations=2) & ~magenta(B)
    lab, n = ndimage.label(dif)
    perto = ndimage.binary_dilation(corpo, iterations=2)
    manter = np.zeros(n + 1, bool)
    for i, s in enumerate(ndimage.find_objects(lab), 1):
        m = lab[s] == i
        tam = m.sum()
        encosta = (perto[s] & m).any()
        manter[i] = tam >= 25 and (encosta or tam >= 150)
    camada = manter[lab]
    # separa as quatro vistas: centros por k-means na posição x dos pixels do corpo
    from sklearn.cluster import KMeans
    xs_c = np.nonzero(corpo)[1].reshape(-1, 1).astype(float)
    cent = sorted(KMeans(4, n_init=4, random_state=0).fit(xs_c).cluster_centers_.ravel())
    X = np.arange(w)[None, :].repeat(h, 0)
    dono = np.argmin(np.abs(X[..., None] - np.array(cent)[None, None, :]), axis=2)
    os.makedirs(a.saida, exist_ok=True)
    for k, nome in enumerate(NOMES):
        mc = corpo & (dono == k); ml = camada & (dono == k)
        ys, xs = np.nonzero(mc | ml)
        y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        def rgba(src, m):
            o = np.zeros((h, w, 4), np.uint8); o[..., :3] = src; o[..., 3] = m * 255
            return o[y0:y1, x0:x1]
        Image.fromarray(rgba(A, mc)).save(f'{a.saida}/corpo_{nome}.png')
        Image.fromarray(rgba(B, ml)).save(f'{a.saida}/acessorios_{nome}.png')
        print(nome, f'{x1 - x0}x{y1 - y0}', 'pixels de acessório:', int(ml.sum()))


if __name__ == '__main__':
    main()

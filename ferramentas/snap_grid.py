"""Encaixa uma imagem de pixel art ampliada (ex.: saída do Gemini) na grade nativa.

Uso:
  python ferramentas/snap_grid.py ENTRADA SAIDA.png [--bloco N] [--cores K] [--paleta PALETA.png]

- Detecta o tamanho do bloco (pixel ampliado) e a fase da grade pelo espectro das bordas.
- Amostra o centro de cada bloco (mediana), o que elimina o borrão do JPEG.
- Fundo magenta (#FF00FF) vira transparente.
- --cores K: reduz a paleta a K cores (k-means) quando não há paleta travada.
- --paleta P: mapeia cada pixel para a cor mais próxima de uma paleta existente
  (PNG com uma linha de cores), para manter as animações com as mesmas cores da base.
"""
import argparse
import numpy as np
from PIL import Image


def detectar_bloco(rgb):
    g = rgb.sum(2)
    res = []
    for ax in (1, 0):
        d = np.abs(np.diff(g, axis=ax)).sum(axis=1 - ax).astype(float)
        d -= d.mean()
        sp = np.abs(np.fft.rfft(d))
        f = np.fft.rfftfreq(len(d))
        m = (f > 1 / 40) & (f < 1 / 3)
        res.append(1 / f[np.argmax(sp * m)])
    return float(np.mean(res))


def detectar_fase(rgb, b):
    g = rgb.sum(2)
    fases = []
    for ax in (1, 0):
        d = np.abs(np.diff(g, axis=ax)).sum(axis=1 - ax).astype(float)
        idx = np.arange(len(d))
        best, bestv = 0.0, -1
        for p in np.linspace(0, b, int(b * 4), endpoint=False):
            # bordas caem em posições p + k*b
            v = np.cos(2 * np.pi * (idx - p + 0.5) / b) @ d
            if v > bestv:
                best, bestv = p, v
        fases.append(best)
    return fases  # (fase x, fase y): posição da primeira borda


def amostrar(rgb, b, fx, fy):
    H, W = rgb.shape[:2]
    x0 = (fx + 1) % b
    y0 = (fy + 1) % b
    nx = int((W - x0) // b)
    ny = int((H - y0) // b)
    out = np.zeros((ny, nx, 3), np.uint8)
    r = max(1, int(b * 0.25))
    for j in range(ny):
        cy = int(y0 + (j + 0.5) * b)
        for i in range(nx):
            cx = int(x0 + (i + 0.5) * b)
            blk = rgb[max(0, cy - r):cy + r + 1, max(0, cx - r):cx + r + 1].reshape(-1, 3)
            out[j, i] = np.median(blk, axis=0)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("entrada")
    ap.add_argument("saida")
    ap.add_argument("--bloco", type=float)
    ap.add_argument("--cores", type=int, default=0)
    ap.add_argument("--paleta")
    ap.add_argument("--salvar-paleta")
    a = ap.parse_args()

    rgb = np.array(Image.open(a.entrada).convert("RGB")).astype(int)
    b = a.bloco or round(detectar_bloco(rgb))
    fx, fy = detectar_fase(rgb, b)
    nat = amostrar(rgb, b, fx, fy).astype(int)

    # fundo magenta -> transparente
    mag = (nat[..., 0] > 200) & (nat[..., 1] < 80) & (nat[..., 2] > 200)
    alpha = np.where(mag, 0, 255).astype(np.uint8)
    # franja: pixels de borda misturados com o magenta (rosados) também saem
    from scipy import ndimage
    r, g, bb = nat[..., 0], nat[..., 1], nat[..., 2]
    rosado = (r - g > 70) & (bb - g > 60) & (r > 150) & (bb > 120)
    for _ in range(2):
        op = alpha > 0
        borda = op & ~ndimage.binary_erosion(op)
        alpha[borda & rosado] = 0
    op = alpha > 0

    if a.paleta:
        pal = np.array(Image.open(a.paleta).convert("RGB")).reshape(-1, 3).astype(int)
    elif a.cores:
        from sklearn.cluster import KMeans
        km = KMeans(a.cores, n_init=4, random_state=0).fit(nat[op])
        pal = np.round(km.cluster_centers_).astype(int)
    else:
        pal = None
    if pal is not None:
        px = nat[op]
        d = ((px[:, None, :] - pal[None, :, :]) ** 2).sum(2)
        nat[op] = pal[d.argmin(1)]
        if a.salvar_paleta:
            usados = np.unique(nat[op], axis=0)
            ordem = np.argsort(usados @ [0.3, 0.59, 0.11])
            Image.fromarray(usados[ordem][None].astype(np.uint8)).save(a.salvar_paleta)

    # recorta à caixa do personagem com 1 px de margem
    ys, xs = np.nonzero(op)
    y0, y1 = max(0, ys.min() - 1), ys.max() + 2
    x0, x1 = max(0, xs.min() - 1), xs.max() + 2
    img = np.dstack([nat, alpha])[y0:y1, x0:x1].astype(np.uint8)
    Image.fromarray(img, "RGBA").save(a.saida)
    print(f"bloco {b} px, fase ({fx:.2f}, {fy:.2f}), nativo {x1 - x0}x{y1 - y0}, "
          f"cores {len(np.unique(img[img[..., 3] > 0][:, :3], axis=0))}")


if __name__ == "__main__":
    main()

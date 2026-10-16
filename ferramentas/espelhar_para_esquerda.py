"""Gera os quadros virados para a ESQUERDA a partir dos quadros virados para a direita.

Espelha cada quadro e troca o que muda de lado: tira a bolsa e a poção do quadril próximo
e coloca a espada (com a bainha) copiada da base de perfil esquerda. O resto espelha bem.

Uso: python ferramentas/espelhar_para_esquerda.py BASE_ESQ.png CORPO_ESQ.png SAIDA_DIR PREFIXO QUADRO1.png QUADRO2.png ...
BASE_ESQ: sprites/cisneo/base/cisneo_perfil_esquerda.png (com acessórios)
CORPO_ESQ: a mesma vista sem acessórios (mesma posição), para isolar a espada por diferença.
"""
import argparse, os
import numpy as np
from PIL import Image
from scipy import ndimage

# geometria da espada na base esquerda (coordenadas nativas da base): eixo da bainha e caixa do punho
EIXO = ((24, 120), (102, 196))
LARG = 5.5
PUNHO = (0, 32, 100, 137)        # x0, x1, y0, y1
POCAO = (20, 34, 136, 150)


def hsv(rgb):
    r, g, b = rgb[..., 0] / 255.0, rgb[..., 1] / 255.0, rgb[..., 2] / 255.0
    mx = np.maximum(np.maximum(r, g), b); mn = np.minimum(np.minimum(r, g), b); d = mx - mn + 1e-9
    h = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    return h, d / (mx + 1e-9), mx


def ancora(im):
    op = im[..., 3] > 0
    ys = np.nonzero(op.any(1))[0]; topo, base = ys.min(), ys.max()
    faixa = op[topo + 10: topo + 50]
    return int(np.median(np.nonzero(faixa)[1])), base


def camada_espada(base, corpo):
    H, W = base.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W]
    (x0, y0), (x1, y1) = EIXO
    vx, vy = x1 - x0, y1 - y0; L = np.hypot(vx, vy); vx, vy = vx / L, vy / L
    t = (xx - x0) * vx + (yy - y0) * vy
    d = np.abs(-(xx - x0) * vy + (yy - y0) * vx)
    banda = (t > -2) & (t < L + 3) & (d <= LARG)
    punho = (t > -34) & (t <= -2) & (d <= 4.0)              # cabo e pomo, ao longo do eixo
    guarda = (np.abs(t) <= 3.5) & (d <= 11)                  # guarda-mão, perpendicular
    pocao = (xx >= POCAO[0]) & (xx < POCAO[1]) & (yy >= POCAO[2]) & (yy < POCAO[3])
    regiao = banda | punho | guarda | pocao
    dif = np.abs(base[..., :3].astype(int) - corpo[..., :3].astype(int)).sum(2)
    h, s, v = hsv(base[..., :3].astype(float))
    pele = (h > 5) & (h < 35) & (s > 0.2) & (s < 0.55) & (v > 0.6)
    vidro = ((h >= 170) & (h <= 215) & (v > 0.55)) | ((h >= 300) & (h <= 345) & (s > 0.5) & (v > 0.6)) | (v > 0.85)
    esp = (banda | punho | guarda) & (dif > 25) & (base[..., 3] > 0) & ~pele
    # fica o maior componente (bainha + guarda) e os pedaços do cabo/pomo que tenham pelo menos 3 px
    lab, n = ndimage.label(esp, structure=np.ones((3, 3)))
    sz = ndimage.sum(esp, lab, range(1, n + 1))
    manter = np.zeros(n + 1, bool)
    manter[1 + int(np.argmax(sz))] = True
    for i in range(1, n + 1):
        if sz[i - 1] >= 3 and ((lab == i) & (punho | guarda)).any():
            manter[i] = True
    esp = manter[lab]
    # tapa os buracos da bainha (onde a mão cobria) copiando ao longo do eixo, no mesmo afastamento do eixo
    buraco = banda & ~esp & (base[..., 3] > 0) & (t > 6) & (t < L - 2)
    esp_f = esp.copy(); cor = base.copy()
    for y, x in zip(*np.nonzero(buraco)):
        tt = (x - x0) * vx + (y - y0) * vy; dd = -(x - x0) * vy + (y - y0) * vx
        achou = None
        for k in range(1, 16):
            for sgn in (-1, 1):
                xs_, ys_ = int(round(x0 + (tt + sgn * k) * vx - dd * vy)), int(round(y0 + (tt + sgn * k) * vy + dd * vx))
                if 0 <= xs_ < W and 0 <= ys_ < H and esp[ys_, xs_]:
                    achou = (ys_, xs_); break
            if achou: break
        if achou:
            cor[y, x] = base[achou]; esp_f[y, x] = True
    out = np.zeros_like(base); out[esp_f] = cor[esp_f]; out[..., 3] = esp_f * 255
    return out


def tirar_bolsa(fr, hx):
    """Remove bolsa e poção do quadril próximo (à esquerda do eixo da cabeça, no quadro espelhado)."""
    rgb = fr[..., :3].astype(float); op = fr[..., 3] > 0
    H, W = op.shape; yy, xx = np.mgrid[0:H, 0:W]
    op_y = np.nonzero(op.any(1))[0]; topo = op_y.min()
    h, s, v = hsv(rgb)
    caixa = (xx >= hx - 40) & (xx <= hx + 32) & (yy >= topo + 116) & (yy <= topo + 182)
    bolsa = ((h >= 238) & (h <= 292) & (s > 0.3) & (v > 0.12))
    pocao = ((h >= 170) & (h <= 215) & (v > 0.55)) | ((h >= 325) & (h <= 345) & (s > 0.5) & (v > 0.7))
    fecho = (h >= 35) & (h <= 50) & (s > 0.5) & (v > 0.6)
    m0 = caixa & op & (bolsa | pocao)
    if m0.sum() < 10:
        return fr
    topo_bolsa = np.nonzero(m0.any(1))[0].min()
    viz = ndimage.binary_dilation(m0, iterations=3) & caixa & op & (yy >= topo_bolsa - 1)
    couro = ((h >= 5) & (h <= 35) & (s > 0.3) & (v > 0.2) & (v < 0.65))
    escuro = v < 0.14
    m = m0 | (viz & (couro | escuro | fecho))
    m = ndimage.binary_closing(m, iterations=1) & caixa & op
    # contorno escuro em volta da bolsa também sai
    tun = (h >= 295) & (h <= 345) & (s > 0.3) & (v < 0.6) & op & ~m
    out = fr.copy()
    for y, x in zip(*np.nonzero(m)):
        for k in range(1, 40):
            for yy_ in (y - k, y + k):
                if 0 <= yy_ < H and tun[yy_, x] and not m[yy_, x]:
                    out[y, x] = fr[yy_, x]; break
            else:
                continue
            break
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('base'); ap.add_argument('corpo'); ap.add_argument('saida'); ap.add_argument('prefixo'); ap.add_argument('quadros', nargs='+')
    a = ap.parse_args()
    base = np.array(Image.open(a.base).convert('RGBA')); corpo = np.array(Image.open(a.corpo).convert('RGBA'))
    esp = camada_espada(base, corpo)
    bx, bb = ancora(base)
    os.makedirs(a.saida, exist_ok=True)
    Image.fromarray(esp).save(os.path.join(a.saida, '_camada_espada.png'))
    for i, q in enumerate(a.quadros):
        fr = np.array(Image.open(q).convert('RGBA'))[:, ::-1].copy()     # espelha
        hx, fb = ancora(fr)
        fr = tirar_bolsa(fr, hx)
        dx, dy = hx - bx, fb - bb
        H, W = fr.shape[:2]
        h, s, v = hsv(fr[..., :3].astype(float))
        pele = (h > 5) & (h < 35) & (s > 0.2) & (s < 0.6) & (v > 0.6)
        creme = (h > 30) & (h < 55) & (s > 0.2) & (v > 0.7)
        tat = (h > 150) & (h < 200) & (s > 0.25) & (v < 0.5)
        bota = ((h >= 350) | (h <= 40)) & (s > 0.58) & (v > 0.1) & (v < 0.62)
        frente = pele | creme | tat | bota
        ys, xs = np.nonzero(esp[..., 3] > 0)
        for y, x in zip(ys, xs):
            Y, X = y + dy, x + dx
            if 0 <= Y < H and 0 <= X < W and not frente[Y, X]:
                fr[Y, X] = esp[y, x]
        Image.fromarray(fr).save(os.path.join(a.saida, '%s_%02d.png' % (a.prefixo, i)))
    print('ok', len(a.quadros), 'quadros')


if __name__ == '__main__':
    main()

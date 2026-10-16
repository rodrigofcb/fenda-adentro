"""Caminhada por boneco de recorte a partir da base de perfil (virado para a direita).

Separa da base: tronco (frente e fundo), braço próximo e a perna próxima (coxa, cano da bota, pé).
A perna distante é a mesma perna com os tons escurecidos. As pernas são posicionadas por
cinemática inversa (mesma lógica do 3D), com os pés fixos no chão durante o apoio; o corpo
sobe e desce, o braço balança por cisalhamento e a capa oscila.

Uso: python ferramentas/boneco_caminhada.py BASE_DIREITA.png SAIDA_DIR [--quadros 16] [--passada 70] [--debug]
Saída: quadros cisneo_caminhada_direita_NN.png no mesmo canvas, e _partes.png (depuração).
"""
import argparse, math, os
import numpy as np
from PIL import Image
from scipy import ndimage

# geometria na base (99 x 257, virado para a direita)
HEM_Y = 176            # abaixo disto começam as pernas visíveis (a barra do gibão fica no tronco)
QUADRIL = (52, 150)    # pivô da coxa (escondido sob o gibão)
JOELHO_Y = 200
TORNOZELO_Y = 240
L1 = JOELHO_Y - QUADRIL[1]        # 50
L2 = TORNOZELO_Y - JOELHO_Y       # 40
OMBRO = (45, 88)       # pivô do braço próximo
MARGEM = 40            # canvas: base deslocada em x para caber a passada


def hsv(rgb):
    r, g, b = rgb[..., 0] / 255.0, rgb[..., 1] / 255.0, rgb[..., 2] / 255.0
    mx = np.maximum(np.maximum(r, g), b); mn = np.minimum(np.minimum(r, g), b); d = mx - mn + 1e-9
    h = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    return h, d / (mx + 1e-9), mx


def classes(im):
    rgb = im[..., :3].astype(float); op = im[..., 3] > 0; h, s, v = hsv(rgb)
    c = dict(
        bota=op & (((h >= 350) | (h <= 40)) & (s > 0.58) & (v > 0.1) & (v < 0.62)),
        calca=op & (((h >= 315) | (h <= 5)) & (s >= 0.25) & (s <= 0.58) & (v > 0.12) & (v < 0.46)),
        creme=op & (h > 30) & (h < 55) & (s > 0.2) & (v > 0.7),
        pele=op & (h > 5) & (h < 35) & (s > 0.2) & (s < 0.6) & (v > 0.6),
        antebraco=op & (((h >= 350) | (h <= 30)) & (s >= 0.28) & (s <= 0.52) & (v > 0.3) & (v < 0.62)) | (op & (h > 240) & (h < 290) & (s < 0.2) & (v > 0.25) & (v < 0.45)),
        capa=op & (h >= 150) & (h <= 245) & (s > 0.2),
        escuro=op & (v < 0.16),
        tunica=op & (h >= 295) & (h <= 345) & (s > 0.3) & (v < 0.6),
    )
    return op, c


def remover_punho_espada(im, sem):
    """Tira o punho da espada que o Gemini desenhou no quadril da vista direita (pela regra dos lados, a espada
    fica no quadril esquerdo, escondida). Usa a vista sem acessórios: o que sobra fora da silhueta dela vira
    transparente e o que sobrepõe o corpo recebe o pixel correspondente dela."""
    H, W = im.shape[:2]
    a = im[..., 3] > 0
    # alinha a vista sem acessórios pela silhueta do tronco
    melhor = None
    for dx in range(-6, 7):
        for dy in range(-3, 4):
            bb = np.zeros((H, W, 4), np.uint8)
            ys = slice(max(0, dy), min(H, sem.shape[0] + dy)); xs = slice(max(0, dx), min(W, sem.shape[1] + dx))
            src = sem[max(0, -dy):max(0, -dy) + (ys.stop - ys.start), max(0, -dx):max(0, -dx) + (xs.stop - xs.start)]
            bb[ys, xs] = src
            b = bb[..., 3] > 0
            r = slice(30, 100)
            sc = (a[r] & b[r]).sum() / max(1, (a[r] | b[r]).sum())
            if melhor is None or sc > melhor[0]:
                melhor = (sc, bb)
    B = melhor[1]
    b = B[..., 3] > 0
    rgb = im[..., :3].astype(float); h, s, v = hsv(rgb)
    yy, xx = np.mgrid[0:H, 0:W]
    caixa = (xx >= 60) & (yy >= 96) & (yy <= 136)
    dif = np.abs(im[..., :3].astype(int) - B[..., :3].astype(int)).sum(2)
    ouro = (h >= 28) & (h <= 52) & (s > 0.4) & (v > 0.45)
    madeira = (h >= 10) & (h <= 35) & (s > 0.35) & (v > 0.2) & (v < 0.75)
    aco = (s < 0.3) & (v > 0.4)
    escuro = v < 0.3
    fora = caixa & a & ~b
    sobre = caixa & a & b & (ouro | madeira | aco) & (dif > 60)
    m = fora | sobre
    m = m | (caixa & a & escuro & (dif > 60) & ndimage.binary_dilation(m, iterations=1))
    out = im.copy()
    out[fora] = 0
    out[m & b] = B[m & b]
    return out


def separar(im):
    """Devolve dict de camadas RGBA (mesmo tamanho da base): fundo, frente, braco, coxa, cano, pe."""
    H, W = im.shape[:2]
    op, c = classes(im)
    yy, xx = np.mgrid[0:H, 0:W]
    # --- perna próxima: botas + calça abaixo do hem, na coluna das pernas, mais o contorno escuro em volta
    zona_perna = (yy > HEM_Y) & (xx > 36) & (xx < 90)
    perna = zona_perna & (((c['bota'] | c['calca']) & ~c['tunica']) | ((yy > HEM_Y + 6) & op & ~c['capa']) | ((yy >= 248) & op))
    perna = ndimage.binary_closing(perna, iterations=2)
    perna = perna | (zona_perna & c['escuro'] & ndimage.binary_dilation(perna, iterations=1))
    perna = ndimage.binary_fill_holes(perna) & op
    coxa = perna & (yy < JOELHO_Y + 5)                    # sobrepõe o joelho para não abrir fresta
    cano = perna & (yy >= JOELHO_Y - 4) & (yy < TORNOZELO_Y)
    pe = perna & (yy >= TORNOZELO_Y)
    # --- braço próximo: manga creme + antebraço tatuado + mão, na coluna do braço
    zona_braco = (yy > OMBRO[1] - 4) & (yy < 166) & (xx > 35) & (xx < 65)
    braco = zona_braco & (c['creme'] | c['antebraco'] | c['pele'])
    braco = ndimage.binary_closing(braco, iterations=2)
    braco = braco | (zona_braco & c['escuro'] & ndimage.binary_dilation(braco, iterations=1))
    braco = ndimage.binary_fill_holes(braco) & op
    # mantém só o componente maior (evita pegar pele do rosto ou creme da capa)
    lab, n = ndimage.label(braco)
    if n > 1:
        sz = ndimage.sum(braco, lab, range(1, n + 1)); braco = lab == (1 + int(np.argmax(sz)))
    resto = op & ~perna & ~braco
    # --- preenche o buraco do braço com a túnica em volta (coluna acima/abaixo, depois lados)
    corpo = im.copy()
    tun = c['tunica'] & resto
    for y, x in zip(*np.nonzero(braco)):
        ok = False
        for k in range(1, 60):
            for yy_ in (y - k, y + k):
                if 0 <= yy_ < H and tun[yy_, x]:
                    corpo[y, x] = im[yy_, x]; ok = True; break
            if ok: break
        if not ok:
            for k in range(1, 40):
                for xx_ in (x + k, x - k):
                    if 0 <= xx_ < W and tun[y, xx_]:
                        corpo[y, x] = im[y, xx_]; ok = True; break
                if ok: break
    corpo[..., 3] = (resto | braco) * 255
    # --- fundo (capa e ponta da bainha atrás das pernas) x frente
    fundo_m = (resto | braco) & (yy > HEM_Y - 18) & (xx < 40)
    frente_m = (resto | braco) & ~fundo_m
    def camada(mask, src):
        out = np.zeros_like(src); out[mask] = src[mask]; out[..., 3] = mask * 255; return out
    return dict(fundo=camada(fundo_m, corpo), frente=camada(frente_m, corpo), braco=camada(braco, im),
                coxa=camada(coxa, im), cano=camada(cano, im), pe=camada(pe, im))


def escurecer(cam, fator=0.72):
    out = cam.copy().astype(float)
    out[..., :3] = out[..., :3] * fator
    out[..., 2] = np.minimum(255, out[..., 2] * 1.08)   # sombra puxando para o azul
    return out.astype(np.uint8)


def ik(dx, dy):
    """Ângulos (coxa, joelho) em graus para o tornozelo em (dx, dy) a partir do quadril; dx>0 frente, dy>0 baixo."""
    d = min(math.hypot(dx, dy), (L1 + L2) * 0.995)
    a = math.degrees(math.atan2(dx, dy))                      # a partir de baixo, positivo para a frente
    alpha = math.degrees(math.acos(max(-1, min(1, (L1 ** 2 + d ** 2 - L2 ** 2) / (2 * L1 * d)))))
    beta = 180 - math.degrees(math.acos(max(-1, min(1, (L1 ** 2 + L2 ** 2 - d ** 2) / (2 * L1 * L2)))))
    return a + alpha, beta


def suave(t):
    t = max(0.0, min(1.0, t)); return t * t * (3 - 2 * t)


def fase_perna(f, S, lift):
    """Posição do tornozelo (dx frente, altura acima do chão) e inclinação do pé (graus, ponta p/ cima > 0)."""
    apoio = 0.6
    if f < apoio:
        u = f / apoio
        dx = S / 2 - S * u; alt = 0.0
        pitch = 10 * (1 - suave(u / 0.3)) if u < 0.3 else -20 * suave((u - 0.55) / 0.45)
    else:
        u = (f - apoio) / (1 - apoio)
        dx = -S / 2 + S * suave(u); alt = lift * math.sin(math.pi * u)
        pitch = -20 * (1 - suave(u * 1.6)) + 10 * suave((u - 0.5) / 0.5)
    return dx, alt, pitch


def rotacionar(layer, angulo, pivo, deslocamento):
    """Gira a camada (PIL RGBA) em torno do pivô e desloca; vizinho mais próximo."""
    return layer.rotate(angulo, resample=Image.NEAREST, center=pivo, translate=deslocamento, expand=False)


def deslocar(layer, dx, dy):
    return layer.transform(layer.size, Image.AFFINE, (1, 0, -dx, 0, 1, -dy), resample=Image.NEAREST)


def cisalhar(arr, y0, k):
    """Desloca cada linha em k*(y-y0) px (cisalhamento horizontal)."""
    out = np.zeros_like(arr); H, W = arr.shape[:2]
    for y in range(H):
        d = int(round(k * (y - y0)))
        if d >= 0:
            out[y, d:] = arr[y, :W - d] if d < W else 0
        else:
            out[y, :W + d] = arr[y, -d:]
    return out


def limpar_farelo(im, minimo=6):
    """Apaga pontos soltos (componentes de alfa com menos de `minimo` px) deixados pela rotação das peças."""
    op = im[..., 3] > 0
    lab, n = ndimage.label(op, structure=np.ones((3, 3)))
    if n == 0:
        return im
    tam = ndimage.sum(op, lab, range(1, n + 1))
    pequenos = np.isin(lab, np.nonzero(tam < minimo)[0] + 1)
    out = im.copy(); out[pequenos] = 0
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('base'); ap.add_argument('saida')
    ap.add_argument('--quadros', type=int, default=16)
    ap.add_argument('--passada', type=float, default=80.0)
    ap.add_argument('--lift', type=float, default=20.0)
    ap.add_argument('--bob', type=float, default=3.0)
    ap.add_argument('--braco', type=float, default=18.0, help='amplitude do braço em graus')
    ap.add_argument('--prefixo', default='cisneo_caminhada_direita')
    ap.add_argument('--debug', action='store_true')
    ap.add_argument('--sem-acessorios', help='vista sem acessórios da mesma direção; serve para apagar o punho da espada do quadril')
    a = ap.parse_args()
    os.makedirs(a.saida, exist_ok=True)
    base = np.array(Image.open(a.base).convert('RGBA'))
    if a.sem_acessorios:
        sem = np.array(Image.open(a.sem_acessorios).convert('RGBA'))
        base = remover_punho_espada(base, sem)
    H, W = base.shape[:2]
    partes = separar(base)
    # canvas maior, base deslocada em x por MARGEM
    CW, CH = W + 2 * MARGEM, H + 8
    def em_canvas(cam):
        c = np.zeros((CH, CW, 4), np.uint8); c[4:4 + H, MARGEM:MARGEM + W] = cam; return c
    P = {k: em_canvas(v) for k, v in partes.items()}
    if a.debug:
        dbg = np.zeros((CH, CW * 6, 4), np.uint8)
        for i, k in enumerate(['fundo', 'frente', 'braco', 'coxa', 'cano', 'pe']):
            dbg[:, i * CW:(i + 1) * CW] = P[k]
        Image.fromarray(dbg).save(os.path.join(a.saida, '_partes.png'))
    quadril = (QUADRIL[0] + MARGEM, QUADRIL[1] + 4)
    joelho0 = (quadril[0], quadril[1] + L1)
    torn0 = (quadril[0], quadril[1] + L1 + L2)
    ombro = (OMBRO[0] + MARGEM, OMBRO[1] + 4)
    N = a.quadros
    for i in range(N):
        f = i / N
        bob = a.bob * math.cos(4 * math.pi * f)          # +: corpo mais baixo (contato), -: mais alto (passagem)
        hip = (quadril[0], quadril[1] + bob)
        canvas = Image.new('RGBA', (CW, CH), (0, 0, 0, 0))
        # fundo (capa) com oscilação crescente para baixo
        sway = 2.0 * math.sin(4 * math.pi * f - 1.2)
        fundo = cisalhar(P['fundo'], HEM_Y + 4, sway / 45.0)
        canvas.alpha_composite(deslocar(Image.fromarray(fundo), 0, bob))
        # pernas: distante (fase + 0.5) primeiro, depois próxima
        for lado, f0 in (('longe', 0.5), ('perto', 0.0)):
            fp = (f + f0) % 1.0
            dx, alt, pitch = fase_perna(fp, a.passada, a.lift)
            alvo = (hip[0] + dx, torn0[1] - alt)
            th, be = ik(alvo[0] - hip[0], alvo[1] - hip[1])
            th_r = math.radians(th); sh = th - be; sh_r = math.radians(sh)
            joelho = (hip[0] + L1 * math.sin(th_r), hip[1] + L1 * math.cos(th_r))
            torn = (joelho[0] + L2 * math.sin(sh_r), joelho[1] + L2 * math.cos(sh_r))
            esc = (lambda c: escurecer(c)) if lado == 'longe' else (lambda c: c)
            coxa = rotacionar(Image.fromarray(esc(P['coxa'])), th, quadril, (0, bob))
            cano = rotacionar(Image.fromarray(esc(P['cano'])), sh, joelho0, (joelho[0] - joelho0[0], joelho[1] - joelho0[1]))
            pe = rotacionar(Image.fromarray(esc(P['pe'])), pitch, torn0, (torn[0] - torn0[0], torn[1] - torn0[1]))
            canvas.alpha_composite(coxa); canvas.alpha_composite(cano); canvas.alpha_composite(pe)
        # tronco (frente)
        canvas.alpha_composite(deslocar(Image.fromarray(P['frente']), 0, bob))
        # braço próximo: oposto à perna próxima (perna na frente em f=0 -> braço atrás)
        ang = -a.braco * math.cos(2 * math.pi * f)
        braco = cisalhar(P['braco'], ombro[1], math.tan(math.radians(ang)))
        canvas.alpha_composite(deslocar(Image.fromarray(braco), 0, bob))
        canvas = Image.fromarray(limpar_farelo(np.array(canvas)))
        canvas.save(os.path.join(a.saida, '%s_%02d.png' % (a.prefixo, i)))
    print('ok', N, 'quadros', CW, 'x', CH)


if __name__ == '__main__':
    main()

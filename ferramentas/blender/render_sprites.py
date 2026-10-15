"""Renderiza o Cisneo 3D em quadros de pixel art (cor + profundidade + id de material).

Uso (com o Python do venv que tem o bpy):
  python ferramentas/blender/render_sprites.py --anim walk --dir right --out /tmp/saida [--frames 8] [--blend modelos/cisneo.blend]

Saída por quadro: NNN.png (cor RGBA, resolução nativa), NNN_depth.npy, NNN_mid.npy.
O contorno e a paleta são aplicados depois por ferramentas/pixelar.py.
"""
import argparse
import math
import os
import sys

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cisneo_modelo as cm  # noqa: E402

PX_POR_M = 144.0           # 1,80 m -> ~259 px, como o sprite aprovado
ALT_M = 2.0                # altura do enquadramento em metros
RES_Y = int(ALT_M * PX_POR_M)   # 288
RES_X = 200


def limpar_cena():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def preparar_cena(direcao):
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE'
    sc.render.resolution_x = RES_X
    sc.render.resolution_y = RES_Y
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = True
    sc.render.filter_size = 0.0
    sc.render.dither_intensity = 0.0
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA'
    sc.render.image_settings.color_depth = '8'
    sc.eevee.taa_render_samples = 1
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'
    sc.display_settings.display_device = 'sRGB'

    # câmera ortográfica
    cam_d = bpy.data.cameras.new('cam')
    cam_d.type = 'ORTHO'
    cam_d.ortho_scale = ALT_M
    cam_d.clip_start = 0.1
    cam_d.clip_end = 20
    cam = bpy.data.objects.new('cam', cam_d)
    sc.collection.objects.link(cam)
    sc.camera = cam
    zc = ALT_M / 2 - 0.1
    if direcao == 'right':      # personagem anda para a direita da tela: vemos o lado direito dele (-X)
        cam.location = (-5, 0, zc); cam.rotation_euler = (math.pi / 2, 0, -math.pi / 2)
        luz_dir = (-1.0, -0.6, 1.4)
    elif direcao == 'left':
        cam.location = (5, 0, zc); cam.rotation_euler = (math.pi / 2, 0, math.pi / 2)
        luz_dir = (1.0, -0.6, 1.4)
    elif direcao == 'front':
        cam.location = (0, -5, zc); cam.rotation_euler = (math.pi / 2, 0, 0)
        luz_dir = (-0.7, -1.0, 1.4)
    else:                        # back
        cam.location = (0, 5, zc); cam.rotation_euler = (math.pi / 2, 0, math.pi)
        luz_dir = (0.7, 1.0, 1.4)

    # sol: vem de cima, do lado da câmera e um pouco da esquerda da tela
    sun_d = bpy.data.lights.new('sol', 'SUN')
    sun_d.energy = 3.0
    sun_d.use_shadow = False
    sun = bpy.data.objects.new('sol', sun_d)
    sc.collection.objects.link(sun)
    d = np.array(luz_dir, float); d /= np.linalg.norm(d)
    # o sol aponta ao longo do seu -Z local; queremos -Z = -d (luz vindo de d)
    from mathutils import Vector
    sun.rotation_euler = Vector((-d[0], -d[1], -d[2])).to_track_quat('-Z', 'Y').to_euler()
    sc.world = bpy.data.worlds.new('mundo')
    sc.world.use_nodes = True
    bg = sc.world.node_tree.nodes['Background']
    bg.inputs['Color'].default_value = (0.25, 0.25, 0.3, 1)
    bg.inputs['Strength'].default_value = 1.0

    return cam


def render_passes(caminho_base):
    """Renderiza cor (toon), id e profundidade do quadro atual."""
    sc = bpy.context.scene
    ims = sc.render.image_settings
    cm.set_modo('toon')
    ims.color_mode = 'RGBA'; ims.color_depth = '8'
    sc.render.filepath = caminho_base + '.png'
    bpy.ops.render.render(write_still=True)
    cm.set_modo('id')
    ims.color_mode = 'RGBA'; ims.color_depth = '8'
    sc.render.filepath = caminho_base + '_id.png'
    bpy.ops.render.render(write_still=True)
    cm.set_modo('depth')
    ims.color_mode = 'BW'; ims.color_depth = '16'
    sc.render.filepath = caminho_base + '_depth.png'
    bpy.ops.render.render(write_still=True)
    cm.set_modo('toon')
    ims.color_mode = 'RGBA'; ims.color_depth = '8'


# ---------------------------------------------------------------- poses
def zerar(J):
    for k, e in J.items():
        if k == 'root':
            continue
        e.rotation_euler = (0, 0, 0)
    J['quadril'].location.z = cm.M['quadril_z']
    J['quadril'].location.y = 0.0


def pose_idle(J, t=0.0):
    zerar(J)
    # respiração leve
    J['peito'].rotation_euler.x = -0.02 + 0.01 * math.sin(2 * math.pi * t)
    J['coluna'].rotation_euler.x = -0.03
    for lado in ('L', 'R'):
        J['braco.' + lado].rotation_euler.x = 0.06
        J['braco.' + lado].rotation_euler.y = (0.12 if lado == 'L' else -0.12)
        J['antebraco.' + lado].rotation_euler.x = -0.22
        J['coxa.' + lado].rotation_euler.y = (0.03 if lado == 'L' else -0.03)


def _ik_perna(dy, dz, L1, L2):
    """Ângulos (coxa, canela) para levar o tornozelo ao deslocamento (dy, dz) a partir do quadril.
    dy>0 = trás; dz<0 = baixo. Rotações em X: r>0 leva a ponta para +Y (trás)."""
    d = math.hypot(dy, dz)
    d = min(d, (L1 + L2) * 0.999)
    a = math.atan2(-dy, -dz)                      # ângulo do vetor quadril->tornozelo a partir de -Z, positivo para a frente
    cos_a = (L1 ** 2 + d ** 2 - L2 ** 2) / (2 * L1 * d)
    alpha = math.acos(max(-1.0, min(1.0, cos_a)))
    cos_b = (L1 ** 2 + L2 ** 2 - d ** 2) / (2 * L1 * L2)
    beta = math.pi - math.acos(max(-1.0, min(1.0, cos_b)))
    coxa = -(a + alpha)
    canela = beta
    return coxa, canela


def _suave(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def pose_walk(J, fase):
    """fase em [0,1): 0 = contato do pé direito."""
    zerar(J)
    S = 0.56          # passada (m)
    H = 0.11          # altura do pé no balanço
    L1, L2 = cm.M['coxa'], cm.M['canela']
    tornozelo_z = cm.M['quadril_z'] - L1 - L2     # altura do tornozelo com a perna esticada (~0.07)
    apoio = 0.6
    bob = -0.022 * math.cos(4 * math.pi * fase)
    J['quadril'].location.z = cm.M['quadril_z'] + bob
    J['quadril'].location.y = -0.02                 # leve inclinação do corpo para a frente
    J['coluna'].rotation_euler.x = -0.06
    J['peito'].rotation_euler.z = 0.06 * math.sin(2 * math.pi * fase)
    J['cabeca'].rotation_euler.z = -J['peito'].rotation_euler.z
    J['cabeca'].rotation_euler.x = 0.03
    for lado, f0 in (('R', 0.0), ('L', 0.5)):
        f = (fase + f0) % 1.0
        if f < apoio:
            u = f / apoio
            frente = S / 2 - S * u                     # +frente no contato, -frente no desprendimento
            alt = 0.0
            pitch = math.radians(12) * (1 - _suave(u / 0.3)) if u < 0.3 else -math.radians(22) * _suave((u - 0.55) / 0.45)
        else:
            u = (f - apoio) / (1 - apoio)
            frente = -S / 2 + S * _suave(u)
            alt = H * math.sin(math.pi * u)
            pitch = -math.radians(22) * (1 - _suave(u * 1.6)) + math.radians(12) * _suave((u - 0.5) / 0.5)
        dy = -frente                                   # frente = -Y
        dz = (tornozelo_z + alt) - (cm.M['quadril_z'] + bob)
        coxa, canela = _ik_perna(dy, dz, L1, L2)
        J['coxa.' + lado].rotation_euler.x = coxa
        J['canela.' + lado].rotation_euler.x = canela
        J['pe.' + lado].rotation_euler.x = -pitch - (coxa + canela)   # pitch>0 = ponta do pé para cima
        # braço oposto à perna: perna na frente -> braço atrás (+X)
        J['braco.' + lado].rotation_euler.x = 0.45 * math.cos(2 * math.pi * f) + 0.05
        J['braco.' + lado].rotation_euler.y = (0.10 if lado == 'L' else -0.10)
        J['antebraco.' + lado].rotation_euler.x = -0.35 - 0.15 * math.cos(2 * math.pi * f)
    # capa balança um pouco atrasada em relação ao tronco
    J['capa'].rotation_euler.x = 0.10 + 0.05 * math.sin(2 * math.pi * fase - 0.8)


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--anim', default='idle', choices=['idle', 'walk'])
    ap.add_argument('--dir', default='right', choices=['right', 'left', 'front', 'back'])
    ap.add_argument('--out', required=True)
    ap.add_argument('--frames', type=int, default=8)
    ap.add_argument('--blend', default=None)
    a = ap.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:])

    os.makedirs(a.out, exist_ok=True)
    limpar_cena()
    preparar_cena(a.dir)
    J = cm.construir()
    sc = bpy.context.scene

    n = 1 if a.anim == 'idle' else a.frames
    for i in range(n):
        fase = i / n
        sc.frame_set(i + 1)          # antes da pose: senão a animação já gravada sobrescreve a pose
        if a.anim == 'idle':
            pose_idle(J)
        else:
            pose_walk(J, fase)
        for e in J.values():
            e.keyframe_insert('rotation_euler', frame=i + 1)
            e.keyframe_insert('location', frame=i + 1)
        render_passes(os.path.join(a.out, '%03d' % i))
    sc.frame_start = 1
    sc.frame_end = n
    if a.blend:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(a.blend))
    print('ok', a.anim, a.dir, n, 'quadros')


if __name__ == '__main__':
    main()

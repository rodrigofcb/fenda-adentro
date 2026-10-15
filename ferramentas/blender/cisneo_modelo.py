"""Modelo 3D do Cisneo construído por script no Blender (bpy).

Convenções:
- Unidades em metros; o personagem tem ~1,80 m de altura e fica em pé em z=0.
- Ele olha para -Y. O lado esquerdo dele é +X, o direito é -X.
- O rig é uma hierarquia de Empties (juntas). Cada malha é filha da junta que a move
  e é construída em coordenadas locais da junta (origem na articulação).
- As flexões dos membros são rotações em X; r>0 leva a ponta do membro para +Y (trás).

Juntas: root > quadril > coluna > peito > pescoco > cabeca
                 peito > ombro.L/R > braco.L/R > antebraco.L/R > mao.L/R
        quadril > coxa.L/R > canela.L/R > pe.L/R
"""
import math
import bpy
import bmesh
from mathutils import Vector, Matrix

# ---------------------------------------------------------------- paleta
# base, sombra, luz (hex). Sombras puxadas para o roxo, luzes para o amarelo,
# como na pixel art aprovada.
PALETA = {
    'pele':        ('#f29a80', '#c9735c', '#fbb8a0'),
    'cabelo':      ('#8c6d5c', '#5f4842', '#b39a88'),
    'cabelo_gris': ('#a8958f', '#7d6c6a', '#cfc2bc'),
    'barba':       ('#916a58', '#6a4a42', '#b48878'),
    'escuro':      ('#2a1a22', '#1c1016', '#3d2a35'),
    'gibao':       ('#6d2f55', '#4a1f3c', '#8e476d'),
    'ouro':        ('#d9a85a', '#a97a38', '#f2cf84'),
    'creme':       ('#f3cf96', '#c9a070', '#fbe4b9'),
    'tatuagem':    ('#2f4f4d', '#223d3b', '#4b6c67'),
    'couro':       ('#6b3a2a', '#4a261b', '#8a5038'),
    'calca':       ('#4f3444', '#392433', '#62445a'),
    'bota':        ('#7a3f28', '#562b1c', '#96563a'),
    'cano':        ('#8f4e30', '#6a3622', '#aa6440'),
    'capa_verde':  ('#336a4e', '#26513c', '#4b8a64'),
    'capa_azul':   ('#3a5a74', '#293f55', '#507596'),
    'capa_borda':  ('#a34f7c', '#733457', '#c86f9c'),
    'capuz':       ('#5b4a7a', '#41355a', '#7866a0'),
    'madeira':     ('#a56a2e', '#774a1e', '#c68c48'),
    'marfim':      ('#e9dcc2', '#bfae90', '#f8f0dd'),
    'bolsa':       ('#4d3f70', '#352b50', '#67588f'),
    'vidro':       ('#a9c8d8', '#7f9db0', '#d4e6ee'),
    'pocao':       ('#d6508a', '#a23566', '#ec7cab'),
    'branco':      ('#f6f2ea', '#cfc8bd', '#ffffff'),
    'laranja':     ('#e8902a', '#b5691c', '#f7b25a'),
}
CONTORNO = '#1c1016'


def hex2rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def srgb_to_linear(c):
    return tuple((v / 12.92) if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c)


_MATS = {}
_MID = [0]


def grupo_modo():
    """Grupo de nós compartilhado com o seletor de modo de render: 0 toon, 1 id, 2 profundidade."""
    g = bpy.data.node_groups.get('modo_sel')
    if g is None:
        g = bpy.data.node_groups.new('modo_sel', 'ShaderNodeTree')
        g.interface.new_socket('modo', in_out='OUTPUT', socket_type='NodeSocketFloat')
        out = g.nodes.new('NodeGroupOutput')
        val = g.nodes.new('ShaderNodeValue')
        val.name = 'modo'
        val.outputs[0].default_value = 0.0
        g.links.new(val.outputs[0], out.inputs[0])
    return g


def set_modo(modo):
    grupo_modo().nodes['modo'].outputs[0].default_value = {'toon': 0.0, 'id': 1.0, 'depth': 2.0}[modo]


def material(nome):
    """Material com três saídas selecionáveis: toon (3 tons chapados), id (cor única) e profundidade."""
    if nome in _MATS:
        return _MATS[nome]
    base, sombra, luz = PALETA[nome]
    m = bpy.data.materials.new(nome)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    emis = nt.nodes.new('ShaderNodeEmission')
    # --- toon
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    s2rgb = nt.nodes.new('ShaderNodeShaderToRGB')
    diff = nt.nodes.new('ShaderNodeBsdfDiffuse')
    diff.inputs['Color'].default_value = (1, 1, 1, 1)
    cr = ramp.color_ramp
    cr.interpolation = 'CONSTANT'
    cr.elements[0].position = 0.0
    cr.elements[0].color = (*srgb_to_linear(hex2rgb(sombra)), 1)
    cr.elements[1].position = 0.30
    cr.elements[1].color = (*srgb_to_linear(hex2rgb(base)), 1)
    e = cr.elements.new(0.78)
    e.color = (*srgb_to_linear(hex2rgb(luz)), 1)
    nt.links.new(diff.outputs['BSDF'], s2rgb.inputs['Shader'])
    nt.links.new(s2rgb.outputs['Color'], ramp.inputs['Fac'])
    # --- id: valor único no canal R (k/255), exato no PNG sRGB
    _MID[0] += 1
    k = _MID[0] * 5
    cor_id = nt.nodes.new('ShaderNodeRGB')
    cor_id.outputs[0].default_value = (*srgb_to_linear((k / 255, k / 255, k / 255)), 1)
    # --- profundidade: distância ao plano da câmera, mapeada de [0,8] m para [0,1]
    cam = nt.nodes.new('ShaderNodeCameraData')
    mapa = nt.nodes.new('ShaderNodeMapRange')
    mapa.inputs['From Min'].default_value = 0.0
    mapa.inputs['From Max'].default_value = 8.0
    nt.links.new(cam.outputs['View Z Depth'], mapa.inputs['Value'])
    # --- seletor
    grp = nt.nodes.new('ShaderNodeGroup')
    grp.node_tree = grupo_modo()
    f1 = nt.nodes.new('ShaderNodeClamp')
    nt.links.new(grp.outputs[0], f1.inputs['Value'])
    sub = nt.nodes.new('ShaderNodeMath')
    sub.operation = 'SUBTRACT'
    sub.inputs[1].default_value = 1.0
    nt.links.new(grp.outputs[0], sub.inputs[0])
    f2 = nt.nodes.new('ShaderNodeClamp')
    nt.links.new(sub.outputs[0], f2.inputs['Value'])
    mix1 = nt.nodes.new('ShaderNodeMix')
    mix1.data_type = 'RGBA'
    mix2 = nt.nodes.new('ShaderNodeMix')
    mix2.data_type = 'RGBA'
    nt.links.new(f1.outputs[0], mix1.inputs['Factor'])
    nt.links.new(ramp.outputs['Color'], mix1.inputs[6])
    nt.links.new(cor_id.outputs[0], mix1.inputs[7])
    nt.links.new(f2.outputs[0], mix2.inputs['Factor'])
    nt.links.new(mix1.outputs[2], mix2.inputs[6])
    nt.links.new(mapa.outputs[0], mix2.inputs[7])
    nt.links.new(mix2.outputs[2], emis.inputs['Color'])
    nt.links.new(emis.outputs['Emission'], out.inputs['Surface'])
    _MATS[nome] = m
    return m


# ---------------------------------------------------------------- geometria
def _obj_from_bmesh(nome, bm, mat, parent=None, loc=(0, 0, 0), rot=(0, 0, 0), smooth=True):
    me = bpy.data.meshes.new(nome)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(nome, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.data.materials.append(material(mat))
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    ob.location = loc
    ob.rotation_euler = rot
    if parent is not None:
        ob.parent = parent
    return ob


def loft(nome, aneis, mat, parent=None, seg=20, fechar=True, arco=(0.0, 360.0), tampas=True,
         loc=(0, 0, 0), rot=(0, 0, 0)):
    """Tubo por anéis. Cada anel: (centro(x,y,z), rx, ry[, giro_rad[, arco_do_anel]]).
    arco limita o anel a um setor (graus, 0 = frente -Y, crescendo no sentido anti-horário visto de cima);
    um anel pode ter o próprio arco (5º elemento), para a abertura variar com a altura.
    """
    bm = bmesh.new()
    completo = abs((arco[1] - arco[0]) - 360.0) < 1e-6
    n = seg if completo else seg + 1
    rings = []
    for anel in aneis:
        c, rx, ry = anel[0], anel[1], anel[2]
        giro = anel[3] if len(anel) > 3 else 0.0
        arc = anel[4] if len(anel) > 4 else arco
        a0, a1 = math.radians(arc[0]), math.radians(arc[1])
        vs = []
        for i in range(n):
            t = a0 + (a1 - a0) * (i / seg)
            # ângulo 0 aponta para -Y (frente)
            x = rx * math.sin(t)
            y = -ry * math.cos(t)
            if giro:
                x, y = x * math.cos(giro) - y * math.sin(giro), x * math.sin(giro) + y * math.cos(giro)
            vs.append(bm.verts.new((c[0] + x, c[1] + y, c[2])))
        rings.append(vs)
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(seg):
            j = (i + 1) % n if completo else i + 1
            bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
    if tampas and completo and fechar:
        bm.faces.new(rings[0][::-1])
        bm.faces.new(rings[-1])
    bm.normal_update()
    return _obj_from_bmesh(nome, bm, mat, parent, loc, rot)


def esfera(nome, mat, centro, escala, parent=None, seg=20, rot=(0, 0, 0), corte=None):
    """Elipsoide. corte: função (x,y,z)->bool que remove vértices (deixa buraco)."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2 + 2, radius=1.0)
    if corte is not None:
        rem = [v for v in bm.verts if corte(v.co.x * escala[0], v.co.y * escala[1], v.co.z * escala[2])]
        bmesh.ops.delete(bm, geom=rem, context='VERTS')
    for v in bm.verts:
        v.co = Vector((v.co.x * escala[0], v.co.y * escala[1], v.co.z * escala[2]))
    bm.normal_update()
    return _obj_from_bmesh(nome, bm, mat, parent, centro, rot)


def caixa(nome, mat, centro, dims, parent=None, rot=(0, 0, 0), arred=0.0):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * dims[0], v.co.y * dims[1], v.co.z * dims[2]))
    if arred > 0:
        bmesh.ops.bevel(bm, geom=list(bm.verts) + list(bm.edges), offset=arred, segments=2, affect='EDGES')
    bm.normal_update()
    return _obj_from_bmesh(nome, bm, mat, parent, centro, rot, smooth=False)


def toro(nome, mat, R, r, parent=None, loc=(0, 0, 0), rot=(0, 0, 0), seg=24, seg_r=8):
    """Toro com eixo em Z."""
    bm = bmesh.new()
    aneis = []
    for i in range(seg):
        t = 2 * math.pi * i / seg
        vs = []
        for j in range(seg_r):
            u = 2 * math.pi * j / seg_r
            rr = R + r * math.cos(u)
            vs.append(bm.verts.new((rr * math.cos(t), rr * math.sin(t), r * math.sin(u))))
        aneis.append(vs)
    for i in range(seg):
        a0, a1 = aneis[i], aneis[(i + 1) % seg]
        for j in range(seg_r):
            bm.faces.new((a0[j], a1[j], a1[(j + 1) % seg_r], a0[(j + 1) % seg_r]))
    bm.normal_update()
    return _obj_from_bmesh(nome, bm, mat, parent, loc, rot)


def tubo_curva(nome, mat, pontos, raio, parent=None, raio_fim=None):
    """Tubo ao longo de uma polilinha suave (curva Bezier com bevel)."""
    cu = bpy.data.curves.new(nome, 'CURVE')
    cu.dimensions = '3D'
    cu.bevel_depth = raio
    cu.bevel_resolution = 4
    cu.resolution_u = 12
    cu.use_fill_caps = True
    sp = cu.splines.new('BEZIER')
    sp.bezier_points.add(len(pontos) - 1)
    for bp, p in zip(sp.bezier_points, pontos):
        bp.co = Vector(p)
        bp.handle_left_type = bp.handle_right_type = 'AUTO'
        bp.radius = 1.0
    if raio_fim is not None:
        n = len(pontos)
        for i, bp in enumerate(sp.bezier_points):
            bp.radius = 1.0 + (raio_fim / raio - 1.0) * (i / (n - 1))
    ob = bpy.data.objects.new(nome, cu)
    bpy.context.scene.collection.objects.link(ob)
    ob.data.materials.append(material(mat))
    if parent is not None:
        ob.parent = parent
    return ob


def junta(nome, parent, loc):
    e = bpy.data.objects.new(nome, None)
    e.empty_display_size = 0.05
    e.empty_display_type = 'PLAIN_AXES'
    bpy.context.scene.collection.objects.link(e)
    e.location = loc
    if parent is not None:
        e.parent = parent
    return e


# ---------------------------------------------------------------- medidas (m)
M = dict(
    altura=1.80,
    quadril_z=0.78, quadril_x=0.09,
    coxa=0.40, canela=0.31,            # joelho em 0.38, tornozelo em 0.07
    coluna_z=0.96, peito_z=1.20, pescoco_z=1.41, cabeca_z=1.49,
    ombro_x=0.185, ombro_z=1.36,
    braco=0.29, antebraco=0.23,
    cabeca_r=(0.10, 0.108, 0.135), cabeca_c=1.62,
)


def construir():
    """Constrói o personagem completo. Devolve dict com as juntas."""
    J = {}
    J['root'] = junta('root', None, (0, 0, 0))
    J['quadril'] = junta('quadril', J['root'], (0, 0, M['quadril_z']))
    J['coluna'] = junta('coluna', J['quadril'], (0, 0, M['coluna_z'] - M['quadril_z']))
    J['peito'] = junta('peito', J['coluna'], (0, 0, M['peito_z'] - M['coluna_z']))
    J['pescoco'] = junta('pescoco', J['peito'], (0, 0, M['pescoco_z'] - M['peito_z']))
    J['cabeca'] = junta('cabeca', J['pescoco'], (0, 0, M['cabeca_z'] - M['pescoco_z']))
    for lado, sx in (('L', 1), ('R', -1)):
        J['ombro.' + lado] = junta('ombro.' + lado, J['peito'], (sx * M['ombro_x'], 0, M['ombro_z'] - M['peito_z']))
        J['braco.' + lado] = junta('braco.' + lado, J['ombro.' + lado], (0, 0, 0))
        J['antebraco.' + lado] = junta('antebraco.' + lado, J['braco.' + lado], (0, 0, -M['braco']))
        J['mao.' + lado] = junta('mao.' + lado, J['antebraco.' + lado], (0, 0, -M['antebraco']))
        J['coxa.' + lado] = junta('coxa.' + lado, J['quadril'], (sx * M['quadril_x'], 0, 0))
        J['canela.' + lado] = junta('canela.' + lado, J['coxa.' + lado], (0, 0, -M['coxa']))
        J['pe.' + lado] = junta('pe.' + lado, J['canela.' + lado], (0, 0, -M['canela']))
    J['capa'] = junta('capa', J['peito'], (0, 0.02, M['ombro_z'] + 0.04 - M['peito_z']))

    _cabeca(J)
    _tronco(J)
    _bracos(J)
    _pernas(J)
    _capa(J)
    _acessorios(J)
    _cisne(J)
    return J


# ---------------------------------------------------------------- partes
def _cabeca(J):
    p = J['cabeca']
    cz = M['cabeca_c'] - M['cabeca_z']          # centro da cabeça relativo à junta
    rx, ry, rz = M['cabeca_r']
    esfera('cabeca', 'pele', (0, 0, cz), (rx, ry, rz), p)
    # pescoço
    loft('pescoco', [((0, 0.01, -0.09), 0.052, 0.05), ((0, 0.01, 0.02), 0.052, 0.05)], 'pele', p)
    # cabelo: casca um pouco maior, sem a parte da frente abaixo da testa e sem a nuca baixa
    linha_testa = 0.055                         # z relativo ao centro da cabeça
    linha_lado = -0.03

    def corte_cabelo(x, y, z):
        if y < -0.03:                           # frente
            return z < linha_testa
        return z < linha_lado
    esfera('cabelo', 'cabelo', (0, 0.01, cz + 0.012), (rx + 0.01, ry + 0.012, rz + 0.022), p, corte=corte_cabelo)
    # topete
    esfera('topete', 'cabelo', (0.0, -0.04, cz + 0.15), (0.075, 0.08, 0.04), p, rot=(math.radians(20), 0, 0))
    # sobrancelhas
    for sx in (1, -1):
        caixa('sobrancelha%d' % sx, 'cabelo', (sx * 0.045, -ry - 0.008, cz + 0.035), (0.045, 0.01, 0.012), p, rot=(0, sx * math.radians(-8), 0))
    # laterais grisalhas (acima das orelhas)
    for sx in (1, -1):
        esfera('gris.' + ('L' if sx > 0 else 'R'), 'cabelo_gris', (sx * (rx + 0.004), 0.005, cz + 0.02), (0.018, 0.075, 0.055), p)
    # barba: casca fina sobre a metade de baixo do rosto (maxilar e queixo), sem a nuca
    esfera('barba', 'barba', (0, 0.0, cz), (rx + 0.012, ry + 0.012, rz + 0.012), p,
           corte=lambda x, y, z: (z > -0.03) or (y > 0.03) or (z > -0.07 and y > -0.07 and abs(x) < 0.04))
    esfera('bigode', 'barba', (0, -ry - 0.004, cz - 0.058), (0.04, 0.012, 0.012), p)
    # orelhas (a esquerda tem a dobra: pequena saliência escura no alto)
    for sx in (1, -1):
        lado = 'L' if sx > 0 else 'R'
        esfera('orelha.' + lado, 'pele', (sx * (rx + 0.004), 0.0, cz - 0.015), (0.014, 0.024, 0.034), p)
    esfera('dobra_orelha', 'barba', (rx + 0.012, -0.004, cz + 0.012), (0.012, 0.013, 0.010), p)
    # olhos, nariz
    ey = -math.sqrt(max(ry ** 2 - 0.045 ** 2, 0)) - 0.004
    for sx in (1, -1):
        esfera('olho.' + ('L' if sx > 0 else 'R'), 'escuro', (sx * 0.045, ey, cz - 0.012), (0.012, 0.008, 0.016), p)
    esfera('nariz', 'pele', (0, -ry - 0.012, cz - 0.035), (0.018, 0.02, 0.02), p)
    # óculos: duas argolas + ponte + hastes
    for sx in (1, -1):
        lado = 'L' if sx > 0 else 'R'
        toro('aro.' + lado, 'escuro', 0.034, 0.005, p, (sx * 0.046, -ry - 0.014, cz - 0.012), (math.radians(90), 0, 0))
        tubo_curva('haste.' + lado, 'escuro',
                   [(sx * 0.080, -ry - 0.012, cz - 0.012), (sx * (rx + 0.01), -0.04, cz - 0.008), (sx * (rx + 0.012), 0.0, cz - 0.01)],
                   0.004, p)
    caixa('ponte', 'escuro', (0, -ry - 0.016, cz - 0.012), (0.03, 0.006, 0.006), p)


def _tronco(J):
    pe = J['peito']
    co = J['coluna']
    qu = J['quadril']
    # gola
    loft('gola', [((0, 0.01, 0.20), 0.08, 0.07), ((0, 0.01, 0.27), 0.085, 0.072)], 'gibao', pe)
    loft('gola_ouro', [((0, 0.01, 0.27), 0.086, 0.073), ((0, 0.01, 0.285), 0.086, 0.073)], 'ouro', pe)
    # tórax (do peito até a coluna)
    loft('torax', [((0, 0, -0.26), 0.135, 0.11), ((0, 0, -0.10), 0.145, 0.12), ((0, 0, 0.10), 0.16, 0.125), ((0, 0, 0.20), 0.15, 0.12)],
         'gibao', pe)
    # friso dourado central do gibão (frente)
    caixa('friso', 'ouro', (0, -0.122, -0.02), (0.035, 0.012, 0.42), pe)
    # abdome (coluna) e saia do gibão (quadril)
    loft('abdome', [((0, 0, -0.20), 0.135, 0.11), ((0, 0, 0.02), 0.138, 0.11)], 'gibao', co)
    loft('saia', [((0, 0, 0.17), 0.14, 0.112), ((0, 0, 0.0), 0.165, 0.135), ((0, 0, -0.17), 0.20, 0.16)], 'gibao', qu, tampas=False)
    loft('saia_ouro', [((0, 0, -0.17), 0.212, 0.167), ((0, 0, -0.145), 0.206, 0.161)], 'ouro', qu, tampas=False)
    loft('saia_fundo', [((0, 0, -0.165), 0.19, 0.15), ((0, 0, -0.12), 0.17, 0.13)], 'creme', qu)
    # cinto e fivela
    loft('cinto', [((0, 0, 0.17), 0.147, 0.118), ((0, 0, 0.205), 0.147, 0.118)], 'couro', qu)
    caixa('fivela', 'ouro', (0, -0.122, 0.188), (0.045, 0.012, 0.04), qu)
    # alça do alaúde: do ombro direito (-X) ao quadril esquerdo (+X), pela frente
    tubo_curva('alca', 'couro',
               [(-0.12, -0.12, 0.17), (-0.03, -0.142, -0.02), (0.08, -0.135, -0.20), (0.15, -0.09, -0.34)],
               0.014, pe)
    # capuz (bolsa roxa atrás do pescoço)
    esfera('capuz', 'capuz', (0, 0.13, 0.20), (0.11, 0.075, 0.08), pe)


def _bracos(J):
    for lado, sx in (('L', 1), ('R', -1)):
        br = J['braco.' + lado]
        an = J['antebraco.' + lado]
        ma = J['mao.' + lado]
        esfera('ombro.' + lado, 'gibao', (0, 0, 0.0), (0.062, 0.06, 0.06), br)
        loft('manga.' + lado, [((0, 0, -0.03), 0.07, 0.068), ((0, 0, -0.15), 0.082, 0.078), ((0, 0, -0.27), 0.066, 0.064)], 'creme', br)
        loft('punho.' + lado, [((0, 0, -0.27), 0.067, 0.065), ((0, 0, -0.30), 0.06, 0.058)], 'ouro', br)
        loft('antebraco.' + lado, [((0, 0, 0.01), 0.052, 0.05), ((0, 0, -0.14), 0.046, 0.044), ((0, 0, -0.235), 0.04, 0.038)], 'tatuagem', an)
        esfera('mao.' + lado, 'pele', (0, -0.008, -0.06), (0.046, 0.03, 0.072), ma)


def _pernas(J):
    for lado, sx in (('L', 1), ('R', -1)):
        cx = J['coxa.' + lado]
        ca = J['canela.' + lado]
        pe = J['pe.' + lado]
        loft('coxa.' + lado, [((0, 0, 0.02), 0.088, 0.09), ((0, 0, -0.22), 0.08, 0.082), ((0, 0, -0.40), 0.072, 0.074)], 'calca', cx)
        # bota de cano alto: cano largo com dobra no alto, depois a bota
        loft('cano.' + lado, [((0, 0, 0.02), 0.088, 0.088), ((0, 0, -0.05), 0.09, 0.09), ((0, 0, -0.07), 0.08, 0.08)], 'cano', ca)
        loft('bota.' + lado, [((0, 0, -0.06), 0.078, 0.078), ((0, 0, -0.20), 0.066, 0.068), ((0, 0, -0.31), 0.06, 0.064)], 'bota', ca)
        caixa('pe.' + lado, 'bota', (0, -0.045, -0.04), (0.11, 0.21, 0.07), pe, arred=0.015)
        caixa('sola.' + lado, 'escuro', (0, -0.045, -0.072), (0.112, 0.215, 0.012), pe)


def _capa(J):
    c = J['capa']
    # capa externa (verde) e interna (azul), abertas na frente
    # a abertura da frente fecha conforme desce: atrás do braço em cima, na frente das pernas embaixo
    abert = [(86, 274), (82, 278), (70, 290), (58, 302)]
    aneis_ext = [((0, 0.03, 0.0), 0.22, 0.17, 0, abert[0]), ((0, 0.04, -0.28), 0.27, 0.20, 0, abert[1]),
                 ((0, 0.05, -0.58), 0.33, 0.225, 0, abert[2]), ((0, 0.06, -0.88), 0.37, 0.235, 0, abert[3])]
    aneis_int = [((0, 0.03, -0.01), 0.21, 0.16, 0, abert[0]), ((0, 0.04, -0.28), 0.26, 0.19, 0, abert[1]),
                 ((0, 0.05, -0.58), 0.32, 0.215, 0, abert[2]), ((0, 0.06, -0.88), 0.36, 0.225, 0, abert[3])]
    loft('capa_ext', aneis_ext, 'capa_verde', c, seg=26, tampas=False)
    loft('capa_int', aneis_int, 'capa_azul', c, seg=26, tampas=False)
    loft('capa_borda', [((0, 0.06, -0.88), 0.372, 0.237, 0, abert[3]), ((0, 0.06, -0.84), 0.366, 0.232, 0, abert[3])], 'capa_borda', c, seg=26, tampas=False)
    # manto sobre os ombros (azul), mais fechado na frente
    loft('capa_ombros', [((0, 0.0, 0.04), 0.12, 0.10), ((0, 0.01, -0.03), 0.235, 0.17), ((0, 0.02, -0.11), 0.265, 0.19)], 'capa_azul', c, seg=26, arco=(35, 325), tampas=False)
    esfera('broche', 'ouro', (0.0, -0.145, -0.03), (0.022, 0.012, 0.022), c)


def _acessorios(J):
    pe = J['peito']
    qu = J['quadril']
    # --- alaúde nas costas (preso ao peito): corpo no meio das costas, braço sobe pelo ombro direito (-X)
    al = junta('alaude', pe, (0.02, 0.24, 0.0))
    al.rotation_euler = (math.radians(-8), math.radians(-28), 0)
    esfera('alaude_corpo', 'madeira', (0, 0.0, 0), (0.15, 0.065, 0.19), al)
    esfera('alaude_tampo', 'ouro', (0, 0.055, 0.0), (0.13, 0.015, 0.165), al)
    esfera('alaude_boca', 'escuro', (0, 0.068, 0.02), (0.035, 0.004, 0.035), al)
    caixa('alaude_braco', 'madeira', (0, 0.04, 0.33), (0.055, 0.03, 0.34), al)
    caixa('alaude_cravelha', 'madeira', (0, 0.04, 0.54), (0.065, 0.035, 0.09), al, rot=(math.radians(-20), 0, 0))
    for i, x in enumerate((-0.012, 0.012)):
        caixa('corda%d' % i, 'marfim', (x, 0.057, 0.25), (0.004, 0.003, 0.5), al)
    # --- espada na bainha + corneta, quadril esquerdo (+X), apontando para trás e para baixo
    es = junta('espada', qu, (0.17, 0.02, 0.17))
    es.rotation_euler = (math.radians(-32), math.radians(-6), 0)
    caixa('bainha', 'couro', (0, 0, -0.33), (0.035, 0.05, 0.66), es, arred=0.01)
    caixa('bainha_ponta', 'ouro', (0, 0, -0.66), (0.037, 0.052, 0.05), es)
    caixa('guarda', 'ouro', (0, 0, 0.02), (0.03, 0.16, 0.025), es)
    loft('punho_esp', [((0, 0, 0.03), 0.016, 0.016), ((0, 0, 0.14), 0.015, 0.015)], 'couro', es)
    esfera('pomo', 'ouro', (0, 0, 0.155), (0.024, 0.024, 0.024), es)
    co = junta('corneta', qu, (0.21, -0.03, 0.08))
    # crescente no plano do lado do corpo: boca larga em cima/atrás, ponta fina embaixo/na frente
    tubo_curva('corneta', 'marfim',
               [(0.0, 0.07, 0.0), (0.012, 0.03, -0.075), (0.0, -0.04, -0.095), (-0.01, -0.10, -0.05)],
               0.03, co, raio_fim=0.008)
    toro('corneta_boca', 'ouro', 0.03, 0.007, co, (0.0, 0.075, 0.005), (math.radians(60), 0, 0), seg=16)
    # --- bolsa roxa e poção no quadril direito (-X)
    bo = junta('bolsa', qu, (-0.19, -0.06, 0.02))
    bo.rotation_euler = (0, math.radians(-12), 0)
    caixa('bolsa_corpo', 'bolsa', (0, 0, 0), (0.07, 0.15, 0.13), bo, arred=0.02)
    caixa('bolsa_aba', 'capuz', (0.012, 0, 0.04), (0.06, 0.155, 0.06), bo, arred=0.012)
    esfera('bolsa_fecho', 'ouro', (-0.045, 0, 0.0), (0.012, 0.022, 0.018), bo)
    po = junta('pocao', qu, (-0.13, -0.15, -0.02))
    loft('frasco', [((0, 0, -0.05), 0.022, 0.022), ((0, 0, 0.01), 0.024, 0.024), ((0, 0, 0.03), 0.012, 0.012), ((0, 0, 0.05), 0.012, 0.012)], 'vidro', po, seg=12)
    loft('liquido', [((0, 0, -0.045), 0.02, 0.02), ((0, 0, 0.0), 0.021, 0.021)], 'pocao', po, seg=12)
    loft('rolha', [((0, 0, 0.05), 0.013, 0.013), ((0, 0, 0.065), 0.014, 0.014)], 'couro', po, seg=10)


def _cisne(J):
    """Cisne pousado no ombro ESQUERDO (+X). Corpo na altura da gola, cabeça na altura dos olhos."""
    ci = junta('cisne', J['peito'], (0.19, 0.03, M['ombro_z'] + 0.06 - M['peito_z']))
    esfera('cisne_corpo', 'branco', (0.0, 0.03, 0.04), (0.075, 0.12, 0.062), ci)
    esfera('cisne_asa', 'branco', (0.025, 0.04, 0.065), (0.05, 0.095, 0.034), ci, rot=(math.radians(-12), 0, 0))
    esfera('cisne_cauda', 'branco', (0, 0.135, 0.09), (0.026, 0.045, 0.02), ci, rot=(math.radians(-40), 0, 0))
    tubo_curva('cisne_pescoco', 'branco',
               [(0.0, -0.07, 0.08), (0.0, -0.115, 0.12), (0.0, -0.105, 0.16), (0.0, -0.125, 0.185)], 0.021, ci, raio_fim=0.016)
    esfera('cisne_cabeca', 'branco', (0, -0.135, 0.20), (0.026, 0.042, 0.027), ci)
    loft('cisne_bico', [((0, -0.165, 0.196), 0.012, 0.012), ((0, -0.215, 0.19), 0.004, 0.004)], 'laranja', ci, seg=10)
    esfera('cisne_mascara', 'escuro', (0, -0.163, 0.198), (0.013, 0.01, 0.013), ci)
    for sx in (1, -1):
        esfera('cisne_olho%d' % sx, 'escuro', (sx * 0.021, -0.145, 0.207), (0.005, 0.005, 0.005), ci)

# Fenda Adentro

Jogo em pixel art, visão lateral, que mistura beat 'em up com RPG de turno.
Em espanhol: *Fenda Adentro: una rendija entre nosotros*.

Personagens: **Cisneo, the Romeo** (elfo druida e botânico, com alaúde e cisne) e
**Rawry, the Manticore** (ainda não desenhado).

Este repositório guarda, por enquanto, os assets de animação, inclusive versões
que ainda não são finais.

## Pastas

| Pasta | Conteúdo |
|---|---|
| `referencia/` | Folhas conceituais. `descartado/` guarda versões abandonadas. |
| `bruto/<personagem>/<animação>/` | O que o gerador de imagem entregou, sem edição. Nunca alterar; é a origem de tudo. |
| `sprites/<personagem>/<animação>/` | Quadros limpos em resolução nativa, fundo transparente. |
| `paleta/` | Paleta travada de cada personagem (PNG de uma linha). |
| `modelos/` | Arquivos `.blend` do Cisneo 3D (modelo, rig e animação), gerados por script. |
| `build/` | Atlas e JSON para o jogo; `previa/` tem GIFs e imagens de conferência; `referencia_gemini/` tem as bases ampliadas 6× em fundo magenta, prontas para anexar nos pedidos ao Gemini. |
| `ferramentas/` | Scripts de limpeza e montagem. `ferramentas/blender/` tem o modelo 3D e o render. |

## Convenções

- **Grafia:** Cisneo (não "Cineo").
- **Resolução nativa do Cisneo:** cerca de 258 px de altura nas vistas sem o cisne (`cisneo_frente`, `cisneo_perfil_direita`, `cisneo_costas`, `cisneo_perfil_esquerda`), que são a referência do jogo. A pose tocando (`cisneo_frente_tocando`, 91 × 183) foi gerada em outra escala. O tamanho de exibição no jogo será decidido num teste em tela de celular; reduzir depois é possível, aumentar não.
- **Paleta:** `paleta/cisneo_v2.png`, 48 cores, tirada das vistas sem o cisne (`paleta/cisneo.png` é a da pose tocando). Toda animação nova é mapeada para ela (`--paleta`), para as cores não mudarem entre animações.
- **Orientação:** cada animação lateral é desenhada nas duas direções (direita e esquerda), sem espelhar, por causa dos acessórios assimétricos (alaúde, espada, bolsa).
- **Lados (regra de geometria):** um personagem virado para a direita da tela mostra o lado DIREITO dele (como Lincoln na moeda de 1 centavo); virado para a esquerda mostra o lado ESQUERDO. Logo: virado para a direita aparecem a bolsa e a poção (quadril direito) e o cisne fica escondido atrás da cabeça; virado para a esquerda aparecem a espada e a corneta (quadril esquerdo) e o cisne fica na frente. A folha `cisneo_vistas_sem_cisne_gemini.jpg` (1ª versão) está certa; a v2 trocou os lados por um pedido errado meu.
- **Cisne:** sempre no ombro esquerdo. No modelo 3D ele é uma peça presa ao peito, então aparece do lado certo sozinho.
- **Decisão (15/10):** o visual do jogo é a pixel art do Gemini; o 3D ficou longe do estilo e serve só para conferir lados e poses.
- **Pipeline 3D (ferramenta auxiliar):** o Cisneo é modelado e animado por script no Blender (`ferramentas/blender/`), renderizado em câmera ortográfica na resolução nativa com materiais toon de 3 tons, e o contorno é aplicado em pós-processamento (`ferramentas/pixelar.py`). Os acessórios e a sobreposição dos membros saem certos em qualquer direção sem conferência manual. A pixel art do Gemini continua sendo a referência de estilo e paleta.
- **Pedidos ao gerador:** sempre anexar a base aprovada, uma animação por pedido, fundo `#FF00FF`, PNG, células do mesmo tamanho sem espaço entre elas.
- **Nomes de arquivo:** `<personagem>_<animação>_<nn>.png`, quadros numerados a partir de 00.

## Limpeza de uma imagem do gerador

```
python ferramentas/snap_grid.py bruto/cisneo/base/cisneo_base_frente_gemini.jpg \
  sprites/cisneo/base/cisneo_frente.png --paleta paleta/cisneo.png
```

O script detecta o tamanho do pixel ampliado e a fase da grade, amostra o centro de
cada bloco (o que remove o borrão do JPEG), torna o magenta transparente e recorta
ao personagem.

## Pipeline 3D (Blender sem interface)

```
python3 -m venv .venv-blender && .venv-blender/bin/pip install bpy      # Blender 5.2 como módulo Python
.venv-blender/bin/python ferramentas/blender/render_sprites.py --anim walk --dir right --frames 8 \
    --out /tmp/render/right --blend modelos/cisneo_caminhada_right.blend
python ferramentas/pixelar.py /tmp/render/right sprites/cisneo/caminhada_direita --prefixo cisneo3d_caminhada_right
python ferramentas/montar_gif.py build/previa/cisneo3d_caminhada_right.gif sprites/cisneo/caminhada_direita/*.png
```

- `cisneo_modelo.py`: corpo segmentado por juntas (Empties), capa com abertura que fecha conforme desce, acessórios e cisne; paleta em `PALETA`.
- `render_sprites.py`: câmera ortográfica (144 px/m, personagem com ~260 px), luz solar, poses `idle` e `walk` (IK das pernas calculada em código), três passes por quadro: cor toon, id de material e profundidade.
- `pixelar.py`: contorno da silhueta + linhas internas onde muda o material ou a profundidade; recorte comum a todos os quadros.
- Direções: `right` e `left` (laterais), `front`, `back`.

## Status

| Personagem | Animação | Estado |
|---|---|---|
| Cisneo | frente tocando o alaúde | aprovada |
| Cisneo | vistas frente, perfil e costas (alaúde nas costas) | v2 em `bruto/`: costas ok; perfil virado à esquerda com o cisne no ombro errado |
| Cisneo | vistas sem o cisne (frente, perfil direita, costas, perfil esquerda) | na grade; lados dos acessórios CERTOS nesta 1ª versão (ver regra dos lados) |
| Cisneo | vistas sem acessórios (corpo) | na grade, mesma posição da folha com acessórios |
| Acessórios | folha solta (alaúde, espada com corneta, bolsa, poção) | em `bruto/`; desenhados na horizontal, servem para animações com o item na mão |
| Cisne | vistas (direita, esquerda, frente, costas) | a gerar |
| Cisneo 3D | parado (frente, direita, esquerda) | 1º teste em `sprites/cisneo/parado_3d/`; comparação em `build/previa/comparacao_3d_vs_gemini.png` |
| Cisneo 3D | caminhada (8 quadros × 2 direções) | 1º teste em `sprites/cisneo/caminhada_*/`; GIFs em `build/previa/` |
| Rawry | conceito | a criar |

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

Folhas de animação: pedir grade 2×2 (4 quadros por imagem). Uma linha de 8 sai com 300 px de altura e sem grade de pixel.
Quando a grade não é detectável (bloco < 4 px no JPEG), cada quadro é reamostrado para 258 px de altura (`--bloco altura/258`),
mapeado na paleta e depois alinhado (`ferramentas/alinhar_quadros.py`: pés na base, cabeça na mesma coluna).
O Gemini só desenha a perna próxima à frente; a fase oposta é gerada por `ferramentas/trocar_pernas.py`, que separa as duas pernas
(watershed a partir das botas) e troca os tons claros/escuros entre elas.
A direção esquerda sai da direita por `ferramentas/espelhar_para_esquerda.py`: espelha, apaga bolsa e poção do quadril e sobrepõe a espada
extraída da base esquerda (diferença entre a vista com e sem acessórios), desenhada atrás do braço, da mão e das botas.

## Caminhada por boneco articulado (v3)

Para o movimento sair fluido, a caminhada v3 não usa poses do Gemini: `ferramentas/boneco_caminhada.py` recorta a base
`cisneo_perfil_direita.png` em peças (capa/fundo, tronco, braço próximo, coxa, cano da bota, pé) e anima por código:
ciclo de 16 quadros a 60 ms, pernas por cinemática inversa de dois ossos (60 % do ciclo em apoio), perna distante como cópia
escurecida, balanço do tronco (3 px), braço e capa por cisalhamento. O punho da espada que o Gemini desenhou no quadril da
vista direita é apagado com a vista sem acessórios (`--sem-acessorios`), porque pela regra dos lados ele não aparece desse lado.

```
python ferramentas/boneco_caminhada.py sprites/cisneo/base/cisneo_perfil_direita.png sprites/cisneo/caminhada_direita_v3 \
  --quadros 16 --sem-acessorios sprites/cisneo/base/cisneo_sem_acessorios_perfil_direita.png
python ferramentas/espelhar_para_esquerda.py sprites/cisneo/base/cisneo_perfil_esquerda.png \
  sprites/cisneo/base/cisneo_sem_acessorios_perfil_esquerda.png sprites/cisneo/caminhada_esquerda_v3 \
  cisneo_caminhada_esquerda sprites/cisneo/caminhada_direita_v3/*.png
python ferramentas/montar_gif.py build/previa/cisneo_caminhada_direita_v3.gif sprites/cisneo/caminhada_direita_v3/*.png --escala 2 --ms 60
python ferramentas/previa_passeio.py build/previa/cisneo_passeio_v3.gif sprites/cisneo/caminhada_direita_v3 sprites/cisneo/caminhada_esquerda_v3 --escala 1 --ms 60 --passo 10
```

Parâmetros: `--passada` (px por passo, 80), `--lift` (altura do pé, 20), `--bob` (3), `--braco` (graus, 18). No jogo, o deslocamento
por quadro que casa com os pés é `passada * 2 / quadros` (10 px a 1×).


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
python ferramentas/pixelar.py /tmp/render/right sprites/cisneo_3d/caminhada_direita --prefixo cisneo3d_caminhada_right
python ferramentas/montar_gif.py build/previa/cisneo3d_caminhada_right.gif sprites/cisneo_3d/caminhada_direita/*.png
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
| Cisneo | caminhada p/ direita, 8 quadros | v2 em `sprites/cisneo/caminhada_direita/`: 4 poses do Gemini (1ª folha) + 4 com o sombreado das pernas trocado (`trocar_pernas.py`), porque o Gemini não desenha a perna distante à frente. GIF `build/previa/cisneo_caminhada_direita_v2.gif`. Pendente: balanço dos braços |
| Cisneo | caminhada p/ esquerda, 8 quadros | v1 em `sprites/cisneo/caminhada_esquerda/`: espelho da direita com a bolsa removida e a espada da base esquerda sobreposta (`espelhar_para_esquerda.py`). O Gemini não conseguiu gerar esta direção (folha em `bruto/`). GIF `build/previa/cisneo_caminhada_esquerda_v1.gif` |
| Cisneo | caminhada p/ direita e esquerda, 16 quadros (boneco articulado) | v3 em `sprites/cisneo/caminhada_direita_v3/` e `caminhada_esquerda_v3/`, 60 ms por quadro. GIFs `build/previa/cisneo_caminhada_direita_v3.gif`, `cisneo_caminhada_esquerda_v3.gif`, `cisneo_passeio_v3.gif`. Em avaliação: fluidez do movimento |
| Cisneo 3D | parado e caminhada | descartado como visual; fica em `sprites/cisneo_3d/` só como referência de lados e poses |
| Rawry | conceito | a criar |

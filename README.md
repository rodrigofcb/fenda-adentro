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
| `build/` | Atlas e JSON para o jogo; `previa/` tem GIFs e imagens de conferência. |
| `ferramentas/` | Scripts de limpeza e montagem. |

## Convenções

- **Grafia:** Cisneo (não "Cineo").
- **Resolução nativa do Cisneo:** cerca de 258 px de altura nas vistas sem o cisne (`cisneo_frente`, `cisneo_perfil_direita`, `cisneo_costas`, `cisneo_perfil_esquerda`), que são a referência do jogo. A pose tocando (`cisneo_frente_tocando`, 91 × 183) foi gerada em outra escala. O tamanho de exibição no jogo será decidido num teste em tela de celular; reduzir depois é possível, aumentar não.
- **Paleta:** `paleta/cisneo_v2.png`, 48 cores, tirada das vistas sem o cisne (`paleta/cisneo.png` é a da pose tocando). Toda animação nova é mapeada para ela (`--paleta`), para as cores não mudarem entre animações.
- **Orientação:** cada animação lateral é desenhada nas duas direções (direita e esquerda), sem espelhar, por causa dos acessórios assimétricos (alaúde, espada, bolsa).
- **Cisne:** fica sempre no ombro esquerdo do Cisneo e é uma camada separada (`sprites/cisne/`), sobreposta no jogo. O Cisneo é desenhado sem o cisne. Virado para a direita, o cisne vai na frente do corpo; virado para a esquerda, atrás da cabeça. Cada quadro do Cisneo precisa de um ponto de ancoragem do ombro esquerdo.
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

## Status

| Personagem | Animação | Estado |
|---|---|---|
| Cisneo | frente tocando o alaúde | aprovada |
| Cisneo | vistas frente, perfil e costas (alaúde nas costas) | v2 em `bruto/`: costas ok; perfil virado à esquerda com o cisne no ombro errado |
| Cisneo | vistas sem o cisne (frente, perfil direita, costas, perfil esquerda) | na grade (pixel de 5,37 px no original); acessórios trocados entre os perfis |
| Cisneo | vistas sem acessórios (corpo) | na grade, mesma posição da folha com acessórios |
| Acessórios | folha solta (alaúde, espada com corneta, bolsa, poção) | em `bruto/`; desenhados na horizontal, servem para animações com o item na mão |
| Cisne | vistas (direita, esquerda, frente, costas) | a gerar |
| Cisneo | caminhada (8 quadros × 2 direções) | a gerar |
| Rawry | conceito | a criar |

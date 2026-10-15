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
- **Resolução nativa do Cisneo:** 183 px de altura (base de frente, 91 × 183). O tamanho de exibição no jogo será decidido num teste em tela de celular; reduzir depois é possível, aumentar não.
- **Paleta:** `paleta/cisneo.png`, 40 cores. Toda animação nova é mapeada para ela (`--paleta`), para as cores não mudarem entre animações.
- **Orientação:** sprites laterais desenhados virados para a direita; a esquerda é espelhada no jogo.
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
| Cisneo | base de frente | aprovada |
| Cisneo | vistas frente, perfil e costas (alaúde nas costas) | v2 em `bruto/`: costas ok; perfil virado à esquerda com o cisne no ombro errado |
| Cisneo | caminhada (8 quadros) | a gerar |
| Rawry | conceito | a criar |

# Sprites Macabros — a forja de pixel art do Ecos da Cripta

Todos os personagens, roupas, camadas de equipamento, objetos do acampamento, ícones de itens e
projéteis do jogo são **desenhados por código** nesta pasta, no estilo sombrio de Castlevania e
Blasphemous. O jogo **não roda a forja**: ele só lê os PNG e o `catalogo.json` que ela grava em
`assets/`. Mudou alguma coisa aqui? Rode o gerador de novo e confira na prévia.

Precisa de `numpy`, `pillow` e `scipy` (já estão no `requirements.txt` da raiz).

## As folhas de sprite

Todos olham para a **direita** (o jogo espelha os inimigos). Cada folha tem uma linha por animação:

| linha | animação | quadros |
|---|---|---|
| 0 | `parado` (respiração, capa ao vento, chamas) | 4 |
| 1 | `ataque` (preparação, golpe com rastro, impacto, volta) | 4 |
| 2 | `dano` (recuo) | 2 |
| 3 | `morte` (cambaleia, ajoelha, desaba, corpo caído) | 4 |
| 4 | `sentado` (em volta da fogueira do acampamento; quem não senta repete o `parado`) | 4 |
| 5+ | extras de alguns modelos (`animacoes_extras`, ex.: `despertar` das gárgulas) | — |

Os humanos têm cerca de 76 px de altura (umas 7 cabeças). No jogo, quem tem até 96 px é ampliado
3× e os maiores 2×, sempre com pixels nítidos.

O `catalogo.json` guarda, para cada folha: célula, âncora (os pés), escala, as linhas de animação,
**família**, **tamanho** (pequeno/médio/grande/enorme) e **papel** na horda (enxame, soldado,
distância, suporte, conjurador, tanque, dano, elite, voador, chefe_de_horda, chefe, heroi, npc,
invocacao, objeto, camada). Hoje são cerca de 1270 entradas: ~140 folhas de herói (roupas e as
versões desarmadas), ~140 inimigos, chefes, invocações, NPCs e objetos, e ~1000 camadas.

## O que tem na pasta

```
sprites_macabros/
├── gerar_sprites.py        personagens, roupas e camadas -> assets/sprites_macabros (+ previas/galeria.png)
├── gerar_itens.py          ícones dos itens -> assets/itens_macabros (+ previas/galeria_itens.png)
├── gerar_efeitos.py        projéteis (voo + impacto) -> assets/efeitos
├── gerar_acampamento.py    paisagem noturna do acampamento -> assets/acampamento_noturno
├── gerar_salao.py          salão da Cripta (tela de título) -> assets/salao_da_cripta
├── gerar_retratos.py       retratos (bustos) -> assets/retratos
├── previa*.py              prévias em PNG/GIF, sem mexer nos assets (ver abaixo)
├── conferir_identicos.py   confere pixel a pixel se a forja ainda gera os mesmos PNG do jogo
├── visualizar.py           janela pygame: galeria animada e modo HORDA (usa o carregador do jogo, src/visual)
├── previas/                saídas das prévias e galerias (descartáveis), menos previas/antes/ (backup do previa_lote)
└── forja/
    ├── motor.py            Tela, Geo (máscaras), Mat (rampas de cor), sombreamento, contorno, brilhos
    ├── humanoide.py        esqueleto humanoide com IK (braços/pernas), tronco, capas, capuzes
    ├── anim.py             Modelo (base de todos), Ctx, biblioteca de poses e montagem das folhas
    ├── armas.py, fx.py     armas, rastros de golpe, fogo, gelo, raio, fumaça, runas
    ├── texturas.py         pelagem, quitina, escamas, casca, musgo, rachaduras, cristal, aura
    ├── itens.py            formas dos ícones (IconeForjado); itens_fases.py e itens_etapa8.py: ícones próprios
    ├── criaturas/          FORJA MODULAR de criaturas (a mais nova; ver abaixo)
    └── personagens/        heróis, inimigos, chefes, NPCs, objetos, roupas, adornos e camadas
```

## Como a forja desenha

1. **Geometria (`motor.Geo`)**: cada parte do corpo é uma máscara (polígono, elipse, cápsula,
   corrente de cápsulas) desenhada com supersampling.
2. **Material (`motor.Mat`)**: uma cor base vira uma rampa do escuro ao claro com *hue-shift*
   (sombras puxando para roxo/azul, luzes para amarelo). `metal()` acrescenta brilho especular.
3. **Pintura (`Tela.pintar`)**: sombreamento volumétrico automático, como se a peça fosse esculpida
   e iluminada de cima, quantizado na rampa com dithering; linha interna onde a peça encosta em outra.
4. **Acabamento (`Tela.finalizar`)**: luz de borda, brilhos aditivos, contorno quase preto e halo.
5. **Animação (`anim.Modelo`)**: `pose(ctx)` devolve a pose do quadro; `esqueleto(pose)` calcula
   as juntas (IK); `desenhar(tela, ctx, J)` pinta. `salvar_folha` monta as linhas da folha.

### Duas gerações de criaturas

- **Antiga** (`personagens/bestas.py`, `inimigos_a.py`, `inimigos_b.py`, `novos.py`): cada criatura
  é uma classe desenhada à mão (`Besta`/`Modelo`), com variações por parâmetro (`Goblin(tipo="bruto")`).
- **Modular** (`criaturas/`): o bicho é montado com peças que guardam só a forma — `Pata`, `Cauda`,
  `Asa`, `Cabeca` (`partes.py`) — sobre as bases `Quadrupede`, `Ave`, `Inseto`, `Verme`
  (`animal.py`), `ForjaMonstro` (`monstro.py`) e `ForjaPlanta`/`Arvore`/`Cogumelo` (`planta.py`).
  Os mixins de `acabamento.py` (`ComAcabamento`, `Corrompido`) reaproveitam um sprite pronto por
  herança e acrescentam camadas (ex.: `class CavaleiroCaido(Corrompido, Guerreiro)`).

Criaturas novas devem usar a forja modular. Os inimigos antigos ficam como estão (a arte deles é boa);
um parente novo de um antigo (ex.: outra aranha, outro louva-a-deus) sai da classe antiga por parâmetro
ou com `ComAcabamento`.

Peças e opções da forja modular (todas desligadas por padrão, para não mudar quem já existe):

| peça | opções |
|---|---|
| `Cabeca` | estilos `canina`, `felina`, `primata`, `morcego`, `ave`, `reptil`, `inseto` e **`roedor`** (focinho fino, bigodes, incisivos amarelos); `orelha_dentro` (cor de dentro da orelha); `antena` dos insetos: `"fio"`, `"pluma"`, `"clava"` ou `None` |
| `Asa` | `membrana`, `penas`, `inseto` (translúcida) e **`mariposa`** (larga, opaca, com mancha em forma de olho) |
| `Cauda` | `pelo`, `rato`, `escamas`, `espinhos`, `lisa` |
| `Inseto` | `pares` (3 ou 4), `elitro`, `asa`, **`cintura`** (formigas, vespas), **`listras`** `(cor, quantas)`, **`ferrao`** (Mat) e **`voa=True`** (paira zumbindo, patas dobradas, despenca ao morrer) |

Exemplos prontos em `criaturas/demos.py`: rato, ratazana, formiga, vespa, mosca e mariposa
(`python previa_forjas.py rato vespa`).

### Heróis: roupas e camadas

- **Roupas** (`personagens/roupas.py`): uma linha por roupa de subclasse, especialização ou skin.
  É o mesmo modelo do herói com outros materiais e uma lista de **adornos de silhueta**
  (`personagens/adornos.py`: armas nas costas, asas, auréolas, ombreiras, cintos, familiares...).
  Cada roupa também ganha a versão `_desarmado` (sem a arma da classe), usada quando o herói tem
  arma equipada.
- **Camadas** (`personagens/camadas.py` e `equipamento.py`): desenham só o acessório, com o MESMO
  esqueleto e as mesmas poses de uma "geometria" de herói (12: guerreiro, paladino, 3 bárbaros,
  mago, arqueira, assassina, bardo, bobo, monge, feiticeira). Por isso encaixam quadro a quadro em
  qualquer roupa daquela geometria. São três tipos:
  - chapéus e encantamentos de arma (skins) e traços de raça (`raca_gnomo`, `raca_anao`...);
  - equipamento: **uma camada por tipo** de peça (`eq_elmo`, `eq_placas`, `eq_espada`...), pintada
    em cinza neutro; o jogo tinge com a cor da peça, do set ou da raridade. O que não se tinge
    (madeira, couro, ouro, chamas) vai na linha `<anim>_fixo`.
  - nome no jogo: `camada_<geometria>_<acessorio>.png`.
- O jogo compõe tudo pelo nome: `"guerreiro_berserker_desarmado+@raca_anao+@eq_placas:404c4c+@aureola"`.

## Gerar

```
python gerar_sprites.py            (gera tudo; demora alguns minutos)
python gerar_sprites.py orc aranha (só os nomes que contêm esses textos; o catálogo é atualizado, não apagado)
python gerar_itens.py
```

## Ver sem abrir o jogo

```
python previa_lote.py 2a lobo_sarnento torreta   antes x depois de um lote (previas/lote_2a.png + GIFs)
python previa_roupas.py [guerreiro ...]          cada roupa ao lado do herói base (previas/roupas/)
python previa_equipamento.py                     classes vestindo peças de verdade
python previa_forjas.py [lobo]                   criaturas de demonstração da forja modular
python conferir_identicos.py [nomes] [--camadas] confere se os sprites do jogo continuam idênticos
python previa_efeitos.py                         projéteis
python previa.py inimigos_a Orc saida.png tipo='"berserker"'   um modelo só, ampliado
python visualizar.py                             janela: G galeria, H horda (A/D atacam, X mata, R sorteia)
```

As prévias das **telas** do jogo ficam em `ferramentas/previa_telas.py` (na raiz das ferramentas).

## Criar ou mudar

**Regra de ouro:** antes e depois de mexer em qualquer arquivo de `forja/`, rode
`python conferir_identicos.py` (e `--camadas` se mexeu no esqueleto, nas roupas ou no equipamento).
Uma folha que mudou sem querer aparece como DIFERENTE; só gere de novo o que era para mudar.

- **Cor de um personagem**: mexa nos `Mat(...)` da classe (a cor base gera a rampa sozinha).
- **Variação**: parâmetros da classe ou uma subclasse com `ComAcabamento`; nunca copie a classe.
- **Criatura nova**: classe em `forja/criaturas/` (ou `personagens/`), uma linha no `CATALOGO` de
  `gerar_sprites.py` (família, tamanho, papel) e `python gerar_sprites.py <nome>`. No jogo, a ficha
  em `src/roguelike/dados/inimigos.json` usa a mesma chave.
- **Roupa nova**: copie uma linha de `ROUPAS` em `roupas.py` e troque nome, cores e adornos.
- **Chapéu, encantamento ou traço de raça**: uma função `desenhar(tela, ctx, J, camada)` em
  `ACESSORIOS` (`camadas.py`). O gerador cria a camada para cada geometria.
- **Tipo de equipamento novo**: uma função em `PECAS` (`equipamento.py`) e o tipo em
  `src/roguelike/dados/visual_equipamentos.json`.
- **Ícone de item**: uma forma em `forja/itens.py` (`FORMAS`); o item escolhe pela tabela `PALAVRAS`
  ou pelo campo `"icone"` no `itens.json`.

## Usar o carregador (pygame)

```python
from visual.sprites_macabros import Sprites, Animador     # dentro de src/

sp = Sprites()
inimigo = Animador(sp, "palhaco_brutamontes")
inimigo.tocar("ataque")                                    # toca uma vez e volta para "parado"
inimigo.atualizar(dt)
imagem = sp.quadro(inimigo.nome, inimigo.anim, inimigo.indice, escala=3, espelhar=True)
```

Um nome que não existe no catálogo vira um esqueleto acinzentado: o jogo nunca quebra por falta de sprite.

"""Gera todas as folhas de sprite em sprites/ + catalogo.json + previas/galeria.png.

Uso:
    python gerar_sprites.py            (gera tudo)
    python gerar_sprites.py orc aranha (só os nomes que contêm esses textos)
"""
import json
import os
import sys
import time
from multiprocessing import Pool

from PIL import Image, ImageDraw

from forja.anim import salvar_folha, ANIMACOES
from forja.personagens import herois as H
from forja.personagens import inimigos_a as A
from forja.personagens import inimigos_b as B
from forja.personagens import novos as N
from forja.personagens import bestas as X
from forja.personagens import acampamento as C
from forja.personagens import invocacoes as V
from forja.personagens import herois_novos as HN
from forja.personagens import herois_do_reino as HR
from forja.personagens import cenario_acampamento as CA
from forja.personagens import acampamento_detalhado as AD
from forja.personagens import fase4 as F4
from forja.personagens import feras as FE
from forja.personagens import flora as FL
from forja.personagens import construtos as CO
from forja.personagens import monstros as MO
from forja.personagens import variantes as VA
from forja.personagens import nomeados as NO
from forja.personagens import eclipse as EC
from forja.personagens import gargulas as GA
from forja.personagens import da_forja as DF
from forja.personagens import lendas as LE
from forja.personagens import chefes as CH
from forja.personagens import reino_dos_ratos as RR
from forja.personagens import bubonicos as BU
from forja.personagens.roupas import ROUPAS
from forja.personagens.camadas import GEOMETRIAS, ACESSORIOS, CamadaVisual
from forja.personagens.equipamento import PECAS, ATRAS as PECAS_ATRAS

# As folhas vão direto para a pasta de imagens do jogo (assets/sprites_macabros)
AQUI = os.path.dirname(os.path.abspath(__file__))
PASTA = os.path.join(os.path.dirname(os.path.dirname(AQUI)), "assets", "sprites_macabros")

# (fábrica, família, tamanho, papel na horda)
CATALOGO = [
    # ---------------- heróis ----------------
    (lambda: H.Guerreiro(), "herois", "medio", "heroi"),
    (lambda: H.Paladino(), "herois", "medio", "heroi"),
    (lambda: H.Barbaro(arma="Espada"), "herois", "medio", "heroi"),
    (lambda: H.Barbaro(arma="Machado"), "herois", "medio", "heroi"),
    (lambda: H.Barbaro(arma="Martelo"), "herois", "medio", "heroi"),
    (lambda: H.MagoFogo(), "herois", "medio", "heroi"),
    (lambda: H.MagoGelo(), "herois", "medio", "heroi"),
    (lambda: H.MagoRaio(), "herois", "medio", "heroi"),
    (lambda: H.Arqueira(), "herois", "medio", "heroi"),
    (lambda: H.Assassina(), "herois", "medio", "heroi"),
    # ---------------- goblins ----------------
    (lambda: A.Goblin(), "goblins", "pequeno", "enxame"),
    (lambda: A.Goblin(tipo="xama"), "goblins", "pequeno", "suporte"),
    (lambda: A.Goblin(tipo="bruto"), "goblins", "medio", "tanque"),
    # ---------------- mortos-vivos ----------------
    (lambda: A.Esqueleto(), "mortos_vivos", "medio", "soldado"),
    (lambda: A.Esqueleto(tipo="arqueiro"), "mortos_vivos", "medio", "distancia"),
    (lambda: A.Esqueleto(tipo="cavaleiro"), "mortos_vivos", "medio", "elite"),
    (lambda: A.Esqueleto(tipo="gigante"), "mortos_vivos", "grande", "chefe_de_horda"),
    (lambda: N.Carnical(), "mortos_vivos", "pequeno", "enxame"),
    (lambda: B.Lich(), "mortos_vivos", "grande", "chefe"),
    # ---------------- orcs ----------------
    (lambda: A.Orc(), "orcs", "grande", "soldado"),
    (lambda: A.Orc(tipo="berserker"), "orcs", "grande", "dano"),
    (lambda: A.Orc(tipo="senhor"), "orcs", "enorme", "chefe_de_horda"),
    # ---------------- bruxaria ----------------
    (lambda: B.Bruxa(), "bruxaria", "medio", "conjurador"),
    (lambda: B.Bruxa(tipo="freira"), "bruxaria", "medio", "conjurador"),
    (lambda: N.Flagelante(), "bruxaria", "medio", "soldado"),
    (lambda: B.Inquisidor(), "bruxaria", "grande", "elite"),
    # ---------------- vampiros ----------------
    (lambda: B.Vampiro(), "vampiros", "medio", "elite"),
    (lambda: B.Vampiro(tipo="cria"), "vampiros", "pequeno", "enxame"),
    (lambda: B.Vampiro(tipo="noiva"), "vampiros", "medio", "conjurador"),
    (lambda: FE.MorcegoGigante(), "vampiros", "pequeno", "voador"),
    # ---------------- golens ----------------
    (lambda: B.Golem(), "golens", "enorme", "tanque"),
    (lambda: B.Golem(carregando=True), "golens", "enorme", "tanque"),
    (lambda: B.Golem(tipo="carne"), "golens", "enorme", "tanque"),
    # ---------------- circo macabro ----------------
    (lambda: N.Palhaco(), "circo_macabro", "medio", "soldado"),
    (lambda: N.Palhaco(tipo="gordo"), "circo_macabro", "grande", "tanque"),
    (lambda: N.Palhaco(tipo="boneco"), "circo_macabro", "pequeno", "enxame"),
    (lambda: N.Bobo(), "circo_macabro", "medio", "dano"),
    (lambda: N.Bobo(tipo="marionete"), "circo_macabro", "medio", "elite"),
    (lambda: N.Bobo(tipo="corcunda"), "circo_macabro", "pequeno", "suporte"),
    # ---------------- aranhas e insetos ----------------
    (lambda: X.Aranha(tipo="filhote"), "insetos", "pequeno", "enxame"),
    (lambda: X.Aranha(), "insetos", "medio", "soldado"),
    (lambda: X.Aranha(tipo="mae"), "insetos", "enorme", "chefe_de_horda"),
    (lambda: X.LouvaDeus(), "insetos", "grande", "dano"),
    (lambda: X.Besouro(), "insetos", "medio", "tanque"),
    (lambda: X.Vespa(), "insetos", "pequeno", "voador"),
    (lambda: FE.Centopeia(), "insetos", "medio", "soldado"),
    # ---------------- dragões ----------------
    (lambda: X.Dragao(tipo="filhote"), "dragoes", "medio", "dano"),
    (lambda: X.Dragao(), "dragoes", "enorme", "chefe"),
    (lambda: X.Dragao(tipo="osseo"), "dragoes", "enorme", "chefe"),
    # ---------------- chefes ----------------
    (lambda: B.Lich(tipo="rei"), "chefes", "grande", "chefe"),
    # ---------------- fase 4: Bosque Carmesim ----------------
    (lambda: FE.LoboSarnento(), "feras", "medio", "soldado"),
    (lambda: FL.FungoEsporento(), "fungos", "pequeno", "suporte"),
    (lambda: F4.EspantalhoPossuido(), "assombracoes", "medio", "dano"),
    (lambda: FL.RaizSanguinea(), "plantas", "pequeno", "invocacao"),
    (lambda: FL.MaeRaiz(), "plantas", "enorme", "chefe"),
    # ---------------- fase 4: Pântano dos Afogados ----------------
    (lambda: MO.Afogado(), "mortos_vivos", "medio", "soldado"),
    (lambda: FE.SanguessugaColossal(), "pantanosos", "grande", "tanque"),
    (lambda: MO.BruxaDoLodo(), "bruxaria", "medio", "conjurador"),
    (lambda: F4.SapoBoi(), "pantanosos", "grande", "suporte"),
    (lambda: MO.BarqueiroSemRosto(), "assombracoes", "enorme", "chefe"),
    # ---------------- fase 4: Catacumbas da Ordem Caída ----------------
    (lambda: CO.RelicarioVivo(), "ordem_caida", "pequeno", "suporte"),
    (lambda: F4.EnxameDeRatos(), "pestes", "pequeno", "enxame"),
    (lambda: F4.InquisidorPenitente(), "ordem_caida", "grande", "chefe"),
    # ---------------- fase 4: Minas de Brasa ----------------
    (lambda: MO.KoboldDinamiteiro(), "kobolds", "pequeno", "dano"),
    (lambda: FE.SalamandraDeLava(), "elementais_de_fogo", "medio", "dano"),
    (lambda: MO.MineradorAmaldicoado(), "mortos_vivos", "medio", "soldado"),
    (lambda: CH.ForjadorAntigo(), "assombracoes", "enorme", "chefe"),
    # ---------------- fase 4: Cidadela Congelada ----------------
    (lambda: MO.SentinelaDeGelo(), "elementais_de_gelo", "grande", "tanque"),
    (lambda: MO.ArautoDaNevasca(), "elementais_de_gelo", "medio", "conjurador"),
    (lambda: MO.DraconianoRenegado(), "dragoes", "medio", "dano"),
    (lambda: CH.RainhaDeGeloEterno(), "elementais_de_gelo", "enorme", "chefe"),
    (lambda: EC.ClerigoDoEclipse(), "eclipse", "medio", "suporte"),                     # fase 4: Catedral do Eclipse
    (lambda: GA.GargulaSentinela(), "construtos", "medio", "tanque"),
    (lambda: GA.GargulaCalha(), "construtos", "medio", "tanque"),
    (lambda: GA.GargulaQuimera(), "construtos", "medio", "tanque"),
    (lambda: EC.AnjoCorrompido(), "eclipse", "medio", "dano"),
    (lambda: EC.BispoEclipsado(), "eclipse", "enorme", "chefe"),
    (lambda: EC.BispoEclipsadoVitral(), "eclipse", "enorme", "chefe"),
    (lambda: EC.DragaoDoEclipse(), "dragoes", "enorme", "chefe"),
    (lambda: MO.MercadorMascarado(), "lendas", "medio", "chefe"),                       # fase 4: chefes secretos
    # ---------------- bardo (classe jogável) ----------------
    (lambda: C.Bardo(), "herois", "medio", "heroi"),
    (lambda: C.BoboDaCorte(), "herois", "medio", "heroi"),
    (lambda: HN.Monge(), "herois", "medio", "heroi"),
    (lambda: HN.Feiticeira(), "herois", "medio", "heroi"),
    (lambda: HR.MedicoDaPeste(), "herois", "medio", "heroi"),                       # etapa 6A: herói secreto do Reino
    (lambda: HR.SenhorDosRatos(), "herois", "medio", "heroi"),                      # etapa 6B: o outro herói secreto
    (lambda: HR.EnxameDeMoscas(), "invocacoes", "pequeno", "invocacao"),            # (a invocação dele)
    # ---------------- personagens do acampamento e das paradas ----------------
    (lambda: C.Taverneiro(), "npcs", "medio", "npc"),
    (lambda: C.Capita(), "npcs", "medio", "npc"),
    (lambda: C.Mercador(), "npcs", "medio", "npc"),
    (lambda: C.Alquimista(), "npcs", "medio", "npc"),
    (lambda: C.Necromante(), "npcs", "medio", "npc"),
    (lambda: C.Mestre(), "npcs", "medio", "npc"),
    (lambda: C.Estudioso(), "npcs", "medio", "npc"),
    (lambda: C.MestreDoGrimorio(), "npcs", "medio", "npc"),
    (lambda: C.MagoAnciao(), "npcs", "medio", "npc"),
    # ---------------- invocações dos heróis ----------------
    (lambda: FE.LoboEspectral(), "invocacoes", "medio", "invocacao"),
    (lambda: FE.LoboEspectralSelvagem(), "espectros", "medio", "invocacao"),      # fase 4: Cidadela
    (lambda: CO.Torreta(), "invocacoes", "pequeno", "invocacao"),
    (lambda: V.Fada(), "invocacoes", "pequeno", "invocacao"),
    (lambda: FE.TigreEspiritual(), "invocacoes", "medio", "invocacao"),
    (lambda: FE.MacacoEspiritual(), "invocacoes", "pequeno", "invocacao"),
    (lambda: FE.GarcaEspiritual(), "invocacoes", "pequeno", "invocacao"),
    (lambda: FE.Corvo(), "invocacoes", "pequeno", "invocacao"),
    (lambda: FE.GatoNegro(), "invocacoes", "pequeno", "invocacao"),
    (lambda: V.SapoVenenoso(), "invocacoes", "pequeno", "invocacao"),
    # ---------------- objetos ----------------
    (lambda: V.Altar(), "objetos", "medio", "objeto"),
    (lambda: V.Bau(), "objetos", "pequeno", "objeto"),
    # ---------------- cena do acampamento ----------------
    (lambda: AD.Fogueira(), "objetos", "medio", "objeto"),
    (lambda: AD.BarracaDaTaverna(), "objetos", "grande", "objeto"),
    (lambda: AD.BalcaoDaTaverna(), "objetos", "grande", "objeto"),
    (lambda: CA.Tronco(), "objetos", "pequeno", "objeto"),
    (lambda: CA.PilhaDeLivros(), "objetos", "pequeno", "objeto"),
    (lambda: CA.PosteDeLanterna(), "objetos", "medio", "objeto"),
    (lambda: AD.EspelhoAntigo(), "objetos", "medio", "objeto"),
    (lambda: AD.BauOrnamentado(), "objetos", "medio", "objeto"),
    (lambda: AD.EstandeDeArmas(), "objetos", "medio", "objeto"),
    (lambda: AD.TendaGrande(), "objetos", "grande", "objeto"),
    (lambda: AD.TendaGrande(nome="tenda_grande_marrom", cores=((58, 80, 70), (200, 176, 130))),
     "objetos", "grande", "objeto"),
    (lambda: AD.Barril(), "objetos", "pequeno", "objeto"),
    (lambda: AD.Caixotes(), "objetos", "pequeno", "objeto"),
    (lambda: CA.Lenha(), "objetos", "pequeno", "objeto"),
    (lambda: CA.Caldeirao(), "objetos", "pequeno", "objeto"),
    (lambda: CA.AtrilDoGrimorio(), "objetos", "pequeno", "objeto"),                 # etapa 5: acampamento novo
    (lambda: AD.Carroca(), "objetos", "grande", "objeto"),
    (lambda: CA.EstandarteDaExpedicao(), "objetos", "medio", "objeto"),
    (lambda: CA.CirculoDeRunas(), "objetos", "medio", "objeto"),
    (lambda: CA.Tapete(), "objetos", "medio", "objeto"),
    (lambda: AD.TroncoComprido(), "objetos", "medio", "objeto"),                     # o banco em volta da fogueira
    # ---------------- acampamento em três planos: as mesmas forjas desenhadas menores (meio 85%, fundo 70%) ----------------
    # (o baú da frente também sai a 85%: no tamanho cheio ele ficava quase da altura de uma pessoa)
    (lambda: AD.na_distancia(C.Taverneiro, AD.LONGE, "longe", animacoes_extras=(("servir", 6),)), "npcs", "medio", "npc"),
    (lambda: AD.na_distancia(AD.BarracaDaTaverna, AD.LONGE, "longe"), "objetos", "grande", "objeto"),
    (lambda: AD.na_distancia(AD.BalcaoDaTaverna, AD.LONGE, "longe"), "objetos", "grande", "objeto"),
    (lambda: AD.na_distancia(AD.EstandeDeArmas, AD.MEIO, "meio"), "objetos", "medio", "objeto"),
    (lambda: AD.na_distancia(AD.BauOrnamentado, AD.MEIO, "meio"), "objetos", "medio", "objeto"),
    (lambda: AD.na_distancia(AD.TendaGrande, AD.LONGE, "longe"), "objetos", "grande", "objeto"),
    (lambda: AD.na_distancia(AD.TendaGrande, AD.LONGE, "longe", nome="tenda_grande_marrom",
                             cores=((58, 80, 70), (200, 176, 130))), "objetos", "grande", "objeto"),
    (lambda: AD.na_distancia(AD.Carroca, AD.LONGE, "longe"), "objetos", "grande", "objeto"),
    (lambda: AD.na_distancia(CA.PosteDeLanterna, AD.LONGE, "longe"), "objetos", "medio", "objeto"),
    (lambda: AD.na_distancia(AD.Barril, AD.LONGE, "longe"), "objetos", "pequeno", "objeto"),
    (lambda: AD.na_distancia(AD.Caixotes, AD.LONGE, "longe"), "objetos", "pequeno", "objeto"),
    (lambda: AD.na_distancia(C.Estudioso, AD.MEIO, "meio", animacoes_extras=(("folhear", 6),)), "npcs", "medio", "npc"),
    (lambda: AD.na_distancia(C.MestreDoGrimorio, AD.MEIO, "meio"), "npcs", "medio", "npc"),
    (lambda: AD.na_distancia(C.MagoAnciao, AD.MEIO, "meio"), "npcs", "medio", "npc"),
    (lambda: AD.na_distancia(AD.EspelhoAntigo, AD.MEIO, "meio"), "objetos", "medio", "objeto"),
    (lambda: AD.na_distancia(CA.CirculoDeRunas, AD.MEIO, "meio"), "objetos", "medio", "objeto"),
    (lambda: AD.na_distancia(CA.EstandarteDaExpedicao, AD.MEIO, "meio"), "objetos", "medio", "objeto"),
    (lambda: AD.na_distancia(CA.Tapete, AD.MEIO, "meio"), "objetos", "medio", "objeto"),
    # ---------------- variantes com sprite próprio (antes eram recolorações) ----------------
    (lambda: VA.GoblinDasCavernas(), "goblins", "pequeno", "enxame"),
    (lambda: VA.GoblinBrutoSangrento(), "goblins", "medio", "tanque"),
    (lambda: VA.EsqueletoMaldito(), "mortos_vivos", "medio", "soldado"),
    (lambda: VA.OrcDeSangue(), "orcs", "grande", "soldado"),
    (lambda: VA.AranhaVenenosa(), "insetos", "medio", "soldado"),
    (lambda: VA.PalhacoPalido(), "circo_macabro", "medio", "soldado"),
    (lambda: VA.BesouroDeBronze(), "insetos", "medio", "tanque"),
    (lambda: VA.CriaVampiricaAnciao(), "vampiros", "pequeno", "enxame"),
    (lambda: VA.LouvaDeusOrquidea(), "insetos", "grande", "dano"),
    (lambda: VA.CavaleiroOssudo(), "mortos_vivos", "medio", "elite"),               # fase 4: Catacumbas
    (lambda: VA.MongeFlagelante(), "ordem_caida", "medio", "soldado"),
    (lambda: VA.GolemDeEscoria(), "golens", "enorme", "tanque"),
    (lambda: VA.SombraDoHeroi(), "sombras", "medio", "soldado"),                    # fase 4: Catedral do Eclipse
    # ---------------- inimigos nomeados (antes usavam o sprite de um herói) ----------------
    (lambda: NO.Gnarl(), "goblins", "medio", "elite"),
    (lambda: NO.CacadoraCorrompida(), "herois_corrompidos", "medio", "elite"),
    (lambda: NO.CavaleiroCaido(), "herois_corrompidos", "medio", "elite"),
    (lambda: NO.BarbaroPossuido(), "herois_corrompidos", "medio", "elite"),
    (lambda: NO.FeiticeiraRenegada(), "herois_corrompidos", "medio", "elite"),
    (lambda: NO.AssassinaSemRosto(), "herois_corrompidos", "medio", "elite"),
    (lambda: NO.PaladinoProfano(), "herois_corrompidos", "medio", "elite"),
    (lambda: LE.PrimeiroHeroi(), "lendas", "medio", "chefe"),                       # fase 4: chefe secreto
    # inimigos que nasceram das demonstrações das forjas (versões novas, ao lado das antigas)
    (lambda: DF.LoboCarnical(), "feras", "medio", "soldado"),
    (lambda: DF.BesouroChifrudo(), "insetos", "medio", "tanque"),
    (lambda: DF.CorvoCarniceiro(), "feras", "pequeno", "dano"),
    (lambda: DF.CogumeloPustulento(), "fungos", "pequeno", "suporte"),
    (lambda: DF.PenitenteDeformado(), "ordem_caida", "medio", "tanque"),
    (lambda: DF.CarnicalEsqueletico(), "mortos_vivos", "medio", "enxame"),
    (lambda: DF.ArvoreFaminta(), "plantas", "grande", "invocacao"),                # invocada pela Mãe-Raiz
    # ---------------- Reino dos Ratos (docs/planos/reino_dos_ratos.md) ----------------
    (lambda: RR.RatoBranco(), "segredos", "pequeno", "guia"),                      # etapa 1: o guia até o bueiro
    (lambda: RR.RatoComum(), "pestes", "pequeno", "enxame"),                       # etapa 3A: o jogo desenha o bando
    (lambda: RR.RatazanaGigante(), "pestes", "medio", "tanque"),
    (lambda: RR.RatoDaPeste(), "pestes", "pequeno", "dano"),
    (lambda: RR.RatoLadrao(), "pestes", "pequeno", "dano"),                       # etapa 3B1
    (lambda: RR.RatoNadador(), "pestes", "pequeno", "dano"),
    (lambda: RR.RatoBombardeiro(), "pestes", "pequeno", "dano"),
    (lambda: RR.RatoAlquimista(), "pestes", "pequeno", "suporte"),
    (lambda: RR.RatoXama(), "pestes", "pequeno", "suporte"),                       # etapa 3B2
    (lambda: RR.RatoGuardaReal(), "pestes", "pequeno", "tanque"),
    (lambda: RR.RatoArauto(), "pestes", "pequeno", "suporte"),
    (lambda: RR.RatoRei(), "pestes", "enorme", "chefe"),                           # etapa 5A: o Rei e o Queijo Real
    (lambda: RR.QueijoReal(), "objetos", "medio", "objeto"),
    (lambda: RR.NoDeCaudas(), "pestes", "enorme", "chefe"),                         # etapa 5B: a Rainha e a roda
    (lambda: RR.MordedorDaRainha(), "pestes", "pequeno", "dano"),
    (lambda: RR.PestilentoDaRainha(), "pestes", "pequeno", "dano"),
    (lambda: RR.GuinchoDaRainha(), "pestes", "pequeno", "suporte"),
    (lambda: RR.CurandeiroDaRainha(), "pestes", "pequeno", "suporte"),
    (lambda: RR.TronoDosRatos(), "cenario", "enorme", "cenario"),                   # etapa 5R1: o trono animado
    (lambda: BU.HomemBubonico(), "bubonicos", "grande", "tanque"),                    # etapa 3C1: humanos bubônicos
    (lambda: BU.MendigoBubonico(), "bubonicos", "medio", "suporte"),
    (lambda: BU.CarrascoBubonico(), "bubonicos", "grande", "elite"),
    (lambda: BU.FreiraRoida(), "bubonicos", "medio", "conjurador"),
    (lambda: BU.MedicoDaPesteCorrompido(), "bubonicos", "grande", "chefe"),          # etapa 3C2: mini-chefes
    (lambda: BU.FlautistaCaido(), "bubonicos", "medio", "chefe"),
    (lambda: RR.RatoMercador(), "eventos", "pequeno", "npc"),                        # etapa 4A: figuras de evento
    (lambda: BU.PrisioneiroNaGaiola(), "eventos", "medio", "npc"),
]

# geometria de cada herói-base (qual esqueleto as camadas cosméticas usam)
GEOMETRIA_DOS_HEROIS = {"guerreiro": "guerreiro", "paladino": "paladino", "barbaro_Espada": "barbaro_Espada",
                        "barbaro_Machado": "barbaro_Machado", "barbaro_Martelo": "barbaro_Martelo",
                        "mago_Fogo": "mago", "mago_Gelo": "mago", "mago_Raio": "mago", "arqueira": "arqueira",
                        "assassina": "assassina", "bardo": "bardo", "bobo": "bobo",
                        "monge": "monge", "feiticeira": "feiticeira", "medico_da_peste": "medico_da_peste",
                        "senhor_dos_ratos": "senhor_dos_ratos"}

# roupas das subclasses/especializações e skins (forja/personagens/roupas.py)
CATALOGO += [(fabrica, "herois", "medio", "heroi", {"geometria": geometria}) for _, geometria, fabrica in ROUPAS]


def desarmar(fabrica):
    """A mesma roupa sem a arma da classe: o jogo usa quando o herói tem arma equipada (ela vem numa camada)."""
    def criar():
        m = fabrica()
        m.armado = False
        m.nome = m.nome + "_desarmado"
        return m
    return criar


def geometria_da_entrada(fabrica, extra):
    return (extra[0] if extra else {}).get("geometria") or GEOMETRIA_DOS_HEROIS.get(fabrica().nome)


# heróis desarmados (o monge luta de mãos vazias: não precisa)
CATALOGO += [(desarmar(fab), fam, tam, papel, {"geometria": geo})
             for fab, fam, tam, papel, *extra in list(CATALOGO)
             if fam == "herois" and (geo := geometria_da_entrada(fab, extra)) and geo != "monge"]


def meta_da_camada(g, a):
    meta = {"geometria": g}
    if a in PECAS:                                       # equipamento: tingido pelo jogo; capas atrás do herói
        meta["tingivel"] = True
        if a in PECAS_ATRAS:
            meta["atras"] = True
    return meta


# camadas cosméticas e de equipamento: uma por geometria (forja/personagens/camadas.py e equipamento.py)
CATALOGO += [((lambda g=g, a=a: CamadaVisual(g, a)), "camadas", "medio", "camada", meta_da_camada(g, a))
             for g in GEOMETRIAS for a in ACESSORIOS]


# Variantes de cor (recolorações) para dar contraste nas hordas:
# (base, novo nome, giro de matiz em graus, saturação x, brilho x[, {campos do catálogo que mudam}])
RECORES = [
]


def recolorir(nome_base, novo, giro, sat, val):
    import numpy as np
    img = Image.open(os.path.join(PASTA, nome_base + ".png")).convert("RGBA")
    a = np.asarray(img).astype(np.float32) / 255.0
    rgb = a[..., :3]
    mx = rgb.max(-1)
    mn = rgb.min(-1)
    d = mx - mn
    h = np.zeros_like(mx)
    m = d > 1e-6
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    idx = m & (mx == r)
    h[idx] = ((g - b)[idx] / d[idx]) % 6
    idx = m & (mx == g)
    h[idx] = (b - r)[idx] / d[idx] + 2
    idx = m & (mx == b)
    h[idx] = (r - g)[idx] / d[idx] + 4
    h = (h / 6 + giro / 360.0) % 1.0
    s = np.where(mx > 0, d / np.maximum(mx, 1e-6), 0) * sat
    s = np.clip(s, 0, 1)
    v = np.clip(mx * val, 0, 1)
    i = np.floor(h * 6).astype(int) % 6
    f = h * 6 - np.floor(h * 6)
    p = v * (1 - s)
    q = v * (1 - f * s)
    t = v * (1 - (1 - f) * s)
    out = np.zeros_like(rgb)
    for k, (R, G, B) in enumerate(((v, t, p), (q, v, p), (p, v, t), (p, q, v), (t, p, v), (v, p, q))):
        sel = i == k
        out[sel] = np.stack([R[sel], G[sel], B[sel]], -1)
    a[..., :3] = out
    Image.fromarray((a * 255).astype(np.uint8), "RGBA").save(os.path.join(PASTA, novo + ".png"))


def _gera(argumentos):
    """Gera uma folha. Com filtro, pula quem não combina (devolve None)."""
    indice, filtro = argumentos
    fab, familia, tamanho, papel, *extra = CATALOGO[indice]
    m = fab()
    if filtro and not any(f in m.nome for f in filtro):
        return None
    meta, _ = salvar_folha(m, PASTA)
    meta.update(familia=familia, tamanho=tamanho, papel=papel)
    if hasattr(m, "meta_extra"):                         # pontos que a tela usa (ex.: onde o rabo dos ratos da roda prende)
        meta.update(m.meta_extra())
    if m.nome in GEOMETRIA_DOS_HEROIS:
        meta["geometria"] = GEOMETRIA_DOS_HEROIS[m.nome]
    if extra:
        meta.update(extra[0])
    return meta


def galeria(metas, saida, escala=2):
    """Prancha com o 1º quadro de cada personagem, agrupado por família."""
    metas = [m for m in metas if m["familia"] != "camadas"]      # as camadas sozinhas não ajudam na prancha
    familias = []
    for m in metas:
        if m["familia"] not in familias:
            familias.append(m["familia"])
    linhas = []
    for fam in familias:
        imgs = []
        for m in metas:
            if m["familia"] != fam:
                continue
            folha = Image.open(os.path.join(PASTA, m["nome"] + ".png"))
            w, h = m["celula"]
            q = folha.crop((0, 0, w, h))
            bb = q.getbbox() or (0, 0, w, h)
            q = q.crop((max(0, bb[0] - 2), max(0, bb[1] - 2), min(w, bb[2] + 2), min(h, bb[3] + 2)))
            imgs.append((m["nome"], q.resize((q.width * escala, q.height * escala), Image.NEAREST)))
        linhas.append((fam, imgs))
    largura = max(sum(i.width + 16 for _, i in imgs) for _, imgs in linhas) + 20
    altura = sum(max(i.height for _, i in imgs) + 44 for _, imgs in linhas) + 10
    img = Image.new("RGBA", (largura, altura), (24, 20, 28, 255))
    d = ImageDraw.Draw(img)
    y = 6
    for fam, imgs in linhas:
        d.text((10, y), fam.upper().replace("_", " "), fill=(220, 190, 140, 255))
        hmax = max(i.height for _, i in imgs)
        x = 10
        for nome, im in imgs:
            img.alpha_composite(im, (x, y + 16 + hmax - im.height))
            d.text((x, y + 20 + hmax), nome, fill=(170, 160, 180, 255))
            x += im.width + 16
        y += hmax + 44
    img.save(saida)


def main():
    """Gera tudo, ou só os nomes que contêm os textos do filtro.

    Com filtro, as folhas novas são JUNTADAS ao catalogo.json que já existe
    (antes o catálogo era sobrescrito e perdia os outros personagens).
    """
    filtro = sys.argv[1:]
    os.makedirs(PASTA, exist_ok=True)
    t0 = time.time()
    with Pool() as pool:
        novas = [m for m in pool.map(_gera, [(i, filtro) for i in range(len(CATALOGO))]) if m is not None]

    caminho_catalogo = os.path.join(PASTA, "catalogo.json")
    catalogo = {}
    if filtro and os.path.exists(caminho_catalogo):
        with open(caminho_catalogo, encoding="utf-8") as f:
            catalogo = json.load(f)
    for meta in novas:
        catalogo[meta["nome"]] = meta
    # recolorações: refeitas quando a base foi gerada agora (ou quando o filtro pede a variante)
    geradas = {m["nome"] for m in novas}
    for base, novo, giro, sat, val, *extra in RECORES:
        if base in catalogo and (base in geradas or any(f in novo for f in filtro)):
            recolorir(base, novo, giro, sat, val)
            catalogo[novo] = dict(catalogo[base], nome=novo, variante_de=base, **(extra[0] if extra else {}))

    # mantém a ordem do CATALOGO (com cada recolor logo depois da base)
    ordem = []
    for meta in catalogo.values():
        if "variante_de" not in meta:
            ordem.append(meta)
            ordem.extend(m for m in catalogo.values() if m.get("variante_de") == meta["nome"])
    with open(caminho_catalogo, "w", encoding="utf-8") as f:
        json.dump({m["nome"]: m for m in ordem}, f, ensure_ascii=False, indent=1)
    os.makedirs(os.path.join(AQUI, "previas"), exist_ok=True)                 # (a galeria é descartável: vai com as prévias)
    galeria(ordem, os.path.join(AQUI, "previas", "galeria.png"))
    print(f"{len(novas)} folhas geradas ({len(ordem)} no catálogo) em {time.time() - t0:.1f}s -> {PASTA}")


if __name__ == "__main__":
    main()

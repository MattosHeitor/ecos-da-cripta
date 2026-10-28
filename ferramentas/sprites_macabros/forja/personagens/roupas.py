"""Roupas dos heróis: o mesmo modelo com outros materiais (tecidos, metais, pelagem) e adornos de silhueta.

Cada subclasse e especialização tem a sua roupa (classes.json -> "sprite"), e há roupas extras
que viram skins desbloqueáveis (skins.json). A pele e o rosto não mudam: só o que o modelo expõe
como material (tabardo, capa, aço, manto...) e os adornos (adornos.py): armas e estandartes nas
costas, asas, auréolas, ombreiras, itens no cinto etc., que dão a cada roupa um contorno próprio.

    ROUPAS = [(nome do sprite, geometria, fábrica)]

Para criar uma roupa nova: copie uma linha, troque o nome, as cores e os adornos, e rode
    python gerar_sprites.py <nome>
"""
from ..motor import Mat, metal
from . import herois as H
from . import acampamento as C
from . import herois_novos as N
from . import herois_do_reino as R
from . import adornos as A
from .. import fx


def pano(cor, **kw):
    kw.setdefault("desce", 0.3)
    kw.setdefault("ruido", 0.12)
    return Mat(cor, 6, **kw)


def capa(cor):
    return Mat(cor, 6, desce=0.4, ruido=0.1, relevo=0.6, arredonda=0.5)


def guerreiro(nome, tabardo, capa_cor, aco, adornos=()):
    return nome, "guerreiro", lambda: H.Guerreiro(nome=nome, tabardo=pano(tabardo), capa_mat=capa(capa_cor), aco=metal(aco),
                                                  adornos=adornos)


def paladino(nome, tabardo, capa_cor, marfim, adornos=()):
    return nome, "paladino", lambda: H.Paladino(nome=nome, tabardo=pano(tabardo), capa_mat=capa(capa_cor),
                                                marfim=metal(marfim, contraste=1.1), adornos=adornos)


def mago(elemento, adornos=()):
    return f"mago_{elemento}", "mago", lambda: H.MagoElemental(elemento=elemento, adornos=adornos)


def barbaro(nome, arma, pelagem, adornos=()):
    return nome, f"barbaro_{arma}", lambda: H.Barbaro(nome=nome, arma=arma,
                                                      pelagem=Mat(pelagem, 6, ruido=0.9, dither=0.7, relevo=0.8),
                                                      adornos=adornos)


def arqueira(nome, verde, capa_cor, adornos=()):
    return nome, "arqueira", lambda: H.Arqueira(nome=nome, verde=pano(verde), capa_mat=capa(capa_cor), adornos=adornos)


def assassina(nome, preto, carmim, adornos=()):
    return nome, "assassina", lambda: H.Assassina(nome=nome, preto=Mat(preto, 6, ruido=0.1, satur=0.6),
                                                  carmim=Mat(carmim, 6, relevo=0.6), adornos=adornos)


def bardo(nome, gibao, capa_cor, chapeu=(52, 24, 40), adornos=()):
    return nome, "bardo", lambda: C.Bardo(nome=nome, gibao=pano(gibao, desce=0.25, ruido=0.1), capa_mat=capa(capa_cor),
                                          chapeu=Mat(chapeu, 6, relevo=0.8), adornos=adornos)


def bobo(nome, cor_a, cor_b, adornos=()):
    return nome, "bobo", lambda: C.BoboDaCorte(nome=nome, cor_a=Mat(cor_a, 6, ruido=0.15), cor_b=Mat(cor_b, 6, ruido=0.15),
                                               adornos=adornos)


def monge(nome, tunica, faixa, aura=None, adornos=()):
    return nome, "monge", lambda: N.Monge(nome=nome, tunica=pano(tunica, desce=0.25), faixa=Mat(faixa, 5, relevo=0.6), aura=aura,
                                          adornos=adornos)


def feiticeira(nome, vestido, chapeu, magia="FOGO_ROXO", cabelo=(150, 40, 40), adornos=()):
    return nome, "feiticeira", lambda: N.Feiticeira(nome=nome, vestido=Mat(vestido, 6, desce=0.45, ruido=0.12, relevo=0.7,
                                                                           arredonda=0.6),
                                                    chapeu=Mat(chapeu, 6, relevo=0.8), magia=getattr(fx, magia),
                                                    cabelo=Mat(cabelo, 5, ruido=0.5), adornos=adornos)


def medico(nome, casaco, chapeu, mascara, lentes, adornos=()):
    """Médico da Peste (herói secreto do Reino): sobretudo encerado, chapéu, máscara de couro e a cor das lentes."""
    return nome, "medico_da_peste", lambda: R.MedicoDaPeste(
        nome=nome, casaco=Mat(casaco, 6, desce=0.35, ruido=0.08, relevo=0.9, especular=tuple(min(255, c + 70) for c in casaco)),
        chapeu=Mat(chapeu, 6, relevo=0.8, ruido=0.1), mascara=Mat(mascara, 6, relevo=1.1, ruido=0.15), lentes=lentes,
        adornos=adornos)


def senhor(nome, trapos, capuz, olhos, magia="FOGO_VERDE", moscas=6, ratos=2, mascara=(222, 214, 196), adornos=()):
    """Senhor dos Ratos (herói secreto do Reino): os trapos, o capuz, a cor dos olhos de mosca, a magia do livro e
    quantas moscas e ratos o acompanham."""
    return nome, "senhor_dos_ratos", lambda: R.SenhorDosRatos(
        nome=nome, trapos=Mat(trapos, 6, desce=0.4, ruido=0.35, relevo=0.8, dither=0.4), capuz=Mat(capuz, 6, relevo=0.8, ruido=0.3),
        mascara=Mat(mascara, 6, relevo=1.0, ruido=0.12), olhos=olhos, magia=getattr(fx, magia), moscas=moscas, ratos=ratos,
        adornos=adornos)


ROUPAS = [
    # ---------------- Guerreiro ----------------
    guerreiro("guerreiro_guardiao", (196, 186, 156), (130, 26, 36), (176, 176, 194), adornos=(
        A.estandarte(cor=(214, 204, 176), emblema="cruz", cor_emblema=(150, 24, 30)),
        A.tabardo_longo(cor=(196, 186, 156), emblema="cruz"),
        A.ombreira("dourada", cor=(150, 150, 168), tam=1.1))),
    guerreiro("guerreiro_berserker", (110, 20, 26), (50, 16, 20), (96, 88, 96), adornos=(
        A.arma_costas("machado", metal_cor=(110, 104, 110)),
        A.ombreira("espinhos", cor=(96, 88, 96), tam=1.2),
        A.cintura(("cranio", "gancho", "cranio")))),
    guerreiro("guerreiro_carniceiro", (70, 10, 14), (36, 12, 14), (120, 76, 54), adornos=(
        A.arma_costas("cutelo", metal_cor=(150, 146, 150)),
        A.avental(cor=(176, 164, 140)),
        A.cintura(("cutelo", "gancho")))),
    guerreiro("guerreiro_gladiador", (150, 110, 40), (90, 40, 24), (176, 124, 62), adornos=(
        A.arma_costas("tridente", metal_cor=(176, 150, 90)),
        A.pteruges(cor=(130, 80, 40)),
        A.manica(cor=(176, 124, 62)))),
    guerreiro("guerreiro_campeao", (200, 160, 60), (120, 20, 30), (214, 174, 84), adornos=(
        A.arma_costas("montante", metal_cor=(214, 174, 84), inclina=0.45),
        A.pteruges(cor=(120, 20, 30), metal_cor=(214, 174, 84)),
        A.ombreira("dourada", cor=(214, 174, 84), tam=1.3))),
    # ---------------- Ladino ----------------
    assassina("assassina_ceifador", (30, 28, 36), (70, 70, 80), adornos=(
        A.arma_costas("foice", metal_cor=(150, 150, 166), inclina=0.45),
        A.fitas(cor=(30, 28, 36), n=2, comp=0.4, estilo="fumaca"))),
    assassina("assassina_duelista", (64, 46, 40), (44, 94, 156), adornos=(
        A.gola_alta("babado", cor=(220, 214, 200)),
        A.cintura(("bainha",), cores=((44, 60, 110),)))),
    assassina("assassina_esgrimista", (84, 62, 42), (204, 172, 84), adornos=(
        A.arma_costas("rapieiras", metal_cor=(190, 190, 204)),
        A.ombreira("couro", cor=(110, 80, 50), tam=0.9))),
    assassina("assassina_envenenador", (40, 54, 40), (110, 172, 60), adornos=(
        A.bandoleira("frascos", cor=(60, 44, 34), cor_item=(110, 210, 70)),
        A.cintura(("frasco", "bolsa"), cores=((150, 90, 220), None)),
        A.particulas("gotas", cor=(90, 190, 60), n=8))),
    assassina("assassina_praga", (50, 40, 62), (150, 204, 64), adornos=(
        A.pteruges(cor=(50, 40, 62), comp=0.2, rasgado=True),
        A.cintura(("incensario",), cores=((150, 204, 64),)),
        A.particulas("moscas", n=12))),
    # ---------------- Mago ----------------
    mago("Morte", adornos=(
        A.asas("osso", cor=(60, 70, 60)),
        A.cintura(("cranio", "livro", "cranio"), cores=(None, (40, 60, 44), None)))),
    mago("Cinzas", adornos=(
        A.gola_alta("rigida", cor=(46, 40, 40)),
        A.ombreira("brasa", cor=(50, 44, 44), tam=1.15),
        A.particulas("brasas", n=12))),
    mago("Inverno", adornos=(
        A.aureola("cristais", cor=(170, 230, 255)),
        A.gola_alta("pele", cor=(220, 226, 236)))),
    mago("Runas", adornos=(
        A.aureola("runas", cor=(150, 200, 255)),
        A.orbes("pedra", cor=(150, 200, 255), n=3),
        A.cintura(("livro",), cores=((60, 72, 96),)))),
    mago("Sangue", adornos=(
        A.fitas(cor=(110, 10, 20), n=3, comp=0.4, estilo="sangue"),
        A.orbes("gota", cor=(150, 16, 26), n=4))),
    # ---------------- Sacerdote ----------------
    paladino("paladino_druida", (60, 100, 50), (70, 90, 50), (150, 132, 92), adornos=(
        A.galhos(cor=(80, 62, 46), folhas=(80, 120, 50)),
        A.ombreira("folhas", cor=(90, 130, 50)),
        A.particulas("folhas", cor=(120, 140, 50), n=8))),
    paladino("paladino_bosque", (40, 120, 60), (90, 70, 40), (170, 150, 100), adornos=(
        A.ombreira("cogumelos", cor=(170, 40, 40), tam=1.1),
        A.raizes(cor=(84, 64, 44), n=4, flores=(230, 200, 90)),
        A.particulas("vagalumes", n=8))),
    paladino("paladino_martelo", (150, 20, 20), (110, 96, 80), (204, 172, 92), adornos=(
        A.ombreira("selos", cor=(204, 172, 92), tam=1.2),
        A.tabardo_longo(cor=(150, 20, 20), emblema="martelo", cor_emblema=(214, 180, 90)),
        A.cintura(("livro",), cores=((120, 20, 20),)))),
    paladino("paladino_ocultista", (60, 30, 80), (40, 30, 50), (150, 150, 170), adornos=(
        A.ombreira("velas", cor=(110, 100, 120)),
        A.orbes("olho", cor=(190, 60, 220), n=3),
        A.cintura(("boneco", "chave"), cores=((120, 100, 140), None)))),
    paladino("paladino_oraculo", (90, 40, 120), (30, 20, 40), (120, 110, 140), adornos=(
        A.asas("penas", cor=(210, 200, 230)),
        A.aureola("mandala", cor=(220, 180, 255)))),
    # ---------------- Bárbaro ----------------
    barbaro("barbaro_besta", "Machado", (204, 204, 214), adornos=(
        A.espinhos_costas(cor=(214, 202, 172), n=5),
        A.ombreira("pele", cor=(204, 204, 214), tam=1.35),
        A.cintura(("garras", "cranio")))),
    barbaro("barbaro_tempestade", "Martelo", (60, 80, 112), adornos=(
        A.orbes("pedra", cor=(170, 210, 255), n=3, raio=0.3),
        A.ombreira("ferro", cor=(80, 90, 110), tam=1.1),
        A.particulas("faiscas", cor=(200, 220, 255), n=10))),
    barbaro("barbaro_tita", "Espada", (40, 34, 30), adornos=(
        A.trofeu("escudos"),
        A.ombreira("ferro", cor=(96, 92, 98), tam=1.45),
        A.cintura(("chave", "cranio")))),
    # ---------------- Patrulheira ----------------
    arqueira("arqueira_bosque", (50, 92, 60), (92, 120, 70), adornos=(
        A.arma_costas("arco", cabo=Mat((110, 80, 46), 5, ruido=0.2)),
        A.ombreira("folhas", cor=(80, 130, 60)),
        A.particulas("folhas", cor=(110, 150, 60), n=8))),
    arqueira("arqueira_cacadora", (52, 40, 62), (40, 30, 52), adornos=(
        A.arma_costas("besta", metal_cor=(190, 196, 210), cabo=Mat((50, 34, 30), 5, ruido=0.2)),
        A.bandoleira("estacas", cor=(50, 36, 34), cor_item=(200, 206, 220)))),
    arqueira("arqueira_monstros", (72, 40, 40), (110, 110, 122), adornos=(
        A.trofeu("cranio"),
        A.cintura(("lanterna", "bolsa")),
        A.bandoleira("dentes", cor=(70, 50, 40), n=6))),
    arqueira("arqueira_armadilheira", (92, 72, 46), (70, 56, 40), adornos=(
        A.armadilhas(),
        A.cintura(("bolsa", "bolsa", "faca"), cores=((110, 80, 50), (90, 70, 46), None)))),
    arqueira("arqueira_mestra", (112, 82, 42), (40, 40, 30), adornos=(
        A.aljava_grande(cor=(110, 70, 40), n=10),
        A.gola_alta("pele", cor=(120, 100, 80)),
        A.ombreira("couro", cor=(112, 82, 42)))),
    # ---------------- Bardo ----------------
    bardo("bardo_hino", (150, 110, 30), (110, 20, 24), adornos=(
        A.estandarte(cor=(150, 110, 30), emblema="nota", cor_emblema=(110, 20, 24)),
        A.cintura(("berrante",)))),
    bardo("bardo_sussurros", (50, 40, 80), (24, 20, 40), (30, 26, 40), adornos=(
        A.fitas(cor=(40, 30, 70), n=3, comp=0.4, estilo="fumaca"),
        A.particulas("notas", cor=(180, 140, 255), n=12))),
    bardo("bardo_abismo", (20, 60, 70), (10, 20, 30), (16, 30, 36), adornos=(
        A.tentaculos(cor=(30, 80, 90), n=3),
        A.cintura(("filacterio",), cores=((90, 220, 230),)))),
    bardo("bardo_menestrel", (40, 90, 90), (90, 30, 40), adornos=(
        A.arma_costas("laminas", metal_cor=(180, 180, 194)),
        A.bandoleira("facas", cor=(80, 30, 40)))),
    bardo("bardo_dancarino", (190, 170, 190), (60, 20, 60), (90, 40, 90), adornos=(
        A.fitas(cor=(200, 60, 120), n=2, comp=0.4, origem="cintura"),
        A.cintura(("sino", "sino", "sino")),
        A.particulas("petalas", n=8))),
    # ---------------- Bobo da Corte ----------------
    bobo("bobo_mascaras", (30, 30, 40), (220, 214, 200), adornos=(
        A.gola_alta("babado", cor=(220, 214, 200)),
        A.cintura(("mascara", "mascara", "mascara"), cores=((222, 214, 200), (30, 30, 40), (170, 30, 40))))),
    bobo("bobo_macabro", (60, 90, 50), (150, 40, 60), adornos=(
        A.balao(cor=(170, 24, 30)),
        A.cintura(("cranio", "chocalho")))),
    bobo("bobo_cripta", (40, 60, 40), (200, 200, 180), adornos=(
        A.arma_costas("pa", metal_cor=(120, 116, 120)),
        A.cintura(("lanterna", "chave"), cores=((150, 255, 160), None)))),
    bobo("bobo_malabarista", (40, 60, 110), (190, 160, 90), adornos=(
        A.bandoleira("facas", cor=(40, 50, 90)),
        A.orbes("faca", n=3, raio=0.3))),
    bobo("bobo_aco", (90, 90, 100), (170, 170, 190), adornos=(
        A.ombreira("espinhos", cor=(150, 150, 166)),
        A.pteruges(metal_cor=(150, 150, 166)))),
    # ---------------- Monge ----------------
    monge("monge_dragao", (170, 40, 30), (230, 170, 60), aura=(255, 140, 60), adornos=(
        A.fitas(cor=(255, 150, 50), n=1, comp=0.5, estilo="dragao"),
        A.manica(cor=(200, 150, 60)))),
    monge("monge_espirito", (210, 210, 220), (90, 140, 200), adornos=(
        A.orbes("espirito", cor=(150, 200, 255), n=3, raio=0.3),
        A.contas_grandes(cor=(120, 90, 60), borla=(90, 140, 200)))),
    monge("monge_ancestral", (150, 160, 190), (60, 70, 110), aura=(150, 200, 255), adornos=(
        A.aureola("mandala", cor=(150, 200, 255), escala=1.15),
        A.contas_grandes(cor=(220, 210, 180), borla=(60, 70, 110)))),
    monge("monge_serenidade", (230, 220, 190), (120, 160, 110), adornos=(
        A.arma_costas("bastao", metal_cor=(150, 130, 80)),
        A.cintura(("cabaca",)))),
    monge("monge_lotus", (230, 170, 190), (110, 150, 90), aura=(255, 200, 220), adornos=(
        A.aureola("lotus", cor=(250, 180, 210)),
        A.particulas("petalas", n=10))),
    # ---------------- Feiticeira ----------------
    feiticeira("feiticeira_ninhada", (60, 70, 40), (40, 46, 26), "FOGO_VERDE", (90, 60, 40), adornos=(
        A.familiar("sapo", cor=(90, 140, 60), olhos=(255, 210, 60)),
        A.cintura(("frasco", "frasco"), cores=((110, 220, 90), (200, 160, 60))))),
    feiticeira("feiticeira_lua", (130, 150, 190), (40, 50, 90), "GELO", (220, 220, 230), adornos=(
        A.aureola("lua", cor=(220, 230, 255)),
        A.particulas("estrelas", cor=(220, 230, 255), n=8))),
    feiticeira("feiticeira_eclipse", (40, 20, 40), (90, 14, 30), "FOGO", (30, 24, 30), adornos=(
        A.aureola("eclipse", cor=(255, 150, 60)),
        A.fitas(cor=(90, 14, 30), n=2, comp=0.35))),
    feiticeira("feiticeira_maldicoes", (30, 30, 34), (70, 20, 60), "FOGO_ROXO", (60, 50, 70), adornos=(
        A.familiar("corvo", cor=(40, 38, 52), olhos=(200, 80, 255)),
        A.cintura(("boneco", "boneco", "chave"), cores=((150, 130, 100), (110, 90, 120), None)))),
    feiticeira("feiticeira_velha", (80, 76, 70), (50, 46, 40), "FOGO_VERDE", (210, 210, 200), adornos=(
        A.arma_costas("vassoura"),
        A.cintura(("caldeirao", "cabaca")))),
    # ---------------- Médico da Peste (etapa 6A; o Doutor da Peste usa o modelo-base: preto, lentes verdes) ----------------
    medico("medico_boticario", (92, 62, 40), (60, 40, 28), (138, 102, 70), (255, 190, 80), adornos=(
        A.bandoleira(itens="frascos", cor=(70, 46, 34), cor_item=(230, 180, 70), n=5),
        A.cintura(("frasco", "bolsa", "frasco"), cores=((150, 220, 80), (110, 80, 50), (220, 90, 70))))),
    medico("medico_cirurgiao", (52, 70, 50), (34, 44, 34), (74, 84, 66), (220, 236, 226), adornos=(
        A.avental(cor=(176, 168, 146)),
        A.cintura(("faca", "gancho"), cores=((190, 196, 206), (150, 150, 160))))),
    medico("medico_quarentena", (30, 30, 36), (20, 20, 24), (40, 38, 44), (150, 255, 170), adornos=(
        A.gola_alta("rigida", cor=(206, 200, 184)),
        A.cintura(("sino", "lanterna")))),
    medico("medico_envenenador", (74, 30, 42), (44, 18, 28), (96, 60, 70), (200, 130, 255), adornos=(
        A.gola_alta("babado", cor=(222, 214, 200)),
        A.bandoleira(itens="frascos", cor=(60, 30, 36), cor_item=(150, 230, 90), n=5),
        A.particulas("vagalumes", cor=(150, 230, 90), n=6))),
    medico("medico_anatomista", (30, 44, 34), (20, 30, 24), (54, 60, 50), (255, 80, 64), adornos=(
        A.avental(cor=(150, 140, 120)),
        A.arma_costas("cutelo", metal_cor=(170, 166, 170)),
        A.particulas("moscas", n=8))),
    # ---------------- Senhor dos Ratos (etapa 6B; o Rei dos Bandos usa o modelo-base: trapos cinza, dois ratos) ----------------
    senhor("senhor_moscas", (40, 48, 36), (28, 34, 26), (240, 70, 40), moscas=14, ratos=0, adornos=(
        A.particulas("moscas", n=12),
        A.cintura(("cabaca", "bolsa")))),
    senhor("senhor_profeta", (52, 36, 56), (36, 24, 40), (230, 70, 150), magia="FOGO_ROXO", moscas=4, ratos=1,
           mascara=(204, 194, 176), adornos=(
        A.orbes("cranio", cor=(200, 90, 230), n=3),
        A.fitas(cor=(52, 36, 56), n=2, comp=0.35, estilo="fumaca"))),
    senhor("senhor_pai_dos_ratos", (88, 70, 52), (60, 48, 38), (230, 40, 30), moscas=4, ratos=4, adornos=(
        A.gola_alta("pele", cor=(96, 86, 76)),
        A.cintura(("cranio", "bolsa")))),
    senhor("senhor_enxame", (30, 36, 28), (20, 24, 18), (255, 90, 40), moscas=22, ratos=0, adornos=(
        A.particulas("moscas", n=20),
        A.fitas(cor=(40, 60, 30), n=2, comp=0.4, estilo="fumaca"))),
    senhor("senhor_arauto", (34, 20, 26), (24, 14, 18), (255, 40, 30), magia="FOGO", moscas=6, ratos=1,
           mascara=(232, 226, 214), adornos=(
        A.aureola("espinhos", cor=(120, 40, 40)),
        A.fitas(cor=(60, 30, 40), n=3, comp=0.4, estilo="fumaca"))),
    # ---------------- skins desbloqueáveis (skins.json) ----------------
    guerreiro("skin_guerreiro_ossudo", (30, 26, 30), (40, 36, 40), (204, 192, 162), adornos=(
        A.espinhos_costas(cor=(204, 192, 162), n=4),
        A.ombreira("cranio", cor=(204, 192, 162), tam=1.2, brilho=(120, 255, 200)))),
    assassina("skin_ladino_aranha", (44, 32, 32), (204, 194, 172), adornos=(
        A.tentaculos(cor=(44, 32, 32), n=4, ventosas=(204, 194, 172), estilo="patas"),)),
    mago("Lich", adornos=(
        A.aureola("espinhos", cor=(100, 130, 120)),
        A.gola_alta("osso"),
        A.cintura(("filacterio",)))),
    paladino("skin_sacerdote_aurora", (230, 220, 200), (220, 200, 150), (224, 192, 110), adornos=(
        A.aureola("sol", cor=(255, 214, 130), escala=1.1),
        A.asas("penas", cor=(250, 240, 220)))),
    barbaro("skin_barbaro_urso", "Machado", (112, 72, 42), adornos=(
        A.gola_alta("pele", cor=(112, 72, 42)),
        A.ombreira("pele", cor=(112, 72, 42), tam=1.4),
        A.cintura(("garras",)))),
    arqueira("skin_patrulheira_lua", (60, 70, 112), (40, 40, 82), adornos=(
        A.asas("mariposa", cor=(110, 120, 170), brilho=(200, 220, 255)),
        A.particulas("vagalumes", cor=(200, 230, 255), n=8))),
    bardo("skin_bardo_circo", (200, 40, 40), (230, 200, 60), (40, 30, 30), adornos=(
        A.estandarte(cor=(200, 40, 40), emblema="listras", cor_emblema=(230, 200, 60)),
        A.cintura(("sino", "chocalho")))),
    bobo("skin_bobo_rei", (24, 20, 28), (220, 180, 70), adornos=(
        A.gola_alta("arminho", cor=(230, 226, 218)),
        A.estandarte(cor=(24, 20, 28), emblema="coroa", cor_emblema=(220, 180, 70)))),
    monge("skin_monge_jade", (70, 150, 110), (200, 180, 90), aura=(140, 255, 190), adornos=(
        A.orbes("jade", cor=(110, 220, 160), n=5, raio=0.3),
        A.manica(cor=(90, 180, 130)))),
    feiticeira("skin_feiticeira_cinzas", (80, 70, 70), (40, 34, 34), "FOGO", (200, 90, 40), adornos=(
        A.fitas(cor=(70, 60, 60), n=3, comp=0.4, estilo="fumaca"),
        A.particulas("brasas", n=12))),
    # Reino dos Ratos (etapa 7C): vencer a Rainha 3 vezes
    senhor("skin_senhor_manto_da_roda", (70, 34, 40), (46, 22, 28), (255, 70, 50), moscas=3, ratos=3,
           mascara=(220, 210, 194), adornos=(
        A.manto_de_caudas(),
        A.gola_alta("pele", cor=(120, 96, 86)))),
]

"""Inimigos que nasceram das demonstrações das forjas (criaturas/demos.py): o mesmo desenho, com o nome
que eles têm no jogo. São versões novas, ao lado das antigas (o Carniçal, o Corvo e o Fungo continuam).

    LoboCarnical         lobo esfomeado de pelo falhado, costelas à mostra e baba de sangue
    BesouroChifrudo      besouro de carapaça violeta e chifre, que abre os élitros para investir
    CorvoCarniceiro      corvo grande em voo, olho vermelho e bico curvo
    ArvoreFaminta        árvore de olhos de brasa e boca de farpas: a Mãe-Raiz a chama quando floresce
    CogumeloPustulento   chapéu sangrento com pintas que brilham e nuvem de esporos
    PenitenteDeformado   corcunda de braço comprido, capuz vazio, armadura partida e correntes
    CarnicalEsqueletico  carniçal só pele e osso, cabeça grande e garras compridas
"""
from ..criaturas import demos as D


class LoboCarnical(D.LoboCarnicalDemo):
    nome = "lobo_carnical"


class BesouroChifrudo(D.BesouroDemo):
    nome = "besouro_chifrudo"


class CorvoCarniceiro(D.CorvoDemo):
    nome = "corvo_carniceiro"


class ArvoreFaminta(D.ArvoreFamintaDemo):
    nome = "arvore_faminta"


class CogumeloPustulento(D.CogumeloDemo):
    nome = "cogumelo_pustulento"


class PenitenteDeformado(D.PenitenteDemo):
    nome = "penitente_deformado"


class CarnicalEsqueletico(D.CarnicalDemo):
    nome = "carnical_esqueletico"

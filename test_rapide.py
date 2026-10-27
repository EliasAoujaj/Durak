"""Vérifie que le moteur rapide applique exactement les mêmes règles que moteur.py."""

import random

from cartes import Carte, Couleur
from joueurs import JoueurAleatoire, JoueurFinal, JoueurPetit, REGLAGES_RECHERCHE
from arene import match
from moteur import TypeAction, actions_legales, appliquer, fin_de_partie, joueur_actif, nouvelle_partie
from rapide import (ATTAQUER, DEFENDRE, PASSER, PRENDRE, TRANSFERER, SolveurRapide, convertir,
                    coups, indice, jouer, masque)
from solveur import BudgetDepasse, Solveur, copier
from test_solveur import fin_de_partie_test

TYPES = {TypeAction.ATTAQUER: ATTAQUER, TypeAction.DEFENDRE: DEFENDRE,
         TypeAction.TRANSFERER: TRANSFERER, TypeAction.PRENDRE: PRENDRE, TypeAction.PASSER: PASSER}


def traduire(action) -> tuple:
    cible = 1 << indice(action.cible) if action.cible is not None else 0
    return (TYPES[action.type_action], masque(action.cartes_jouees), cible)


def etats_de_parties(n_parties, fabrique):
    """Tous les états rencontrés pendant des parties (copies indépendantes)."""
    for seed in range(n_parties):
        etat = nouvelle_partie(seed)
        joueurs = fabrique(seed)
        for _ in range(2_000):   # garde-fou : les règles permettent des boucles infinies
            if fin_de_partie(etat)[0]:
                break
            yield copier(etat)
            actif = joueur_actif(etat)
            appliquer(etat, joueurs[actif].choisir(etat, actif, actions_legales(etat)))


FABRIQUES = [
    lambda s: [JoueurAleatoire(s), JoueurAleatoire(s + 1)],
    lambda s: [JoueurPetit(**REGLAGES_RECHERCHE), JoueurPetit()],
]


def test_indices_distincts():
    from cartes import nouveau_paquet
    assert sorted(indice(c) for c in nouveau_paquet()) == list(range(36))


def test_memes_coups_et_memes_effets():
    """À chaque état de 300 parties : mêmes coups légaux, même joueur actif,
    et chaque coup mène au même état (ou au même gagnant) dans les deux moteurs."""
    for fabrique in FABRIQUES:
        for etat in etats_de_parties(150, fabrique):
            rapide = convertir(etat)
            a = etat.atout.value - 1
            actif, liste = coups(rapide, a)
            actions = actions_legales(etat)
            assert actif == joueur_actif(etat)
            assert sorted(liste) == sorted(traduire(x) for x in actions)
            assert len(liste) == len(actions)   # aucun coup en double
            for action in actions:
                lent = copier(etat)
                appliquer(lent, action)
                suivant, gagnant = jouer(rapide, traduire(action))
                terminee, classement = fin_de_partie(lent)
                if terminee:
                    assert gagnant == classement[0]
                else:
                    assert gagnant == -1
                    assert suivant == convertir(lent)


def test_memes_valeurs_que_le_solveur_lent():
    """Sur des petites fins de partie réelles, les deux solveurs donnent la même valeur."""
    compares = 0
    for etat in etats_de_parties(300, FABRIQUES[1]):
        if etat.pioche or sum(len(m) for m in etat.mains) > 8:
            continue
        try:
            lent = Solveur(0, 200_000).evaluer(etat)
        except BudgetDepasse:
            continue
        assert SolveurRapide(0, 10**7).evaluer(etat) == lent
        compares += 1
    assert compares > 50


def test_cas_construits():
    pique = Couleur.PIQUE
    etat = fin_de_partie_test([Carte(14, pique)], [Carte(6, Couleur.COEUR), Carte(7, Couleur.COEUR)])
    assert SolveurRapide(0, 10_000).evaluer(etat) == 1
    etat = fin_de_partie_test([Carte(6, Couleur.COEUR), Carte(7, Couleur.TREFLE)], [Carte(14, pique)])
    assert SolveurRapide(0, 10_000).evaluer(etat) == -1


def test_parties_completes_sans_erreur():
    resultats = match([JoueurFinal(**REGLAGES_RECHERCHE), JoueurPetit(**REGLAGES_RECHERCHE)], 20)
    assert resultats[0].parties == 40

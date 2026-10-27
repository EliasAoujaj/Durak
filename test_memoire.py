import random

import pytest

from cartes import Carte, Couleur
from joueurs import JoueurAleatoire, JoueurCompteur, JoueurPetit, REGLAGES_RECHERCHE
from memoire import Memoire
from moteur import (Action, TypeAction, actions_legales, appliquer, fin_de_partie,
                    joueur_actif, nouvelle_partie)


def parties_suivies(n_parties, joueurs_fabrique):
    """Joue des parties en tenant la mémoire du joueur 0, et renvoie (etat, memoire) à chaque coup."""
    for seed in range(n_parties):
        etat = nouvelle_partie(seed)
        joueurs = joueurs_fabrique(seed)
        memoire = Memoire(0, 2)
        for place, j in enumerate(joueurs):
            j.debut_partie(place, 2)
        while not fin_de_partie(etat)[0]:
            yield etat, memoire
            actif = joueur_actif(etat)
            action = joueurs[actif].choisir(etat, actif, actions_legales(etat))
            memoire.mettre_a_jour(etat, actif, action)
            for j in joueurs:
                j.observer(etat, actif, action)
            appliquer(etat, action)


FABRIQUES = [
    lambda s: [JoueurAleatoire(s), JoueurAleatoire(s + 1)],
    lambda s: [JoueurPetit(), JoueurCompteur(**REGLAGES_RECHERCHE)],
]


@pytest.mark.parametrize("fabrique", FABRIQUES)
def test_cartes_connues_toujours_dans_la_main(fabrique):
    for etat, memoire in parties_suivies(200, fabrique):
        assert memoire.connues[1] <= set(etat.mains[1])


@pytest.mark.parametrize("fabrique", FABRIQUES)
def test_inconnues_exactement_main_cachee_et_pioche(fabrique):
    for etat, memoire in parties_suivies(200, fabrique):
        attendu = (set(etat.mains[1]) - memoire.connues[1]) | set(etat.pioche)
        assert memoire.inconnues(etat) == attendu


@pytest.mark.parametrize("fabrique", FABRIQUES)
def test_pioche_vide_main_adverse_connue(fabrique):
    for etat, memoire in parties_suivies(200, fabrique):
        if not etat.pioche:
            assert memoire.inconnues(etat) | memoire.connues[1] == set(etat.mains[1])


def test_prise_puis_rejeu():
    etat = nouvelle_partie(42)
    etat.attaquant = 0
    huit = Carte(8, Couleur.COEUR)
    etat.table = [(huit, None)]
    etat.defenseur_prend = True
    memoire = Memoire(0, 2)
    memoire.mettre_a_jour(etat, 0, Action(TypeAction.PASSER))
    assert memoire.connues[1] == {huit}
    memoire.mettre_a_jour(etat, 1, Action(TypeAction.ATTAQUER, frozenset({huit})))
    assert memoire.connues[1] == set()


def test_proba_imbattable_carte_connue():
    etat = nouvelle_partie(42)
    etat.atout = Couleur.PIQUE
    memoire = Memoire(0, 2)
    memoire.connues[1] = {Carte(10, Couleur.COEUR)}
    assert memoire.proba_imbattable(etat, Carte(8, Couleur.COEUR), 1) == 0.0


def test_proba_imbattable_bornes():
    # un as d'atout est toujours imbattable ; un 6 non-atout presque toujours battable
    etat = nouvelle_partie(42)
    memoire = Memoire(0, 2)
    as_atout = Carte(14, etat.atout)
    assert memoire.proba_imbattable(etat, as_atout, 1) == 1.0
    six = next(Carte(6, c) for c in Couleur if c != etat.atout)
    assert memoire.proba_imbattable(etat, six, 1) < 0.1

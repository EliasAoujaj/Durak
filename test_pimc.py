import random

from arene import match
from cartes import Carte, Couleur
from joueurs import JoueurAleatoire, JoueurPetit, JoueurPimc, REGLAGES_RECHERCHE
from memoire import Memoire
from moteur import actions_legales, appliquer, fin_de_partie, joueur_actif, nouvelle_partie
from solveur import GAGNE, BudgetDepasse, Solveur, cle_position
from test_solveur import fin_de_partie_test


def test_mondes_compatibles_avec_la_realite():
    """À chaque coup de parties aléatoires, un monde tiré doit respecter tout ce qu'on sait."""
    rng = random.Random(0)
    for seed in range(100):
        etat = nouvelle_partie(seed)
        joueurs = [JoueurAleatoire(seed), JoueurAleatoire(seed + 1)]
        memoire = Memoire(0, 2)
        while not fin_de_partie(etat)[0]:
            monde = memoire.tirer_monde(etat, rng)
            # ma main ne change pas
            assert monde.mains[0] == etat.mains[0]
            # la main adverse a la bonne taille et contient les cartes connues
            assert len(monde.mains[1]) == len(etat.mains[1])
            assert memoire.connues[1] <= set(monde.mains[1])
            # les cartes cachées sont redistribuées, ni perdues ni inventées
            assert set(monde.mains[1]) | set(monde.pioche) == set(etat.mains[1]) | set(etat.pioche)
            assert len(monde.pioche) == len(etat.pioche)
            # la carte du dessous reste au dessous
            if etat.pioche:
                assert monde.pioche[0] == etat.pioche[0]
            actif = joueur_actif(etat)
            action = joueurs[actif].choisir(etat, actif, actions_legales(etat))
            memoire.mettre_a_jour(etat, actif, action)
            appliquer(etat, action)


def test_cle_depend_de_la_pioche():
    a = nouvelle_partie(1)
    b = nouvelle_partie(1)
    b.pioche[1], b.pioche[2] = b.pioche[2], b.pioche[1]
    assert cle_position(a) != cle_position(b)


def test_parties_completes_sans_erreur():
    # réglages légers pour que le test reste rapide
    pimc = JoueurPimc(n_mondes=3, pioche_max=2, **REGLAGES_RECHERCHE)
    resultats = match([pimc, JoueurPetit(**REGLAGES_RECHERCHE)], 15)
    assert resultats[0].parties == 30
    assert pimc.pimc_decisions + pimc.pimc_abandons > 0   # le PIMC a bien servi


def test_valeur_hybride_pioche_vide_egale_minimax():
    # pioche vide : pas de simulation, la valeur hybride est la valeur exacte
    etat = fin_de_partie_test([Carte(14, Couleur.PIQUE)], [Carte(6, Couleur.COEUR), Carte(7, Couleur.COEUR)])
    assert Solveur(0, 10_000).valeur_hybride(etat, JoueurPetit()) == GAGNE


def test_valeurs_hybrides_avec_pioche():
    # peu avant la fin de la pioche, chaque coup reçoit une valeur valide
    resolus = 0
    for seed in range(20):
        etat = nouvelle_partie(seed)
        joueur = JoueurPetit()
        while len(etat.pioche) > 2 and not fin_de_partie(etat)[0]:
            actif = joueur_actif(etat)
            appliquer(etat, joueur.choisir(etat, actif, actions_legales(etat)))
        if not etat.pioche or fin_de_partie(etat)[0]:
            continue
        actions = actions_legales(etat)
        try:
            valeurs = Solveur(joueur_actif(etat), 20_000).valeurs_hybrides(etat, actions, joueur)
        except BudgetDepasse:
            continue   # fin de partie trop grosse pour ce test : on passe à la donne suivante
        assert len(valeurs) == len(actions)
        assert all(v in (-1, 0, 1) for v in valeurs)
        resolus += 1
    assert resolus > 0

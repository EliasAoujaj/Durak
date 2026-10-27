from cartes import Carte, Couleur, nouveau_paquet
from joueurs import JoueurFinal, JoueurPetit, REGLAGES_RECHERCHE
from arene import match
from moteur import Action, TypeAction, actions_legales, nouvelle_partie
from solveur import GAGNE, PERDU, Solveur

PIQUE = Couleur.PIQUE


def fin_de_partie_test(main0, main1):
    """Pioche vide, atout pique, joueur 0 attaque ; toutes les autres cartes sont défaussées."""
    etat = nouvelle_partie(0)
    etat.atout = PIQUE
    etat.mains = [list(main0), list(main1)]
    etat.pioche = []
    etat.table = []
    etat.defausse = [c for c in nouveau_paquet() if c not in main0 and c not in main1]
    etat.attaquant = 0
    etat.defenseur_prend = False
    etat.classement = []
    return etat


def test_as_d_atout_gagne():
    # le joueur 0 attaque avec son as d'atout : imbattable, l'adversaire prend, 0 a fini
    etat = fin_de_partie_test([Carte(14, PIQUE)], [Carte(6, Couleur.COEUR), Carte(7, Couleur.COEUR)])
    assert Solveur(0, 10_000).evaluer(etat) == GAGNE
    assert Solveur(1, 10_000).evaluer(etat) == PERDU


def test_defenseur_avec_atout_gagne():
    # quoi que joue le 0, le 1 bat avec son as d'atout et se vide le premier
    etat = fin_de_partie_test([Carte(6, Couleur.COEUR), Carte(7, Couleur.TREFLE)], [Carte(14, PIQUE)])
    assert Solveur(0, 10_000).evaluer(etat) == PERDU


# Attaquer avec 6♥ perd (le 7♥ le bat et le défenseur se vide) ;
# attaquer avec 6♣ gagne (le défenseur doit prendre, puis ne peut plus s'en sortir).
SIX_COEUR, SIX_TREFLE, SEPT_COEUR = Carte(6, Couleur.COEUR), Carte(6, Couleur.TREFLE), Carte(7, Couleur.COEUR)
BON_COUP = Action(TypeAction.ATTAQUER, frozenset({SIX_TREFLE}))


def test_solveur_trouve_le_coup_gagnant():
    etat = fin_de_partie_test([SIX_COEUR, SIX_TREFLE], [SEPT_COEUR])
    assert Solveur(0, 10_000).meilleure_action(etat, actions_legales(etat)) == BON_COUP


def test_joueur_final_trouve_le_coup_gagnant():
    etat = fin_de_partie_test([SIX_COEUR, SIX_TREFLE], [SEPT_COEUR])
    joueur = JoueurFinal()
    joueur.debut_partie(0, 2)
    assert joueur.choisir(etat, 0, actions_legales(etat)) == BON_COUP
    assert joueur.resolus == 1


def test_parties_completes_sans_erreur():
    # l'arène vérifie la légalité de chaque coup, et la mémoire est contrôlée par un assert
    resultats = match([JoueurFinal(**REGLAGES_RECHERCHE), JoueurPetit(**REGLAGES_RECHERCHE)], 30)
    assert resultats[0].parties == 60

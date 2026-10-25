from cartes import Carte, Couleur
from moteur import nouvelle_partie, premier_joueur, TAILLE_MAIN, joueur_actif, defenseur, non_battues, valeurs_sur_table, sous_groupes, par_valeur
import pytest

def test_distribution():
    etat = nouvelle_partie(42)
    assert len(etat.mains[0]) == TAILLE_MAIN
    assert len(etat.mains[1]) == TAILLE_MAIN
    assert len(etat.pioche) == 24

def test_cartes_ttes_differentes():
    etat = nouvelle_partie(42)
    assert len(set(etat.mains[0]) | set(etat.mains[1]) | set(etat.pioche)) == 36

def test_graine():
    assert all(nouvelle_partie(i) == nouvelle_partie(i) for i in range(10))
    assert nouvelle_partie(1) != nouvelle_partie(2)

@pytest.mark.parametrize("mains, attendu", [
    # Les deux ont des atouts, le joueur 1 a le plus petit
    ([[Carte(9, Couleur.PIQUE), Carte(7, Couleur.COEUR)],
      [Carte(6, Couleur.PIQUE), Carte(14, Couleur.COEUR)]], 1),

    # Seul le joueur 1 a un atout (le joueur 0 a un 6, mais pas d'atout)
    ([[Carte(14, Couleur.COEUR), Carte(6, Couleur.TREFLE)],
      [Carte(13, Couleur.PIQUE), Carte(8, Couleur.CARREAU)]], 1),

    # Personne n'a d'atout (le joueur 1 a la plus petite carte, mais ça ne compte pas)
    ([[Carte(10, Couleur.COEUR), Carte(12, Couleur.TREFLE)],
      [Carte(6, Couleur.CARREAU), Carte(7, Couleur.COEUR)]], 0),
])

def test_premier_joueur(mains, attendu):
    assert premier_joueur(mains,Couleur.PIQUE) == attendu

def test_table_vide_attaquant_joue():
    etat = nouvelle_partie(42)
    assert joueur_actif(etat) == etat.attaquant

def test_table_vide_attaquant_joue():
    etat = nouvelle_partie(42)
    assert joueur_actif(etat) == etat.attaquant


def test_attaque_non_battue_defenseur_joue():
    etat = nouvelle_partie(42)
    etat.table = [(Carte(8, Couleur.COEUR), None)]
    assert joueur_actif(etat) == defenseur(etat)


def test_defenseur_prend_attaquant_joue():
    etat = nouvelle_partie(42)
    etat.table = [(Carte(8, Couleur.COEUR), None)]
    etat.defenseur_prend = True
    assert joueur_actif(etat) == etat.attaquant


def test_tout_battu_attaquant_joue():
    etat = nouvelle_partie(42)
    etat.table = [
        (Carte(8, Couleur.COEUR), Carte(10, Couleur.COEUR)),
        (Carte(8, Couleur.TREFLE), Carte(13, Couleur.TREFLE)),
    ]
    assert joueur_actif(etat) == etat.attaquant

def test_une_battue_une_non_battue_defenseur_joue():
    etat = nouvelle_partie(42)
    etat.table = [
        (Carte(8, Couleur.COEUR), Carte(10, Couleur.COEUR)),
        (Carte(8, Couleur.TREFLE), None),
    ]
    assert joueur_actif(etat) == defenseur(etat)

def test_defenseur_est_l_autre_joueur():
    etat = nouvelle_partie(42)
    assert defenseur(etat) != etat.attaquant
    assert defenseur(etat) in (0, 1)

HUIT_COEUR = Carte(8, Couleur.COEUR)
HUIT_TREFLE = Carte(8, Couleur.TREFLE)
DIX_COEUR = Carte(10, Couleur.COEUR)
DAME_PIQUE = Carte(12, Couleur.PIQUE)

def test_non_battues_table_vide():
    etat = nouvelle_partie(42)
    assert non_battues(etat) == []

def test_non_battues_table_mixte():
    etat = nouvelle_partie(42)
    etat.table = [(HUIT_COEUR, DIX_COEUR), (HUIT_TREFLE, None)]
    assert non_battues(etat) == [HUIT_TREFLE]

def test_valeurs_sur_table_vide():
    etat = nouvelle_partie(42)
    assert valeurs_sur_table(etat) == set()

def test_valeurs_sur_table_attaques_et_defenses():
    etat = nouvelle_partie(42)
    etat.table = [(HUIT_COEUR, DIX_COEUR), (HUIT_TREFLE, None)]
    assert valeurs_sur_table(etat) == {8, 10}

def test_sous_groupes_liste_vide():
    assert sous_groupes([]) == []

def test_sous_groupes_deux_cartes():
    resultat = sous_groupes([HUIT_COEUR, HUIT_TREFLE])
    assert set(resultat) == {
        frozenset({HUIT_COEUR}),
        frozenset({HUIT_TREFLE}),
        frozenset({HUIT_COEUR, HUIT_TREFLE}),
    }

def test_sous_groupes_trois_cartes():
    resultat = sous_groupes([HUIT_COEUR, HUIT_TREFLE, DAME_PIQUE])
    assert len(resultat) == 7
    assert len(set(resultat)) == 7          # tous différents
    assert all(len(g) > 0 for g in resultat)  # aucun vide

def test_par_valeur():
    groupes = par_valeur([HUIT_COEUR, DAME_PIQUE, HUIT_TREFLE])
    assert set(groupes.keys()) == {8, 12}
    assert set(groupes[8]) == {HUIT_COEUR, HUIT_TREFLE}
    assert set(groupes[12]) == {DAME_PIQUE}

def test_par_valeur_main_vide():
    assert par_valeur([]) == {}

from moteur import actions_attaquant, Action, TypeAction


def etat_test(main_att, main_def, table, prend=False):
    """Crée un état où le joueur 0 attaque avec les mains et la table données."""
    etat = nouvelle_partie(42)
    etat.attaquant = 0
    etat.mains = [main_att, main_def]
    etat.table = table
    etat.defenseur_prend = prend
    return etat


def main_quelconque(n):
    """Une main de n cartes de carreau, pour le défenseur."""
    return [Carte(v, Couleur.CARREAU) for v in range(6, 6 + n)]


def attaque(*cartes):
    return Action(TypeAction.ATTAQUER, frozenset(cartes))


PASSER = Action(TypeAction.PASSER)
DIX_PIQUE = Carte(10, Couleur.PIQUE)


def test_attaque_initiale():
    etat = etat_test([HUIT_COEUR, HUIT_TREFLE, DAME_PIQUE], main_quelconque(6), [])
    assert set(actions_attaquant(etat)) == {
        attaque(HUIT_COEUR),
        attaque(HUIT_TREFLE),
        attaque(HUIT_COEUR, HUIT_TREFLE),
        attaque(DAME_PIQUE),
    }


def test_attaque_initiale_limitee_par_defenseur():
    etat = etat_test([HUIT_COEUR, HUIT_TREFLE, DAME_PIQUE], main_quelconque(1), [])
    assert set(actions_attaquant(etat)) == {
        attaque(HUIT_COEUR),
        attaque(HUIT_TREFLE),
        attaque(DAME_PIQUE),
    }


def test_ajout_valeurs_attaque_et_defense():
    # 8♥ battu par 10♥ : l'attaquant peut ajouter un 8 ou un 10, pas la dame
    etat = etat_test([HUIT_TREFLE, DIX_PIQUE, DAME_PIQUE], main_quelconque(5),
                     [(HUIT_COEUR, DIX_COEUR)])
    assert set(actions_attaquant(etat)) == {
        PASSER,
        attaque(HUIT_TREFLE),
        attaque(DIX_PIQUE),
    }


def test_table_pleine_seulement_passer():
    table = [(Carte(v, Couleur.COEUR), Carte(v, Couleur.CARREAU)) for v in range(6, 12)]
    etat = etat_test([Carte(7, Couleur.TREFLE)], main_quelconque(6), table)
    assert actions_attaquant(etat) == [PASSER]


def test_apres_prise_limite_atteinte():
    # le défenseur a pris avec 1 carte en main et 1 attaque non battue : plus d'ajout
    etat = etat_test([HUIT_TREFLE], main_quelconque(1), [(HUIT_COEUR, None)], prend=True)
    assert actions_attaquant(etat) == [PASSER]


def test_apres_prise_ajout_possible():
    etat = etat_test([HUIT_TREFLE], main_quelconque(3), [(HUIT_COEUR, None)], prend=True)
    assert set(actions_attaquant(etat)) == {PASSER, attaque(HUIT_TREFLE)}
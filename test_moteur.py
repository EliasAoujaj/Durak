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
    etat.atout = Couleur.PIQUE
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

    

from moteur import actions_defenseur

HUIT_PIQUE = Carte(8, Couleur.PIQUE)
HUIT_CARREAU = Carte(8, Couleur.CARREAU)
SEPT_COEUR = Carte(7, Couleur.COEUR)
SIX_PIQUE = Carte(6, Couleur.PIQUE)
DAME_CARREAU = Carte(12, Couleur.CARREAU)

PRENDRE = Action(TypeAction.PRENDRE)


def defense(carte, cible):
    return Action(TypeAction.DEFENDRE, frozenset({carte}), cible)


def transfert(*cartes):
    return Action(TypeAction.TRANSFERER, frozenset(cartes))


def test_defense_simple():
    # 10♥ bat le 8♥, le 6♠ aussi (atout) ; le 7♥ et la D♦ non
    etat = etat_test(main_quelconque(6), [DIX_COEUR, SEPT_COEUR, SIX_PIQUE, DAME_CARREAU],
                     [(HUIT_COEUR, None)])
    assert set(actions_defenseur(etat)) == {
        PRENDRE,
        defense(DIX_COEUR, HUIT_COEUR),
        defense(SIX_PIQUE, HUIT_COEUR),
    }


def test_transferts_possibles():
    # deux 8 en main : trois transferts ; le 8♠ peut aussi défendre (atout)
    etat = etat_test(main_quelconque(6), [HUIT_TREFLE, HUIT_PIQUE, DAME_CARREAU],
                     [(HUIT_COEUR, None)])
    assert set(actions_defenseur(etat)) == {
        PRENDRE,
        transfert(HUIT_TREFLE),
        transfert(HUIT_PIQUE),
        transfert(HUIT_TREFLE, HUIT_PIQUE),
        defense(HUIT_PIQUE, HUIT_COEUR),
    }


def test_transfert_limite_par_main_attaquant():
    # l'attaquant n'a que 2 cartes : il ne pourra pas défendre 3 attaques
    etat = etat_test(main_quelconque(2), [HUIT_TREFLE, HUIT_PIQUE],
                     [(HUIT_COEUR, None)])
    assert set(actions_defenseur(etat)) == {
        PRENDRE,
        transfert(HUIT_TREFLE),
        transfert(HUIT_PIQUE),
        defense(HUIT_PIQUE, HUIT_COEUR),
    }


def test_pas_de_transfert_si_une_attaque_battue():
    # le 8♣ ne peut ni transférer (une attaque est battue) ni battre le 8♦
    etat = etat_test(main_quelconque(6), [HUIT_TREFLE],
                     [(HUIT_COEUR, DIX_COEUR), (HUIT_CARREAU, None)])
    assert actions_defenseur(etat) == [PRENDRE]


def test_defense_seulement_sur_attaques_non_battues():
    # deux attaques non battues, le 10♥ ne bat que le 8♥
    etat = etat_test(main_quelconque(6), [DIX_COEUR],
                     [(HUIT_COEUR, None), (HUIT_CARREAU, None)])
    assert set(actions_defenseur(etat)) == {
        PRENDRE,
        defense(DIX_COEUR, HUIT_COEUR),
    }

import random
from moteur import actions_legales, appliquer, fin_de_partie


def nombre_total_cartes(etat):
    """Compte toutes les cartes du jeu : mains, pioche, défausse et table."""
    sur_table = sum(1 + (defense is not None) for _, defense in etat.table)
    return (sum(len(main) for main in etat.mains)
            + len(etat.pioche) + len(etat.defausse) + sur_table)


def test_parties_aleatoires():
    for seed in range(1000):
        etat = nouvelle_partie(seed)
        rng = random.Random(seed)
        for _ in range(10_000):
            terminee, classement = fin_de_partie(etat)
            if terminee:
                break
            actions = actions_legales(etat)
            assert actions, f"aucune action possible, graine {seed}"
            appliquer(etat, rng.choice(actions))
            assert nombre_total_cartes(etat) == 36, f"cartes perdues ou dupliquées, graine {seed}"
        else:
            assert False, f"partie trop longue, graine {seed}"
        assert sorted(classement) == [0, 1], f"classement incorrect, graine {seed}"
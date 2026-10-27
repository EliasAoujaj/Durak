from arene import match
from cartes import Carte, Couleur
from joueurs import JoueurPetit, JoueurSage, REGLAGES_RECHERCHE, REGLES_SAGE
from moteur import Action, TypeAction, actions_legales, nouvelle_partie

CARREAU, COEUR, TREFLE = Couleur.CARREAU, Couleur.COEUR, Couleur.TREFLE


def etat_defense():
    """Pioche vide, atout carreau. Le joueur 1 défend face à 7♥ et 7♣, avec 6♦ et D♥ :
    la seule façon de tout battre est D♥ sur 7♥ et 6♦ (atout) sur 7♣."""
    etat = nouvelle_partie(0)
    etat.atout = CARREAU
    etat.attaquant = 0
    etat.pioche = []
    etat.mains = [[Carte(9, Couleur.PIQUE)], [Carte(6, CARREAU), Carte(12, COEUR)]]
    etat.table = [(Carte(7, COEUR), None), (Carte(7, TREFLE), None)]
    etat.defenseur_prend = False
    return etat


def test_plan_trouve_la_seule_solution():
    etat = etat_defense()
    plan = JoueurSage().plan_defense(etat, etat.mains[1], [Carte(7, COEUR), Carte(7, TREFLE)])
    assert sorted(plan, key=str) == sorted([(Carte(7, COEUR), Carte(12, COEUR)),
                                            (Carte(7, TREFLE), Carte(6, CARREAU))], key=str)


def test_glouton_valide():
    # ici, comme l'atout coûte cher (26), le glouton garde lui aussi le 6♦ pour le 7♣
    etat = etat_defense()
    plan = JoueurSage().plan_glouton(etat, etat.mains[1], [Carte(7, COEUR), Carte(7, TREFLE)])
    assert plan == [(Carte(7, COEUR), Carte(12, COEUR)), (Carte(7, TREFLE), Carte(6, CARREAU))]


def test_defense_suit_le_plan():
    etat = etat_defense()
    action = JoueurSage().choisir(etat, 1, actions_legales(etat))
    assert action in (Action(TypeAction.DEFENDRE, frozenset({Carte(12, COEUR)}), Carte(7, COEUR)),
                      Action(TypeAction.DEFENDRE, frozenset({Carte(6, CARREAU)}), Carte(7, TREFLE)))


def test_toutes_les_variantes_jouent_sans_erreur():
    for sans in [()] + [(r,) for r in REGLES_SAGE]:
        resultats = match([JoueurSage(sans=sans), JoueurPetit(**REGLAGES_RECHERCHE)], 10)
        assert resultats[0].parties == 20


def test_ameliore_sans_regle_identique_a_petit_regle():
    # sans aucune règle, JoueurAmeliore doit jouer exactement comme JoueurPetit réglé
    from joueurs import JoueurAmeliore
    from moteur import appliquer, fin_de_partie, joueur_actif
    for seed in range(50):
        etat = nouvelle_partie(seed)
        a, p = JoueurAmeliore(), JoueurPetit(**REGLAGES_RECHERCHE)
        for _ in range(2000):
            if fin_de_partie(etat)[0]:
                break
            actif = joueur_actif(etat)
            actions = actions_legales(etat)
            choix = a.choisir(etat, actif, actions)
            assert choix == p.choisir(etat, actif, actions)
            appliquer(etat, choix)


def test_ameliore_toutes_regles_sans_erreur():
    from joueurs import JoueurAmeliore, REGLES_AMELIORATION
    for avec in [REGLES_AMELIORATION] + [(r,) for r in REGLES_AMELIORATION]:
        resultats = match([JoueurAmeliore(avec=avec), JoueurPetit(**REGLAGES_RECHERCHE)], 10)
        assert resultats[0].parties == 20

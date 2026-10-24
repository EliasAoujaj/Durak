from cartes import Carte, Couleur
from moteur import nouvelle_partie, premier_joueur, TAILLE_MAIN
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

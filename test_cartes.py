from cartes import Carte, Couleur, bat
import pytest

@pytest.mark.parametrize("attaque,defense,attendu", [
        (Carte(7, Couleur.COEUR), Carte(10, Couleur.COEUR), True),     # plus forte, même couleur
    (Carte(10, Couleur.COEUR), Carte(7, Couleur.COEUR), False),    # plus faible, même couleur
    (Carte(9, Couleur.COEUR), Carte(9, Couleur.COEUR), False),     # même carte
    (Carte(14, Couleur.COEUR), Carte(6, Couleur.PIQUE), True),     # petit atout contre as
    (Carte(6, Couleur.PIQUE), Carte(14, Couleur.COEUR), False),    # non-atout contre atout
    (Carte(9, Couleur.PIQUE), Carte(13, Couleur.PIQUE), True),     # atout fort contre atout faible
    (Carte(7, Couleur.COEUR), Carte(14, Couleur.CARREAU), False),  # couleurs différentes, sans atout
])

def test_bat(attaque, defense, attendu):
    assert bat(attaque, defense, Couleur.PIQUE) == attendu

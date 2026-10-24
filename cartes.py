from enum import Enum
from dataclasses import dataclass

class Couleur(Enum):
    TREFLE = 1
    CARREAU = 2
    COEUR = 3
    PIQUE = 4

VALEURS = range(6, 15) # 6, 7, 8, 9, 10, Valet, Dame, Roi, As
COULEURS = {Couleur.TREFLE: "♣", Couleur.CARREAU: "♦", Couleur.COEUR: "♥", Couleur.PIQUE: "♠"}
NOMS_FIGURES = {11: "V", 12: "D", 13: "R", 14: "A"}

@dataclass(frozen=True)
class Carte:
    valeur: int
    couleur: Couleur

    def __str__(self):
        if self.valeur >= 11:
            return f"{NOMS_FIGURES[self.valeur]}{COULEURS[self.couleur]}"
        else:
            return f"{self.valeur}{COULEURS[self.couleur]}"


c = Carte(8, Couleur.TREFLE)

print(c == Carte(8, Couleur.TREFLE))
print(Carte(8, Couleur.TREFLE))
print(Carte(12, Couleur.COEUR))
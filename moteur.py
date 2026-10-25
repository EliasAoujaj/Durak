import random
from enum import Enum

from dataclasses import dataclass
from cartes import Carte, Couleur, nouveau_paquet

TAILLE_MAIN = 6
MAX_ATTAQUES = 6
NB_JOUEUR = 2

@dataclass
class EtatPartie:
    mains: list[list[Carte]]
    pioche: list[Carte]
    atout: Couleur
    table: list[tuple[Carte, Carte | None]]
    defausse: list[Carte]
    attaquant: int
    defenseur_prend: bool

def premier_joueur(mains, atout):
    plus_petit = [15 for _ in range(NB_JOUEUR)] # 15 > as : signifie "pas d'atout"
    for joueur in range(NB_JOUEUR):
        for carte in mains[joueur]:
            if carte.couleur == atout and carte.valeur < plus_petit[joueur]:
                plus_petit[joueur] = carte.valeur
    meilleur = 0
    for pp in range(NB_JOUEUR):
        if plus_petit[pp] < plus_petit[meilleur]:
            meilleur = pp
    return meilleur

def nouvelle_partie(seed: int) -> EtatPartie:
    pioche = nouveau_paquet()
    rng = random.Random(seed)
    rng.shuffle(pioche)
    mains = [[] for _ in range(NB_JOUEUR)]
    for i in range(NB_JOUEUR * TAILLE_MAIN):
        mains[i % NB_JOUEUR].append(pioche.pop())
    return EtatPartie(
        mains=mains,
        pioche=pioche,
        atout=pioche[0].couleur,
        table=[],
        defausse=[],
        attaquant=premier_joueur(mains, pioche[0].couleur),
        defenseur_prend=False
    )

class TypeAction(Enum):
    ATTAQUER = 1
    DEFENDRE = 2
    TRANSFERER = 3
    PRENDRE = 4
    PASSER = 5

@dataclass(frozen=True)
class Action:
    type_action: TypeAction
    cartes_jouees: frozenset[Carte] = frozenset()
    cible: Carte | None = None

def joueur_actif(etat: EtatPartie) -> int:
    carte_non_def = any(defense is None for _, defense in etat.table)
    if carte_non_def and not etat.defenseur_prend:
        return defenseur(etat)
    else:
        return etat.attaquant

def defenseur(etat: EtatPartie) -> int:
    return (etat.attaquant + 1) % NB_JOUEUR

def non_battues(etat) -> list[Carte]:
    return [attaque for attaque, defense in etat.table if defense is None]

def valeurs_sur_table(etat) -> set[int]:
    return {attaque.valeur for attaque, _ in etat.table} | {defense.valeur for _, defense in etat.table if defense is not None}

def sous_groupes(cartes: list[Carte]) -> list[frozenset[Carte]]:
    liste = []
    for i in range(1, 2 ** len(cartes)):
        ensemble = set()
        for j in range(len(cartes)):
            if (i >> j) & 1: # >> decale i de j bits vers la droite, & 1 garde le dernier bit, on teste donc si le jieme bit vaut 1
                ensemble.add(cartes[j])
        liste.append(frozenset(ensemble))
    return liste

def par_valeur(main: list[Carte]) -> dict[int, list[Carte]]:
    groupes = {}
    for carte in main:
        groupes.setdefault(carte.valeur, []).append(carte)
    return groupes

def actions_attaquant(etat: EtatPartie) -> list[Action]:
    liste_attaques = []
    n_def = len(etat.mains[defenseur(etat)]) # nombre de cartes possedees par le defenseur, limite de nombre de cartes d'attaque
    if not etat.table:
        for groupes_cartes in par_valeur(etat.mains[etat.attaquant]).values():
            liste_attaques += [Action(
                type_action=TypeAction.ATTAQUER,
                cartes_jouees=ss_gr
            ) for ss_gr in sous_groupes(groupes_cartes) if len(ss_gr) <= n_def] 
    else:
        liste_attaques.append(Action(
            type_action=TypeAction.PASSER
        ))
        if len(etat.table) < MAX_ATTAQUES and len(non_battues(etat)) < n_def:
            valeurs = valeurs_sur_table(etat)
            liste_attaques += [Action(
                type_action=TypeAction.ATTAQUER,
                cartes_jouees=frozenset({carte})
            ) for carte in etat.mains[etat.attaquant] if carte.valeur in valeurs]
    return liste_attaques


if __name__ == "__main__":
    etat = nouvelle_partie(42)
    print("Atout :", etat.atout, "- carte du dessous :", etat.pioche[0])
    print("Joueur 0 :", *etat.mains[0])
    print("Joueur 1 :", *etat.mains[1])
    print("Premier attaquant :", etat.attaquant)


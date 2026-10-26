"""Affichage d'une partie de durak dans le terminal, et mode où l'on joue soi-même."""

import random

from cartes import Carte
from moteur import (
    Action,
    EtatPartie,
    TypeAction,
    actions_legales,
    appliquer,
    defenseur,
    fin_de_partie,
    joueur_actif,
    nouvelle_partie,
)


def texte_cartes(cartes) -> str:
    """Les cartes triées par couleur puis par valeur, séparées par des espaces."""
    triees = sorted(cartes, key=lambda c: (c.couleur.value, c.valeur))
    return " ".join(str(c) for c in triees)


def afficher(etat: EtatPartie, cache: int | None = None) -> None:
    """Affiche l'état de la partie. Si `cache` est un numéro de joueur, sa main est masquée."""
    if etat.pioche:
        dessous = f"carte du dessous : {etat.pioche[0]}"
    else:
        dessous = "pioche vide"
    print(f"Atout : {etat.atout.name.lower()} ({dessous})   "
          f"Pioche : {len(etat.pioche)}   Défausse : {len(etat.defausse)}")

    for joueur, main in enumerate(etat.mains):
        if joueur == etat.attaquant:
            role = "attaquant"
        elif joueur == defenseur(etat):
            role = "défenseur"
        else:
            role = ""
        if joueur == cache:
            contenu = f"{len(main)} cartes cachées"
        else:
            contenu = texte_cartes(main) or "(vide)"
        print(f"Joueur {joueur} ({role}) : {contenu}")

    if etat.table:
        paires = [f"{attaque}/{defense if defense else '—'}" for attaque, defense in etat.table]
        prise = "   (le défenseur prend)" if etat.defenseur_prend else ""
        print("Table : " + "  ".join(paires) + prise)


def decrire(action: Action, joueur: int) -> str:
    """Une phrase qui décrit l'action jouée par `joueur`."""
    cartes = texte_cartes(action.cartes_jouees)
    if action.type_action == TypeAction.ATTAQUER:
        return f"Joueur {joueur} attaque avec {cartes}"
    if action.type_action == TypeAction.DEFENDRE:
        return f"Joueur {joueur} bat {action.cible} avec {cartes}"
    if action.type_action == TypeAction.TRANSFERER:
        return f"Joueur {joueur} transfère avec {cartes}"
    if action.type_action == TypeAction.PRENDRE:
        return f"Joueur {joueur} prend"
    return f"Joueur {joueur} passe"


def texte_action(action: Action) -> str:
    """Version courte de l'action, pour le menu du joueur humain."""
    cartes = texte_cartes(action.cartes_jouees)
    if action.type_action == TypeAction.ATTAQUER:
        return f"Attaquer avec {cartes}"
    if action.type_action == TypeAction.DEFENDRE:
        return f"Battre {action.cible} avec {cartes}"
    if action.type_action == TypeAction.TRANSFERER:
        return f"Transférer avec {cartes}"
    if action.type_action == TypeAction.PRENDRE:
        return "Prendre"
    return "Passer"


def cle_tri(action: Action):
    """Ordre d'affichage stable des actions : par type, puis par cartes."""
    cartes = sorted((c.valeur, c.couleur.value) for c in action.cartes_jouees)
    return (action.type_action.value, cartes)


def demander_choix(n: int) -> int:
    """Demande un numéro entre 1 et n, et renvoie l'indice correspondant (0 à n - 1)."""
    while True:
        reponse = input("Ton choix : ")
        try:
            choix = int(reponse)
        except ValueError:
            print("Tape un numéro.")
            continue
        if 1 <= choix <= n:
            return choix - 1
        print(f"Choisis un numéro entre 1 et {n}.")


def annoncer_resultat(classement: list[int]) -> None:
    print(f"\nFin de la partie : le joueur {classement[0]} gagne, "
          f"le joueur {classement[-1]} est le durak.")


def partie_commentee(seed: int) -> None:
    """Joue une partie entre deux joueurs aléatoires en racontant chaque coup."""
    etat = nouvelle_partie(seed)
    rng = random.Random(seed)
    print(f"=== Partie {seed} ===")
    afficher(etat)
    while True:
        terminee, classement = fin_de_partie(etat)
        if terminee:
            annoncer_resultat(classement)
            return
        joueur = joueur_actif(etat)
        action = rng.choice(actions_legales(etat))
        print(decrire(action, joueur))
        appliquer(etat, action)
        if action.type_action == TypeAction.PASSER:
            print("--- Fin de l'attaque ---")
            afficher(etat)


def jouer(seed: int, humain: int = 0) -> None:
    """Partie où le joueur `humain` est contrôlé au clavier, contre un adversaire aléatoire."""
    etat = nouvelle_partie(seed)
    rng = random.Random(seed)
    adversaire = 1 - humain
    print(f"=== Partie {seed} : tu es le joueur {humain} ===")
    while True:
        terminee, classement = fin_de_partie(etat)
        if terminee:
            afficher(etat)
            annoncer_resultat(classement)
            return
        joueur = joueur_actif(etat)
        actions = actions_legales(etat)
        if joueur == humain:
            print()
            afficher(etat, cache=adversaire)
            actions = sorted(actions, key=cle_tri)
            print("Tes actions possibles :")
            for i, action in enumerate(actions, start=1):
                print(f"  {i}. {texte_action(action)}")
            action = actions[demander_choix(len(actions))]
        else:
            action = rng.choice(actions)
            print(decrire(action, joueur))
        appliquer(etat, action)


if __name__ == "__main__":
    graine = random.randrange(1_000_000)
    mode = input("1 : regarder une partie aléatoire   2 : jouer contre l'ordinateur\nMode : ")
    if mode.strip() == "1":
        partie_commentee(graine)
    else:
        jouer(graine)

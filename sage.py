"""Les leçons de l'analyse valent-elles quelque chose ? On mesure JoueurSage,
puis l'apport de chacune de ses règles en la désactivant (« ablation »)."""

import time

from arene import afficher, demi_intervalle, match, nouvel_executeur
from joueurs import (JoueurCompteur, JoueurFinal, JoueurPetit, JoueurSage, REGLAGES_RECHERCHE,
                     REGLES_SAGE)

N_DONNES = 5000   # 10 000 parties par match : précision d'environ ± 1 %


if __name__ == "__main__":
    with nouvel_executeur() as executeur:
        debut = time.perf_counter()

        print("1. JoueurSage contre les autres joueurs\n")
        for adversaire in [JoueurPetit(), JoueurPetit(**REGLAGES_RECHERCHE),
                           JoueurCompteur(**REGLAGES_RECHERCHE), JoueurFinal(**REGLAGES_RECHERCHE)]:
            afficher(match([JoueurSage(), adversaire], N_DONNES, executeur=executeur))
            print()

        print("2. Ablation : JoueurSage privé d'une règle, contre JoueurPetit réglé")
        print("   (si le taux baisse quand on retire une règle, c'est qu'elle est utile)\n")
        complet = match([JoueurSage(), JoueurPetit(**REGLAGES_RECHERCHE)], N_DONNES,
                        executeur=executeur)[0].taux_victoire
        print(f"   {'toutes les règles':<22} {complet:6.1%}")
        for regle in REGLES_SAGE:
            res = match([JoueurSage(sans=(regle,)), JoueurPetit(**REGLAGES_RECHERCHE)], N_DONNES,
                        executeur=executeur)[0]
            ecart = res.taux_victoire - complet
            print(f"   sans {regle:<17} {res.taux_victoire:6.1%}   (écart {ecart:+.1%}, "
                  f"marge ± {demi_intervalle(res.taux_victoire, res.parties):.1%})")

        print(f"\nDurée totale : {time.perf_counter() - debut:.0f} s")

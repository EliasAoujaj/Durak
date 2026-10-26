import copy
import os
import random
import time

from moteur import actions_legales, appliquer, fin_de_partie, nouvelle_partie


def partie_aleatoire(seed):
    etat = nouvelle_partie(seed)
    rng = random.Random(seed)
    while not fin_de_partie(etat)[0]:
        appliquer(etat, rng.choice(actions_legales(etat)))


if __name__ == "__main__":
    debut = time.perf_counter()
    for seed in range(2000):
        partie_aleatoire(seed)
    duree = time.perf_counter() - debut
    print(f"Parties aléatoires : {2000 / duree:.0f} par seconde")

    etat = nouvelle_partie(1)
    debut = time.perf_counter()
    for _ in range(20_000):
        copy.deepcopy(etat)
    duree = time.perf_counter() - debut
    print(f"Copies d'état : {20_000 / duree:.0f} par seconde")

    print(f"Nombre de cœurs : {os.cpu_count()}")
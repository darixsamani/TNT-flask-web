"""
TP Traitement Numérique du Signal
Partie A : Analyse du signal
"""

import numpy as np
import matplotlib.pyplot as plt

# ---------------------------------------------------------
# 1. Définition du signal discret x[n]
# ---------------------------------------------------------
x = np.array([12, 15, 18, 22, 30, 28, 35, 40, 38, 45, 50, 48, 55, 60])
n = np.arange(len(x))  # indices n = 0, 1, 2, ..., 13

# ---------------------------------------------------------
# 2. Représentation du signal x[n]
# ---------------------------------------------------------
plt.figure(figsize=(9, 5))
plt.stem(n, x, basefmt=" ")
plt.plot(n, x, linestyle="--", alpha=0.5)
plt.title("Représentation du signal discret x[n]")
plt.xlabel("n (échantillons)")
plt.ylabel("Amplitude x[n]")
plt.grid(True, alpha=0.3)
plt.xticks(n)
plt.tight_layout()
plt.savefig("signal_xn.png", dpi=150)
plt.show()

# ---------------------------------------------------------
# 3. Calcul des grandeurs statistiques
# ---------------------------------------------------------
moyenne = np.mean(x)
variance = np.var(x)          # variance population (biaisée), diviseur N
variance_ech = np.var(x, ddof=1)  # variance d'échantillon, diviseur N-1
ecart_type = np.std(x)
amplitude_max = np.max(x)
amplitude_min = np.min(x)

print("=" * 50)
print("Résultats de l'analyse statistique de x[n]")
print("=" * 50)
print(f"Nombre d'échantillons (N)      : {len(x)}")
print(f"Moyenne                        : {moyenne:.3f}")
print(f"Variance (biaisée, /N)         : {variance:.3f}")
print(f"Variance (échantillon, /N-1)   : {variance_ech:.3f}")
print(f"Écart-type                     : {ecart_type:.3f}")
print(f"Amplitude maximale              : {amplitude_max}")
print(f"Amplitude minimale              : {amplitude_min}")
print(f"Étendue (max - min)             : {amplitude_max - amplitude_min}")

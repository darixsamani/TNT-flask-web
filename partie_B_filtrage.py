"""
TP Traitement Numérique du Signal
Partie B : Filtrage numérique
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ---------------------------------------------------------
# Signal d'entrée x[n]
# ---------------------------------------------------------
x = np.array([12, 15, 18, 22, 30, 28, 35, 40, 38, 45, 50, 48, 55, 60])
n = np.arange(len(x))
N = len(x)

# ===========================================================
# 1) FILTRE FIR - MOYENNE GLISSANTE (ordre 4)
#    y[n] = 1/4 * sum_{k=0}^{3} x[n-k]
#    Convention : x[n] = 0 pour n < 0 (signal causal, padding à gauche)
# ===========================================================
x_pad = np.concatenate((np.zeros(3), x))  # 3 zéros ajoutés avant x[0]

y_fir = np.zeros(N)
for i in range(N):
    # x_pad[i:i+4] correspond à x[n-3..n] -> on les additionne puis /4
    y_fir[i] = np.mean(x_pad[i:i + 4])

# Vérification équivalente avec un produit de convolution (même résultat)
h_fir = np.ones(4) / 4
y_fir_conv = np.convolve(x, h_fir, mode="full")[:N]
assert np.allclose(y_fir, y_fir_conv), "Les deux méthodes doivent être identiques"

# ===========================================================
# 2) FILTRE PASSE-HAUT (différence première)
#    y[n] = x[n] - x[n-1]
#    Convention : x[-1] = 0
# ===========================================================
x_pad_hp = np.concatenate(([0], x))
y_hp = x_pad_hp[1:] - x_pad_hp[:-1]

# ===========================================================
# Tableau récapitulatif (pandas)
# ===========================================================
df = pd.DataFrame({
    "n": n,
    "x[n]": x,
    "y_FIR[n] (moy. glissante)": np.round(y_fir, 3),
    "y_HP[n] (passe-haut)": y_hp
})

print("=" * 65)
print("Tableau complet des signaux filtrés")
print("=" * 65)
print(df.to_string(index=False))

print("\n" + "=" * 65)
print("5 premières valeurs filtrées (filtre FIR moyenne glissante)")
print("=" * 65)
for i in range(5):
    print(f"y[{i}] = {y_fir[i]:.3f}")

# ---------------------------------------------------------
# Sauvegarde du tableau en CSV
# ---------------------------------------------------------
df.to_csv("partie_B_resultats.csv", index=False)

# ===========================================================
# Visualisation
# ===========================================================
fig, axes = plt.subplots(3, 1, figsize=(10, 11), sharex=True)

# --- Signal original ---
axes[0].stem(n, x, basefmt=" ", linefmt="C0-", markerfmt="C0o")
axes[0].plot(n, x, "C0--", alpha=0.4)
axes[0].set_title("Signal original x[n]")
axes[0].set_ylabel("Amplitude")
axes[0].grid(True, alpha=0.3)

# --- Signal filtré FIR ---
axes[1].stem(n, y_fir, basefmt=" ", linefmt="C2-", markerfmt="C2o")
axes[1].plot(n, y_fir, "C2--", alpha=0.4)
axes[1].set_title("Signal filtré - FIR moyenne glissante (ordre 4)")
axes[1].set_ylabel("Amplitude")
axes[1].grid(True, alpha=0.3)

# --- Signal filtré passe-haut ---
axes[2].stem(n, y_hp, basefmt=" ", linefmt="C3-", markerfmt="C3o")
axes[2].plot(n, y_hp, "C3--", alpha=0.4)
axes[2].axhline(0, color="black", linewidth=0.8)
axes[2].set_title("Signal filtré - Passe-haut (différence première)")
axes[2].set_xlabel("n (échantillons)")
axes[2].set_ylabel("Amplitude")
axes[2].grid(True, alpha=0.3)

plt.xticks(n)
plt.tight_layout()
plt.savefig("partie_B_filtrage.png", dpi=150)
plt.show()

# ===========================================================
# Comparaison superposée x[n] vs y_FIR[n]
# ===========================================================
plt.figure(figsize=(10, 5))
plt.plot(n, x, "o-", label="x[n] (original, bruité)", alpha=0.7)
plt.plot(n, y_fir, "s-", label="y[n] (FIR moyenne glissante)", linewidth=2)
plt.title("Effet du filtre FIR moyenne glissante sur le bruit")
plt.xlabel("n")
plt.ylabel("Amplitude")
plt.legend()
plt.grid(True, alpha=0.3)
plt.xticks(n)
plt.tight_layout()
plt.savefig("partie_B_comparaison_fir.png", dpi=150)
plt.show()

# ---------------------------------------------------------
# Indicateurs quantitatifs de l'effet du lissage
# ---------------------------------------------------------
variation_originale = np.sum(np.abs(np.diff(x)))
variation_filtree = np.sum(np.abs(np.diff(y_fir)))
reduction_pct = (1 - variation_filtree / variation_originale) * 100

print("\n" + "=" * 65)
print("Effet du filtre FIR sur la variabilité du signal")
print("=" * 65)
print(f"Somme des variations absolues (x[n])    : {variation_originale}")
print(f"Somme des variations absolues (y_FIR[n]): {variation_filtree:.3f}")
print(f"Réduction de variabilité                : {reduction_pct:.1f} %")

print("\n" + "=" * 65)
print("Amplitude des variations mises en évidence par le passe-haut")
print("=" * 65)
print(f"Variation max détectée (|y_HP|)  : {np.max(np.abs(y_hp))}")
print(f"Indices des plus fortes variations: {n[np.argsort(np.abs(y_hp))[::-1][:3]]}")

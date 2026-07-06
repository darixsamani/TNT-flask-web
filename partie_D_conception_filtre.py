"""
TP Traitement Numérique du Signal
Partie D : Conception d'un filtre numérique
H(z) = 0.5 + 0.5 z^-1
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
# Filtre H(z) = 0.5 + 0.5 z^-1
# -> équation temporelle : y[n] = 0.5 x[n] + 0.5 x[n-1]
# Convention causale : x[-1] = 0
# ===========================================================
x_pad = np.concatenate(([0], x))
y = 0.5 * x_pad[1:] + 0.5 * x_pad[:-1]

# Vérification par convolution avec la réponse impulsionnelle h = [0.5, 0.5]
h = np.array([0.5, 0.5])
y_conv = np.convolve(x, h, mode="full")[:N]
assert np.allclose(y, y_conv)

# ===========================================================
# Tableau récapitulatif
# ===========================================================
df = pd.DataFrame({
    "n": n,
    "x[n]": x,
    "y[n] = 0.5x[n]+0.5x[n-1]": np.round(y, 3)
})
print(df.to_string(index=False))
df.to_csv("partie_D_resultats.csv", index=False)

# ===========================================================
# Réponse en fréquence (module) de H(z)
# H(e^jw) = 0.5 + 0.5 e^-jw
# ===========================================================
w = np.linspace(0, np.pi, 512)
H = 0.5 + 0.5 * np.exp(-1j * w)
H_mag = np.abs(H)

# ===========================================================
# Visualisation
# ===========================================================
fig, axes = plt.subplots(3, 1, figsize=(10, 11))

axes[0].stem(n, x, basefmt=" ", linefmt="C0-", markerfmt="C0o")
axes[0].plot(n, x, "C0--", alpha=0.4)
axes[0].set_title("Signal original x[n]")
axes[0].set_ylabel("Amplitude")
axes[0].grid(True, alpha=0.3)

axes[1].stem(n, y, basefmt=" ", linefmt="C2-", markerfmt="C2o")
axes[1].plot(n, y, "C2--", alpha=0.4)
axes[1].set_title("Signal filtré y[n] par H(z) = 0.5 + 0.5 z⁻¹")
axes[1].set_xlabel("n")
axes[1].set_ylabel("Amplitude")
axes[1].grid(True, alpha=0.3)

axes[2].plot(w / np.pi, H_mag, color="C3")
axes[2].set_title("Réponse en fréquence |H(e^jω)| du filtre")
axes[2].set_xlabel("Fréquence normalisée (× π rad/éch.)")
axes[2].set_ylabel("|H(e^jω)|")
axes[2].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig("partie_D_filtre.png", dpi=150)
plt.show()

# ---------------------------------------------------------
# Indicateur quantitatif de l'effet du filtre
# ---------------------------------------------------------
variation_x = np.sum(np.abs(np.diff(x)))
variation_y = np.sum(np.abs(np.diff(y)))
reduction_pct = (1 - variation_y / variation_x) * 100

print(f"\nVariation totale x[n] : {variation_x}")
print(f"Variation totale y[n] : {variation_y:.3f}")
print(f"Réduction de variabilité : {reduction_pct:.1f} %")
print(f"\nGain à f=0 (DC)  |H(0)|   = {np.abs(0.5+0.5):.3f}")
print(f"Gain à f=Nyquist |H(π)|  = {np.abs(0.5-0.5):.3f}")

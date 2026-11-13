"""
Étape 1 : capteur, repliement et filtre anti-repliement sur un signal réel CWRU.
Lancer : python etape1_capteur_repliement.py   (résultats dans resultats/)
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from chaine import (charger_cwru, capteur, filtre_anti_repliement, reponse_filtre,
                    echantillonner, spectre, BPFO)

os.makedirs("resultats", exist_ok=True)

# ---------------------------------------------------------------------------
# 1. La « réalité » : vibration réelle d'un roulement avec défaut de bague extérieure
#    + une vibration d'engrenage simulée à 1 700 Hz (ajoutée pour la démonstration)
# ---------------------------------------------------------------------------
acc, fe_reel = charger_cwru("OR007_0.mat")          # g, 12 000 Hz
t = np.arange(len(acc)) / fe_reel
F_ENGRENAGE = 1700.0                                 # Hz
acc = acc + 0.5 * np.sin(2 * np.pi * F_ENGRENAGE * t)

SENSIBILITE = 0.100                                  # V/g
v = capteur(acc, fe_reel, sensibilite=SENSIBILITE)   # tension en sortie du capteur

# ---------------------------------------------------------------------------
# 2. Réglage de la chaîne : on veut mesurer jusqu'à FMAX
# ---------------------------------------------------------------------------
FE = 2000.0                                          # fréquence d'échantillonnage de la carte (Hz)
FMAX = FE / 2.56                                     # fréquence maximale fiable : 781 Hz
NYQUIST = FE / 2                                     # 1 000 Hz
F_FAUSSE = FE - F_ENGRENAGE                          # où l'engrenage va se replier : 300 Hz

# Cas A : sans filtre -> on échantillonne directement
vA, _ = echantillonner(v, fe_reel, FE)
# Cas B : filtre anti-repliement (Butterworth ordre 8, coupure FMAX) AVANT l'échantillonnage
vB, _ = echantillonner(filtre_anti_repliement(v, fe_reel, FMAX, ordre=8), fe_reel, FE)

f_ref, X_ref = spectre(v / SENSIBILITE, fe_reel)     # référence (on remet en g)
fA, XA = spectre(vA / SENSIBILITE, FE)
fB, XB = spectre(vB / SENSIBILITE, FE)

def pic(f, X, f0, demi_largeur=3):
    m = (f > f0 - demi_largeur) & (f < f0 + demi_largeur)
    return X[m].max()

print("RÉGLAGE  : fe = %.0f Hz, fmax = fe/2,56 = %.0f Hz, Nyquist = %.0f Hz" % (FE, FMAX, NYQUIST))
print("ENGRENAGE: %.0f Hz > Nyquist -> se replie à fe - f = %.0f Hz" % (F_ENGRENAGE, F_FAUSSE))
print("Amplitude vue à %.0f Hz (fréquence qui n'existe pas en réalité) :" % F_FAUSSE)
print("   référence (réalité)     : %.4f g" % pic(f_ref, X_ref, F_FAUSSE))
print("   A - sans filtre         : %.4f g   <- FAUX PIC" % pic(fA, XA, F_FAUSSE))
print("   B - filtre ordre 8      : %.4f g" % pic(fB, XB, F_FAUSSE))
print("Pic du défaut de roulement à BPFO = %.1f Hz :" % BPFO)
print("   référence %.4f g | sans filtre %.4f g | avec filtre %.4f g"
      % (pic(f_ref, X_ref, BPFO), pic(fA, XA, BPFO), pic(fB, XB, BPFO)))

# ---------------------------------------------------------------------------
# 3. Figures
# ---------------------------------------------------------------------------
# Figure 1 : le capteur
n = int(0.1 * fe_reel)
fig, ax = plt.subplots(2, 1, figsize=(9, 5), sharex=True)
ax[0].plot(t[:n] * 1000, acc[:n], lw=0.7); ax[0].set_ylabel("Accélération (g)")
ax[0].set_title("Entrée du capteur : vibration réelle (CWRU, défaut bague extérieure) + engrenage 1 700 Hz")
ax[1].plot(t[:n] * 1000, v[:n] * 1000, lw=0.7, color="C1"); ax[1].set_ylabel("Tension (mV)")
ax[1].set_xlabel("Temps (ms)"); ax[1].set_title("Sortie du capteur : 100 mV/g + bruit propre")
fig.tight_layout(); fig.savefig("resultats/1_capteur.png", dpi=150)

# Figure 2 : le repliement
fig, ax = plt.subplots(3, 1, figsize=(9, 7.5), sharex=True, sharey=True)
for a_, (f, X, titre, c) in zip(ax, [
        (f_ref, X_ref, "Réalité (spectre à 12 kHz)", "k"),
        (fA, XA, "A - carte à 2 000 Hz SANS filtre anti-repliement", "C3"),
        (fB, XB, "B - carte à 2 000 Hz AVEC filtre anti-repliement (ordre 8, coupure 781 Hz)", "C0")]):
    m = f <= NYQUIST
    a_.plot(f[m], X[m], lw=0.7, color=c); a_.set_title(titre, fontsize=10)
    a_.axvline(F_FAUSSE, color="C3", ls=":", lw=1); a_.axvline(BPFO, color="C2", ls=":", lw=1)
    a_.axvspan(FMAX, NYQUIST, color="0.9"); a_.set_ylabel("Amplitude (g)")
ax[1].annotate("faux pic à 300 Hz\n(engrenage 1 700 Hz replié)", xy=(F_FAUSSE, pic(fA, XA, F_FAUSSE)),
               xytext=(420, pic(fA, XA, F_FAUSSE) * 0.8), arrowprops=dict(arrowstyle="->"), fontsize=9)
ax[0].text(BPFO + 8, ax[0].get_ylim()[1] * 0.8, "BPFO 107 Hz", color="C2", fontsize=9)
ax[2].set_xlabel("Fréquence (Hz)  —  zone grise : entre fmax et Nyquist")
fig.tight_layout(); fig.savefig("resultats/2_repliement.png", dpi=150)

# Figure 3 : la réponse du filtre
f = np.linspace(1, 5000, 3000)
fig, ax = plt.subplots(figsize=(9, 4))
for ordre, c in ((4, "C1"), (8, "C0")):
    ax.plot(f, 20 * np.log10(reponse_filtre(fe_reel, FMAX, ordre, f) + 1e-12), color=c, label=f"Butterworth ordre {ordre}")
ax.axvline(FMAX, color="k", ls="--", lw=0.8); ax.text(FMAX - 30, -60, "fmax\n781 Hz", fontsize=8, ha="right")
ax.axvline(NYQUIST, color="k", ls=":", lw=0.8); ax.text(NYQUIST + 30, -100, "Nyquist\n1 000 Hz", fontsize=8)
ax.axvspan(FE - FMAX, 5000, color="C3", alpha=0.08); ax.text(2300, -12, "zone dangereuse : f > fe - fmax = 1 219 Hz\n(se replie dans la zone mesurée)", fontsize=8, color="C3")
ax.plot([F_ENGRENAGE], [20 * np.log10(reponse_filtre(fe_reel, FMAX, 8, [F_ENGRENAGE])[0])], "o", color="C3")
ax.annotate("engrenage 1 700 Hz :\natténué ≈ 800 fois", xy=(F_ENGRENAGE, -58), xytext=(1900, -45), fontsize=8, arrowprops=dict(arrowstyle="->"))
ax.set(xlabel="Fréquence (Hz)", ylabel="Gain (dB)", ylim=(-110, 5), title="Filtre anti-repliement : ce qui passe et ce qui est bloqué")
ax.legend(loc="upper right"); fig.tight_layout(); fig.savefig("resultats/3_filtre.png", dpi=150)
print("Figures enregistrées dans resultats/")

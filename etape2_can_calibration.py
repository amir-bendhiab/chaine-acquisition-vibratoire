"""
Étape 2 : convertisseur analogique-numérique (résolution) et calibration du capteur.
Lancer : python etape2_can_calibration.py   (résultats dans resultats/)
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from chaine import charger_cwru, capteur, can, indicateurs

os.makedirs("resultats", exist_ok=True)
S_NOM = 0.100                                    # sensibilité de la fiche technique : 100 mV/g

# ===========================================================================
# PARTIE A — Résolution du convertisseur : que voit-on d'un roulement SAIN ?
# ===========================================================================
acc, fe = charger_cwru("Normal_0.mat")           # roulement sain : petites vibrations
acc = acc[: fe * 2]                              # 2 secondes suffisent
v = capteur(acc, fe, sensibilite=S_NOM)          # tension (V)
rms_vrai = indicateurs(v / S_NOM)["RMS"]

cas = [  # (nom, bits, plage +/- en V, gain d'amplification avant le CAN)
    ("Arduino 10 bits", 10, 2.5, 1),
    ("Arduino 10 bits + ampli x20", 10, 2.5, 20),
    ("Carte 16 bits", 16, 5.0, 1),
    ("NI 9234, 24 bits", 24, 5.0, 1),
]
def comparer(titre, v, gardes=None):
    ref = indicateurs(v / S_NOM)
    print("\n%s : réalité RMS = %.4f g, crête = %.3f g, kurtosis = %.2f" % (titre, ref["RMS"], ref["crête"], ref["kurtosis"]))
    print("%-30s %9s %12s %10s %10s %10s %11s" % ("Convertisseur", "pas (mV)", "pas (g)", "RMS (g)", "crête (g)", "kurtosis", "saturation"))
    sortie = {}
    for nom, bits, plage, gain in cas:
        vn, q = can(v * gain, bits, plage)       # numérisation
        acc_mes = vn / gain / S_NOM              # retour en g
        ind = indicateurs(acc_mes)
        sat = np.mean(np.abs(v * gain) >= plage) * 100
        sortie[nom] = acc_mes
        print("%-30s %9.4f %12.6f %10.4f %10.3f %10.2f %9.2f %%"
              % (nom, q * 1000, q / gain / S_NOM, ind["RMS"], ind["crête"], ind["kurtosis"], sat))
    return sortie

resultats = comparer("ROULEMENT SAIN (petites vibrations)", v)
acc_d, fe_d = charger_cwru("OR007_0.mat")
comparer("ROULEMENT DÉFECTUEUX (chocs)", capteur(acc_d[: fe_d * 2], fe_d, sensibilite=S_NOM))

# Figure : 20 ms du signal vu par chaque convertisseur
n = int(0.005 * fe); t = np.arange(n) / fe * 1000
fig, axs = plt.subplots(len(cas), 1, figsize=(9, 8), sharex=True, sharey=True)
for ax, (nom, *_ ) in zip(axs, cas):
    ax.plot(t, acc[:n], color="0.7", lw=1.2, label="réalité")
    ax.step(t, resultats[nom][:n], where="mid", color="C3", lw=1, label="mesuré")
    ax.set_title(nom, fontsize=10, loc="left"); ax.set_ylabel("g")
axs[0].legend(loc="upper right", fontsize=8)
axs[-1].set_xlabel("Temps (ms) — roulement sain (CWRU)")
fig.tight_layout(); fig.savefig("resultats/4_resolution_CAN.png", dpi=150)

# ===========================================================================
# PARTIE B — Calibration à 1 g, 159,2 Hz (pot vibrant de référence)
# ===========================================================================
# Le capteur simulé a une sensibilité RÉELLE un peu différente de la fiche technique
# (hypothèse de la simulation : 97,3 mV/g et un petit décalage de 2 mV).
S_REELLE, DECALAGE = 0.0973, 0.002
FE_CAL, F_CAL = 25600, 159.2                     # 159,2 Hz : omega = 1 000 rad/s
t = np.arange(0, 2.0, 1 / FE_CAL)

def mesurer(amplitude_g):
    """Le pot vibrant impose une accélération sinusoïdale connue ; on mesure la tension."""
    a = amplitude_g * np.sin(2 * np.pi * F_CAL * t)
    v = capteur(a, FE_CAL, sensibilite=S_REELLE, bruit_g=0.0005) + DECALAGE
    vn, _ = can(v, 24, 5.0)
    vn = vn[FE_CAL // 2:]                         # on attend 0,5 s que le capteur se stabilise
    vn = vn - vn.mean()                           # correction du décalage (offset)
    return np.sqrt(2) * np.sqrt(np.mean(vn ** 2))  # amplitude (V) à partir de la valeur efficace

v1 = mesurer(1.0)
S_MESUREE = v1 / 1.0
print("\nCALIBRATION à 1 g, %.1f Hz" % F_CAL)
print("  sensibilité fiche technique : %.1f mV/g" % (S_NOM * 1000))
print("  sensibilité mesurée         : %.1f mV/g  (écart %.1f %%)" % (S_MESUREE * 1000, (S_MESUREE / S_NOM - 1) * 100))
print("  à 1 g, en gardant 100 mV/g, on lirait %.3f g au lieu de 1,000 g" % (v1 / S_NOM))
print("\nVérification de la linéarité (avec la sensibilité mesurée) :")
lin = []
for A in (0.5, 1.0, 2.0, 5.0, 10.0):
    lu = mesurer(A) / S_MESUREE
    lin.append((A, lu)); print("  imposé %5.1f g -> lu %6.3f g  (écart %+.2f %%)" % (A, lu, (lu / A - 1) * 100))

fig, ax = plt.subplots(1, 2, figsize=(10, 3.8))
tt = t[FE_CAL // 2: FE_CAL // 2 + int(0.02 * FE_CAL)]
a = np.sin(2 * np.pi * F_CAL * tt)
ax[0].plot((tt - tt[0]) * 1000, a, color="0.6", lw=2, label="imposé : 1 g")
ax[0].plot((tt - tt[0]) * 1000, a * S_REELLE / S_NOM, "C3--", lw=1.2, label="lu avec 100 mV/g (non calibré)")
ax[0].set(xlabel="Temps (ms)", ylabel="g", title="Calibration à 1 g, 159,2 Hz"); ax[0].legend(fontsize=8)
A, L = np.array(lin).T
ax[1].plot(A, A, color="0.6", lw=2, label="idéal"); ax[1].plot(A, L, "o", color="C0", label="mesuré (calibré)")
ax[1].set(xlabel="Accélération imposée (g)", ylabel="Accélération lue (g)", title="Vérification de la linéarité"); ax[1].legend(fontsize=8)
fig.tight_layout(); fig.savefig("resultats/5_calibration.png", dpi=150)
print("\nFigures enregistrées dans resultats/")

"""
Étape 4 : traitement du signal et diagnostic des 4 roulements CWRU.
Indicateurs globaux (RMS, facteur de crête, kurtosis) puis spectre d'enveloppe
pour retrouver la fréquence du défaut et l'identifier.
Lancer : python etape4_diagnostic.py   (résultats dans resultats/)
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import signal
from chaine import charger_cwru, indicateurs, spectre, spectre_enveloppe, FR, BPFO, BPFI, BSF

os.makedirs("resultats", exist_ok=True)
FE = 12000                        # tout le monde à 12 kHz
DUREE = 10                        # secondes analysées -> résolution 0,1 Hz
BANDE = (2000, 4500)              # bande de résonance pour l'enveloppe (sous fe/2,56 = 4 687 Hz)
SEUIL = 10                        # un pic doit dépasser 10 fois le bruit de fond
DOMINANCE = 3                     # ... et 3 fois la fréquence de défaut suivante

FICHIERS = [("Sain", "Normal_0.mat"), ("Bague extérieure", "OR007_0.mat"),
            ("Bague intérieure", "IR007_0.mat"), ("Bille", "Ball007_0.mat")]
DEFAUTS = {"bague extérieure (BPFO)": BPFO, "bague intérieure (BPFI)": BPFI, "bille (BSF)": BSF}

def charger(fichier):
    acc, fe = charger_cwru(fichier)
    if fe == 48000:                                   # le sain est à 48 kHz : on le ramène à 12 kHz
        acc = signal.decimate(acc, 4, ftype="fir", zero_phase=True)   # avec filtre anti-repliement
    return acc[: FE * DUREE]

def emergence(f, X, f0, tolerance=0.015):
    """Hauteur du pic autour de f0 (+/- 1,5 %) divisée par le bruit de fond (médiane 5-500 Hz)."""
    fond = np.median(X[(f > 5) & (f < 500)])
    m = (f > f0 * (1 - tolerance)) & (f < f0 * (1 + tolerance))
    i = np.argmax(X[m])
    return X[m][i] / fond, f[m][i]

print("Fréquences de défaut théoriques à 1 797 tr/min : rotation %.1f Hz | BPFO %.1f | BPFI %.1f | BSF %.1f Hz"
      % (FR, BPFO, BPFI, BSF))

# --------------------------------------------------------------------------
# 1. Indicateurs globaux : « est-ce que le roulement va mal ? »
# --------------------------------------------------------------------------
print("\n1. INDICATEURS GLOBAUX")
print("%-18s %9s %10s %16s %10s" % ("Roulement", "RMS (g)", "crête (g)", "facteur de crête", "kurtosis"))
signaux, ind = {}, {}
for nom, fichier in FICHIERS:
    x = charger(fichier)
    signaux[nom] = x
    ind[nom] = indicateurs(x)
    i = ind[nom]
    print("%-18s %9.3f %10.3f %16.1f %10.2f" % (nom, i["RMS"], i["crête"], i["facteur de crête"], i["kurtosis"]))
print("Repère : kurtosis = 3 pour une vibration aléatoire sans chocs ; nettement plus = chocs.")

# --------------------------------------------------------------------------
# 2. Spectre d'enveloppe : « quel est le défaut ? »
# --------------------------------------------------------------------------
print("\n2. DIAGNOSTIC PAR SPECTRE D'ENVELOPPE (bande %d-%d Hz)" % BANDE)
print("Émergence = hauteur du pic / bruit de fond. Critère : > %d et %d fois plus que la suivante."
      % (SEUIL, DOMINANCE))
print("%-18s %13s %13s %13s   %s" % ("Roulement", "BPFO", "BPFI", "BSF", "Diagnostic"))
spectres, diagnostics = {}, {}
for nom, _ in FICHIERS:
    f, E = spectre_enveloppe(signaux[nom], FE, BANDE)
    spectres[nom] = (f, E)
    em = {d: emergence(f, E, f0) for d, f0 in DEFAUTS.items()}
    classe = sorted(em, key=lambda d: em[d][0], reverse=True)
    premier, second = em[classe[0]][0], em[classe[1]][0]
    if premier < SEUIL:
        diag = "aucun défaut détecté"
    elif premier < DOMINANCE * second:
        diag = "NON CONCLUSIF (plusieurs pics comparables)"
    else:
        diag = "défaut de %s, pic mesuré à %.1f Hz" % (classe[0], em[classe[0]][1])
    diagnostics[nom] = diag
    print("%-18s %13.1f %13.1f %13.1f   %s"
          % (nom, em["bague extérieure (BPFO)"][0], em["bague intérieure (BPFI)"][0], em["bille (BSF)"][0], diag))

# Pourquoi l'enveloppe ? Comparaison avec le spectre « direct » sur la bague extérieure
f_d, X_d = spectre(signaux["Bague extérieure"], FE)
f_e, X_e = spectres["Bague extérieure"]
print("\nPourquoi l'enveloppe ? Émergence de BPFO sur la bague extérieure :")
print("   spectre direct : %.0f   |   spectre d'enveloppe : %.0f" % (emergence(f_d, X_d, BPFO)[0], emergence(f_e, X_e, BPFO)[0]))

# --------------------------------------------------------------------------
# 3. Figures
# --------------------------------------------------------------------------
couleurs = {"Sain": "C2", "Bague extérieure": "C3", "Bague intérieure": "C0", "Bille": "C1"}
fig, axs = plt.subplots(4, 2, figsize=(11, 9), gridspec_kw={"width_ratios": [1, 1.6]})
n = int(0.1 * FE)
t = np.arange(n) / FE * 1000
for (nom, _), (a_t, a_f) in zip(FICHIERS, axs):
    c = couleurs[nom]
    a_t.plot(t, signaux[nom][:n], lw=0.6, color=c)
    a_t.set_ylim(-4, 4); a_t.set_ylabel("g")
    a_t.set_title("%s : kurtosis %.1f" % (nom, ind[nom]["kurtosis"]), fontsize=9, loc="left")
    f, E = spectres[nom]
    m = (f > 2) & (f < 500)
    a_f.plot(f[m], E[m], lw=0.7, color=c)
    for nom_f, f0, cl in (("BPFO", BPFO, "C3"), ("BPFI", BPFI, "C0"), ("BSF", BSF, "C1")):
        for h in (1, 2, 3):
            if f0 * h < 500:
                a_f.axvline(f0 * h, color=cl, ls=":", lw=0.8, alpha=0.8)
        a_f.text(f0, 1.0, nom_f, color=cl, fontsize=7, transform=a_f.get_xaxis_transform(), va="top")
    a_f.set_title(diagnostics[nom], fontsize=9, loc="left")
    a_f.set_ylabel("g")
axs[-1, 0].set_xlabel("Temps (ms)")
axs[-1, 1].set_xlabel("Fréquence (Hz) — spectre d'enveloppe ; pointillés : fréquences de défaut et harmoniques")
fig.tight_layout(); fig.savefig("resultats/7_diagnostic.png", dpi=150)

fig, ax = plt.subplots(1, 2, figsize=(9, 3.4))
noms = [n_ for n_, _ in FICHIERS]
ax[0].bar(noms, [ind[n_]["RMS"] for n_ in noms], color=[couleurs[n_] for n_ in noms])
ax[0].set(title="RMS (niveau global)", ylabel="g")
ax[1].bar(noms, [ind[n_]["kurtosis"] for n_ in noms], color=[couleurs[n_] for n_ in noms])
ax[1].axhline(3, color="k", ls="--", lw=0.8); ax[1].text(-0.4, 3.2, "3 = sans chocs", fontsize=8)
ax[1].set(title="Kurtosis (présence de chocs)")
for a in ax:
    a.tick_params(axis="x", labelsize=8)
fig.tight_layout(); fig.savefig("resultats/8_indicateurs.png", dpi=150)
print("\nFigures enregistrées : resultats/7_diagnostic.png, resultats/8_indicateurs.png")

"""
Étape 3 : lecture et contrôle des mesures Arduino (MPU6050 simulé sous Wokwi).
Fichiers attendus (copiés depuis le moniteur série de Wokwi) :
    arduino_methode1.csv  (delay naïf)   et/ou   arduino_methode2.csv  (horloge fixe)
Lancer : python etape3_arduino.py   (figure dans resultats/)
"""
import os
import re
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from chaine import FR

os.makedirs("resultats", exist_ok=True)

def lire(fichier):
    """Renvoie (réglages lus dans l'en-tête, tableau t_us / ax / ay / az)."""
    reglages, lignes = {}, []
    with open(fichier, encoding="utf-8", errors="ignore") as f:
        for l in f:
            l = l.strip()
            if l.startswith("#"):
                for cle, val in re.findall(r"(\w+)=(\d+)", l):
                    reglages[cle] = int(val)
            elif l[:1].isdigit():
                try:
                    lignes.append([float(x) for x in l.split(",")[:4]])
                except ValueError:
                    pass                                   # ligne abîmée par le copier-coller
    return reglages, np.array(lignes)

NOMS = {1: "Méthode 1 : delay() naïf", 2: "Méthode 2 : horloge fixe (micros)"}
mesures = {}
for m in (1, 2):
    fichier = "arduino_methode%d.csv" % m
    if not os.path.exists(fichier):
        print("(%s absent : ignoré)" % fichier)
        continue
    reg, d = lire(fichier)
    if len(d) < 10:
        print("(%s : moins de 10 mesures lues, vérifiez le copier-coller)" % fichier)
        continue
    t = d[:, 0] / 1e6
    dt = np.diff(t)
    fe_voulue = reg.get("fe", 200)
    fe_reelle = 1 / dt.mean()
    lsb = reg.get("lsb_par_g", 16384)
    acc = d[:, 1:4] / lsb                                  # comptes -> g
    mesures[m] = (t, dt, acc, fe_voulue)

    print("\n" + NOMS[m])
    print("  points reçus           : %d (attendu %d)" % (len(d), reg.get("N", len(d))))
    print("  fe voulue              : %d Hz  -> période %.0f µs" % (fe_voulue, 1e6 / fe_voulue))
    print("  période réelle         : %.0f µs en moyenne (min %.0f, max %.0f, dispersion %.0f µs)"
          % (dt.mean() * 1e6, dt.min() * 1e6, dt.max() * 1e6, dt.std() * 1e6))
    print("  fe réelle              : %.1f Hz  (écart %+.1f %%)" % (fe_reelle, (fe_reelle / fe_voulue - 1) * 100))
    print("  conséquence : une vibration à %.2f Hz (rotation du moteur CWRU) serait lue à %.2f Hz"
          % (FR, FR * fe_voulue / fe_reelle))

    # Contrôle statique : au repos, le capteur doit lire 0 / 0 / +1 g (gravité)
    repos = d[: min(50, len(d)), 1:4]
    az_brut = np.median(repos[:, 2])
    print("  réglages capteur       : plage +/-%d g, filtre interne %d Hz (fe/2,56 = %.0f Hz)"
          % (reg.get("plage_g", 2), reg.get("dlpf_hz", 44), fe_voulue / 2.56))
    print("  résolution             : 1 compte = %.3f mg" % (1000 / lsb))
    print("  au repos (50 premiers) : ax = %.3f g, ay = %.3f g, az = %.3f g"
          % tuple(np.median(repos, axis=0) / lsb))
    print("  sensibilité vérifiée par la gravité : %.0f comptes/g (fiche : %d)" % (az_brut, lsb))

if not mesures:
    raise SystemExit("Aucun fichier de mesure trouvé : copiez la sortie Wokwi dans arduino_methode1.csv / arduino_methode2.csv")

# Figure : l'accélération mesurée et la régularité de l'horloge
fig, ax = plt.subplots(2, 1, figsize=(9, 6.5))
for m, (t, dt, acc, fe_v) in mesures.items():
    c = "C3" if m == 1 else "C0"
    ax[0].plot(t, acc[:, 2], color=c, lw=1, label=NOMS[m])
    ax[1].plot(np.arange(len(dt)), dt * 1e6, ".", ms=3, color=c, label=NOMS[m])
fe_v = next(iter(mesures.values()))[3]
ax[0].set(xlabel="Temps (s)", ylabel="az (g)", title="Accélération verticale mesurée (MPU6050, Wokwi)")
ax[1].axhline(1e6 / fe_v, color="k", ls="--", lw=0.8)
ax[1].text(0, 1e6 / fe_v, " période voulue %.0f µs" % (1e6 / fe_v), va="bottom", fontsize=8)
ax[1].set(xlabel="Numéro de l'intervalle", ylabel="Intervalle entre 2 mesures (µs)",
          title="Régularité de l'échantillonnage")
for a in ax:
    a.legend(fontsize=8)
fig.tight_layout()
fig.savefig("resultats/6_arduino.png", dpi=150)
print("\nFigure enregistrée : resultats/6_arduino.png")

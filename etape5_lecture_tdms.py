"""
Étape 5 : lecture du fichier TDMS enregistré par LabVIEW (NI 9234 simulé) et contrôle.
Installer une fois :  pip install npTDMS
Lancer : python etape5_lecture_tdms.py   (figure dans resultats/)
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from nptdms import TdmsFile
from chaine import indicateurs, spectre

FICHIER = "mesure_labview.tdms"
FE_VOULUE = 25600
os.makedirs("resultats", exist_ok=True)

if not os.path.exists(FICHIER):
    raise SystemExit("Fichier %s absent : lancez d'abord l'acquisition LabVIEW (Logging Mode = Log and Read)." % FICHIER)
tdms = TdmsFile.read(FICHIER)
print("Contenu du fichier %s :" % FICHIER)
voie = None
for groupe in tdms.groups():
    for v in groupe.channels():
        print("   groupe '%s', voie '%s' : %d points" % (groupe.name, v.name, len(v)))
        if voie is None and len(v) > 0:
            voie = v
if voie is None:
    raise SystemExit("Aucune donnée dans le fichier : l'acquisition a-t-elle tourné avec Logging Mode = Log and Read ?")

x = np.asarray(voie[:], dtype=float)
prop = voie.properties
dt = prop.get("wf_increment")
if dt:
    fe = 1 / float(dt)
    origine = "lue dans le fichier (wf_increment)"
else:
    fe = FE_VOULUE
    origine = "NON trouvée dans le fichier : valeur réglée supposée"
unite = prop.get("unit_string", "g")

print("\nVoie analysée          : %s" % voie.name)
print("Fréquence d'échant.    : %.1f Hz (%s)" % (fe, origine))
print("Écart avec le réglage  : %+.3f %%" % ((fe / FE_VOULUE - 1) * 100))
print("Nombre de points       : %d, soit %.2f s de mesure" % (len(x), len(x) / fe))
print("Unité enregistrée      : %s" % unite)
print("Bande utile (fe/2,56)  : %.0f Hz" % (fe / 2.56))

ind = indicateurs(x)
print("\nIndicateurs : moyenne %.3f %s | RMS (sans la moyenne) %.3f | crête %.3f | kurtosis %.2f"
      % (x.mean(), unite, ind["RMS"], ind["crête"], ind["kurtosis"]))
f, X = spectre(x, fe)
m = f > 0.2
i = np.argmax(X[m])
print("Pic principal du spectre : %.2f Hz, amplitude %.3f %s" % (f[m][i], X[m][i], unite))
print("Résolution en fréquence  : %.3f Hz (= 1 / durée)" % (fe / len(x)))

fig, ax = plt.subplots(2, 1, figsize=(9, 6))
t = np.arange(len(x)) / fe
ax[0].plot(t, x, lw=0.5)
ax[0].set(xlabel="Temps (s)", ylabel=unite, title="Signal enregistré par LabVIEW (NI 9234 simulé) — fichier TDMS")
ax[1].semilogx(f[m], X[m], lw=0.7)
ax[1].set(xlabel="Fréquence (Hz)", ylabel=unite, title="Spectre")
fig.tight_layout(); fig.savefig("resultats/9_labview.png", dpi=150)
print("\nFigure enregistrée : resultats/9_labview.png")

"""
Chaîne d'acquisition vibratoire simulée : un maillon = une fonction.
capteur -> filtre anti-repliement -> échantillonnage -> convertisseur (CAN) -> traitement
"""
import numpy as np
import scipy.io as sio
from scipy import signal

# ---------------------------------------------------------------------------
# 0. Données réelles : jeu CWRU (accéléromètre côté entraînement, en g)
# ---------------------------------------------------------------------------
def charger_cwru(fichier):
    """Renvoie (accélération en g, fréquence d'échantillonnage en Hz).
    Le roulement sain (Normal) est enregistré à 48 kHz, les défauts à 12 kHz."""
    data = sio.loadmat(fichier)
    cle = [k for k in data if k.endswith("_DE_time")][0]      # voie côté entraînement
    acc = data[cle].ravel().astype(float)
    fe = 48000 if "normal" in fichier.lower() else 12000
    return acc, fe

# Roulement SKF 6205 (côté entraînement), vitesse 1 797 tr/min à 0 HP
FR = 1797 / 60                       # fréquence de rotation : 29,95 Hz
BPFO = 3.5848 * FR                   # défaut bague extérieure : ≈ 107,4 Hz
BPFI = 5.4152 * FR                   # défaut bague intérieure : ≈ 162,2 Hz
BSF = 2.3570 * FR                    # défaut bille : ≈ 70,6 Hz

# ---------------------------------------------------------------------------
# 1. Capteur : accélération (g) -> tension (V)
# ---------------------------------------------------------------------------
def capteur(acc_g, fe, sensibilite=0.100, bruit_g=0.0005, f_basse=0.5, plage_v=5.0, graine=1):
    """Accéléromètre piézoélectrique IEPE.
    sensibilite : V/g (100 mV/g) ; bruit_g : bruit propre (g efficace) ;
    f_basse : coupure basse (un piézo ne voit pas le continu) ; plage_v : sortie maxi (écrêtage)."""
    rng = np.random.default_rng(graine)
    a = acc_g + bruit_g * rng.standard_normal(len(acc_g))
    b, a_ = signal.butter(1, f_basse, btype="highpass", fs=fe)
    v = signal.lfilter(b, a_, sensibilite * a)
    return np.clip(v, -plage_v, plage_v)

# ---------------------------------------------------------------------------
# 2. Filtre anti-repliement (passe-bas « analogique », placé AVANT l'échantillonnage)
# ---------------------------------------------------------------------------
def filtre_anti_repliement(v, fe_entree, fc, ordre=8):
    """Butterworth passe-bas d'ordre 'ordre', coupure fc (Hz)."""
    sos = signal.butter(ordre, fc, btype="lowpass", fs=fe_entree, output="sos")
    return signal.sosfilt(sos, v)

def reponse_filtre(fe_entree, fc, ordre, f):
    """Gain du filtre (sans unité, 1 = tout passe) aux fréquences f."""
    sos = signal.butter(ordre, fc, btype="lowpass", fs=fe_entree, output="sos")
    _, h = signal.sosfreqz(sos, worN=f, fs=fe_entree)
    return np.abs(h)

# ---------------------------------------------------------------------------
# 3. Échantillonnage : on ne garde qu'un point sur k (la carte mesure moins souvent)
# ---------------------------------------------------------------------------
def echantillonner(v, fe_entree, fe_sortie):
    k = int(round(fe_entree / fe_sortie))
    assert abs(fe_entree / k - fe_sortie) < 1e-6, "fe_sortie doit diviser fe_entree"
    return v[::k], fe_entree / k

# ---------------------------------------------------------------------------
# 4. Convertisseur analogique-numérique (CAN)
# ---------------------------------------------------------------------------
def can(v, bits, plage_v=5.0):
    """Quantification sur 'bits' bits, entrée de -plage_v à +plage_v."""
    q = 2 * plage_v / 2 ** bits                    # pas de quantification (V)
    return np.clip(np.round(v / q) * q, -plage_v, plage_v - q), q

# ---------------------------------------------------------------------------
# 5. Traitement
# ---------------------------------------------------------------------------
def spectre(x, fe):
    """Spectre d'amplitude (même unité que x), fenêtre de Hann."""
    n = len(x)
    w = np.hanning(n)
    X = np.abs(np.fft.rfft((x - x.mean()) * w)) * 2 / w.sum()
    return np.fft.rfftfreq(n, 1 / fe), X

def indicateurs(x):
    x = x - x.mean()
    rms = np.sqrt(np.mean(x ** 2))
    crete = np.max(np.abs(x))
    kurt = np.mean(x ** 4) / rms ** 4
    return {"RMS": rms, "crête": crete, "facteur de crête": crete / rms, "kurtosis": kurt}

def spectre_enveloppe(x, fe, bande=(2000, 5000)):
    """Analyse d'enveloppe : filtre passe-bande autour de la résonance, puis enveloppe (Hilbert)."""
    sos = signal.butter(4, bande, btype="bandpass", fs=fe, output="sos")
    env = np.abs(signal.hilbert(signal.sosfiltfilt(sos, x)))
    return spectre(env, fe)

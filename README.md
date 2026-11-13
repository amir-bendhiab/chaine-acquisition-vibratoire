# Chaîne d'acquisition vibratoire : du capteur au diagnostic de roulement

Construction et validation, maillon par maillon, d'une chaîne de mesure de vibrations (capteur, filtre anti-repliement, échantillonnage, convertisseur, calibration, acquisition), puis diagnostic de défauts de roulement par **spectre d'enveloppe**. Python, Arduino (Wokwi) et LabVIEW / NI-DAQmx.

> **English summary.** Step-by-step validation of a vibration measurement chain on real bearing vibration data (CWRU dataset): aliasing and anti-aliasing filter, ADC resolution and saturation, sensor calibration, sampling clock on Arduino, IEPE acquisition under LabVIEW / NI-DAQmx with a simulated NI 9234 and TDMS logging, then bearing fault diagnosis with envelope analysis. The vibrations are real; the sensor, filter and converters are simulated (no hardware).

<p align="center"><img src="images/f0_chaine.png" width="720" alt="La chaîne de mesure et les étapes du projet"></p>

## Le problème

Une chaîne de mesure mal réglée affiche des courbes propres, avec la bonne unité, mais fausses, et rien ne le signale. Le projet répond à une question : **comment vérifier qu'une mesure de vibration est juste, du capteur jusqu'au diagnostic ?**

Les vibrations sont réelles : elles viennent du banc de roulements de Case Western Reserve University (CWRU), avec un roulement sain et trois défauts (bague extérieure, bague intérieure, bille). Le capteur, le filtre et le convertisseur sont simulés en Python.

## Résultats par étape

| Étape | Ce qui est testé | Résultat |
|---|---|---|
| **1. Repliement** | Échantillonnage à 2 000 Hz avec et sans filtre anti-repliement (Butterworth d'ordre 8) | Sans filtre, un **faux pic de 0,49 g** apparaît à 300 Hz et le pic de défaut est faux de +75 %. Le filtre supprime les deux. |
| **2. Convertisseur et calibration** | Arduino 10 bits (avec et sans amplificateur), 16 bits, NI 9234 24 bits ; calibration à 1 g / 159,2 Hz | Avec l'amplificateur, **9 % de saturation** : le kurtosis passe de 7,6 à 4,3, le défaut est à moitié caché. La calibration corrige un **écart de sensibilité de 2,7 %**. |
| **3. Arduino** | MPU6050 simulé sous Wokwi, deux méthodes de cadencement | Avec `delay()`, la cadence réelle est de **165 Hz au lieu de 200 Hz** (−17 %). Avec une horloge fixe : 200,0 Hz. |
| **4. Diagnostic** | RMS, kurtosis, spectre d'enveloppe (bande 2 000 – 4 500 Hz) | Bague extérieure identifiée à **107,6 Hz** (107,4 Hz théoriques), bague intérieure à **161,7 Hz** (162,2 Hz). Bille : **non conclusif**. |
| **5. LabVIEW** | Voie IEPE à 100 mV/g sur un NI 9234 simulé, 25,6 kHz, enregistrement TDMS relu en Python | Fréquence d'échantillonnage confirmée par la carte et par le fichier : **25 600 Hz**. |

<p align="center">
<img src="images/2_repliement.png" width="420" alt="Repliement avec et sans filtre">
<img src="images/f_enveloppe.png" width="420" alt="Principe du spectre d'enveloppe">
</p>
<p align="center"><img src="images/7_diagnostic.png" width="720" alt="Diagnostic des quatre roulements"></p>
<p align="center"><img src="images/labview_acquisition.png" width="720" alt="Acquisition sous LabVIEW sur un NI 9234 simulé"></p>

## Lancer les scripts

```bash
pip install -r requirements.txt
python etape1_capteur_repliement.py
python etape2_can_calibration.py
python etape4_diagnostic.py
```

Les figures sont enregistrées dans `resultats/`.

**Données CWRU (non incluses dans le dépôt).** Les télécharger sur le site du [Bearing Data Center de CWRU](https://engineering.case.edu/bearingdatacenter/download-data-file) et les renommer ainsi, à la racine du dépôt :

| Fichier CWRU | Nom attendu | Contenu |
|---|---|---|
| `97.mat` (Normal Baseline, 0 HP) | `Normal_0.mat` | Roulement sain, 48 kHz |
| `130.mat` (12k Drive End, 0,007", Outer Race @6:00, 0 HP) | `OR007_0.mat` | Défaut de bague extérieure, 12 kHz |
| `105.mat` (12k Drive End, 0,007", Inner Race, 0 HP) | `IR007_0.mat` | Défaut de bague intérieure, 12 kHz |
| `118.mat` (12k Drive End, 0,007", Ball, 0 HP) | `Ball007_0.mat` | Défaut de bille, 12 kHz |

**Étape 3 (Arduino).** Copier `arduino_wokwi/sketch.ino` et `diagram.json` dans un projet Arduino Uno sur [wokwi.com](https://wokwi.com), lancer une acquisition (taper `a` dans le moniteur série), enregistrer la sortie dans `arduino_methode1.csv` ou `arduino_methode2.csv`, puis lancer `python etape3_arduino.py`.

**Étape 5 (LabVIEW).** Le guide pas à pas (installation, carte simulée dans NI MAX, réglages de l'exemple NI « IEPE - Continuous Input ») est dans la note technique, § 7. Une fois `mesure_labview.tdms` enregistré, lancer `python etape5_lecture_tdms.py`.

## Contenu du dépôt

| Fichier | Rôle |
|---|---|
| `chaine.py` | Les maillons de la chaîne : lecture CWRU, capteur, filtre, échantillonnage, convertisseur, spectre, indicateurs, enveloppe |
| `etape1` à `etape5` | Un script par étape (voir le tableau des résultats) |
| `arduino_wokwi/` | Programme Arduino et câblage du MPU6050 pour Wokwi |
| `docs/note_technique_acquisition.pdf` | Note technique complète : démarche, résultats, guide LabVIEW, questions et réponses |

## Limites

- **Pas de matériel.** Les vibrations sont réelles, mais le capteur, le filtre, le convertisseur et la carte NI 9234 sont simulés. La vibration d'engrenage à 1 700 Hz de l'étape 1 est ajoutée pour la démonstration.
- Sous Wokwi, le capteur est idéal ; sous LabVIEW, le signal de la carte simulée est factice. Ces étapes valident le **logiciel d'acquisition** (réglages, cadence, enregistrement), pas une mesure physique.
- Le diagnostic est testé sur 4 enregistrements seulement (une vitesse, une taille de défaut). Ses seuils devraient être validés sur beaucoup plus de données.
- La suite logique : un vrai accéléromètre IEPE vissé sur une machine, une vraie carte d'acquisition, et des jauges de déformation pour mesurer les efforts.

## Auteur

Amir Mokhtar Ben Dhiab — élève ingénieur en génie électromécanique (mécatronique), École Polytechnique de Sousse. Projet personnel, novembre 2026.

Données : Case Western Reserve University Bearing Data Center.

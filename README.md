# TP Traitement Numérique du Signal (TNS)

> ENSET Douala — Département de Génie Informatique — Niveau 4 I.I/TIC
> Session normale 2025-2026

Ce dépôt regroupe l'ensemble des livrables du TP de Traitement Numérique du Signal : analyse statistique d'un signal discret bruité, conception de filtres numériques (FIR, passe-haut, passe-bas), étude fréquentielle (TFD), et implémentation embarquée temps réel (ESP32 + Flask + dashboard web).

## Contexte

Un système embarqué acquiert un signal analogique bruité provenant d'un capteur biomédical ou industriel :

```
x[n] = {12, 15, 18, 22, 30, 28, 35, 40, 38, 45, 50, 48, 55, 60}
```

Ce signal contient du bruit haute fréquence, des variations lentes et des perturbations impulsionnelles. L'objectif est de l'analyser, le filtrer et l'interpréter, puis de proposer une chaîne d'acquisition et de traitement embarquée complète.

## Structure du projet

```
.
├── partie_A_analyse_signal.py       # Analyse statistique du signal (moyenne, variance, amplitude)
├── signal_xn.png                    # Figure : représentation du signal x[n]
│
├── partie_B_filtrage.py             # Filtre FIR moyenne glissante + filtre passe-haut
├── partie_B_resultats.csv           # Tableau des valeurs filtrées
├── partie_B_filtrage.png            # Figure : signaux filtrés
├── partie_B_comparaison_fir.png     # Figure : comparaison brut vs FIR
│
├── partie_C_spectre.png             # Figure : spectre d'amplitude |X[k]| (TFD)
│
├── partie_D_conception_filtre.py    # Filtre passe-bas H(z) = 0.5 + 0.5z⁻¹
├── partie_D_resultats.csv           # Tableau des valeurs filtrées
├── partie_D_filtre.png              # Figure : signal filtré + réponse en fréquence
│
├── esp32_firmware.ino               # Firmware ESP32 (acquisition, filtres, WiFi/UART)
├── serveur_flask.py                 # Serveur Flask + SocketIO (API, KPIs, config à distance)
├── templates/
│   └── index.html                   # Dashboard web temps réel (Chart.js + Socket.IO)
│
├── rapport_tp_tns.tex               # Rapport LaTeX complet (compilable sur Overleaf)
└── README.md
```

## Prérequis

- Python ≥ 3.9
- Un compte [Overleaf](https://www.overleaf.com) (ou une distribution LaTeX locale) pour le rapport
- Une carte ESP32 + Arduino IDE (ou PlatformIO) pour la Partie E — optionnel, un mode simulation est fourni

### Dépendances Python

```bash
pip install numpy matplotlib pandas flask flask-socketio simple-websocket
```

## Parties A à D — Analyse et filtrage du signal

Chaque script est autonome, s'exécute indépendamment et génère ses figures/tableaux dans le dossier courant.

```bash
python partie_A_analyse_signal.py        # Représentation, moyenne, variance, amplitude
python partie_B_filtrage.py              # Filtre FIR + filtre passe-haut
python partie_D_conception_filtre.py     # Filtre passe-bas H(z) = 0.5 + 0.5z⁻¹
```

| Partie | Contenu | Sorties |
|---|---|---|
| A | Analyse statistique du signal | `signal_xn.png` |
| B | Filtre FIR (moyenne glissante) + filtre passe-haut | `partie_B_*.png`, `partie_B_resultats.csv` |
| C | Transformée de Fourier Discrète (TFD) | `partie_C_spectre.png` |
| D | Conception d'un filtre passe-bas | `partie_D_filtre.png`, `partie_D_resultats.csv` |

## Partie E — Implémentation embarquée

Architecture : **Capteur → ESP32 (acquisition + filtrage + détection) → Flask (API + SocketIO) → Dashboard web (temps réel)**, avec un canal UART de secours pour le debug local.

### 1. Lancer le serveur Flask

```bash
python serveur_flask.py
```

Puis ouvrir **http://localhost:5000** dans un navigateur.

### 2. Tester sans matériel ESP32 (mode simulation)

Depuis le dashboard, cliquer sur **« Démarrer simulation »** : le signal du TP est rejoué en continu, avec bruit aléatoire simulé, pour valider toute la chaîne (filtrage, détection d'événements, spectre, KPIs) sans matériel.

### 3. Utiliser un vrai ESP32

1. Ouvrir `esp32_firmware.ino` dans l'Arduino IDE.
2. Installer la librairie **ArduinoJson** (Library Manager).
3. Renseigner dans le firmware :
   ```cpp
   const char* WIFI_SSID     = "NOM_DE_VOTRE_WIFI";
   const char* WIFI_PASSWORD = "MOT_DE_PASSE_WIFI";
   const char* URL_DONNEES   = "http://<IP_DU_SERVEUR>:5000/api/data";
   const char* URL_CONFIG    = "http://<IP_DU_SERVEUR>:5000/api/config";
   ```
4. Flasher l'ESP32, lancer `serveur_flask.py` sur une machine du même réseau WiFi.

### Fonctionnalités du dashboard

- **Graphique temporel** : signal brut vs signal filtré, mis à jour en direct (Socket.IO)
- **Spectre fréquentiel** : TFD glissante sur les 32 derniers échantillons
- **Indicateurs (KPIs)** : moyenne, variance, écart-type, min/max, débit réel (Hz)
- **LED virtuelle** à 3 états : normal (vert) / avertissement (orange) / critique (rouge)
- **Journal des alertes** horodaté
- **Panneau de contrôle à distance** : type de filtre (FIR / passe-haut / adaptatif), seuil de détection, fréquence d'acquisition — synchronisés avec l'ESP32 sans reflashage
- **Statut infrastructure** : RSSI WiFi, uptime, état de connexion

## Rapport

Le rapport complet (réponses aux questions, tableaux, figures, architecture) est disponible dans `rapport_tp_tns.tex`, prêt à compiler sur Overleaf (pdfLaTeX). Les images produites par les scripts Python doivent être uploadées à la racine du projet Overleaf sous les mêmes noms de fichiers.

## Auteur

**Darix SAMANI SIEWE** — Niveau 4 I.I, ENSET Douala
Sous la supervision de Dr OBONO, Dr NGONO
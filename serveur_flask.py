"""
TP Traitement Numérique du Signal - Partie E (v2)
Serveur Flask + SocketIO : réception ESP32, calcul des KPIs,
détection d'événements graduée, configuration à distance,
push temps réel vers le dashboard web.

Lancement :
    pip install flask flask-socketio simple-websocket
    python serveur_flask.py
Puis ouvrir http://localhost:5000
"""

import time
import threading
from collections import deque

import numpy as np
from flask import Flask, request, jsonify, render_template
from flask_socketio import SocketIO

app = Flask(__name__)
app.config["SECRET_KEY"] = "tns-esp32-dashboard"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# ============================================================
# Configuration du système (modifiable à distance)
# ============================================================
CONFIG = {
    "filtre": "FIR",              # "FIR" | "PASSE_HAUT" | "ADAPTATIF"
    "seuil_evenement": 8.0,       # seuil de détection (unité du signal)
    "intervalle_ms": 500,         # période d'échantillonnage cible
}

# ============================================================
# État / stockage en mémoire
# ============================================================
TAILLE_BUFFER = 200
TAILLE_FENETRE_KPI = 20         # fenêtre glissante pour les statistiques

donnees = deque(maxlen=TAILLE_BUFFER)
evenements = deque(maxlen=100)
horodatages_reception = deque(maxlen=50)   # pour calculer le débit réel (Hz)

etat_infra = {
    "derniere_reception": None,
    "rssi": None,
    "uptime_esp32_s": None,
    "en_ligne": False,
}

simulation_en_cours = False
lock = threading.Lock()


# ============================================================
# Filtres numériques (mêmes équations que les Parties B/D)
# ============================================================
def filtre_fir(buffer_brut):
    """Moyenne glissante d'ordre 4."""
    fenetre = buffer_brut[-4:]
    if len(fenetre) < 4:
        fenetre = [0] * (4 - len(fenetre)) + list(fenetre)
    return float(np.mean(fenetre))


def filtre_passe_haut(buffer_brut):
    """y[n] = x[n] - x[n-1]"""
    if len(buffer_brut) < 2:
        return float(buffer_brut[-1])
    return float(buffer_brut[-1] - buffer_brut[-2])


def filtre_adaptatif(buffer_brut):
    """
    Ordre de la moyenne glissante ajusté selon la variance locale :
    signal bruité -> fenêtre large (plus de lissage) ;
    signal stable -> fenêtre courte (plus réactif).
    """
    fenetre_analyse = buffer_brut[-6:] if len(buffer_brut) >= 2 else buffer_brut
    variance_locale = float(np.var(fenetre_analyse)) if len(fenetre_analyse) > 1 else 0.0
    ordre = 6 if variance_locale > 25 else (4 if variance_locale > 8 else 2)
    fenetre = buffer_brut[-ordre:]
    if len(fenetre) < ordre:
        fenetre = [0] * (ordre - len(fenetre)) + list(fenetre)
    return float(np.mean(fenetre))


def appliquer_filtre(buffer_brut, type_filtre):
    if type_filtre == "PASSE_HAUT":
        return filtre_passe_haut(buffer_brut)
    if type_filtre == "ADAPTATIF":
        return filtre_adaptatif(buffer_brut)
    return filtre_fir(buffer_brut)


# ============================================================
# Détection d'événements graduée (LED virtuelle : vert/orange/rouge)
# ============================================================
def evaluer_severite(valeur_brute, valeur_precedente, seuil):
    variation = abs(valeur_brute - valeur_precedente) if valeur_precedente is not None else 0.0
    if variation > seuil:
        return "critique", variation
    if variation > 0.5 * seuil:
        return "avertissement", variation
    return "normal", variation


# ============================================================
# Calcul des KPIs (Partie A) sur la fenêtre glissante
# ============================================================
def calculer_kpis():
    if len(donnees) == 0:
        return None
    fenetre = list(donnees)[-TAILLE_FENETRE_KPI:]
    valeurs_brutes = np.array([p["brut"] for p in fenetre])

    debit_hz = None
    if len(horodatages_reception) >= 2:
        ts = list(horodatages_reception)
        duree = ts[-1] - ts[0]
        debit_hz = round((len(ts) - 1) / duree, 2) if duree > 0 else None

    return {
        "moyenne": round(float(np.mean(valeurs_brutes)), 3),
        "variance": round(float(np.var(valeurs_brutes)), 3),
        "ecart_type": round(float(np.std(valeurs_brutes)), 3),
        "max": round(float(np.max(valeurs_brutes)), 3),
        "min": round(float(np.min(valeurs_brutes)), 3),
        "debit_hz": debit_hz,
        "nb_echantillons_fenetre": len(fenetre),
    }


# ============================================================
# Spectre fréquentiel (TFD - Partie C) sur la fenêtre glissante
# ============================================================
def calculer_spectre():
    fenetre = list(donnees)[-32:]
    if len(fenetre) < 8:
        return None
    valeurs = np.array([p["brut"] for p in fenetre])
    spectre = np.abs(np.fft.rfft(valeurs))
    freqs = np.fft.rfftfreq(len(valeurs))
    return {
        "freqs": [round(f, 4) for f in freqs.tolist()],
        "magnitudes": [round(m, 2) for m in spectre.tolist()],
    }


# ============================================================
# Traitement centralisé d'un nouvel échantillon brut
# ============================================================
def traiter_nouvel_echantillon(brut, rssi=None, uptime_esp32_s=None, source="esp32"):
    with lock:
        n = len(donnees)
        buffer_brut = [p["brut"] for p in donnees] + [brut]

        filtre_actif = CONFIG["filtre"]
        valeur_filtree = appliquer_filtre(buffer_brut, filtre_actif)

        precedent = donnees[-1]["brut"] if donnees else None
        severite, variation = evaluer_severite(brut, precedent, CONFIG["seuil_evenement"])

        maintenant = time.time()
        point = {
            "n": n,
            "brut": round(float(brut), 3),
            "filtre": round(float(valeur_filtree), 3),
            "severite": severite,
            "variation": round(variation, 3),
            "filtre_utilise": filtre_actif,
            "timestamp": maintenant,
        }
        donnees.append(point)
        horodatages_reception.append(maintenant)

        if rssi is not None:
            etat_infra["rssi"] = rssi
        if uptime_esp32_s is not None:
            etat_infra["uptime_esp32_s"] = uptime_esp32_s
        etat_infra["derniere_reception"] = maintenant
        etat_infra["en_ligne"] = True

        evenement = None
        if severite != "normal":
            evenement = {
                "n": n,
                "horodatage": time.strftime("%d/%m/%Y %H:%M:%S", time.localtime(maintenant)),
                "severite": severite,
                "valeur": point["brut"],
                "variation": point["variation"],
                "message": (
                    f"Seuil critique dépassé (valeur={point['brut']}, Δ={point['variation']})"
                    if severite == "critique"
                    else f"Variation rapide suspecte (Δ={point['variation']})"
                ),
            }
            evenements.append(evenement)

        kpis = calculer_kpis()
        spectre = calculer_spectre()

    payload = {
        "point": point,
        "kpis": kpis,
        "spectre": spectre,
        "config": CONFIG,
        "infra": {**etat_infra, "source": source},
    }
    socketio.emit("nouvelle_donnee", payload)
    if evenement:
        socketio.emit("nouvel_evenement", evenement)

    return point, evenement


# ============================================================
# Routes API - Réception des données ESP32
# ============================================================
@app.route("/api/data", methods=["POST"])
def recevoir_donnees():
    payload = request.get_json(force=True)
    point, evenement = traiter_nouvel_echantillon(
        brut=payload.get("brut"),
        rssi=payload.get("rssi"),
        uptime_esp32_s=payload.get("uptime_s"),
        source="esp32",
    )
    return jsonify({"status": "ok", "point": point}), 200


@app.route("/api/data", methods=["GET"])
def obtenir_donnees():
    with lock:
        return jsonify({
            "donnees": list(donnees),
            "evenements": list(evenements),
            "kpis": calculer_kpis(),
            "spectre": calculer_spectre(),
            "config": CONFIG,
            "infra": etat_infra,
        })


# ============================================================
# Routes API - Configuration à distance
# (l'ESP32 interroge GET /api/config périodiquement pour se synchroniser)
# ============================================================
@app.route("/api/config", methods=["GET"])
def obtenir_config():
    return jsonify(CONFIG)


@app.route("/api/config", methods=["POST"])
def modifier_config():
    data = request.get_json(force=True)
    with lock:
        if "filtre" in data and data["filtre"] in ("FIR", "PASSE_HAUT", "ADAPTATIF"):
            CONFIG["filtre"] = data["filtre"]
        if "seuil_evenement" in data:
            CONFIG["seuil_evenement"] = float(data["seuil_evenement"])
        if "intervalle_ms" in data:
            CONFIG["intervalle_ms"] = int(data["intervalle_ms"])
    socketio.emit("config_maj", CONFIG)
    return jsonify({"status": "ok", "config": CONFIG})


@app.route("/api/reset", methods=["POST"])
def reinitialiser():
    with lock:
        donnees.clear()
        evenements.clear()
        horodatages_reception.clear()
    socketio.emit("reinitialisation")
    return jsonify({"status": "ok"})


# ============================================================
# Simulation (sans matériel ESP32) - injection progressive en arrière-plan
# ============================================================
def boucle_simulation():
    global simulation_en_cours
    signal_tp = [12, 15, 18, 22, 30, 28, 35, 40, 38, 45, 50, 48, 55, 60]
    i = 0
    rssi_simule = -55
    debut = time.time()
    while simulation_en_cours:
        brut = signal_tp[i % len(signal_tp)] + np.random.uniform(-1.5, 1.5)
        rssi_simule = max(-90, min(-40, rssi_simule + np.random.randint(-2, 3)))
        traiter_nouvel_echantillon(
            brut=brut,
            rssi=rssi_simule,
            uptime_esp32_s=round(time.time() - debut, 1),
            source="simulation",
        )
        i += 1
        time.sleep(max(CONFIG["intervalle_ms"], 100) / 1000)


@app.route("/api/simuler/demarrer", methods=["POST"])
def demarrer_simulation():
    global simulation_en_cours
    if not simulation_en_cours:
        simulation_en_cours = True
        socketio.start_background_task(boucle_simulation)
    return jsonify({"status": "ok", "simulation": "démarrée"})


@app.route("/api/simuler/arreter", methods=["POST"])
def arreter_simulation():
    global simulation_en_cours
    simulation_en_cours = False
    return jsonify({"status": "ok", "simulation": "arrêtée"})


# ============================================================
# Page web
# ============================================================
@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True, use_reloader=False, allow_unsafe_werkzeug=True)

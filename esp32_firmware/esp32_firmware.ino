/*
 * TP Traitement Numérique du Signal - Partie E (v2)
 * Implémentation embarquée sur ESP32
 * ------------------------------------------------------------
 * - Acquisition du signal analogique (capteur biomédical/industriel)
 * - Filtrage numérique commutable à distance : FIR / Passe-haut / Adaptatif
 * - Détection d'événements avec seuil réglable à distance
 * - Transmission WiFi (JSON) incluant RSSI et uptime
 * - Synchronisation périodique de la configuration depuis le serveur Flask
 *   (filtre actif, seuil de détection, intervalle d'échantillonnage)
 * ------------------------------------------------------------
 * Bibliothèques nécessaires :
 *   - WiFi.h        (native ESP32)
 *   - HTTPClient.h  (native ESP32)
 *   - ArduinoJson   (v6.x, via Library Manager)
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// ============================================================
// Configuration réseau
// ============================================================
const char* WIFI_SSID     = "10 virus detectes";
const char* WIFI_PASSWORD = "6775212952";
const char* URL_DONNEES   = "http://192.168.0.161:5000/api/data";
const char* URL_CONFIG    = "http://192.168.0.161:5000/api/config";

// ============================================================
// Configuration matérielle
// ============================================================
const int PIN_CAPTEUR = 34;  // GPIO34 (ADC1_CH6)

// ============================================================
// Configuration dynamique (synchronisée depuis le serveur Flask)
// ============================================================
enum TypeFiltre { FIR, PASSE_HAUT, ADAPTATIF };
TypeFiltre filtreActif = FIR;
float seuilEvenement = 8.0;
unsigned long intervalleEchantillonnageMs = 500;

const unsigned long PERIODE_SYNC_CONFIG_MS = 5000; // resynchronisation toutes les 5 s
unsigned long dernierSyncConfig = 0;
unsigned long dernierEnvoi = 0;
unsigned long compteurEchantillon = 0;

// ============================================================
// Buffers pour les filtres
// ============================================================
const int TAILLE_MAX_BUFFER = 8;
float bufferBrut[TAILLE_MAX_BUFFER] = {0};
int indexBuffer = 0;
int nbValeursBuffer = 0;

float dernierEchantillon = 0;
bool premierEchantillon = true;

// ------------------------------------------------------------
// Ajoute un échantillon au buffer circulaire
// ------------------------------------------------------------
void ajouterAuBuffer(float valeur) {
  bufferBrut[indexBuffer] = valeur;
  indexBuffer = (indexBuffer + 1) % TAILLE_MAX_BUFFER;
  if (nbValeursBuffer < TAILLE_MAX_BUFFER) nbValeursBuffer++;
}

// ------------------------------------------------------------
// Récupère les `n` derniers échantillons dans l'ordre chronologique
// ------------------------------------------------------------
void obtenirDerniers(int n, float* sortie) {
  n = min(n, nbValeursBuffer);
  for (int i = 0; i < n; i++) {
    int idx = (indexBuffer - n + i + TAILLE_MAX_BUFFER) % TAILLE_MAX_BUFFER;
    sortie[i] = bufferBrut[idx];
  }
}

// ------------------------------------------------------------
// Filtre FIR - Moyenne glissante d'ordre 4
// ------------------------------------------------------------
float appliquerFIR() {
  float derniers[4] = {0, 0, 0, 0};
  obtenirDerniers(4, derniers);
  return (derniers[0] + derniers[1] + derniers[2] + derniers[3]) / 4.0;
}

// ------------------------------------------------------------
// Filtre passe-haut - y[n] = x[n] - x[n-1]
// ------------------------------------------------------------
float appliquerPasseHaut() {
  if (nbValeursBuffer < 2) return bufferBrut[(indexBuffer - 1 + TAILLE_MAX_BUFFER) % TAILLE_MAX_BUFFER];
  float derniers[2] = {0, 0};
  obtenirDerniers(2, derniers);
  return derniers[1] - derniers[0];
}

// ------------------------------------------------------------
// Filtre adaptatif - ordre de la moyenne ajusté selon la variance locale
// ------------------------------------------------------------
float appliquerAdaptatif() {
  float derniers[6] = {0};
  int n = min(6, nbValeursBuffer);
  obtenirDerniers(n, derniers);

  float somme = 0, sommeCarres = 0;
  for (int i = 0; i < n; i++) { somme += derniers[i]; sommeCarres += derniers[i] * derniers[i]; }
  float moyenne = (n > 0) ? somme / n : 0;
  float variance = (n > 0) ? (sommeCarres / n - moyenne * moyenne) : 0;

  int ordre = (variance > 25) ? 6 : ((variance > 8) ? 4 : 2);
  ordre = min(ordre, nbValeursBuffer);
  if (ordre == 0) return 0;

  float fenetre[8] = {0};
  obtenirDerniers(ordre, fenetre);
  float s = 0;
  for (int i = 0; i < ordre; i++) s += fenetre[i];
  return s / ordre;
}

// ------------------------------------------------------------
// Applique le filtre actuellement sélectionné
// ------------------------------------------------------------
float appliquerFiltreActif() {
  switch (filtreActif) {
    case PASSE_HAUT: return appliquerPasseHaut();
    case ADAPTATIF:  return appliquerAdaptatif();
    default:         return appliquerFIR();
  }
}

// ------------------------------------------------------------
// Détection d'événement (variation brutale = perturbation)
// ------------------------------------------------------------
bool detecterEvenement(float echantillonBrut) {
  if (premierEchantillon) { dernierEchantillon = echantillonBrut; premierEchantillon = false; return false; }
  float variation = fabs(echantillonBrut - dernierEchantillon);
  dernierEchantillon = echantillonBrut;
  return (variation > seuilEvenement);
}

// ------------------------------------------------------------
// Synchronisation de la configuration depuis le serveur Flask
// (permet de changer le filtre, le seuil et la fréquence sans reflasher)
// ------------------------------------------------------------
void synchroniserConfig() {
  if (WiFi.status() != WL_CONNECTED) return;

  HTTPClient http;
  http.begin(URL_CONFIG);
  int code = http.GET();

  if (code == 200) {
    StaticJsonDocument<256> doc;
    DeserializationError err = deserializeJson(doc, http.getString());
    if (!err) {
      const char* filtreTexte = doc["filtre"];
      if (strcmp(filtreTexte, "PASSE_HAUT") == 0) filtreActif = PASSE_HAUT;
      else if (strcmp(filtreTexte, "ADAPTATIF") == 0) filtreActif = ADAPTATIF;
      else filtreActif = FIR;

      seuilEvenement = doc["seuil_evenement"] | seuilEvenement;
      intervalleEchantillonnageMs = doc["intervalle_ms"] | intervalleEchantillonnageMs;

      Serial.printf("Config synchronisée : filtre=%s, seuil=%.1f, intervalle=%lums\n",
                    filtreTexte, seuilEvenement, intervalleEchantillonnageMs);
    }
  }
  http.end();
}

// ------------------------------------------------------------
// Envoi des données via UART (debug local, toujours actif)
// ------------------------------------------------------------
void envoyerUART(unsigned long n, float brut, float filtre, bool evenement) {
  Serial.print("n=");        Serial.print(n);
  Serial.print(",brut=");    Serial.print(brut, 2);
  Serial.print(",filtre=");  Serial.print(filtre, 2);
  Serial.print(",event=");   Serial.println(evenement ? "1" : "0");
}

// ------------------------------------------------------------
// Envoi des données via WiFi (HTTP POST JSON), incluant RSSI et uptime
// ------------------------------------------------------------
void envoyerWiFi(float brut) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi non connecté - envoi ignoré");
    return;
  }

  HTTPClient http;
  http.begin(URL_DONNEES);
  http.addHeader("Content-Type", "application/json");

  StaticJsonDocument<256> doc;
  doc["brut"] = brut;
  doc["rssi"] = WiFi.RSSI();               // niveau du signal WiFi (dBm)
  doc["uptime_s"] = millis() / 1000.0;     // temps depuis le démarrage

  String payload;
  serializeJson(doc, payload);

  int codeReponse = http.POST(payload);
  if (codeReponse <= 0) {
    Serial.printf("Erreur envoi HTTP : %s\n", http.errorToString(codeReponse).c_str());
  }
  http.end();
}

// ------------------------------------------------------------
// Connexion WiFi
// ------------------------------------------------------------
void connecterWiFi() {
  Serial.print("Connexion au WiFi");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  int tentatives = 0;
  while (WiFi.status() != WL_CONNECTED && tentatives < 30) {
    delay(500);
    Serial.print(".");
    tentatives++;
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi connecté, IP : " + WiFi.localIP().toString());
  } else {
    Serial.println("\nÉchec de connexion WiFi (fonctionnement en mode UART seul)");
  }
}

// ------------------------------------------------------------
// SETUP
// ------------------------------------------------------------
void setup() {
  Serial.begin(115200);
  analogReadResolution(12); // ESP32 : ADC 12 bits (0-4095)
  connecterWiFi();
  synchroniserConfig();
  Serial.println("Système d'acquisition démarré.");
}

// ------------------------------------------------------------
// LOOP - Acquisition temps réel
// ------------------------------------------------------------
void loop() {
  unsigned long maintenant = millis();

  // Resynchronisation périodique de la configuration à distance
  if (maintenant - dernierSyncConfig >= PERIODE_SYNC_CONFIG_MS) {
    dernierSyncConfig = maintenant;
    synchroniserConfig();
  }

  if (maintenant - dernierEnvoi >= intervalleEchantillonnageMs) {
    dernierEnvoi = maintenant;

    // 1) Acquisition du signal analogique
    int lectureBrute = analogRead(PIN_CAPTEUR);
    float valeurBrute = lectureBrute * (60.0 / 4095.0); // mise à l'échelle 0-60 (cf. plage du TP)
    ajouterAuBuffer(valeurBrute);

    // 2) Filtrage temps réel (selon le mode configuré à distance)
    float valeurFiltree = appliquerFiltreActif();

    // 3) Détection d'événement (perturbation impulsionnelle)
    bool evenement = detecterEvenement(valeurBrute);

    // 4) Transmission des données (UART toujours actif + WiFi si disponible)
    envoyerUART(compteurEchantillon, valeurBrute, valeurFiltree, evenement);
    envoyerWiFi(valeurBrute); // le serveur calcule aussi le filtre/l'événement côté Flask

    compteurEchantillon++;
  }
}


# 📄 README – Système de Détection de Présence avec ESP32 et Flask

Ce projet comprend **4 serveurs Flask** permettant de détecter la présence humaine dans une image transmise par un ESP32-CAM, via différentes méthodes : OpenCV, YOLOv8, YOLOv3 avec SSIM, et YOLOv8 avec SSIM.
SSIM = *Structural Similarity Index*

J’ai également fourni un test d’utilisation de MediaPipe pour la détection de présence, via Docker, en raison d'erreurs lors du téléchargement de certains paquets nécessaires.

---

## 📁 Organisation des Serveurs

### Dossiers d’upload

Chaque serveur utilise un dossier distinct pour stocker les images reçues :

* `uploads_cv2`
* `uploads_yolov8`
* `uploads_yolov3_ssim`
* `uploads_yolov8_ssim`

Une **image temporaire** est d’abord enregistrée, puis renommée si la détection réussit, selon le format suivant :

```
capture_methode_YYYYMMDD_HHMMSS_presence_0ou1.jpg
```

L’image de référence utilisée pour la comparaison dans les méthodes SSIM est également stockée dans chaque dossier sous le nom :

```
reference_image.jpg
```

---

## 🧠 Méthodes de Détection et Serveurs

### 1. `cv2` – port 5001

**Détection de présence basée sur la détection de visages avec OpenCV**

* L’image reçue est convertie en niveaux de gris.
* La fonction `face_cascade.detectMultiScale()` utilise un classificateur Haar cascade préentraîné pour détecter les visages.
* Paramètres importants :

  * `scaleFactor=1.1` : réduit l’image progressivement pour détecter les visages à différentes tailles.
  * `minNeighbors=5` : réduit les fausses détections.
  * `minSize=(30, 30)` : ignore les objets plus petits.
* **Interprétation** : si au moins un visage est détecté, la présence est validée (`presence=1`), sinon absence (`presence=0`).
* L’image est renommée selon la détection et enregistrée dans `uploads_cv2`.
* Pas de mécanisme de secours (fallback).

---

### 2. `yolov8` – port 5002

**Détection d’objets basée sur le modèle YOLOv8**

* Utilise le modèle `yolov8n.pt` pour détecter des objets dans l’image.
* Recherche uniquement la classe "person" (classe 0 dans COCO).
* Si au moins une personne est détectée, `presence = 1`, sinon `0`.
* Image enregistrée dans `uploads_yolov8`.
* Pas de fallback.

---

### 3. `yolov3 + SSIM` – port 5003

**Détection hybride combinant YOLOv3 et SSIM (Structural Similarity Index)**

* Détection de personnes avec YOLOv3 (confiance minimale : 0.3, ligne 122).
* Si personnes détectées → `presence = 1`.
* Sinon, fallback : comparaison via SSIM avec l’image de référence.
* SSIM varie de 0 (différentes) à 1 (identiques). Si `SSIM < 0.90`, alors `presence = 1`, sinon `0`.
* Réduit les faux négatifs.
* Images renommées et enregistrées dans `uploads_yolov3_ssim`.

---

### 4. `yolov8 + SSIM` – port 5004

**Détection hybride combinant YOLOv8 et SSIM**

* Même principe que `yolov8`, avec fallback SSIM si aucune personne n’est détectée.
* Seuil de confiance : 0.3
* Seuil SSIM : 0.90
* Images enregistrées dans `uploads_yolov8_ssim`

---

### 5. `Mediapipe` (pas inclus dans l'interface des résultats de test) – port 5012

**Exécuté avec Docker**

1. Télécharger Docker Desktop :
   [https://docs.docker.com/desktop/install/windows-install/](https://docs.docker.com/desktop/install/windows-install/)

2. Vérifier que Docker est installé :

   docker --version


3. Démarrer Docker Desktop

4. Dans un terminal constuire l'image et exécuter le conteneur :

   
   docker build -t monimage-flask .
   docker run -d -p 5012:5012 --name moncontainer-flask monimage-flask:latest
   

---

### Interface graphique – port 5010

Une interface web permet de visualiser les résultats des détections.

---

## 🗃️ Base de Données

* Fichier : `presence.db`
* Stocke les logs de détection pour chaque image.
* Colonnes :

  * `filename`
  * `presence` (0 ou 1)
  * `fallback_used` (0 = non, 1 = oui)
  * `method` (nom de la méthode)
  * `timestamp` (horodatage)
  * `try_id` (identifiant unique)

---

## 🛠️ Scripts Utiles

### `database_setup.py`

* Initialise la base de données et crée la table `presence_logs`
* À exécuter une seule fois au début
* Peut aussi être utilisé pour réinitialiser la base ou supprimer des lignes

### `clean_directories.py`

* Supprime toutes les images des dossiers `uploads_*` sauf `reference_image.jpg`

---

## 📤 Envoi d’une Image

L’image est envoyée au serveur via une requête HTTP `POST` :


POST /uploads
Form-Data: imageFile=@image.jpg


L’ESP32 ou des outils comme `curl`, Postman, etc., peuvent être utilisés.

---

## 📦 Dépendances et Installation

Paquets nécessaires :

* `Flask`
* `OpenCV (cv2)`
* `NumPy`
* `sqlite3` (standard Python)
* `ultralytics` (pour YOLOv8)
* `torch` (PyTorch)
* `scikit-image` (pour SSIM)

Installer avec :

```bash
pip install -r paquets.txt
```

---

## ▶️ Utilisation

1. **Télécharger les paquets nécessaires**

2. **Dans l’IDE Arduino** :

   * Sélectionner la carte **AI Thinker ESP32-CAM**
   * Sélectionner le port série
   * Télécharger le code `test_servers.ino` sur l’ESP32-CAM

3. **Dans `test_servers.ino`** :

   * Modifier les lignes 7 et 8 : SSID et mot de passe du Wi-Fi
   * Connecter l'ordinateur qui héberge les serveurs au même réseau Wi-Fi
   * Modifier l’adresse IP ligne 10 (celle des serverus Flask qui partagent la meme ip)
   * Si besoin, modifier la liste de ports ligne 13 et la condition ligne 118 pour ne tester que certains serveurs (i < nb+1)

4. **Lancer le script database_setup.py ainsi que les serveurs** :

   * Exemple :

    
     python server_cv2.py
     python server_yolov8.py
    

5. **Lancer le serveur d’interface graphique** (port 5010)

---

### 📝 Remarques

* Le serveur utilisant MediaPipe consomme plus de ressources CPU/GPU.
* Les instructions pour lancer ce serveur sont dans la section "Méthodes de Détection et Serveurs".

---


# Importation des bibliothèques nécessaires
from flask import Flask, request
from datetime import datetime
import os
import cv2
import numpy as np
import sqlite3
from ultralytics import YOLO  # Bibliothèque pour le modèle YOLOv8

# Création de l'application Flask
app = Flask(__name__)

# Chemins des dossiers et fichiers utilisés
UPLOAD_FOLDER = 'uploads_yolov8'          # Dossier pour enregistrer les images
STATUS_FILE = os.path.join(UPLOAD_FOLDER, 'status.txt')   # Fichier texte indiquant le statut de détection
DATABASE_FILE = 'presence.db'             # Base de données SQLite



# Création du dossier de stockage s’il n’existe pas
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Page d'accueil
@app.route('/')
def index():
    return "<h2>ESP32 Image Upload Server with YOLOv8 Presence Detection</h2>", 200

# Route pour la réception des images
@app.route('/uploads', methods=['POST'])
def upload_file():
    # Vérifie que le fichier image est bien dans la requête
    if 'imageFile' not in request.files:
        return "No file part", 400
    
    file = request.files['imageFile']
    if file.filename == '':
        return "No selected file", 400

    # Nom et chemin temporaire du fichier
    temp_filename = 'temp_image.jpg'
    temp_filepath = os.path.join(UPLOAD_FOLDER, temp_filename)
    
    try:
        # Sauvegarde de l'image temporaire
        file.save(temp_filepath)
        print(f"[INFO] Temp image saved as {temp_filename}")

        # Appel de la fonction de détection de présence
        presence_detected = detect_presence(temp_filepath)

        # Création du nom de fichier final avec horodatage et statut
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        presence_flag = 1 if presence_detected else 0
        final_filename = f"capture_YOLOv8_{timestamp}_presence_{presence_flag}.jpg"
        final_filepath = os.path.join(UPLOAD_FOLDER, final_filename)

        # Renommage du fichier
        os.rename(temp_filepath, final_filepath)
        print(f"[INFO] Renamed image to {final_filename}")

        # Écriture du statut dans le fichier texte
        with open(STATUS_FILE, 'w') as f:
            f.write(str(presence_flag))

        # Sauvegarde des informations dans la base de données
        save_to_db(final_filename, presence_flag, fallback_used=0, method='YOLOv8')

        # Message de retour
        result_msg = "Presence Detected" if presence_detected else "No Presence Detected"
        print(f"[INFO] {result_msg}")
        
        return result_msg, 200

    except Exception as e:
        print(f"[ERROR] {e}")
        return "Error saving image", 500


# Chargement du modèle YOLOv8 (version "n" = nano pour les petits appareils comme Raspberry Pi)
model = YOLO("yolov8n.pt")

# Fonction de détection de présence (personne uniquement)
def detect_presence(image_path):
    results = model(image_path)
    for result in results:
        for cls in result.boxes.cls:  # Récupère les classes détectées
            if int(cls) == 0:         # Classe 0 = "person" dans COCO
                print("[INFO] Person detected by YOLOv8")
                return True
    print("[INFO] No person detected by YOLOv8")
    return False

# Récupère l'identifiant de tentative suivant en se basant uniquement sur les méthodes YOLO8
def get_next_try_id():
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(try_id) FROM presence_logs WHERE method = 'YOLOv8'")
    result = cursor.fetchone()[0]
    conn.close()
    print(f"[INFO] Initial try_id: {result + 1 if result is not None else 1}")
    return 1 if result is None else result + 1


# Fonction d’enregistrement dans la base de données
def save_to_db(filename, presence, fallback_used, method):
    try_id = get_next_try_id()
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c.execute('''
        INSERT INTO presence_logs (filename, presence, fallback_used, method, timestamp, try_id)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (filename, presence, fallback_used, method, timestamp, try_id))
    conn.commit()
    conn.close()
    print(f"[INFO] Detection result saved to database for file {filename}")

# Lancement de l'application Flask
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002)

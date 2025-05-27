from flask import Flask, request
from datetime import datetime
import os
import cv2
import sqlite3

# Configuration initiale
app = Flask(__name__)
UPLOAD_FOLDER = 'uploads_cv2'
DATABASE_FILE = 'presence.db'
STATUS_FILE = os.path.join(UPLOAD_FOLDER, 'status.txt')





# Création du dossier d'uploads s'il n'existe pas
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Chargement du classificateur Haar pour la détection de visages
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml') #fourni par OpenCV

@app.route('/')
def index():
    return "<h2>ESP32 Image Upload Server with OpenCV Presence Detection</h2>", 200

@app.route('/uploads', methods=['POST'])
def upload_file():
    """Traite l'image envoyée par POST et détecte la présence de visages."""
    if 'imageFile' not in request.files:
        return "No file part", 400

    file = request.files['imageFile']
    if file.filename == '':
        return "No selected file", 400

    # Sauvegarde temporaire du fichier
    temp_filepath = os.path.join(UPLOAD_FOLDER, 'temp_upload.jpg')
    try:
        file.save(temp_filepath)

        # Détection de présence
        presence_detected = detect_presence(temp_filepath)
        presence_flag = 1 if presence_detected else 0

        # Génération du nom de fichier final
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"capture_CV2_{timestamp}_presence_{presence_flag}.jpg"
        final_path = os.path.join(UPLOAD_FOLDER, filename)
        os.rename(temp_filepath, final_path)

        # Sauvegarde du statut et enregistrement en base de données
        write_status(presence_detected)
        save_to_db(filename, presence_flag, fallback_used=0, method='cv2')

        return "Presence Detected" if presence_detected else "No Presence Detected", 200

    except Exception as e:
        print(f"[ERROR] {e}")
        return "Error saving image", 500

def detect_presence(image_path):
    """Utilise OpenCV pour détecter des visages sur une image."""
    img = cv2.imread(image_path)
    if img is None:
        print("[ERROR] Failed to load image.")
        return False

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

    if len(faces) > 0:  # si au moins un visage est détecté
        print(f"[INFO] {len(faces)} face(s) detected.")
        return True
    else:
        print("[INFO] No faces detected.")
        return False

def write_status(presence_detected):
    """Écrit le statut de présence (1 ou 0) dans un fichier texte."""
    try:
        with open(STATUS_FILE, 'w') as f:
            f.write('1' if presence_detected else '0')
        print(f"[INFO] Status written: {'1' if presence_detected else '0'}")
    except Exception as e:
        print(f"[ERROR] Failed to write status: {e}")



# Récupère l'identifiant de tentative suivant en se basant uniquement sur les méthodes cv2
def get_next_try_id():
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(try_id) FROM presence_logs WHERE method = 'cv2'")
    result = cursor.fetchone()[0]
    conn.close()
    print(f"[INFO] Initial try_id: {result + 1 if result is not None else 1}")
    return 1 if result is None else result + 1

def save_to_db(filename, presence, fallback_used, method):
    try_id = get_next_try_id()
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    cursor.execute('''
        INSERT INTO presence_logs (filename, presence, fallback_used, method, timestamp, try_id)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (filename, presence, fallback_used, method, timestamp, try_id))

    conn.commit()
    conn.close()
    print(f"[INFO] Detection result saved to database for file {filename}")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)

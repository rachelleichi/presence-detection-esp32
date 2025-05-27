from flask import Flask, request
from datetime import datetime
import os
import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim
import sqlite3

app = Flask(__name__)

# Répertoires pour stocker les images
UPLOAD_FOLDER = 'uploads_yolov3_ssim'
FALLBACK_FOLDER = os.path.join(UPLOAD_FOLDER, 'fallback_images')
STATUS_FILE = os.path.join(UPLOAD_FOLDER, 'status.txt')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(FALLBACK_FOLDER, exist_ok=True)

# Configuration YOLOv3
YOLO_PATH = 'yolo'
REFERENCE_IMAGE_PATH = os.path.join(UPLOAD_FOLDER, 'reference_image.jpg')
DATABASE_FILE = 'presence.db'

# Chargement du modèle YOLOv3
net = cv2.dnn.readNetFromDarknet(f"{YOLO_PATH}/yolov3.cfg", f"{YOLO_PATH}/yolov3.weights")
layer_names = net.getLayerNames()
output_layers = [layer_names[i - 1] for i in net.getUnconnectedOutLayers().flatten()]

# Chargement des classes COCO (par ex. personne, voiture, etc.)
with open(f"{YOLO_PATH}/coco.names", 'r') as f:
    classes = [line.strip() for line in f.readlines()]

# Page d'accueil simple
@app.route('/')
def index():
    return "<h2>ESP32 YOLOv3-based Presence Detection Server</h2>", 200

# Route pour recevoir des images
@app.route('/uploads', methods=['POST'])
def upload_file():
    if 'imageFile' not in request.files:
        return "No file part", 400

    file = request.files['imageFile']
    if file.filename == '':
        return "No selected file", 400

    try:
        # Lecture de l'image
        image = cv2.imdecode(np.frombuffer(file.read(), np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            return "Invalid image", 400

        temp_filename = 'temp_image.jpg'
        temp_filepath = os.path.join(UPLOAD_FOLDER, temp_filename)
        cv2.imwrite(temp_filepath, image)

        # Détection de présence avec YOLO
        presence = detect_person_yolo(temp_filepath)
        fallback_used = 0
        method = 'YOLO3+SSIM'
        final_filepath = None

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        db_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        presence_flag = 1 if presence else 0

        if presence:
            # Sauvegarde si présence détectée
            final_filename = f"capture_YOLO3+SSIM_{timestamp}_presence_{presence_flag}.jpg"
            final_filepath = os.path.join(UPLOAD_FOLDER, final_filename)
            os.rename(temp_filepath, final_filepath)

        else:
            # Fallback avec SSIM
            if detect_change_by_comparison(temp_filepath):
                presence = True
                fallback_used = 1
                method = 'Fallback (YOLO3+SSIM)'
                presence_flag = 1
                final_filename = f"fallback_YOLO3_{timestamp}_presence_1.jpg"
                final_filepath = os.path.join(FALLBACK_FOLDER, final_filename)
                os.rename(temp_filepath, final_filepath)
            else:
                # Aucun changement détecté
                final_filename = f"capture_YOLO3+SSIM_{timestamp}_presence_0.jpg"
                os.remove(temp_filepath)
                final_filepath = None  # Image non sauvegardée

                # Log en base
                log_presence_to_db(
                    filename=final_filename,
                    presence=0,
                    fallback_used=0,
                    method=method,
                    timestamp=db_timestamp
                )

        # Écriture du statut de présence
        with open(STATUS_FILE, 'w') as f:
            f.write(str(presence_flag))
        print(f"[INFO] Presence status: {presence_flag}")

        # Log en base si image sauvegardée
        if final_filepath:
            log_presence_to_db(
                filename=final_filename,
                presence=presence_flag,
                fallback_used=fallback_used,
                method=method,
                timestamp=db_timestamp
            )

        return "Presence Detected" if presence else "No Presence Detected", 200

    except Exception as e:
        print(f"[ERROR] {e}")
        return "Server error", 500

# ---------- Fonctions de détection ----------

# Détection de personnes avec YOLO
def detect_person_yolo(image_path, confidence_threshold=0.3):  # seuil par défaut est 0.3
    img = cv2.imread(image_path)
    if img is None:
        print("[ERROR] Cannot read image for YOLO.")
        return False

    height, width = img.shape[:2]
    blob = cv2.dnn.blobFromImage(img, 1 / 255, (416, 416), swapRB=True, crop=False)
    net.setInput(blob)
    outputs = net.forward(output_layers)

    for detection in outputs:
        for obj in detection:
            scores = obj[5:]
            class_id = np.argmax(scores)
            confidence = scores[class_id]
            if confidence > confidence_threshold and classes[class_id] == "person":
                print(f"[INFO] YOLO: Person detected (confidence: {confidence:.2f})")
                return True

    print("[INFO] YOLO: No person detected.")
    return False

# Comparaison avec l'image de référence (SSIM)
def detect_change_by_comparison(image_path, threshold=0.9): # seuil par défaut est 0.9
    current_img = cv2.imread(image_path)
    if current_img is None:
        print("[ERROR] Cannot read current image.")
        return False

    if not os.path.exists(REFERENCE_IMAGE_PATH):
        cv2.imwrite(REFERENCE_IMAGE_PATH, current_img)
        print("[INFO] Reference image saved.")
        return False

    reference_img = cv2.imread(REFERENCE_IMAGE_PATH)
    if reference_img is None:
        return False
    # Redimensionner l'image courante pour qu'elle corresponde à la taille de l'image de référence
    resized = cv2.resize(current_img, (reference_img.shape[1], reference_img.shape[0]))
    # Convertir les images en niveaux de gris pour le calcul SSIM
    gray_current = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    gray_reference = cv2.cvtColor(reference_img, cv2.COLOR_BGR2GRAY)

    score, _ = ssim(gray_reference, gray_current, full=True)
    print(f"[INFO] SSIM score: {score:.4f}")  # afficher le score SSIM
    return score < threshold


# Récupère l'identifiant de tentative suivant en se basant uniquement sur les méthodes YOLO3+SSIM
def get_next_try_id():
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT MAX(try_id) FROM presence_logs
        WHERE method IN ('YOLO3+SSIM', 'Fallback (YOLO3+SSIM)')
    """)
    result = cursor.fetchone()[0]
    conn.close()
    print(f"[INFO] Initial try_id: {result + 1 if result is not None else 1}")
    return 1 if result is None else result + 1

# Enregistre les logs de présence dans la base de données
def log_presence_to_db(filename, presence, fallback_used, method, timestamp):
    try_id = get_next_try_id()
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO presence_logs (filename, presence, fallback_used, method, timestamp, try_id)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (filename, presence, fallback_used, method, timestamp, try_id))
        conn.commit()
        conn.close()
        print(f"[INFO] Logged to DB: {filename} | presence: {presence} | method: {method}")
    except Exception as e:
        print(f"[ERROR] DB log failed: {e}")

# Lancement du serveur Flask
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5003)

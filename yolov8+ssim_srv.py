# Importation des bibliothèques nécessaires
from flask import Flask, request  # Pour créer le serveur web
from datetime import datetime  # Pour obtenir la date et l'heure actuelle
import os  # Pour gérer les fichiers et les dossiers
import cv2  # Pour le traitement d'image
import sqlite3  # Pour interagir avec une base de données SQLite
from skimage.metrics import structural_similarity as ssim  # Pour comparer des images
from ultralytics import YOLO  # Pour la détection d'objet avec YOLOv8

# Création de l'application Flask
app = Flask(__name__)

# Définition des chemins
UPLOAD_FOLDER = 'uploads_yolov8_ssim'
FALLBACK_FOLDER = os.path.join(UPLOAD_FOLDER, 'fallback_images')
REFERENCE_IMAGE_PATH = os.path.join(UPLOAD_FOLDER, 'reference_image.jpg')
DB_PATH = 'presence.db'
STATUS_FILE_PATH = os.path.join(UPLOAD_FOLDER, 'status.txt')

# Création des dossiers nécessaires s'ils n'existent pas
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
if not os.path.exists(FALLBACK_FOLDER):
    os.makedirs(FALLBACK_FOLDER)

# Chargement du modèle YOLOv8
model = YOLO('yolov8n.pt')

# Page d'accueil du serveur
@app.route('/')
def index():
    return "<h2>ESP32 YOLOv8-based Presence Detection Server with DB and File Logging</h2>", 200

# Route qui gère la réception des images
@app.route('/uploads', methods=['POST'])
def upload_file():
    if 'imageFile' not in request.files:
        return "No file part", 400

    file = request.files['imageFile']
    if file.filename == '':
        return "No selected file", 400

    temp_filename = 'temp_image.jpg'
    temp_filepath = os.path.join(UPLOAD_FOLDER, temp_filename)

    try:
        file.save(temp_filepath)
        print(f"[INFO] Image temporarily saved as {temp_filename}")

        # Détection de présence avec YOLO
        presence = detect_person_yolov8(temp_filepath)
        method = "YOLO8+SSIM"
        fallback_used = 0

        # Si YOLO échoue, utiliser la méthode de secours (comparaison d'image)
        if not presence:
            if detect_change_by_comparison(temp_filepath):
                print("[WARNING] YOLO missed it. Image comparison detected presence.")
                presence = True
                fallback_used = 1
                method = "Fallback (YOLO8+SSIM)"

        presence_flag = 1 if presence else 0
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Traitement de l'image selon le résultat de la détection
        if presence:
            if fallback_used:
                fallback_filename = f"fallback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                fallback_filepath = os.path.join(FALLBACK_FOLDER, fallback_filename)
                img = cv2.imread(temp_filepath)
                cv2.imwrite(fallback_filepath, img)
                os.remove(temp_filepath)
                image_name = fallback_filename
                print(f"[INFO] Fallback image saved as {fallback_filename}")
            else:
                image_name = f"capture_YOLO8+SSIM_{datetime.now().strftime('%Y%m%d_%H%M%S')}_presence_1.jpg"
                image_path = os.path.join(UPLOAD_FOLDER, image_name)
                os.rename(temp_filepath, image_path)
                print(f"[INFO] Image saved as {image_name}")
        else:
            image_name = f"capture_YOLO8+SSIM_{datetime.now().strftime('%Y%m%d_%H%M%S')}_presence_0.jpg"
            image_path = os.path.join(UPLOAD_FOLDER, image_name)
            os.rename(temp_filepath, image_path)
            print(f"[INFO] Image saved as {image_name} for no presence.")

        # Sauvegarde de l'état de présence dans un fichier
        save_to_file(presence_flag)

        # Sauvegarde des résultats dans la base de données
        save_to_database(
            filename=image_name,
            presence=presence_flag,
            fallback_used=fallback_used,
            method=method,
            timestamp=timestamp
        )

        return ("Presence Detected" if presence else "No Presence Detected"), 200

    except Exception as e:
        print(f"[ERROR] {e}")
        return "Error processing image", 500


# Détection de personne avec YOLOv8
def detect_person_yolov8(image_path, confidence_threshold=0.3):
    results = model(image_path)
    for result in results:
        for box in result.boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            class_name = model.names[cls_id]

            if conf > confidence_threshold and class_name == 'person':
                print(f"[INFO] Person detected by YOLOv8 with confidence: {conf:.2f}")
                return True

    print("[INFO] No person detected by YOLOv8.")
    return False


# Détection par comparaison avec une image de référence (SSIM)
def detect_change_by_comparison(image_path, threshold=0.9):
    current_img = cv2.imread(image_path)
    if current_img is None:
        print("[ERROR] Could not read current image.")
        return False

    if not os.path.exists(REFERENCE_IMAGE_PATH):
        print("[INFO] Reference image not found. Saving current image as reference.")
        cv2.imwrite(REFERENCE_IMAGE_PATH, current_img)
        return False

    reference_img = cv2.imread(REFERENCE_IMAGE_PATH)
    # Redimensionner l'image courante pour qu'elle corresponde à la taille de l'image de référence
    current_img_resized = cv2.resize(current_img, (reference_img.shape[1], reference_img.shape[0]))

    gray_current = cv2.cvtColor(current_img_resized, cv2.COLOR_BGR2GRAY)
    gray_reference = cv2.cvtColor(reference_img, cv2.COLOR_BGR2GRAY)

    score, _ = ssim(gray_reference, gray_current, full=True)
    print(f"[INFO] SSIM score: {score:.4f}")

    return score < threshold


# Sauvegarde d'une image fallback (utilisée uniquement si YOLO échoue)
def save_fallback_image(image_path):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    fallback_filename = f"fallback_YOLO8_{timestamp}.jpg"
    fallback_filepath = os.path.join(FALLBACK_FOLDER, fallback_filename)

    img = cv2.imread(image_path)
    cv2.imwrite(fallback_filepath, img)
    print(f"[INFO] Fallback image saved as {fallback_filename}")



# Récupère l'identifiant de tentative suivant en se basant uniquement sur les méthodes YOLO8+SSIM
def get_next_try_id():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT MAX(try_id) FROM presence_logs
        WHERE method IN ('YOLO8+SSIM', 'Fallback (YOLO8+SSIM)')
    """)
    result = cursor.fetchone()[0]
    conn.close()
    print(f"[INFO] Initial try_id: {result + 1 if result is not None else 1}")
    return 1 if result is None else result + 1


# Sauvegarde des informations de détection dans la base de données
def save_to_database(filename, presence, fallback_used, method, timestamp):
    try_id = get_next_try_id()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO presence_logs (filename, presence, fallback_used, method, timestamp, try_id)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (filename, presence, fallback_used, method, timestamp, try_id))
    conn.commit()
    conn.close()
    print(f"[INFO] Logged to DB: {filename}, Presence={presence}, Fallback={fallback_used}, Method={method}, Time={timestamp}")


# Sauvegarde du dernier état de présence dans un fichier texte
def save_to_file(presence):
    with open(STATUS_FILE_PATH, 'w') as file:
        file.write(str(presence))
    print(f"[INFO] Status written to {STATUS_FILE_PATH}: {presence}")


# Lancement du serveur Flask sur toutes les interfaces réseau, port 5000
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
#     app.run(debug=True)
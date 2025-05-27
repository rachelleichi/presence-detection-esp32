from flask import Flask, request, jsonify
import cv2
import numpy as np
import mediapipe as mp
import os
from datetime import datetime

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads_mediapipe'
STATUS_FILE = os.path.join(UPLOAD_FOLDER, 'status.txt')


if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

mp_pose = mp.solutions.pose
pose = mp_pose.Pose(static_image_mode=True, model_complexity=1)
mp_drawing = mp.solutions.drawing_utils

@app.route('/')
def index():
    return "<h2>ESP32-CAM MediaPipe Presence Detection Server</h2>", 200

@app.route('/uploads', methods=['POST'])
def upload_file():
    if 'imageFile' not in request.files:
        return "No file part", 400

    file = request.files['imageFile']
    if file.filename == '':
        return "No selected file", 400

    try:
        # Sauvegarde temporaire
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"capture_{timestamp}.jpg"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        print(f"[INFO] Image saved to {filepath}")

        # Détection de présence
        presence_detected = detect_presence(filepath)

        # Écriture du statut dans le fichier
        with open(STATUS_FILE, 'w') as f:
            f.write('1' if presence_detected else '0')

        result_msg = "Presence Detected" if presence_detected else "No Presence Detected"
        print(f"[INFO] {result_msg}")
        return result_msg, 200

    except Exception as e:
        print(f"[ERROR] {e}")
        return "Error saving image", 500

def detect_presence(image_path):
    try:
        image = cv2.imread(image_path)
        if image is None:
            print("[ERROR] Failed to load image.")
            return False

        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = pose.process(image_rgb)

        if results.pose_landmarks:
            print("[INFO] Person detected by MediaPipe")
            return True
        else:
            print("[INFO] No person detected by MediaPipe")
            return False
    except Exception as e:
        print(f"[ERROR] Exception in detect_presence: {e}")
        return False

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5012, debug=True)

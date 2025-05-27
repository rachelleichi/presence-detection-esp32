import os

# Directories to clean up
directories_to_clean = [
    'uploads_mediapipe',
    'uploads_yolov8_ssim',
    'uploads_yolov8',
    'uploads_cv2',
    'uploads_yolov3_ssim',
]

# Path to the reference image
reference_image_path = 'C:\\Users\\Utilisateur\\Documents\\~Stage2025\\test_server\\uploads\\reference_image.jpg'

def delete_images_in_directory(directory_path):
    """Delete all images in the directory except the reference image."""
    if not os.path.exists(directory_path):
        print(f"[ERROR] Directory {directory_path} does not exist.")
        return
    
    # Walk through the directory
    for root, dirs, files in os.walk(directory_path):  # Use os.walk to also visit subdirectories
        for filename in files:
            file_path = os.path.join(root, filename)

            # Skip the reference image
            if filename == 'reference_image.jpg':
                print(f"[INFO] Skipping {filename}, it's the reference image.")
                continue

            try:
                os.remove(file_path)  # Delete the file
                print(f"[INFO] Deleted {filename} from {root}")
            except Exception as e:
                print(f"[ERROR] Failed to delete {filename}: {e}")

def main():
    # Clean the specified directories
    base_path = 'C:\\Users\\Utilisateur\\Documents\\~Stage2025\\test_server\\'
    for directory in directories_to_clean:
        full_directory_path = os.path.join(base_path, directory)
        delete_images_in_directory(full_directory_path)

if __name__ == '__main__':
    main()

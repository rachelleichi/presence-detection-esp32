FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies (OpenCV & MediaPipe support)
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libglib2.0-dev \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy project files into the container
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port Flask will run on
EXPOSE 5012

# Run the Flask server
CMD ["python", "mediapipe_test.py"]

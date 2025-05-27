#include <Arduino.h>
#include <WiFi.h>
#include "soc/soc.h"
#include "soc/rtc_cntl_reg.h"
#include "esp_camera.h"

const char* ssid = "Test"; 
const char* password = "rachel2025";

String serverIP = "192.168.43.218"; // adresse IP du serveur
String serverPath = "/uploads";     // endpoint serveur

const int ports[] = {5000, 5001, 5002, 5003, 5012}; // Liste des ports

WiFiClient client; 

// CAMERA_MODEL_AI_THINKER
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27

#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

const int timerInterval = 60000;    // 60s
unsigned long previousMillis = 0;

void setup() {
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0); 
  Serial.begin(115200);

  WiFi.mode(WIFI_STA);
  Serial.print("Connecting to ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);  
  while (WiFi.status() != WL_CONNECTED) {
    Serial.print(".");
    delay(500);
  }

  Serial.println();
  Serial.print("ESP32-CAM IP Address: ");
  Serial.println(WiFi.localIP());

  // Init caméra
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;

  if(psramFound()){
    config.frame_size = FRAMESIZE_SVGA;
    config.jpeg_quality = 10;
    config.fb_count = 2;
  } else {
    config.frame_size = FRAMESIZE_CIF;
    config.jpeg_quality = 12;
    config.fb_count = 1;
  }
  
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x", err);
    delay(1000);
    ESP.restart();
  }

  sendImageToAllPorts(); // Envoie au démarrage
}

void loop() {
  unsigned long currentMillis = millis();
  if (currentMillis - previousMillis >= timerInterval) {
    sendImageToAllPorts();
    previousMillis = currentMillis;
  }
}

// Envoie à tous les ports
void sendImageToAllPorts() {
  camera_fb_t * fb = esp_camera_fb_get();
  if (!fb || fb->len == 0) {
    Serial.println("Camera capture failed");
    ESP.restart();
    return;
  }


//modifier selon le nb ports dans i< nb+1 
  for (int i = 0; i < 4; i++) {    
    sendPhotoToServer(fb, ports[i]);
  }

  esp_camera_fb_return(fb); // On libère après envoi à tous
}

// Fonction pour envoyer à un port spécifique
void sendPhotoToServer(camera_fb_t * fb, int port) {
  WiFiClient client;

  Serial.print("Connecting to ");
  Serial.print(serverIP);
  Serial.print(":");
  Serial.println(port);

  if (client.connect(serverIP.c_str(), port)) {
    Serial.println("Connected!");

    String head = "--RandomNerdTutorials\r\nContent-Disposition: form-data; name=\"imageFile\"; filename=\"esp32-cam.jpg\"\r\nContent-Type: image/jpeg\r\n\r\n";
    String tail = "\r\n--RandomNerdTutorials--\r\n";

    uint32_t imageLen = fb->len;
    uint32_t extraLen = head.length() + tail.length();
    uint32_t totalLen = imageLen + extraLen;

    client.println("POST " + serverPath + " HTTP/1.1");
    client.println("Host: " + serverIP);
    client.println("Content-Length: " + String(totalLen));
    client.println("Content-Type: multipart/form-data; boundary=RandomNerdTutorials");
    client.println();
    client.print(head);

    size_t fbLen = fb->len;
    uint8_t *fbBuf = fb->buf;

    for (size_t n = 0; n < fbLen; n += 1024) {
      size_t toSend = (n + 1024 < fbLen) ? 1024 : fbLen - n;
      client.write(fbBuf + n, toSend);
    }

    client.print(tail);

    long timeout = millis() + 10000;
    while (client.connected() && millis() < timeout) {
      while (client.available()) {
        char c = client.read();
        Serial.write(c);
      }
    }
    client.stop();
    Serial.println("Image sent to port " + String(port));
  } else {
    Serial.println("Connection failed to port " + String(port));
  }
}

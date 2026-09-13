#include <Arduino.h>
#include <WiFi.h>
#include <WebSocketsClient.h>
#include <ArduinoJson.h>

// --- THÔNG SỐ KẾT NỐI MẠNG ---
const char* WIFI_SSID = "Quoc Tuan_2.4";       // Đổi thành SSID Wi-Fi LAN nhà bạn
const char* WIFI_PASS = "0344176713";          // Đổi thành mật khẩu Wi-Fi
const char* PI_IP     = "192.168.1.95";            // Đổi thành IP Raspberry Pi
const int   PI_PORT   = 8765;

WebSocketsClient webSocket;
unsigned long lastPingTime = 0;

void setup() {
    // 1. Chờ 3 giây để nguồn điện và cổng USB Native CDC ổn định
    delay(3000); 
    Serial.begin(115200);

    // 2. Ép Serial CDC chờ tối đa 3s
    unsigned long start = millis();
    while (!Serial && (millis() - start < 3000));

    Serial.println("\n==========================================");
    Serial.println("   RASPFLIP ESP32-S3 REMOTE GUI STARTING   ");
    Serial.println("==========================================");

    // 3. Khởi tạo Wi-Fi dạng Station
    WiFi.mode(WIFI_STA);
    WiFi.disconnect(); // Clear cấu hình Wi-Fi cũ trong Flash
    delay(100);

    Serial.printf("[Wi-Fi] Connecting to SSID: %s ...\n", WIFI_SSID);
    WiFi.begin(WIFI_SSID, WIFI_PASS);

    // 4. Chờ kết nối Wi-Fi (Tối đa 15 giây)
    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 30) {
        delay(500);
        Serial.print(".");
        attempts++;
    }

    // 5. Kiểm tra trạng thái Wi-Fi
    if (WiFi.status() == WL_CONNECTED) {
        Serial.println();
        Serial.printf("✅ [Wi-Fi] Connected Successfully!\n");
        Serial.printf("   ➜ ESP32 IP: %s\n", WiFi.localIP().toString().c_str());
        Serial.printf("   ➜ RSSI (Signal): %d dBm\n", WiFi.RSSI());

        // Khởi tạo WebSocket Client nếu Wi-Fi đã kết nối
        webSocket.begin(PI_IP, PI_PORT, "/");
        webSocket.setReconnectInterval(5000);
    } else {
        Serial.println();
        Serial.printf("❌ [Wi-Fi] Connection Failed! Status code: %d\n", WiFi.status());
        Serial.println("   ➜ Hãy kiểm tra lại SSID (tên Wi-Fi 2.4GHz) và Mật khẩu.");
    }
}

void loop() {
    // Chỉ duy trì WebSocket nếu Wi-Fi đã kết nối thành công
    if (WiFi.status() == WL_CONNECTED) {
        webSocket.loop();

        if (millis() - lastPingTime > 5000) {
            lastPingTime = millis();
            if (webSocket.isConnected()) {
                StaticJsonDocument<128> doc;
                doc["action"] = "ping";
                String jsonOutput;
                serializeJson(doc, jsonOutput);
                webSocket.sendTXT(jsonOutput);
                Serial.println("📤 [WS] Sent ping: " + jsonOutput);
            }
        }
    } else {
        // In cảnh báo định kỳ nếu mất mạng Wi-Fi
        if (millis() - lastPingTime > 5000) {
            lastPingTime = millis();
            Serial.println("⚠️ [Wi-Fi] Not connected. Retrying...");
            WiFi.reconnect();
        }
    }
}
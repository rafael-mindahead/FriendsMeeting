
#include <Arduino.h>

#include "wifi/wifi_manager.h"
#include "websocket/websocket_server.h"

void setup() {
    Serial.begin(115200);

    inicializarWiFi();
    inicializarWebSocket();
}

void loop() {
    verificarWiFi();
    atualizarWebSocket();

    delay(10);
}

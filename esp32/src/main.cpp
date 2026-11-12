
#include <Arduino.h>

#include <HTTPClient.h>
#include "secrets.h"
#include "wifi/wifi_manager.h"
#include "websocket/websocket_server.h"
#include "calls/call_manager.h"


void testarConexaoBackend() {
    HTTPClient http;

    String url = String("http://") +
                 BACKEND_HOST +
                 ":" +
                 BACKEND_PORT +
                 "/api/v1/health";

    http.begin(url);

    int status = http.GET();

    Serial.printf("Resposta HTTP: %d\n", status);

    http.end();
}


void setup() {
    Serial.begin(115200);

    inicializarWiFi();
    testarConexaoBackend();
    inicializarWebSocket();
}

void loop() {
    verificarWifi();
    atualizarChamadas();
    atualizarWebSocket();
    limparChamadasFinalizadas();

    delay(10);
}

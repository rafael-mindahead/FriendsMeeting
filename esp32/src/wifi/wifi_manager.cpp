#include "wifi_manager.h"

#include <Arduino.h>
#include <WiFi.h>
#include "secrets.h"

void inicializarWiFi(){
    Serial.println("Inicializando WiFi...");

    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }

    Serial.println("");
    Serial.print("Conectado ao WiFi. Endereço IP: ");
    Serial.println(WiFi.localIP());
}

void verificarWifi(){
    if (WiFi.status() == WL_CONNECTED){
        return;
    }

    Serial.println("WiFi desconectado. Tentando reconectar...");
    WiFi.reconnect();

}
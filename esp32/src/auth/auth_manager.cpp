
#include "auth_manager.h"

#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <WiFi.h>
#include "secrets.h"

bool autenticarCredencial(
    const String& credencial,
    String& usuarioId
) {
    usuarioId = "";

    if (WiFi.status() != WL_CONNECTED) {
        return false;
    }

    HTTPClient http;

    String url = String("http://") +
                 BACKEND_HOST +
                 ":" +
                 BACKEND_PORT +
                 "/api/v1/calls/auth/consume";

    http.begin(url);
    http.addHeader(
        "Content-Type",
        "application/json"
    );

    http.addHeader(
        "X-Device-Key",
        ESP32_DEVICE_KEY
    );

    JsonDocument requisicao;
    requisicao["credential"] = credencial;

    String corpo;
    serializeJson(requisicao, corpo);

    int status = http.POST(corpo);

    if (status != 200) {
        Serial.printf(
            "[AUTH] Falha HTTP: %d\n",
            status
        );

        http.end();
        return false;
    }

    JsonDocument resposta;

    DeserializationError erro =
        deserializeJson(
            resposta,
            http.getString()
        );

    http.end();

    if (erro) {
        return false;
    }

    const char* id = resposta["user_id"] | "";

    if (strlen(id) != 36) {
        return false;
    }

    usuarioId = id;

    return true;
}


#include "websocket_server.h"

#include <Arduino.h>
#include <WebSocketsServer.h>
#include <ArduinoJson.h>

WebSocketsServer webSocket(81);

void tratarEventoWebSocket(
    uint8_t cliente,
    WStype_t tipo,
    uint8_t* payload,
    size_t tamanho
) {
    switch (tipo) {

        case WStype_CONNECTED:
            Serial.printf(
                "Cliente %u conectado.\n",
                cliente
            );
            break;

        case WStype_DISCONNECTED:
            Serial.printf(
                "Cliente %u desconectado.\n",
                cliente
            );
            break;

        case WStype_TEXT: {
            JsonDocument documento;

            DeserializationError erro =
                deserializeJson(
                    documento,
                    payload,
                    tamanho
                );

            if (erro) {
                webSocket.sendTXT(
                    cliente,
                    "{\"type\":\"error\",\"message\":\"JSON invalido\"}"
                );
                return;
            }

            const char* tipoMensagem =
                documento["type"] | "";

            if (strcmp(tipoMensagem, "ping") == 0) {
                webSocket.sendTXT(
                    cliente,
                    "{\"type\":\"pong\"}"
                );
            }

            break;
        }

        default:
            break;
    }
}

void inicializarWebSocket() {
    webSocket.begin();

    webSocket.onEvent(
        tratarEventoWebSocket
    );

    Serial.println(
        "Servidor WebSocket iniciado na porta 81."
    );
}

void atualizarWebSocket() {
    webSocket.loop();
}

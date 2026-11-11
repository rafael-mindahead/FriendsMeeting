
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

        case WStype_CONNECTED: {
            Serial.printf(
                "[WS] Cliente %u conectado\n",
                cliente
            );

            JsonDocument resposta;
            resposta["type"] = "connected";
            resposta["clientId"] = cliente;

            String mensagem;
            serializeJson(resposta, mensagem);

            webSocket.sendTXT(cliente, mensagem);
            break;
        }

        case WStype_DISCONNECTED:
            Serial.printf(
                "[WS] Cliente %u desconectado\n",
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
                break;
            }

            const char* tipoMensagem =
                documento["type"] | "";

            if (strcmp(tipoMensagem, "ping") == 0) {
                webSocket.sendTXT(
                    cliente,
                    "{\"type\":\"pong\"}"
                );
            }

            else if (strcmp(tipoMensagem, "relay") == 0) {

                if (!documento["to"].is<uint8_t>()) {
                    webSocket.sendTXT(
                        cliente,
                        "{\"type\":\"error\",\"message\":\"Destinatario invalido\"}"
                    );
                    break;
                }

                uint8_t destinatario =
                    documento["to"].as<uint8_t>();

                JsonDocument encaminhamento;

                encaminhamento["type"] = "message";
                encaminhamento["from"] = cliente;
                encaminhamento["data"] = documento["data"];

                String mensagem;
                serializeJson(
                    encaminhamento,
                    mensagem
                );

                bool enviado = webSocket.sendTXT(
                    destinatario,
                    mensagem
                );

                if (!enviado) {
                    webSocket.sendTXT(
                        cliente,
                        "{\"type\":\"error\",\"message\":\"Falha no encaminhamento\"}"
                    );
                }
            }

            break;
        }

        default:
            break;
    }
}

void inicializarWebSocket() {
    webSocket.begin();
    webSocket.onEvent(tratarEventoWebSocket);

    Serial.println(
        "Servidor WebSocket iniciado na porta 81."
    );
}

void atualizarWebSocket() {
    webSocket.loop();
}

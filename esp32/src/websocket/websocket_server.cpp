
#include "websocket_server.h"
#include "../auth/auth_manager.h"

#include <Arduino.h>
#include <WebSocketsServer.h>
#include <ArduinoJson.h>
#include <map>

WebSocketsServer webSocket(81);

// Associa cada cliente WebSocket ao UUID autenticado.
std::map<uint8_t, String> clientesAutenticados;

void enviarErro(uint8_t cliente, const char* mensagem) {
    JsonDocument resposta;
    resposta["type"] = "error";
    resposta["message"] = mensagem;

    String json;
    serializeJson(resposta, json);
    webSocket.sendTXT(cliente, json);
}

void tratarEventoWebSocket(
    uint8_t cliente,
    WStype_t tipo,
    uint8_t* payload,
    size_t tamanho
) {
    switch (tipo) {

        case WStype_CONNECTED: {
            clientesAutenticados.erase(cliente);

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

        case WStype_DISCONNECTED: {
            clientesAutenticados.erase(cliente);

            Serial.printf(
                "[WS] Cliente %u desconectado\n",
                cliente
            );
            break;
        }

        case WStype_TEXT: {
            JsonDocument documento;

            DeserializationError erro =
                deserializeJson(
                    documento,
                    payload,
                    tamanho
                );

            if (erro) {
                enviarErro(cliente, "JSON invalido");
                break;
            }

            const char* tipoMensagem =
                documento["type"] | "";

            // Autenticação da conexão.
            if (strcmp(tipoMensagem, "auth") == 0) {

                if (clientesAutenticados.count(cliente)) {
                    enviarErro(cliente, "Cliente ja autenticado");
                    break;
                }

                const char* credencial =
                    documento["credential"] | "";

                if (strlen(credencial) == 0) {
                    enviarErro(cliente, "Credencial ausente");
                    break;
                }

                String usuarioId;

                bool autenticado = autenticarCredencial(
                    String(credencial),
                    usuarioId
                );

                if (!autenticado) {
                    enviarErro(cliente, "Autenticacao falhou");
                    break;
                }

                clientesAutenticados[cliente] = usuarioId;

                JsonDocument resposta;
                resposta["type"] = "authenticated";
                resposta["userId"] = usuarioId;

                String mensagem;
                serializeJson(resposta, mensagem);

                webSocket.sendTXT(cliente, mensagem);

                Serial.printf(
                    "[AUTH] Cliente %u autenticado\n",
                    cliente
                );

                break;
            }

            // Bloqueia outros eventos antes da autenticação.
            if (!clientesAutenticados.count(cliente)) {
                enviarErro(cliente, "Cliente nao autenticado");
                break;
            }

            if (strcmp(tipoMensagem, "ping") == 0) {
                webSocket.sendTXT(
                    cliente,
                    "{\"type\":\"pong\"}"
                );
            }

            else if (strcmp(tipoMensagem, "relay") == 0) {

                if (!documento["to"].is<uint8_t>()) {
                    enviarErro(cliente, "Destinatario invalido");
                    break;
                }

                uint8_t destinatario =
                    documento["to"].as<uint8_t>();

                // O destinatário também precisa estar autenticado.
                if (!clientesAutenticados.count(destinatario)) {
                    enviarErro(
                        cliente,
                        "Destinatario nao autenticado"
                    );
                    break;
                }

                JsonDocument encaminhamento;

                encaminhamento["type"] = "message";
                encaminhamento["from"] = cliente;
                encaminhamento["fromUserId"] =
                    clientesAutenticados[cliente];

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
                    enviarErro(
                        cliente,
                        "Falha no encaminhamento"
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

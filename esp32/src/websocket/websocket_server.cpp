
#include "websocket_server.h"
#include "../auth/auth_manager.h"
#include "../calls/call_manager.h"

#include <Arduino.h>
#include <WebSocketsServer.h>
#include <ArduinoJson.h>
#include <map>

WebSocketsServer webSocket(81);

// Associa cada conexao ao UUID autenticado.
std::map<uint8_t, String> clientesAutenticados;

int encontrarClientePorUsuario(const String& usuarioId) {
    for (const auto& cliente : clientesAutenticados) {
        if (cliente.second == usuarioId) {
            return cliente.first;
        }
    }

    return -1;
}

void enviarEventoChamada(
    const String& userId,
    const String& evento,
    const CallSession& chamada
) {
    int cliente = encontrarClientePorUsuario(userId);

    if (cliente == -1) {
        return;
    }

    JsonDocument resposta;

    resposta["type"] = evento;
    resposta["callId"] = chamada.callId;
    resposta["callerId"] = chamada.callerId;
    resposta["calleeId"] = chamada.calleeId;
    resposta["state"] = nomeEstadoChamada(chamada.state);

    String mensagem;
    serializeJson(resposta, mensagem);

    webSocket.sendTXT(
        static_cast<uint8_t>(cliente),
        mensagem
    );
}

void notificarParticipantes(
    const CallSession& chamada,
    const String& evento
) {
    enviarEventoChamada(
        chamada.callerId,
        evento,
        chamada
    );

    enviarEventoChamada(
        chamada.calleeId,
        evento,
        chamada
    );
}

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

            auto it = clientesAutenticados.find(cliente);

            if (it != clientesAutenticados.end()) {
                String usuarioId = it->second;

                clientesAutenticados.erase(it);

                // Evita marcar o usuario como desconectado
                // caso outra conexao autenticada continue ativa.
                if (encontrarClientePorUsuario(usuarioId) == -1) {
                    usuarioDesconectado(usuarioId);
                }
            }

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
                usuarioReconectado(usuarioId);

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

            if (!clientesAutenticados.count(cliente)) {
                enviarErro(cliente, "Cliente nao autenticado");
                break;
            }

            const String usuarioId =
                clientesAutenticados[cliente];

            if (strcmp(tipoMensagem, "call-invite") == 0) {

                const char* destinatario =
                    documento["toUserId"] | "";

                if (strlen(destinatario) == 0) {
                    enviarErro(
                        cliente,
                        "UUID do destinatario ausente"
                    );
                    break;
                }

                if (encontrarClientePorUsuario(destinatario) == -1) {
                    enviarErro(
                        cliente,
                        "Destinatario nao conectado"
                    );
                    break;
                }

                String callId;

                CallResult resultado = iniciarChamada(
                    usuarioId,
                    String(destinatario),
                    callId
                );

                if (resultado != CallResult::SUCCESS) {
                    enviarErro(
                        cliente,
                        "Nao foi possivel iniciar chamada"
                    );
                    break;
                }

                const CallSession* chamada =
                    buscarChamada(callId);

                if (chamada) {
                    enviarEventoChamada(
                        chamada->callerId,
                        "call-created",
                        *chamada
                    );

                    enviarEventoChamada(
                        chamada->calleeId,
                        "call-incoming",
                        *chamada
                    );

                    Serial.printf(
                        "[CALL] Chamada %s iniciada\n",
                        callId.c_str()
                    );
                }

                break;
            }

            else if (
                strcmp(tipoMensagem, "call-accept") == 0 ||
                strcmp(tipoMensagem, "call-reject") == 0 ||
                strcmp(tipoMensagem, "call-cancel") == 0 ||
                strcmp(tipoMensagem, "call-end") == 0
            ) {
                const char* id =
                    documento["callId"] | "";

                if (strlen(id) == 0) {
                    enviarErro(cliente, "callId ausente");
                    break;
                }

                String callId(id);

                CallResult resultado =
                    CallResult::INVALID_STATE;

                if (strcmp(tipoMensagem, "call-accept") == 0) {
                    resultado = aceitarChamada(
                        callId,
                        usuarioId
                    );
                }
                else if (strcmp(tipoMensagem, "call-reject") == 0) {
                    resultado = recusarChamada(
                        callId,
                        usuarioId
                    );
                }
                else if (strcmp(tipoMensagem, "call-cancel") == 0) {
                    resultado = cancelarChamada(
                        callId,
                        usuarioId
                    );
                }
                else if (strcmp(tipoMensagem, "call-end") == 0) {
                    resultado = encerrarChamada(
                        callId,
                        usuarioId
                    );
                }

                if (resultado != CallResult::SUCCESS) {
                    enviarErro(
                        cliente,
                        "Operacao de chamada invalida"
                    );
                    break;
                }

                const CallSession* chamada =
                    buscarChamada(callId);

                if (chamada) {
                    notificarParticipantes(
                        *chamada,
                        "call-updated"
                    );

                    Serial.printf(
                        "[CALL] Chamada %s: %s\n",
                        callId.c_str(),
                        nomeEstadoChamada(chamada->state)
                    );
                }

                break;
            }


            else if (strcmp(tipoMensagem, "call-ready") == 0) {

                const char* id = documento["callId"] | "";

                if (strlen(id) == 0) {
                    enviarErro(cliente, "callId ausente");
                    break;
                }

                String callId(id);

                CallResult resultado = confirmarConexaoChamada(
                    callId,
                    usuarioId
                );

                if (resultado != CallResult::SUCCESS) {
                    enviarErro(
                        cliente,
                        "Confirmacao de chamada invalida"
                    );
                    break;
                }

                const CallSession* chamada = buscarChamada(callId);

                if (chamada && chamada->state == CallState::ACTIVE) {
                    notificarParticipantes(
                        *chamada,
                        "call-updated"
                    );
                }

                break;
            }


            else if (strcmp(tipoMensagem, "call-signal") == 0) {

                    const char* id = documento["callId"] | "";

                    if (strlen(id) == 0) {
                        enviarErro(cliente, "callId ausente");
                        break;
                    }

                    if (!documento["data"].is<JsonObject>()) {
                        enviarErro(cliente, "Dados de sinalizacao invalidos");
                        break;
                    }

                    String destinatarioId;

                    CallResult resultado = validarSinalizacao(
                        String(id),
                        usuarioId,
                        destinatarioId
                    );

                    if (resultado != CallResult::SUCCESS) {
                        enviarErro(
                            cliente,
                            "Sinalizacao nao autorizada"
                        );
                        break;
                    }

                    int destinatario =
                        encontrarClientePorUsuario(destinatarioId);

                    if (destinatario == -1) {
                        enviarErro(
                            cliente,
                            "Participante nao conectado"
                        );
                        break;
                    }

                    JsonDocument encaminhamento;

                    encaminhamento["type"] = "call-signal";
                    encaminhamento["callId"] = id;
                    encaminhamento["fromUserId"] = usuarioId;
                    encaminhamento["data"] = documento["data"];

                    String mensagem;
                    serializeJson(encaminhamento, mensagem);

                    bool enviado = webSocket.sendTXT(
                        static_cast<uint8_t>(destinatario),
                        mensagem
                    );

                    if (!enviado) {
                        enviarErro(
                            cliente,
                            "Falha no encaminhamento da sinalizacao"
                        );
                    }

                    break;
                }

            else if (strcmp(tipoMensagem, "ping") == 0) {
                webSocket.sendTXT(
                    cliente,
                    "{\"type\":\"pong\"}"
                );
            }

            else if (strcmp(tipoMensagem, "relay") == 0) {
                enviarErro(cliente, "Relay generico desativado");
            }

            else {
                enviarErro(
                    cliente,
                    "Tipo de mensagem desconhecido"
                );
            }

            break;
        }

        default:
            break;
    }
}

void notificarTimeoutChamada(const CallSession& chamada) {

    if (chamada.state == CallState::RINGING) {

        enviarEventoChamada(
            chamada.calleeId,
            "call-incoming",
            chamada
        );

        return;
    }

    notificarParticipantes(
        chamada,
        "call-updated"
    );
}

void inicializarWebSocket() {
    webSocket.begin();
    webSocket.onEvent(tratarEventoWebSocket);

    registrarCallbackChamada(notificarTimeoutChamada);

    Serial.println(
        "Servidor WebSocket iniciado na porta 81."
    );
}

void atualizarWebSocket() {
    webSocket.loop();
}

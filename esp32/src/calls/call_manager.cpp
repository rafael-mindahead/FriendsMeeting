
#include "call_manager.h"

#include <esp_system.h>

namespace {

constexpr unsigned long RING_TIMEOUT_MS = 45000;
constexpr unsigned long RECONNECT_TIMEOUT_MS = 10000;

std::vector<CallSession> chamadas;
std::vector<CallSession> eventosPendentes;
CallEventCallback callbackChamada = nullptr;

bool estadoFinal(CallState estado) {
    return estado == CallState::ENDED ||
           estado == CallState::REJECTED ||
           estado == CallState::CANCELLED ||
           estado == CallState::MISSED ||
           estado == CallState::FAILED;
}

bool usuarioOcupado(const String& userId) {
    for (const CallSession& chamada : chamadas) {
        if (!estadoFinal(chamada.state) &&
            (chamada.callerId == userId ||
             chamada.calleeId == userId)) {
            return true;
        }
    }

    return false;
}

CallSession* encontrarChamada(const String& callId) {
    for (CallSession& chamada : chamadas) {
        if (chamada.callId == callId) {
            return &chamada;
        }
    }

    return nullptr;
}

String gerarCallId() {
    char identificador[33];

    snprintf(
        identificador,
        sizeof(identificador),
        "%08lx%08lx%08lx%08lx",
        static_cast<unsigned long>(esp_random()),
        static_cast<unsigned long>(esp_random()),
        static_cast<unsigned long>(esp_random()),
        static_cast<unsigned long>(esp_random())
    );

    return String(identificador);
}

void alterarEstado(CallSession& chamada, CallState novoEstado) {
    chamada.state = novoEstado;
    chamada.stateStartedAt = millis();
}

}

CallResult iniciarChamada(
    const String& callerId,
    const String& calleeId,
    String& callId
) {
    callId = "";

    if (callerId.isEmpty() ||
        calleeId.isEmpty() ||
        callerId == calleeId) {
        return CallResult::INVALID_USER;
    }

    if (usuarioOcupado(callerId) ||
        usuarioOcupado(calleeId)) {
        return CallResult::USER_BUSY;
    }

    CallSession chamada;

    chamada.callId = gerarCallId();
    chamada.callerId = callerId;
    chamada.calleeId = calleeId;
    chamada.state = CallState::RINGING;
    chamada.createdAt = millis();
    chamada.stateStartedAt = chamada.createdAt;
    chamada.callerDisconnectedAt = 0;
    chamada.callerOnline = true;
    chamada.calleeOnline = true;

    callId = chamada.callId;
    chamadas.push_back(chamada);

    return CallResult::SUCCESS;
}

CallResult aceitarChamada(
    const String& callId,
    const String& userId
) {
    CallSession* chamada = encontrarChamada(callId);

    if (!chamada) {
        return CallResult::CALL_NOT_FOUND;
    }

    if (chamada->calleeId != userId) {
        return CallResult::UNAUTHORIZED;
    }

    if (chamada->state != CallState::RINGING) {
        return CallResult::INVALID_STATE;
    }

    if (!chamada->callerOnline || !chamada->calleeOnline) {
        return CallResult::INVALID_STATE;
    }

    alterarEstado(*chamada, CallState::CONNECTING);

    return CallResult::SUCCESS;
}


CallResult confirmarConexaoChamada(
    const String& callId,
    const String& userId
) {
    CallSession* chamada = encontrarChamada(callId);

    if (!chamada) {
        return CallResult::CALL_NOT_FOUND;
    }

    if (
        chamada->callerId != userId &&
        chamada->calleeId != userId
    ) {
        return CallResult::UNAUTHORIZED;
    }

    if (chamada->state != CallState::CONNECTING) {
        return CallResult::INVALID_STATE;
    }

    if (
        !chamada->callerOnline ||
        !chamada->calleeOnline
    ) {
        return CallResult::INVALID_STATE;
    }

    if (chamada->callerId == userId) {
        chamada->callerReady = true;
    } else {
        chamada->calleeReady = true;
    }

    if (
        chamada->callerReady &&
        chamada->calleeReady
    ) {
        alterarEstado(*chamada, CallState::ACTIVE);

        Serial.printf(
            "[CALL] Chamada %s ativa\n",
            callId.c_str()
        );
    }

    return CallResult::SUCCESS;
}


CallResult recusarChamada(
    const String& callId,
    const String& userId
) {
    CallSession* chamada = encontrarChamada(callId);

    if (!chamada) {
        return CallResult::CALL_NOT_FOUND;
    }

    if (chamada->calleeId != userId) {
        return CallResult::UNAUTHORIZED;
    }

    if (chamada->state != CallState::RINGING) {
        return CallResult::INVALID_STATE;
    }

    alterarEstado(*chamada, CallState::REJECTED);

    return CallResult::SUCCESS;
}

CallResult cancelarChamada(
    const String& callId,
    const String& userId
) {
    CallSession* chamada = encontrarChamada(callId);

    if (!chamada) {
        return CallResult::CALL_NOT_FOUND;
    }

    if (chamada->callerId != userId) {
        return CallResult::UNAUTHORIZED;
    }

    if (chamada->state != CallState::RINGING) {
        return CallResult::INVALID_STATE;
    }

    alterarEstado(*chamada, CallState::CANCELLED);

    return CallResult::SUCCESS;
}

CallResult encerrarChamada(
    const String& callId,
    const String& userId
) {
    CallSession* chamada = encontrarChamada(callId);

    if (!chamada) {
        return CallResult::CALL_NOT_FOUND;
    }

    if (chamada->callerId != userId &&
        chamada->calleeId != userId) {
        return CallResult::UNAUTHORIZED;
    }

    if (chamada->state != CallState::CONNECTING &&
        chamada->state != CallState::ACTIVE) {
        return CallResult::INVALID_STATE;
    }

    alterarEstado(*chamada, CallState::ENDED);

    return CallResult::SUCCESS;
}

const CallSession* buscarChamada(const String& callId) {
    return encontrarChamada(callId);
}

void atualizarChamadas() {
    unsigned long agora = millis();

    for (CallSession& chamada : chamadas) {

        if (chamada.state == CallState::RINGING &&
            !chamada.callerOnline &&
            chamada.callerDisconnectedAt != 0 &&
            agora - chamada.callerDisconnectedAt >= RECONNECT_TIMEOUT_MS) {

            alterarEstado(chamada, CallState::CANCELLED);
            eventosPendentes.push_back(chamada);

            Serial.printf(
                "[CALL] Chamador nao retornou. Chamada %s cancelada\n",
                chamada.callId.c_str()
            );

            continue;
        }

        if (chamada.state == CallState::RINGING &&
            agora - chamada.stateStartedAt >= RING_TIMEOUT_MS) {

            alterarEstado(chamada, CallState::MISSED);

            eventosPendentes.push_back(chamada);

            Serial.printf(
                "[CALL] Chamada %s nao atendida\n",
                chamada.callId.c_str()
            );
        }

        if (chamada.state == CallState::RECONNECTING &&
            agora - chamada.stateStartedAt >= RECONNECT_TIMEOUT_MS) {

            alterarEstado(chamada, CallState::FAILED);

            eventosPendentes.push_back(chamada);

            Serial.printf(
                "[CALL] Reconexao expirou. Chamada %s falhou\n",
                chamada.callId.c_str()
            );
        }
    }
}

const char* nomeEstadoChamada(CallState estado) {
    switch (estado) {
        case CallState::RINGING: return "RINGING";
        case CallState::CONNECTING: return "CONNECTING";
        case CallState::ACTIVE: return "ACTIVE";
        case CallState::RECONNECTING: return "RECONNECTING";
        case CallState::ENDED: return "ENDED";
        case CallState::REJECTED: return "REJECTED";
        case CallState::CANCELLED: return "CANCELLED";
        case CallState::MISSED: return "MISSED";
        case CallState::FAILED: return "FAILED";
        default: return "UNKNOWN";
    }
}


CallResult validarSinalizacao(
    const String& callId,
    const String& remetenteId,
    String& destinatarioId
) {
    destinatarioId = "";

    const CallSession* chamada = buscarChamada(callId);

    if (chamada == nullptr) {
        return CallResult::CALL_NOT_FOUND;
    }

    if (chamada->callerId != remetenteId &&
        chamada->calleeId != remetenteId) {
        return CallResult::UNAUTHORIZED;
    }

    if (chamada->state != CallState::CONNECTING &&
        chamada->state != CallState::ACTIVE &&
        chamada->state != CallState::RECONNECTING) {
        return CallResult::INVALID_STATE;
    }

    if (!chamada->callerOnline || !chamada->calleeOnline) {
        return CallResult::INVALID_STATE;
    }

    destinatarioId =
        chamada->callerId == remetenteId
            ? chamada->calleeId
            : chamada->callerId;

    return CallResult::SUCCESS;
}

void registrarCallbackChamada(CallEventCallback callback) {
    callbackChamada = callback;
}

void limparChamadasFinalizadas() {

    if (callbackChamada != nullptr) {
        for (const CallSession& evento : eventosPendentes) {
            callbackChamada(evento);
        }
    }

    eventosPendentes.clear();

    for (auto it = chamadas.begin(); it != chamadas.end();) {
        if (estadoFinal(it->state)) {
            Serial.printf(
                "[CALL] Removendo chamada %s\n",
                it->callId.c_str()
            );

            it = chamadas.erase(it);
        } else {
            ++it;
        }
    }
}

void usuarioDesconectado(const String& userId) {
    for (CallSession& chamada : chamadas) {

        if (estadoFinal(chamada.state)) {
            continue;
        }

        bool participante = false;

        if (chamada.callerId == userId) {
            chamada.callerOnline = false;
            participante = true;
        }

        if (chamada.calleeId == userId) {
            chamada.calleeOnline = false;
            participante = true;
        }

        if (!participante) {
            continue;
        }

        if (chamada.state == CallState::RINGING) {

            if (chamada.callerId == userId) {
                chamada.callerDisconnectedAt = millis();

                Serial.printf(
                    "[CALL] Chamador desconectado. Chamada %s aguardando 10 segundos\n",
                    chamada.callId.c_str()
                );
            }

            continue;
        }

        if (chamada.state == CallState::CONNECTING ||
            chamada.state == CallState::ACTIVE) {

            alterarEstado(chamada, CallState::RECONNECTING);
            eventosPendentes.push_back(chamada);

            Serial.printf(
                "[CALL] Chamada %s aguardando reconexao\n",
                chamada.callId.c_str()
            );
        }
    }
}

void usuarioReconectado(const String& userId) {
    for (CallSession& chamada : chamadas) {

        if (estadoFinal(chamada.state)) {
            continue;
        }

        bool ehCaller = chamada.callerId == userId;
        bool ehCallee = chamada.calleeId == userId;

        if (!ehCaller && !ehCallee) {
            continue;
        }

        unsigned long agora = millis();

        // Verifica o prazo antes de registrar a reconexao.
        if (chamada.state == CallState::RINGING &&
            ehCaller &&
            !chamada.callerOnline &&
            chamada.callerDisconnectedAt != 0 &&
            agora - chamada.callerDisconnectedAt >= RECONNECT_TIMEOUT_MS) {

            alterarEstado(chamada, CallState::CANCELLED);
            eventosPendentes.push_back(chamada);
            continue;
        }

        if (chamada.state == CallState::RECONNECTING &&
            chamada.callerOnline &&
            chamada.calleeOnline) {

            chamada.callerReady = false;
            chamada.calleeReady = false;

            alterarEstado(chamada, CallState::CONNECTING);
            eventosPendentes.push_back(chamada);
            continue;
        }

        if (ehCaller) {
            chamada.callerOnline = true;
        }

        if (ehCallee) {
            chamada.calleeOnline = true;
        }

        if (chamada.state == CallState::RINGING) {

            if (ehCaller) {
                chamada.callerDisconnectedAt = 0;
            }

            if (ehCallee) {
                eventosPendentes.push_back(chamada);
            }

            continue;
        }

        if (chamada.state == CallState::RECONNECTING &&
            chamada.callerOnline &&
            chamada.calleeOnline) {

            alterarEstado(chamada, CallState::CONNECTING);
            eventosPendentes.push_back(chamada);

            Serial.printf(
                "[CALL] Participantes reconectados. Chamada %s em CONNECTING\n",
                chamada.callId.c_str()
            );
        }
    }
}


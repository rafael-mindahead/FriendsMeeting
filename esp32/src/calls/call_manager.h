
#pragma once

#include <Arduino.h>
#include <vector>

enum class CallState {
    RINGING,
    CONNECTING,
    ACTIVE,
    RECONNECTING,
    ENDED,
    REJECTED,
    CANCELLED,
    MISSED,
    FAILED
};

struct CallSession {
    String callId;
    String callerId;
    String calleeId;

    CallState state;
    unsigned long createdAt;
    unsigned long stateStartedAt;
    unsigned long callerDisconnectedAt;

    bool callerOnline;
    bool calleeOnline;

    bool callerReady = false;
    bool calleeReady = false;
};

enum class CallResult {
    SUCCESS,
    USER_BUSY,
    INVALID_USER,
    CALL_NOT_FOUND,
    INVALID_STATE,
    UNAUTHORIZED
};

CallResult iniciarChamada(
    const String& callerId,
    const String& calleeId,
    String& callId
);

CallResult aceitarChamada(
    const String& callId,
    const String& userId
);

CallResult recusarChamada(
    const String& callId,
    const String& userId
);

CallResult cancelarChamada(
    const String& callId,
    const String& userId
);

CallResult encerrarChamada(
    const String& callId,
    const String& userId
);

const CallSession* buscarChamada(
    const String& callId
);

const char* nomeEstadoChamada(CallState estado);

CallResult validarSinalizacao(
    const String& callId,
    const String& remetenteId,
    String& destinatarioId
);

CallResult confirmarConexaoChamada(
    const String& callId,
    const String& userId
);

using CallEventCallback = void (*)(const CallSession&);

void registrarCallbackChamada(CallEventCallback callback);

void usuarioDesconectado(const String& userId);

void usuarioReconectado(const String& userId);

void limparChamadasFinalizadas();

void atualizarChamadas();


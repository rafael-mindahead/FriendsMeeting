
import { CallSignaling } from "./call-signaling.js";
import { CallWebRTC } from "./webrtc.js";

const TERMINAL_STATES = new Set([
  "ENDED",
  "REJECTED",
  "CANCELLED",
  "MISSED",
  "FAILED"
]);

export class CallManager {
  constructor(url, callbacks = {}) {
    this.callbacks = callbacks;

    this.call = null;
    this.role = null;
    this.rtc = null;
    this.pendingSignals = [];
    this.signalQueue = Promise.resolve();
    this.offerStarted = false;
    this.readySent = false;

    this.signaling = new CallSignaling(url, {
      authenticated: (data) => {
        this.emit("connected", data);
      },

      message: (packet) => {
        this.handleMessage(packet);
      },

      disconnected: () => {
        // A desconexão do ESP32 não interrompe
        // automaticamente o áudio P2P.
        this.emit("disconnected");
      },

      error: (error) => {
        this.emit("error", error);
      }
    });
  }

  emit(event, data) {
    this.callbacks[event]?.(data);
  }

  async connect() {
    await this.signaling.connect();
  }

  send(type, data = {}) {
    return this.signaling.send({ type, ...data });
  }

  createRTC() {
    if (this.rtc) return this.rtc;

    const rtc = new CallWebRTC(
      (data) => {
        if (!this.call?.callId) return;

        const sent = this.signal(
          this.call.callId,
          data
        );

        if (!sent) {
          this.emit(
            "error",
            "Não foi possível enviar a sinalização WebRTC."
          );
        }
      },
      {
        "connection-state": (state) => {
          this.emit("rtc-state", state);

          if (
            state === "connected" &&
            this.call?.callId &&
            !this.readySent
          ) {
            const sent = this.send("call-ready", {
              callId: this.call.callId
            });

            if (sent) {
              this.readySent = true;
            } else {
              this.emit(
                "error",
                "Não foi possível confirmar a conexão com o ESP32."
              );
            }
          }
        },

        "remote-track": (track) => {
          this.emit("remote-track", track);
        },

        error: (error) => {
          this.emit("error", error);
        }
      }
    );

    this.rtc = rtc;
    return rtc;
  }

  async invite(toUserId) {
    if (this.call || this.rtc) {
      throw new Error("Já existe uma chamada em andamento.");
    }

    this.role = "caller";

    try {
      await this.createRTC().prepare();

      if (!this.send("call-invite", { toUserId })) {
        throw new Error("ESP32 não está conectado.");
      }
    } catch (error) {
      this.cleanup();
      throw error;
    }
  }

  async accept(callId) {
    if (
      !this.call ||
      this.call.callId !== callId ||
      this.role !== "callee"
    ) {
      throw new Error("Chamada recebida inválida.");
    }

    try {
      await this.createRTC().prepare();

      if (!this.send("call-accept", { callId })) {
        throw new Error("ESP32 não está conectado.");
      }
    } catch (error) {
      this.rtc?.close();
      this.rtc = null;
      throw error;
    }
  }

  reject(callId) {
    return this.send("call-reject", { callId });
  }

  cancel(callId) {
    return this.send("call-cancel", { callId });
  }

  end(callId) {
    const sent = this.send("call-end", { callId });

    // Libera o áudio local mesmo se o ESP32 estiver offline.
    this.cleanup();

    return sent;
  }

  signal(callId, data) {
    return this.send("call-signal", { callId, data });
  }

  async startOffer() {
    if (
      this.role !== "caller" ||
      this.offerStarted ||
      !this.rtc
    ) {
      return;
    }

    this.offerStarted = true;

    try {
      await this.rtc.createOffer();
    } catch (error) {
      this.emit("error", error);
    }
  }

  processSignal(packet) {
    if (
      !this.call?.callId ||
      packet.callId !== this.call.callId
    ) {
      return;
    }

    if (!this.rtc) {
      this.pendingSignals.push(packet.data);
      return;
    }

    this.signalQueue = this.signalQueue
      .then(() => this.rtc?.handleSignal(packet.data))
      .catch((error) => this.emit("error", error));
  }

  flushSignals() {
    if (!this.rtc) return;

    const signals = this.pendingSignals.splice(0);

    for (const data of signals) {
      this.processSignal({
        callId: this.call.callId,
        data
      });
    }
  }

  handleMessage(packet) {
    switch (packet.type) {
      case "call-created":
        this.call = packet;
        this.emit("call", packet);
        break;

      case "call-incoming":
        if (this.call || this.rtc) {
          this.emit(
            "error",
            "Já existe uma chamada em andamento."
          );
          return;
        }

        this.call = packet;
        this.role = "callee";
        this.emit("call", packet);
        break;

      case "call-updated":
        if (
          !this.call ||
          packet.callId !== this.call.callId
        ) {
          return;
        }

        this.call = packet;
        this.emit("call", packet);

        if (packet.state === "CONNECTING") {
          this.flushSignals();

          if (this.role === "caller") {
            this.startOffer();
          }
        }

        if (TERMINAL_STATES.has(packet.state)) {
          this.cleanup();
        }
        break;

      case "call-signal":
        this.processSignal(packet);
        break;

      default:
        this.emit("message", packet);
    }
  }

  cleanup() {
    this.rtc?.close();

    this.rtc = null;
    this.call = null;
    this.role = null;
    this.pendingSignals = [];
    this.signalQueue = Promise.resolve();
    this.offerStarted = false;
    this.readySent = false;
  }

  close() {
    this.cleanup();
    this.signaling.close();
  }
}

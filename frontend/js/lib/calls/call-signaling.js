
import { obterCredencialChamada } from "./call-api.js";

export class CallSignaling {
  constructor(url, callbacks = {}) {
    this.url = url;
    this.callbacks = callbacks;
    this.socket = null;
    this.authenticated = false;
  }

  emit(evento, dados) {
    this.callbacks[evento]?.(dados);
  }

  async connect() {
    if (this.socket) {
      throw new Error("Conexão de chamadas já iniciada.");
    }

    const credential = await obterCredencialChamada();
    const socket = new WebSocket(this.url);

    this.socket = socket;

    socket.addEventListener("open", () => {
      if (this.socket !== socket) return;

      socket.send(JSON.stringify({
        type: "auth",
        credential
      }));
    });

    socket.addEventListener("message", (event) => {
      if (this.socket !== socket) return;

      let packet;

      try {
        packet = JSON.parse(event.data);
      } catch {
        this.emit("error", "Mensagem inválida do ESP32.");
        return;
      }

      if (packet.type === "authenticated") {
        this.authenticated = true;
        this.emit("authenticated", packet);
      } else if (packet.type === "error") {
        this.emit("error", packet);
      } else {
        this.emit("message", packet);
      }
    });

    socket.addEventListener("close", () => {
      if (this.socket !== socket) return;

      this.socket = null;
      this.authenticated = false;
      this.emit("disconnected");
    });

    socket.addEventListener("error", () => {
      if (this.socket !== socket) return;
      this.emit("error", "Falha na conexão com o ESP32.");
    });
  }

  send(packet) {
    if (
      !this.authenticated ||
      this.socket?.readyState !== WebSocket.OPEN
    ) {
      return false;
    }

    this.socket.send(JSON.stringify(packet));
    return true;
  }

  close() {
    const socket = this.socket;

    this.socket = null;
    this.authenticated = false;

    if (socket) {
      socket.close();
    }
  }
}

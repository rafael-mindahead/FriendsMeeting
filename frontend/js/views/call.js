import { esc } from "../lib/dom.js";
import { avatar } from "../lib/avatars.js";
import { icon } from "../lib/icons.js";

const terminalStates = new Set(["ENDED", "REJECTED", "CANCELLED", "MISSED", "FAILED"]);

const callLabels = {
  RINGING: { incoming: "Chamada de voz recebida", outgoing: "Chamando…" },
  CONNECTING: "Conectando áudio…",
  ACTIVE: "Chamada em andamento",
  RECONNECTING: "Tentando reconectar…",
  ENDED: "Chamada encerrada",
  REJECTED: "Chamada recusada",
  CANCELLED: "Chamada cancelada",
  MISSED: "Chamada não atendida",
  FAILED: "Não foi possível completar a chamada"
};

export function renderCallLayer(state) {
  const call = state.callDisplay;
  if (!call) return "";
  const peer = state.friends.find(friend => friend.id === call.peerId)
    || { id: call.peerId, username: "Usuário" };
  const incoming = call.role === "callee";
  const ringing = call.state === "RINGING";
  const pending = state.callActionPending;
  const ended = terminalStates.has(call.state);
  const title = ringing
    ? callLabels.RINGING[incoming ? "incoming" : "outgoing"]
    : callLabels[call.state] || "Chamada de voz";
  const muted = Boolean(state.callMuted);
  const actions = ended
    ? `<button class="call-control call-control-close" type="button" data-action="call-dismiss">Fechar</button>`
    : ringing && incoming
      ? `<button class="call-control call-control-decline" type="button" data-action="call-reject" ${pending ? "disabled" : ""}>${icon("phone-off",22)}<span>Recusar</span></button>
         <button class="call-control call-control-accept" type="button" data-action="call-accept" ${pending ? "disabled" : ""}>${icon("phone",22)}<span>Atender</span></button>`
      : `${ringing ? "" : `<button class="call-control call-control-mute ${muted ? "is-muted" : ""}" type="button" data-action="call-mute" aria-pressed="${muted}" ${pending || !state.callManager?.rtc?.localStream ? "disabled" : ""}>${icon(muted ? "mic-off" : "mic",22)}<span>${muted ? "Ativar microfone" : "Silenciar"}</span></button>`}
        <button class="call-control call-control-decline" type="button" data-action="${ringing ? "call-cancel" : "call-end"}" ${pending || !call.callId ? "disabled" : ""}>${icon("phone-off",22)}<span>${ringing ? "Cancelar" : "Desligar"}</span></button>`;
  return `<div class="call-overlay" role="dialog" aria-modal="true" aria-labelledby="callTitle" aria-describedby="callStatus">
    <section class="call-panel">
      <div class="call-panel-top"><span class="call-overline">FriendsMeeting · Voz</span>${ended ? "" : `<span class="call-live-dot" aria-hidden="true"></span>`}</div>
      <div class="call-peer">${avatar(peer,"xlarge")}
        <h2 id="callTitle">${esc(peer.username)}</h2>
        <p id="callStatus" aria-live="polite">${esc(title)}</p>
      </div>
      ${pending ? '<p class="call-wait">Aguarde…</p>' : '<p class="call-wait">&nbsp;</p>'}
      <div class="call-controls">${actions}</div>
      ${call.state === "ACTIVE" ? '<p class="call-caption">Áudio entre os participantes · controle pelo ESP32</p>' : ""}
    </section>
  </div>`;
}

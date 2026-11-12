import { preference } from "../lib/theme.js";
import { esc } from "../lib/dom.js";
import { icon } from "../lib/icons.js";

const choice=(value,label,icon,selected)=>
  `<button type="button" class="theme-option ${selected===value?"selected":""}" data-action="theme" data-theme="${value}" aria-pressed="${selected===value}"><span class="icon" aria-hidden="true">${icon}</span>${esc(label)}</button>`;

export function renderSettings(state){
  const selected=preference();
  const notificationPreferences=state.notificationPreferences||{muted:false,volume:100,senders:[]};
  return `<header class="panel-header"><div><h1>Configurações</h1><p>Aparência, conta e privacidade.</p></div></header>
    <div class="section-content">
      <section class="card-section"><h2>Aparência</h2><p class="section-subtitle">Escolha o tema. A opção automática acompanha o dispositivo.</p>
      <div class="theme-options" role="group" aria-label="Escolher aparência">
        ${choice("light","Claro",icon("sun",25),selected)}
        ${choice("dark","Escuro",icon("moon",25),selected)}
        ${choice("system","Automático",icon("monitor",25),selected)}
      </div></section>
      <section class="card-section"><h2>Notificações</h2>
        <p class="section-subtitle">Os avisos visuais continuam ativos. Ajuste o som de cada pessoa pelo menu de opções ao lado da conversa.</p>
        <label class="notification-toggle"><input type="checkbox" id="notificationMuted" ${notificationPreferences.muted?"checked":""}>
          <span>Silenciar todos os sons</span></label>
        <label class="notification-volume-label" for="notificationVolume">
          Volume geral <output id="notificationVolumeOutput">${notificationPreferences.volume}%</output>
        </label>
        <input id="notificationVolume" class="notification-volume" type="range" min="0" max="100" step="5" value="${notificationPreferences.volume}" data-original-value="${notificationPreferences.volume}" aria-label="Volume geral das notificações">
        <div class="notification-sound-actions">
          <button class="button ghost" type="button" data-action="test-notification-sound">Testar som</button>
          <span class="section-subtitle">O navegador pode exigir este teste para autorizar áudio.</span>
        </div>
      </section>
      <section class="card-section"><h2>Chamadas de voz</h2>
        <p class="section-subtitle">Informe o endereço WebSocket do ESP32 na rede local. Exemplo: ws://192.168.1.100:81. O navegador precisa de permissão para acessar o microfone.</p>
        <form id="callConnectionForm" class="call-connection-settings">
          <label for="callSocketUrl">Endereço do ESP32</label>
          <input id="callSocketUrl" name="url" type="text" autocomplete="off" spellcheck="false" placeholder="ws://192.168.1.100:81" value="${esc(state.callUrl||"")}">
          <div class="call-connection-actions"><button class="button primary" type="submit">Salvar e conectar</button>
          <small id="callConnectionText" role="status">${state.callConnection==="connected"?"ESP32 conectado":state.callConnection==="connecting"?"Conectando ao ESP32…":"ESP32 desconectado"}</small></div>
        </form>
      </section>
      <section class="card-section"><h2>Sua conta</h2>
        <div class="settings-row"><div><h3>Perfil e foto</h3><p>Foto e código de amizade.</p></div><button class="button ghost" data-action="tab" data-tab="profile">Meu perfil</button></div>
        <div class="settings-row"><div><h3>Sair da conta</h3><p>Encerra esta sessão no navegador.</p></div><button class="button danger" data-action="logout">Sair</button></div>
      </section>
      <section class="card-section"><h2>Sobre o projeto</h2><p class="section-subtitle">Chat com FastAPI, PostgreSQL e WebSocket. Chamadas de voz utilizam o ESP32 para sinalização e WebRTC para áudio entre navegadores.</p>
      <a class="button ghost" href="https://github.com/rafael-mindahead/FriendsMeeting" target="_blank" rel="noopener noreferrer">Ver código no GitHub ↗</a></section>
    </div>`;
}

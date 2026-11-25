import { preference } from "../lib/theme.js";
import { esc } from "../lib/dom.js";
import { icon } from "../lib/icons.js";

const choice=(value,label,icon,selected)=>
  `<button type="button" class="theme-option ${selected===value?"selected":""}" data-action="theme" data-theme="${value}" aria-pressed="${selected===value}"><span class="icon" aria-hidden="true">${icon}</span>${esc(label)}</button>`;

export function renderSettings(state){
  const selected=preference();
  return `<header class="panel-header"><div><h1>Configurações</h1><p>Aparência, conta e privacidade.</p></div></header>
    <div class="section-content">
      <section class="card-section"><h2>Aparência</h2><p class="section-subtitle">Escolha o tema. A opção automática acompanha o dispositivo.</p>
      <div class="theme-options" role="group" aria-label="Escolher aparência">
        ${choice("light","Claro",icon("sun",25),selected)}
        ${choice("dark","Escuro",icon("moon",25),selected)}
        ${choice("system","Automático",icon("monitor",25),selected)}
      </div></section>
      <section class="card-section"><h2>Sua conta</h2>
        <div class="settings-row"><div><h3>Perfil e foto</h3><p>Foto e código de amizade.</p></div><button class="button ghost" data-action="tab" data-tab="profile">Meu perfil</button></div>
        <div class="settings-row"><div><h3>Sair da conta</h3><p>Encerra esta sessão no navegador.</p></div><button class="button danger" data-action="logout">Sair</button></div>
      </section>
      <section class="card-section"><h2>Sobre o projeto</h2><p class="section-subtitle">Chat com FastAPI, PostgreSQL e WebSocket. A integração com ESP32 é uma etapa futura.</p>
      <a class="button ghost" href="https://github.com/rafael-mindahead/FriendsMeeting" target="_blank" rel="noopener noreferrer">Ver código no GitHub ↗</a></section>
    </div>`;
}

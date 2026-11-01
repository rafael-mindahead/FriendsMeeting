import { preference } from "../lib/theme.js";
import { esc } from "../lib/dom.js";

const choice=(value,label,icon,selected)=>
  `<button type="button" class="theme-option ${selected===value?"selected":""}" data-action="theme" data-theme="${value}" aria-pressed="${selected===value}"><span class="icon" aria-hidden="true">${icon}</span>${esc(label)}</button>`;

export function renderSettings(state){
  const selected=preference();
  return `<header class="panel-header"><div><h1>Configurações</h1><p>Deixe o FriendsMeeting do seu jeito.</p></div></header>
    <div class="section-content">
      <section class="card-section"><h2>Aparência</h2><p class="section-subtitle">Escolha como prefere enxergar suas conversas. A opção automática acompanha o tema do seu dispositivo.</p>
      <div class="theme-options" role="group" aria-label="Escolher aparência">
        ${choice("light","Claro","☀",selected)}
        ${choice("dark","Escuro","☾",selected)}
        ${choice("system","Automático","◐",selected)}
      </div></section>
      <section class="card-section"><h2>Sua conta</h2>
        <div class="settings-row"><div><h3>Perfil e foto</h3><p>Gerencie as informações que seus amigos veem.</p></div><button class="button ghost" data-action="tab" data-tab="profile">Meu perfil</button></div>
        <div class="settings-row"><div><h3>Sair da conta</h3><p>Encerra esta sessão no navegador.</p></div><button class="button danger" data-action="logout">Sair</button></div>
      </section>
      <section class="card-section"><h2>Sobre o projeto</h2><p class="section-subtitle">FriendsMeeting é desenvolvido com FastAPI, PostgreSQL e WebSocket. A integração com ESP32 ainda está em desenvolvimento.</p>
      <a class="button ghost" href="https://github.com/rafael-mindahead/FriendsMeeting" target="_blank" rel="noopener noreferrer">Ver código no GitHub ↗</a></section>
    </div>`;
}

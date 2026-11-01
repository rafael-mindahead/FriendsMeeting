import { esc,shortId } from "../lib/dom.js";
import { avatar } from "../lib/avatars.js";
import { renderChat } from "./chat.js";
import { renderProfile } from "./profile.js";
import { renderSettings } from "./settings.js";

export function friendFor(state, conversation){
  if(!conversation) return null;
  const otherId=conversation.user_a_id===state.user.id?conversation.user_b_id:conversation.user_a_id;
  return state.friends.find(friend=>friend.id===otherId)||{id:otherId,username:"Usuário "+shortId(otherId)};
}
export function contactItems(state){
  const search=(state.search||"").trim().toLocaleLowerCase("pt-BR");
  const entries=state.conversations.filter(conversation=>friendFor(state,conversation).username.toLocaleLowerCase("pt-BR").includes(search));
  if(!entries.length) return `<div class="empty-state"><p>${search?"Nenhuma conversa encontrada.":"Seu espaço de conversas está esperando por um olá. Vá até Amigos para começar."}</p></div>`;
  return entries.map(conversation=>{
    const person=friendFor(state,conversation);
    const messages=state.messages.get(conversation.id)||[];
    const latest=messages.at(-1);
    const selected=state.selectedId===conversation.id;
    return `<button class="contact-item ${selected?"active":""}" type="button" data-action="select-conversation" data-id="${esc(conversation.id)}" aria-current="${selected?"true":"false"}">
      ${avatar(person)}<span class="contact-data"><strong>${esc(person.username)}</strong>
      <small>${latest?esc(latest.body):"Iniciar conversa"}</small></span>
      <span class="contact-extra">${state.online.has(person.id)?"●":""}</span></button>`;
  }).join("");
}
function renderFriends(state){
  const friends=state.friends.map(person=>`<div class="invite-row">${avatar(person)}<span class="contact-data"><strong>${esc(person.username)}</strong><small>Amigo adicionado</small></span><button class="button ghost" type="button" data-action="open-friend" data-id="${esc(person.id)}">Conversar</button></div>`).join("");
  const invites=state.requests.map(req=>`<div class="invite-row">
    <span class="avatar small">✉</span><span class="contact-data"><strong>Solicitação recebida</strong><small>De: ${esc(shortId(req.sender_id))}</small></span>
    <div class="invite-actions"><button class="button primary" data-action="accept" data-id="${esc(req.id)}">Aceitar</button><button class="button ghost" data-action="reject" data-id="${esc(req.id)}">Recusar</button></div></div>`).join("");
  return `<header class="panel-header"><div><h1>Amigos</h1><p>Seu círculo de conversas.</p></div><button class="icon-button" data-action="refresh" title="Atualizar" aria-label="Atualizar amigos">↻</button></header>
  <div class="section-content">
    <section class="card-section"><h2>Adicionar um amigo</h2><p class="section-subtitle">Peça o código de amizade e envie um convite.</p>
      <form id="inviteForm" class="field"><label for="friendCode">Código de amizade</label>
        <input id="friendCode" name="friend_code" autocomplete="off" placeholder="FM-XXXXXXXX" required maxlength="11">
        <button class="button primary" type="submit">Enviar convite</button></form>
    </section>
    <section class="card-section"><h2>Convites recebidos ${state.requests.length?"("+state.requests.length+")":""}</h2>${invites||'<p class="section-subtitle">Nenhum convite pendente.</p>'}</section>
    <section class="card-section"><h2>Seus amigos ${state.friends.length?"("+state.friends.length+")":""}</h2>${friends||'<p class="section-subtitle">Você ainda não adicionou amigos.</p>'}</section>
  </div>`;
}
const nav = (section,label,icon,current) =>
  `<button type="button" class="rail-button ${current===section?"active":""}" data-action="tab" data-tab="${section}" aria-label="${label}" title="${label}" aria-current="${current===section?"page":"false"}">${icon}</button>`;
export function renderShell(state){
  const mobileClass=state.view==="chat"&&state.selectedId?"show-conversation":state.view==="friends"?"page-friends":state.view==="profile"?"page-profile":state.view==="settings"?"page-settings":"";
  const central=state.view==="friends"?renderFriends(state):state.view==="profile"?renderProfile(state):state.view==="settings"?renderSettings(state):renderChat(state);
  return `<div class="app-shell ${mobileClass}">
    <nav class="app-rail" aria-label="Navegação do aplicativo">
      <a href="/" title="Página inicial"><img class="rail-logo" src="/assets/logo.svg" alt="FriendsMeeting"></a>
      ${nav("chat","Conversas","◉",state.view)}
      ${nav("friends","Amigos","♧",state.view)}
      ${nav("profile","Meu perfil","♙",state.view)}
      ${nav("settings","Configurações","⚙",state.view)}
      <div class="rail-spacer"></div>
      <button class="rail-user" type="button" data-action="tab" data-tab="profile" title="Meu perfil">${avatar(state.user,"small",state.avatarRevision)}</button>
    </nav>
    <aside class="sidebar" aria-label="Lista de conversas">
      <div class="sidebar-top"><h1>Conversas</h1><input id="contactSearch" class="search-input sidebar-search" aria-label="Buscar conversas" value="${esc(state.search)}" placeholder="Buscar uma conversa…"></div>
      <div class="sidebar-subheading"><span>Mensagens</span><button class="icon-button" type="button" data-action="refresh" title="Atualizar" aria-label="Atualizar conversas">↻</button></div>
      <div id="contactList" class="contact-list">${contactItems(state)}</div>
      <div class="sidebar-bottom"><span>${state.demo?"Demonstração":"Amigos e conversas privadas"}</span><span>✳</span></div>
    </aside>
    <main class="main-content" id="appMain">${central}</main>
  </div>`;
}

import { esc, fmtTime } from "../lib/dom.js";
import { avatar } from "../lib/avatars.js";
import { icon } from "../lib/icons.js";

export function renderMessageItems(state){
  const messages=state.messages.get(state.selectedId)||[];
  if(!messages.length) return `<div class="empty-state"><div class="empty-glyph">${icon("message-circle",40)}</div><h2>Sua primeira mensagem</h2><p>Que tal começar com um olá?</p></div>`;
  const entries=messages.map(item=>{
    const mine=item.sender_id===state.user.id;
    const receipt=mine
      ?item.read_at
        ?`<span class="message-receipt read" role="img" aria-label="Visualizada" title="Visualizada">${icon("check-double",17)}</span>`
        :item.delivered_at
          ?`<span class="message-receipt" role="img" aria-label="Entregue" title="Entregue">${icon("check-double",17)}</span>`
          :`<span class="message-receipt" role="img" aria-label="Enviada" title="Enviada">${icon("check",17)}</span>`
      :"";
    return `<article class="chat-message ${mine?"mine":""}" data-message-id="${esc(item.id)}" data-sender-id="${esc(item.sender_id)}" data-incoming="${!mine}">
      <div class="message-bubble">${esc(item.body)}</div><div class="message-meta"><time class="message-time" datetime="${esc(item.created_at)}">${fmtTime(item.created_at)}</time>${receipt}</div></article>`;
  }).join("");
  const more=state.olderAvailable?.get(state.selectedId)?`<button type="button" class="load-older" data-action="load-older">Carregar mensagens anteriores</button>`:"";
  return more+entries;
}

export function renderChat(state){
  const conversation=state.conversations.find(item=>item.id===state.selectedId);
  if(!conversation) return `<div class="main-empty"><div class="empty-state"><div class="empty-glyph">${icon("message-circle",40)}</div>
    <h2>As boas conversas começam com um olá.</h2><p>Selecione alguém na lista ou adicione um amigo para começar.</p>
    <button class="button primary" data-action="tab" data-tab="friends">Encontrar amigos</button></div></div>`;
  const otherId=conversation.user_a_id===state.user.id?conversation.user_b_id:conversation.user_a_id;
  const friend=state.friends.find(item=>item.id===otherId)||{id:otherId,username:"Amigo"};
  const messages=state.messages.get(conversation.id)||[];
  const online=state.online.has(otherId);
  const status=state.demo?"Demonstração":state.connection==="connected"?"Conectado":state.connection==="connecting"?"Conectando…":"Reconectando…";
  const items=renderMessageItems(state);
  return `
    <header class="chat-head"><div class="chat-head-user">
      <button class="icon-button chat-back" data-action="back" aria-label="Voltar às conversas">${icon("arrow-left")}</button>
      ${avatar(friend)}<div><strong>${esc(friend.username)}</strong><small id="friendPresence" class="${online?"online":""}">${online?"● Online agora":"Conversa privada"}</small></div>
    </div><div class="chat-actions"><span id="connectionBadge" class="connection-badge ${state.connection==="connected"||state.demo?"connected":""}"><i class="green-dot"></i><span id="connectionStatus">${esc(status)}</span></span></div></header>
    <div class="chat-scroll" id="messages" role="log" aria-label="Mensagens da conversa" aria-live="polite">
      ${items}
    </div>
    <form class="chat-composer" id="messageForm">
      <div class="composer-inner"><textarea id="messageInput" aria-label="Escrever mensagem" name="body" placeholder="Escreva uma mensagem…" rows="1" maxlength="2000" required></textarea>
      <button type="submit" aria-label="Enviar mensagem" ${!state.demo&&state.connection!=="connected"?"disabled":""}>${icon("send")}</button></div>
      <div class="composer-hint">Enter envia · Shift + Enter quebra a linha</div>
    </form>`;
}

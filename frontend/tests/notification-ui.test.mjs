import test from "node:test";
import assert from "node:assert/strict";

globalThis.window={matchMedia:()=>({matches:false,addEventListener(){}})};
const { contactItems, renderShell }=await import("../js/views/shell.js");

const state={
  user:{id:"me",username:"Eu"},
  view:"chat",
  selectedId:null,
  search:"",
  friends:[{id:"friend-1",username:"Amiga"}],
  requests:[{id:"request-1",sender_id:"friend-2",sender_username:"Outro amigo"}],
  conversations:[{id:"conversation-1",user_a_id:"me",user_b_id:"friend-1"}],
  messages:new Map(),
  online:new Set(),
  unreadMessages:new Map([["conversation-1",3]]),
  notificationPreferences:{
    muted:false,
    volume:80,
    senders:[{user_id:"friend-1",muted:true,volume_factor:45}]
  },
  avatarRevision:""
};

test("shows unread message count and per-contact sound controls in conversation row",()=>{
  const html=contactItems(state);
  assert.match(html,/class="unread-badge" aria-label="3 mensagens não lidas">3<\/span>/);
  assert.match(html,/aria-label="Opções de notificação para Amiga"/);
  assert.match(html,/class="contact-extra"><svg[^>]*><path d="M10\.3/);
  assert.match(html,/Som silenciado/);
  assert.match(html,/data-notification-sender-muted data-id="friend-1" checked/);
  assert.match(html,/value="45" data-original-value="45" data-notification-sender-volume/);
  assert.match(html,/Volume da notificação/);
  assert.match(html,/aria-label="Volume da notificação de Amiga"/);
});

test("shows the friend-request indicator on the friends navigation icon",()=>{
  const html=renderShell(state);
  assert.match(html,/aria-label="Amigos, 1 convite pendente"/);
  assert.match(html,/<span class="friend-invite-indicator" aria-hidden="true">\+1<\/span>/);
  assert.match(html,/contact-main[\s\S]*unread-badge[\s\S]*contact-options/);
});

test("shows the received invite count with a plus sign",()=>{
  const html=renderShell({...state,requests:[...state.requests,...state.requests]});
  assert.match(html,/<span class="friend-invite-indicator" aria-hidden="true">\+2<\/span>/);
});

test("does not show the friend-request indicator when there are no pending requests",()=>{
  const html=renderShell({...state,requests:[]});
  assert.doesNotMatch(html,/friend-invite-indicator/);
});

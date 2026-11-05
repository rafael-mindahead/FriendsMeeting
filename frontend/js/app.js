import { $, esc, toast } from "./lib/dom.js";
import { initializeTheme, setTheme } from "./lib/theme.js";
import { bindAvatarFallbacks, uploadAvatar, deleteAvatar } from "./lib/avatars.js";
import { api, login, register, logout, me } from "./lib/request.js";
import { accessToken } from "./lib/session.js";
import { getFriends, getRequests, getConversations, sendInvite, decideInvite } from "./lib/friends.js";
import { createConversation, getHistory, mergedMessages } from "./lib/conversations.js";
import {
  applyMessageStatus,
  applyPendingMessageStatuses,
  mergeMessageStatus
} from "./lib/message-status.js";
import { ChatConnection } from "./lib/realtime.js";
import { UserEventsConnection } from "./lib/user-events.js";
import {
  cachedNotificationPreferences,
  loadNotificationPreferences,
  resetSenderNotificationPreferences,
  saveNotificationPreferences,
  saveSenderNotificationPreferences
} from "./lib/notification-preferences.js";
import {
  claimNotificationSound,
  notificationVolume,
  playNotificationSound
} from "./lib/notification-audio.js";
import { showAuth } from "./views/auth.js";
import { renderShell, contactItems } from "./views/shell.js";
import { renderMessageItems } from "./views/chat.js";
import { renderSettings } from "./views/settings.js";

initializeTheme();
const root = $("#appRoot");
const params = new URLSearchParams(location.search);
const state = {
  demo:false,user:null,authMode:params.get("mode")==="register"?"register":"login",
  view:"chat",search:"",selectedId:null, friends:[],requests:[],conversations:[],
  messages:new Map(),online:new Set(),connection:"disconnected",
  unreadMessages:new Map(),
  typingUsers:new Map(),
  unreadDividerDismissed:new Set(),
  unreadDividerMessages:new Map(),unreadDividerHoldUntil:new Map(),
  unreadDividerTimers:new Map(),
  avatarRevision:"",socket:null,userEvents:null,
  notificationPreferences:{muted:false,volume:100,senders:[]},
  processedNotificationIds:new Set(),
  pendingMessageStatuses:new Map(),
  deliveredAcknowledgements:new Set(),readAcknowledgements:new Set(),
  historyOffsets:new Map(),olderAvailable:new Map()
};
let soundUnlockReminderShown=false;
let messageReadObserver=null;
const UNREAD_DIVIDER_MINIMUM_MS=10000;
const TYPING_STOP_DEBOUNCE_MS=1500;
const TYPING_REFRESH_INTERVAL_MS=2000;
const TYPING_INDICATOR_TTL_MS=5000;
let localTypingConversation=null;
let typingStopTimer=null;
let typingRefreshTimer=null;

function demoData() {
  state.demo=true;
  state.user={id:"demo-me",username:"Rafael",email:"demo@friendsmeeting.local",friend_code:"FM-DEMO2026"};
  state.friends=[
    {id:"demo-vinicius",username:"Vinícius"},
    {id:"demo-marina",username:"Marina"},
    {id:"demo-luiza",username:"Luiza"}
  ];
  state.conversations=state.friends.map(friend=>({
    id:"conversation-"+friend.id,user_a_id:state.user.id,user_b_id:friend.id
  }));
  const now=new Date().toISOString();
  state.messages.set("conversation-demo-vinicius",[
    {id:"demo-1",sender_id:"demo-vinicius",body:"Fala! Bora testar o chat?",created_at:now},
    {id:"demo-2",sender_id:"demo-me",body:"Tá ficando muito bom! ✨",created_at:now},
    {id:"demo-3",sender_id:"demo-vinicius",body:"Depois testamos o ESP32.",created_at:now}
  ]);
  state.messages.set("conversation-demo-marina",[
    {id:"demo-4",sender_id:"demo-marina",body:"Como está o projeto?",created_at:now}
  ]);
  state.online=new Set(["demo-vinicius","demo-marina"]);
  state.selectedId="conversation-demo-vinicius";
  state.view="chat";
  state.connection="demo";
  history.replaceState(null,"","/app.html?demo=1");
  render();
}
function showLogin(){
  disconnect();
  disconnectUserEvents();
  showAuth({
    mode:state.authMode,
    onMode:mode=>{state.authMode=mode;history.replaceState(null,"", "/app.html?mode="+mode);showLogin();},
    onDemo:demoData,
    onSubmit:async ({mode,email,password,username})=>{
      if(mode==="register"){
        await register(username,email,password);
        state.authMode="login";
        showLogin();
        toast("Conta criada! Entre para continuar.");
        const field=$("#email");if(field) field.value=email;
        return;
      }
      await login(email,password);
      state.user=await me();
      await loadLists();
      try{
        state.notificationPreferences=await loadNotificationPreferences(state.user.id);
      }catch(error){
        state.notificationPreferences=cachedNotificationPreferences(state.user.id);
        toast("Não foi possível sincronizar as preferências de notificação. Usando o último valor salvo neste navegador.");
        console.error("Falha ao carregar preferências de notificação.",error);
      }
      state.view="chat";state.selectedId=null;
      history.replaceState(null,"","/app.html");
      render();
      connectUserEvents();
    }
  });
}
async function loadLists(){
  if(state.demo)return;
  const [friends,requests,conversations]=await Promise.all([
    getFriends(),getRequests(),getConversations()
  ]);
  state.friends=friends;
  state.requests=requests;
  state.conversations=conversations;
  state.unreadMessages.clear();
  for(const conversation of conversations){
    if(conversation.unread_count>0){
      state.unreadMessages.set(conversation.id,conversation.unread_count);
    }
  }
}
function render(){
  if(!state.user)return showLogin();
  root.innerHTML=renderShell(state);
  bindAvatarFallbacks(root);
  const messages=$("#messages",root);
  if(messages) messages.scrollTop=messages.scrollHeight;
  observeIncomingMessages();
  acknowledgeDeliveredMessages();
}
function refreshContactList(){
  const list=$("#contactList",root);
  if(list){list.innerHTML=contactItems(state);bindAvatarFallbacks(list);}
}
function refreshFriendIndicator(){
  const button=root.querySelector('.rail-button[data-tab="friends"]');
  if(!button)return;
  const indicator=button.querySelector(".friend-invite-indicator");
  if(!state.requests.length){
    indicator?.remove();
  }else if(indicator){
    indicator.textContent=`+${state.requests.length}`;
  }else{
    const badge=document.createElement("span");
    badge.className="friend-invite-indicator";
    badge.setAttribute("aria-hidden","true");
    badge.textContent=`+${state.requests.length}`;
    button.querySelector(".rail-icon-wrap")?.append(badge);
  }
  button.setAttribute("aria-label",`Amigos${state.requests.length?`, ${state.requests.length} convite${state.requests.length===1?"":"s"} pendente${state.requests.length===1?"":"s"}`:""}`);
}
// Update conversation content without replacing composer focus or rascunhos.
function refreshChat({forceScroll=false,updateMessages=false,preserveTop=false}={}){
  if(state.view!=="chat"||!state.selectedId)return;
  const badge=$("#connectionBadge",root), status=$("#connectionStatus",root);
  if(status)status.textContent=state.demo?"Demonstração":state.connection==="connected"?"Conectado":state.connection==="connecting"?"Conectando…":"Reconectando…";
  if(badge)badge.classList.toggle("connected",state.demo||state.connection==="connected");
  const conversation=state.conversations.find(item=>item.id===state.selectedId);
  const otherId=conversation?.user_a_id===state.user.id?conversation?.user_b_id:conversation?.user_a_id;
  const presence=$("#friendPresence",root);
  if(presence){const online=state.online.has(otherId);presence.textContent=online?"● Online agora":"Conversa privada";presence.classList.toggle("online",online);}
  const submit=$("#messageForm button[type=submit]",root);
  if(submit)submit.disabled=!state.demo&&state.connection!=="connected";
  if(!updateMessages)return;
  const scroll=$("#messages",root);
  if(!scroll)return;
  const oldHeight=scroll.scrollHeight, oldTop=scroll.scrollTop;
  const nearBottom=oldHeight-oldTop-scroll.clientHeight<110;
  scroll.innerHTML=renderMessageItems(state);
  if(preserveTop)scroll.scrollTop=oldTop+(scroll.scrollHeight-oldHeight);
  else scroll.scrollTop=forceScroll||nearBottom?scroll.scrollHeight:oldTop;
  const list=$("#contactList",root);
  if(list){list.innerHTML=contactItems(state);bindAvatarFallbacks(list);}
  observeIncomingMessages();
  acknowledgeDeliveredMessages();
}
function disconnect(){
  stopLocalTyping();
  state.socket?.close();state.socket=null;
  state.connection="disconnected";
  messageReadObserver?.disconnect();
  messageReadObserver=null;
  state.deliveredAcknowledgements.clear();
  state.readAcknowledgements.clear();
}
function disconnectUserEvents(){
  state.userEvents?.close();
  state.userEvents=null;
}
function clearUnreadDividerHold(id){
  clearTimeout(state.unreadDividerTimers.get(id));
  state.unreadDividerTimers.delete(id);
  state.unreadDividerHoldUntil.delete(id);
}
function holdUnreadDivider(id){
  const holdUntil=Math.max(
    state.unreadDividerHoldUntil.get(id)||0,
    Date.now()+UNREAD_DIVIDER_MINIMUM_MS
  );
  state.unreadDividerHoldUntil.set(id,holdUntil);
  clearTimeout(state.unreadDividerTimers.get(id));
  state.unreadDividerTimers.set(id,setTimeout(()=>{
    state.unreadDividerTimers.delete(id);
    state.unreadDividerHoldUntil.delete(id);
    if(!countUnreadMessages(id))state.unreadDividerMessages.delete(id);
    if(state.view==="chat"&&state.selectedId===id){
      refreshChat({updateMessages:true});
    }
  },holdUntil-Date.now()));
}
function finishUnreadDividerOnExit(id){
  if(id&&!countUnreadMessages(id)){
    clearUnreadDividerHold(id);
    state.unreadDividerMessages.delete(id);
  }
}
function stopLocalTyping(notify=true){
  clearTimeout(typingStopTimer);
  clearInterval(typingRefreshTimer);
  typingStopTimer=null;
  typingRefreshTimer=null;
  const conversationId=localTypingConversation;
  localTypingConversation=null;
  if(notify&&conversationId&&state.socket?.id===conversationId){
    state.socket.send({type:"typing:stop"});
  }
}
function updateLocalTyping(){
  const conversationId=state.selectedId;
  const body=$("#messageInput",root)?.value.trim();
  if(!body){
    stopLocalTyping();
    return;
  }
  if(state.demo||!conversationId||!state.socket||state.connection!=="connected")return;
  if(localTypingConversation!==conversationId){
    stopLocalTyping();
    localTypingConversation=conversationId;
    state.socket.send({type:"typing:start"});
    typingRefreshTimer=setInterval(()=>{
      if(localTypingConversation===conversationId&&state.socket?.id===conversationId){
        state.socket.send({type:"typing:start"});
      }
    },TYPING_REFRESH_INTERVAL_MS);
  }
  clearTimeout(typingStopTimer);
  typingStopTimer=setTimeout(()=>stopLocalTyping(),TYPING_STOP_DEBOUNCE_MS);
}
function removeTypingUser(conversationId,userId){
  const users=state.typingUsers.get(conversationId);
  const typing=users?.get(userId);
  if(!typing)return;
  clearTimeout(typing.timer);
  users.delete(userId);
  if(!users.size)state.typingUsers.delete(conversationId);
}
function handleTypingEvent(event){
  if(!event
    ||typeof event.conversation_id!=="string"
    ||typeof event.sender_id!=="string"
    ||event.sender_id===state.user?.id
    ||!state.conversations.some(conversation=>conversation.id===event.conversation_id))return;
  const conversation=state.conversations.find(item=>item.id===event.conversation_id);
  const otherId=conversation.user_a_id===state.user.id?conversation.user_b_id:conversation.user_a_id;
  if(event.sender_id!==otherId)return;

  if(event.type==="typing:stop"){
    removeTypingUser(event.conversation_id,event.sender_id);
  }else if(event.type==="typing:start"){
    removeTypingUser(event.conversation_id,event.sender_id);
    const users=state.typingUsers.get(event.conversation_id)||new Map();
    const timer=setTimeout(()=>{
      removeTypingUser(event.conversation_id,event.sender_id);
      refreshContactList();
      if(state.view==="chat"&&state.selectedId===event.conversation_id){
        refreshChat({updateMessages:true});
      }
    },TYPING_INDICATOR_TTL_MS);
    users.set(event.sender_id,{timer});
    state.typingUsers.set(event.conversation_id,users);
  }else{
    return;
  }

  refreshContactList();
  if(state.view==="chat"&&state.selectedId===event.conversation_id){
    refreshChat({updateMessages:true});
  }
}
function connectUserEvents(){
  disconnectUserEvents();
  if(state.demo||!state.user)return;
  state.userEvents=new UserEventsConnection({
    notification:handleNotification,
    message_status:handleMessageStatus,
    "typing:start":handleTypingEvent,
    "typing:stop":handleTypingEvent,
    error:code=>console.warn("Evento de notificação rejeitado pelo servidor:",code),
    expired:async()=>{
      await logout();
      state.user=null;
      state.selectedId=null;
      showLogin();
      toast("Sua sessão terminou. Entre novamente.");
    }
  });
}
function rememberAcknowledgement(set,messageId){
  set.add(messageId);
  if(set.size>1000)set.delete(set.values().next().value);
}
function acknowledgeDeliveredMessages(){
  if(state.demo||!state.socket||state.connection!=="connected")return;
  for(const message of state.messages.get(state.selectedId)||[]){
    if(message.sender_id===state.user?.id||message.delivered_at||state.deliveredAcknowledgements.has(message.id))continue;
    if(state.socket.send({type:"message_delivered",message_id:message.id})){
      rememberAcknowledgement(state.deliveredAcknowledgements,message.id);
    }
  }
}
function acknowledgeMessageRead(message){
  if(state.demo||!state.socket||state.connection!=="connected"
    ||document.visibilityState!=="visible"
    ||message.sender_id===state.user?.id
    ||message.read_at
    ||state.readAcknowledgements.has(message.id))return;
  if(state.socket.send({type:"message_read",message_id:message.id})){
      const messages=state.messages.get(message.conversation_id)||[];
      const firstUnread=messages.find(item=>item.sender_id!==state.user?.id&&!item.read_at);
      if(state.unreadMessages.get(message.conversation_id)>0){
        const trackedMessages=state.unreadDividerMessages.get(message.conversation_id)||new Set();
        for(const unreadMessage of messages){
          if(unreadMessage.sender_id!==state.user?.id&&!unreadMessage.read_at){
            trackedMessages.add(unreadMessage.id);
          }
        }
        state.unreadDividerMessages.set(message.conversation_id,trackedMessages);
        holdUnreadDivider(message.conversation_id);
      }
      rememberAcknowledgement(state.readAcknowledgements,message.id);
      message.read_at=new Date().toISOString();
      message.delivered_at=message.delivered_at||message.read_at;
    const unread=state.unreadMessages.get(message.conversation_id)||0;
    if(unread<=1)state.unreadMessages.delete(message.conversation_id);
    else state.unreadMessages.set(message.conversation_id,unread-1);
    refreshContactList();
    if(firstUnread?.id===message.id){
      refreshChat({updateMessages:true});
    }
  }
}
function observeIncomingMessages(){
  messageReadObserver?.disconnect();
  messageReadObserver=null;
  const container=$("#messages",root);
  if(!container)return;
  const incoming=container.querySelectorAll('.chat-message[data-incoming="true"]');
  if(!incoming.length)return;
  if("IntersectionObserver" in window){
    messageReadObserver=new IntersectionObserver(entries=>{
      if(document.visibilityState!=="visible")return;
      for(const entry of entries){
        if(!entry.isIntersecting)continue;
        const message=(state.messages.get(state.selectedId)||[])
          .find(item=>item.id===entry.target.dataset.messageId);
        if(message)acknowledgeMessageRead(message);
      }
    },{root:container,threshold:0.01});
    incoming.forEach(message=>messageReadObserver.observe(message));
  }else{
    reportVisibleMessages();
  }
}
function reportVisibleMessages(){
  if(document.visibilityState!=="visible"||state.view!=="chat"||!state.selectedId)return;
  const container=$("#messages",root);
  if(!container)return;
  const bounds=container.getBoundingClientRect();
  for(const element of container.querySelectorAll('.chat-message[data-incoming="true"]')){
    const rect=element.getBoundingClientRect();
    if(rect.bottom<=bounds.top||rect.top>=bounds.bottom||rect.right<=bounds.left||rect.left>=bounds.right)continue;
    const message=(state.messages.get(state.selectedId)||[])
      .find(item=>item.id===element.dataset.messageId);
    if(message)acknowledgeMessageRead(message);
  }
}
function handleMessageStatus(status){
  if(!status||status.sender_id!==state.user?.id
    ||typeof status.message_id!=="string"
    ||typeof status.conversation_id!=="string")return;
  const messages=state.messages.get(status.conversation_id);
  const message=messages?.find(item=>item.id===status.message_id);
  if(!message){
    state.pendingMessageStatuses.set(
      status.message_id,
      mergeMessageStatus(
        state.pendingMessageStatuses.get(status.message_id),
        status
      )
    );
    if(state.pendingMessageStatuses.size>1000){
      state.pendingMessageStatuses.delete(
        state.pendingMessageStatuses.keys().next().value
      );
    }
    return;
  }
  applyMessageStatus(message,status);
  if(state.selectedId===status.conversation_id&&state.view==="chat"){
    refreshChat({updateMessages:true});
  }
}
function rememberNotification(eventId){
  if(state.processedNotificationIds.has(eventId))return false;
  state.processedNotificationIds.add(eventId);
  if(state.processedNotificationIds.size>500){
    state.processedNotificationIds.delete(state.processedNotificationIds.values().next().value);
  }
  return true;
}
function senderName(senderId,event){
  return event.sender_name
    ||state.friends.find(friend=>friend.id===senderId)?.username
    ||"Seu amigo";
}
function handleNotification(event){
  if(!event||typeof event.event_id!=="string"||!event.event_id)return;
  if(!rememberNotification(event.event_id))return;
  if(event.sender_id===state.user?.id)return;

  const senderId=event.sender_id;
  const name=senderName(senderId,event);
  if(event.kind==="message"){
    const visibleInOpenChat=state.view==="chat"
      &&state.selectedId===event.conversation_id
      &&document.visibilityState==="visible";
    const message={
      id:event.event_id,
      conversation_id:event.conversation_id,
      sender_id:senderId,
      body:event.body||"",
      created_at:event.created_at
    };
    const unread=state.unreadMessages.get(event.conversation_id)||0;
    state.unreadMessages.set(event.conversation_id,unread+1);
    if(message.conversation_id)addMessages(message.conversation_id,[message]);
    if(!visibleInOpenChat){
      refreshContactList();
      toast(`Nova mensagem de ${name}.`);
    }
  }else if(event.kind==="friend_request"){
    toast(`${name} enviou um convite de amizade.`);
    loadLists().then(()=>{
      if(state.view==="friends")render();
      else if(state.view==="settings")refreshSettings();
      refreshFriendIndicator();
    }).catch(error=>toast(`O convite chegou, mas não foi possível atualizar a lista: ${error.message}`));
  }else{
    return;
  }

  const volume=notificationVolume(state.notificationPreferences,senderId);
  if(volume===0)return;
  claimNotificationSound(event.event_id).then(async claimed=>{
    if(!claimed)return;
    try{
      const played=await playNotificationSound(volume);
      if(!played&&!soundUnlockReminderShown){
        soundUnlockReminderShown=true;
        toast("Para ativar o som, use “Testar som” nas configurações.");
      }
    }catch(error){
      console.error("Não foi possível reproduzir o som da notificação.",error);
      if(!soundUnlockReminderShown){
        soundUnlockReminderShown=true;
        toast("Não foi possível reproduzir o som neste navegador.");
      }
    }
  }).catch(error=>{
    console.error("Não foi possível deduplicar o som da notificação.",error);
  });
}
function refreshSettings(){
  if(state.view!=="settings")return;
  const main=$("#appMain",root);
  if(main)main.innerHTML=renderSettings(state);
}
function replaceNotificationPreferences(preferences){
  state.notificationPreferences=preferences;
  refreshSettings();
  refreshContactList();
}
function updateSenderPreference(senderId,update){
  const preferences=state.notificationPreferences;
  const current=preferences.senders.find(item=>item.user_id===senderId);
  const next={user_id:senderId,muted:false,volume_factor:100,...current,...update};
  preferences.senders=preferences.senders.filter(item=>item.user_id!==senderId);
  preferences.senders.push(next);
}
function addMessages(id,items,{preserveTop=false}={}){
  const messages=mergedMessages(state.messages.get(id)||[],items||[]);
  applyPendingMessageStatuses(messages,state.pendingMessageStatuses);
  if((state.unreadMessages.get(id)||0)>0){
    const trackedMessages=state.unreadDividerMessages.get(id)||new Set();
    for(const message of messages){
      if(message.sender_id!==state.user?.id&&!message.read_at){
        trackedMessages.add(message.id);
      }
    }
    state.unreadDividerMessages.set(id,trackedMessages);
  }
  state.messages.set(id,messages);
  if(state.selectedId===id && state.view==="chat"){
    refreshChat({updateMessages:true,preserveTop});
  }else if(state.socket?.id===id){
    acknowledgeDeliveredMessages();
  }
}
function countUnreadMessages(id){
  return (state.messages.get(id)||[]).filter(
    message=>message.sender_id!==state.user?.id&&!message.read_at
  ).length;
}
async function reloadMessages(id){
  if(state.demo || state.selectedId!==id)return;
  try{
    const incoming=await getHistory(id,40,0);
    if(state.selectedId!==id)return;
    if(!state.historyOffsets.has(id)){
      state.historyOffsets.set(id,incoming.length);
      state.olderAvailable.set(id,incoming.length===40);
    }
    addMessages(id,incoming);

    while(
      state.selectedId===id
      &&countUnreadMessages(id)<(state.unreadMessages.get(id)||0)
      &&state.olderAvailable.get(id)
    ){
      const offset=state.historyOffsets.get(id)||0;
      const older=await getHistory(id,40,offset);
      if(state.selectedId!==id)return;
      state.historyOffsets.set(id,offset+older.length);
      state.olderAvailable.set(id,older.length===40);
      if(older.length)addMessages(id,older,{preserveTop:true});
    }
  }catch(error){toast(error.message);}
}
async function loadOlderMessages(id){
  if(state.demo || state.selectedId!==id || !state.olderAvailable.get(id))return;
  const button=root.querySelector('[data-action="load-older"]');
  if(button)button.disabled=true;
  const offset=state.historyOffsets.get(id)||0;
  try{
    const page=await getHistory(id,40,offset);
    if(state.selectedId!==id)return;
    state.historyOffsets.set(id,offset+page.length);
    state.olderAvailable.set(id,page.length===40);
    addMessages(id,page,{preserveTop:true});
  }catch(error){toast(error.message);if(button)button.disabled=false;}
}
async function selectConversation(id){
  if(!state.conversations.some(item=>item.id===id))return;
  if(state.selectedId!==id)finishUnreadDividerOnExit(state.selectedId);
  disconnect();
  state.view="chat";state.selectedId=id;
  state.unreadDividerDismissed.delete(id);
  state.online=state.demo?new Set(["demo-vinicius","demo-marina"]):new Set();
  state.connection=state.demo?"demo":"connecting";
  render();
  if(state.demo)return;
  try{
    await reloadMessages(id);
    if(state.selectedId!==id)return;
    state.socket=new ChatConnection(id,{
      cursor:()=>state.messages.get(id)?.at(-1)?.id||null,
      reload:()=>reloadMessages(id),
      status:status=>{
        if(state.selectedId!==id)return;
        state.connection=status;
        if(status==="connecting"){
          stopLocalTyping(false);
          state.deliveredAcknowledgements.clear();
          state.readAcknowledgements.clear();
        }
        refreshChat();
        if(status==="connected"){
          updateLocalTyping();
          acknowledgeDeliveredMessages();
          reportVisibleMessages();
        }
      },
      messages:incoming=>{if(state.selectedId===id)addMessages(id,incoming);},
      snapshot:users=>{if(state.selectedId===id){state.online=new Set(users);refreshChat();}},
      presence:event=>{
        if(state.selectedId!==id)return;
        event.online?state.online.add(event.user_id):state.online.delete(event.user_id);
        refreshChat();
      },
      error:code=>{
        if(code==="typing_unavailable")toast("Não foi possível atualizar o indicador de digitação.");
        else if(code!=="unsupported_event")toast("Não foi possível concluir: "+code);
      },
      expired:async()=>{
        await logout();state.user=null;state.selectedId=null;showLogin();
        toast("Sua sessão terminou. Entre novamente.");
      }
    });
  }catch(error){state.connection="disconnected";refreshChat();toast(error.message);}
}
async function openFriend(id){
  if(state.demo){
    let found=state.conversations.find(c=>c.user_a_id===id||c.user_b_id===id);
    if(!found){found={id:"conversation-"+id,user_a_id:state.user.id,user_b_id:id};state.conversations.push(found);}
    return selectConversation(found.id);
  }
  try{
    const result=await createConversation(id);
    await loadLists();
    await selectConversation(result.id);
  }catch(error){toast(error.message);}
}
async function signOut(){
  disconnect();
  disconnectUserEvents();
  if(!state.demo)await logout();
  state.demo=false;state.user=null;state.friends=[];state.requests=[];
  state.conversations=[];state.messages.clear();state.online.clear();
  state.unreadMessages.clear();
  state.unreadDividerDismissed.clear();
  for(const timer of state.unreadDividerTimers.values())clearTimeout(timer);
  state.unreadDividerTimers.clear();
  state.unreadDividerMessages.clear();
  state.unreadDividerHoldUntil.clear();
  for(const users of state.typingUsers.values()){
    for(const typing of users.values())clearTimeout(typing.timer);
  }
  state.typingUsers.clear();
  state.selectedId=null;state.search="";state.avatarRevision="";
  state.notificationPreferences={muted:false,volume:100,senders:[]};
  state.processedNotificationIds.clear();
  state.pendingMessageStatuses.clear();
  state.deliveredAcknowledgements.clear();state.readAcknowledgements.clear();
  state.historyOffsets.clear();state.olderAvailable.clear();
  history.replaceState(null,"","/app.html?mode=login");
  state.authMode="login";
  showLogin();
}

root.addEventListener("click",async event=>{
  const button=event.target.closest("[data-action]");
  if(!button)return;
  const action=button.dataset.action;
  try {
    if(action==="tab"){
      finishUnreadDividerOnExit(state.selectedId);
      disconnect();
      state.view=button.dataset.tab;
      state.selectedId=null;state.search="";
      render();
    } else if(action==="select-conversation"){
      await selectConversation(button.dataset.id);
    } else if(action==="load-older"){
      await loadOlderMessages(state.selectedId);
    } else if(action==="open-friend"){
      await openFriend(button.dataset.id);
    } else if(action==="back"){
      finishUnreadDividerOnExit(state.selectedId);
      disconnect();state.selectedId=null;render();
    } else if(action==="refresh"){
      await loadLists();render();toast("Atualizado.");
    } else if(action==="copy-code"){
      if(navigator.clipboard?.writeText){
        await navigator.clipboard.writeText(state.user.friend_code);
        toast("Código copiado!");
      }else toast("Seu código: "+state.user.friend_code);
    } else if(action==="accept"||action==="reject"){
      if(state.demo)return toast("Entre na sua conta para responder a convites.");
      await decideInvite(button.dataset.id,action==="accept"?"accept":"reject");
      await loadLists();render();toast(action==="accept"?"Convite aceito.":"Convite recusado.");
    } else if(action==="theme"){
      setTheme(button.dataset.theme);render();
    } else if(action==="test-notification-sound"){
      const volume=notificationVolume(state.notificationPreferences,null);
      if(volume===0)return toast("Ajuste o volume geral e desative o silêncio para testar o som.");
      const played=await playNotificationSound(volume);
      toast(played?"Som de notificação reproduzido.":"O navegador não autorizou a reprodução de áudio.");
    } else if(action==="reset-notification-sender"){
      if(state.demo)return toast("Entre na sua conta para salvar preferências.");
      const preferences=await resetSenderNotificationPreferences(state.user.id,button.dataset.id);
      replaceNotificationPreferences(preferences);
      toast("Volume do contato restaurado ao padrão.");
    } else if(action==="remove-avatar"){
      if(state.demo)return toast("Entre na sua conta para alterar sua foto.");
      await deleteAvatar();state.avatarRevision="deleted-"+Date.now();
      render();toast("Foto removida.");
    } else if(action==="logout"){
      await signOut();
    }
  } catch(error){toast(error.message||"Não foi possível concluir essa ação.");}
});

root.addEventListener("submit",async event=>{
  const form=event.target;
  if(form.id==="authForm")return;
  event.preventDefault();
  if(form.id==="inviteForm"){
    if(state.demo)return toast("Entre na sua conta para adicionar amigos.");
    const field=form.elements.namedItem("friend_code");
    try{
      await sendInvite(field.value);
      field.value="";
      await loadLists();render();
      toast("Convite enviado!");
    }catch(error){toast(error.message);}
    return;
  }
  if(form.id==="messageForm"){
    const field=form.elements.namedItem("body");
    const body=field.value.trim();
    if(!body || body.length>2000)return;
    stopLocalTyping();
    if(state.demo){
      addMessages(state.selectedId,[{
        id:"demo-"+Date.now()+"-"+Math.random(),sender_id:state.user.id,
        body,created_at:new Date().toISOString()
      }]);
      field.value="";
      return;
    }
    if(!state.socket?.send({type:"send_message",body})){
      toast("Aguarde a conexão para enviar.");return;
    }
    clearUnreadDividerHold(state.selectedId);
    state.unreadDividerMessages.delete(state.selectedId);
    state.unreadDividerDismissed.add(state.selectedId);
    refreshChat({updateMessages:true});
    field.value="";
  }
});
root.addEventListener("keydown",event=>{
  if(event.target.id==="messageInput"&&event.key==="Enter"&&!event.shiftKey&&!event.isComposing){
    event.preventDefault();event.target.form?.requestSubmit();
  }
});
document.addEventListener("visibilitychange",()=>{
  if(document.visibilityState!=="visible"||state.view!=="chat"||!state.selectedId)return;
  reportVisibleMessages();
});
root.addEventListener("scroll",event=>{
  if(event.target.id==="messages")reportVisibleMessages();
},true);
root.addEventListener("input",event=>{
  if(event.target.id==="messageInput"){
    updateLocalTyping();
    return;
  }
  if(event.target.id==="contactSearch"){
    state.search=event.target.value;
    refreshContactList();
    return;
  }
  if(event.target.id==="notificationVolume"){
    const volume=Number(event.target.value);
    state.notificationPreferences.volume=volume;
    $("#notificationVolumeOutput",root).textContent=`${volume}%`;
  }else if(event.target.matches("[data-notification-sender-volume]")){
    const volumeFactor=Number(event.target.value);
    updateSenderPreference(event.target.dataset.id,{volume_factor:volumeFactor});
    const output=root.querySelector(`[data-sender-volume-output="${CSS.escape(event.target.dataset.id)}"]`);
    if(output)output.textContent=`${volumeFactor}%`;
  }
});
root.addEventListener("change",async event=>{
  if(event.target.id==="notificationMuted"){
    if(state.demo)return toast("Entre na sua conta para salvar preferências.");
    const previous=!event.target.checked;
    try{
      replaceNotificationPreferences(await saveNotificationPreferences(state.user.id,{
        muted:event.target.checked,
        volume:state.notificationPreferences.volume
      }));
      toast(event.target.checked?"Sons de notificação silenciados.":"Sons de notificação ativados.");
    }catch(error){
      state.notificationPreferences.muted=previous;
      refreshSettings();
      toast(error.message);
    }
    return;
  }
  if(event.target.id==="notificationVolume"){
    if(state.demo)return toast("Entre na sua conta para salvar preferências.");
    const previous=Number(event.target.dataset.originalValue);
    try{
      replaceNotificationPreferences(await saveNotificationPreferences(state.user.id,{
        muted:state.notificationPreferences.muted,
        volume:Number(event.target.value)
      }));
      toast("Volume geral salvo.");
    }catch(error){
      state.notificationPreferences.volume=previous;
      refreshSettings();
      toast(error.message);
    }
    return;
  }
  if(event.target.matches("[data-notification-sender-muted],[data-notification-sender-volume]")){
    if(state.demo)return toast("Entre na sua conta para salvar preferências.");
    const senderId=event.target.dataset.id;
    const stored=state.notificationPreferences.senders.find(item=>item.user_id===senderId)
      ||{user_id:senderId,muted:false,volume_factor:100};
    const previous={
      ...stored,
      volume_factor:event.target.matches("[data-notification-sender-volume]")
        ?Number(event.target.dataset.originalValue)
        :stored.volume_factor,
      muted:event.target.matches("[data-notification-sender-muted]")
        ?!event.target.checked
        :stored.muted
    };
    const update=event.target.matches("[data-notification-sender-muted]")
      ?{muted:event.target.checked,volume_factor:previous.volume_factor}
      :{muted:previous.muted,volume_factor:Number(event.target.value)};
    updateSenderPreference(senderId,update);
    try{
      replaceNotificationPreferences(await saveSenderNotificationPreferences(state.user.id,senderId,update));
      toast("Preferência do contato salva.");
    }catch(error){
      updateSenderPreference(senderId,previous);
      refreshSettings();
      toast(error.message);
    }
    return;
  }
  if(event.target.id!=="avatarUpload")return;
  const file=event.target.files?.[0];
  if(!file)return;
  if(state.demo){toast("Entre na sua conta para alterar sua foto.");event.target.value="";return;}
  try {
    const result=await uploadAvatar(file);
    state.avatarRevision=result.revision;
    render();toast("Foto atualizada! Seus amigos já podem vê-la.");
  }catch(error){toast(error.message||"Não foi possível carregar a foto.");}
});

if(params.has("demo"))demoData();
else showLogin();

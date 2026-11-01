import { $, esc, toast } from "./lib/dom.js";
import { initializeTheme, setTheme } from "./lib/theme.js";
import { bindAvatarFallbacks, uploadAvatar, deleteAvatar } from "./lib/avatars.js";
import { api, login, register, logout, me } from "./lib/request.js";
import { accessToken } from "./lib/session.js";
import { getFriends, getRequests, getConversations, sendInvite, decideInvite } from "./lib/friends.js";
import { createConversation, getHistory, mergedMessages } from "./lib/conversations.js";
import { ChatConnection } from "./lib/realtime.js";
import { showAuth } from "./views/auth.js";
import { renderShell, contactItems } from "./views/shell.js";
import { renderMessageItems } from "./views/chat.js";

initializeTheme();
const root = $("#appRoot");
const params = new URLSearchParams(location.search);
const state = {
  demo:false,user:null,authMode:params.get("mode")==="register"?"register":"login",
  view:"chat",search:"",selectedId:null, friends:[],requests:[],conversations:[],
  messages:new Map(),online:new Set(),connection:"disconnected",
  avatarRevision:"",socket:null,historyOffsets:new Map(),olderAvailable:new Map()
};

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
      state.view="chat";state.selectedId=null;
      history.replaceState(null,"","/app.html");
      render();
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
}
function render(){
  if(!state.user)return showLogin();
  root.innerHTML=renderShell(state);
  bindAvatarFallbacks(root);
  const messages=$("#messages",root);
  if(messages) messages.scrollTop=messages.scrollHeight;
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
}
function disconnect(){
  state.socket?.close();state.socket=null;
  state.connection="disconnected";
}
function addMessages(id,items,{preserveTop=false}={}){
  state.messages.set(id,mergedMessages(state.messages.get(id)||[],items||[]));
  if(state.selectedId===id && state.view==="chat")refreshChat({updateMessages:true,preserveTop});
}
async function reloadMessages(id){
  if(state.demo || state.selectedId!==id)return;
  try{
    const incoming=await getHistory(id,40,0);
    if(state.selectedId===id){
      if(!state.historyOffsets.has(id)){
        state.historyOffsets.set(id,incoming.length);
        state.olderAvailable.set(id,incoming.length===40);
      }
      addMessages(id,incoming);
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
  disconnect();
  state.view="chat";state.selectedId=id;
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
      status:status=>{if(state.selectedId===id){state.connection=status;refreshChat();}},
      messages:incoming=>{if(state.selectedId===id)addMessages(id,incoming);},
      snapshot:users=>{if(state.selectedId===id){state.online=new Set(users);refreshChat();}},
      presence:event=>{
        if(state.selectedId!==id)return;
        event.online?state.online.add(event.user_id):state.online.delete(event.user_id);
        refreshChat();
      },
      error:code=>{if(code!=="unsupported_event")toast("Não foi possível concluir: "+code);},
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
  if(!state.demo)await logout();
  state.demo=false;state.user=null;state.friends=[];state.requests=[];
  state.conversations=[];state.messages.clear();state.online.clear();
  state.selectedId=null;state.search="";state.avatarRevision="";
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
    field.value="";
  }
});
root.addEventListener("keydown",event=>{
  if(event.target.id==="messageInput"&&event.key==="Enter"&&!event.shiftKey&&!event.isComposing){
    event.preventDefault();event.target.form?.requestSubmit();
  }
});
root.addEventListener("input",event=>{
  if(event.target.id!=="contactSearch")return;
  state.search=event.target.value;
  const list=$("#contactList",root);
  if(list){list.innerHTML=contactItems(state);bindAvatarFallbacks(list);}
});
root.addEventListener("change",async event=>{
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

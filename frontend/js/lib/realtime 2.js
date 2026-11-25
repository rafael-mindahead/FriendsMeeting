import { accessToken } from "./session.js";
import { refreshSession } from "./request.js";

export class ChatConnection {
  constructor(conversationId, callbacks = {}) {
    this.id = conversationId;
    this.callbacks = callbacks;
    this.socket = null;
    this.closed = false;
    this.attempts = 0;
    this.timer = null;
    this.heartbeat = null;
    this.connect();
  }
  emit(type,detail) { this.callbacks[type]?.(detail); }
  send(event) {
    if (this.socket?.readyState !== WebSocket.OPEN) return false;
    this.socket.send(JSON.stringify(event));
    return true;
  }
  async connect() {
    if (this.closed) return;
    this.emit("status","connecting");
    const scheme = location.protocol === "https:" ? "wss:" : "ws:";
    const ws = new WebSocket(`${scheme}//${location.host}/api/v1/conversations/${encodeURIComponent(this.id)}/ws`);
    this.socket = ws;
    ws.addEventListener("open",()=>this.send({type:"auth",token:accessToken()}));
    ws.addEventListener("message",event=>{
      if (this.socket !== ws) return;
      let packet;try { packet=JSON.parse(event.data); } catch { return; }
      if (packet.type === "ready") {
        this.attempts = 0;
        this.emit("status","connected");
        this.send({type:"subscribe_presence"});
        const afterId = this.callbacks.cursor?.();
        if (afterId) this.send({type:"sync_messages",after_id:afterId,limit:100});
        else this.callbacks.reload?.();
        clearInterval(this.heartbeat);
        this.heartbeat=setInterval(()=>this.send({type:"ping"}),25000);
      } else if(packet.type === "messages_sync") {
        this.emit("messages",packet.messages || []);
        if(packet.has_more && packet.next_after_id) {
          this.send({type:"sync_messages",after_id:packet.next_after_id,limit:100});
        }
      } else if(packet.type === "message") this.emit("messages",[packet.data]);
      else if(packet.type === "presence_snapshot") this.emit("snapshot",packet.online_user_ids || []);
      else if(packet.type === "presence") this.emit("presence",packet);
      else if(packet.type === "error") {
        if(packet.code === "sync_failed" && packet.status === 409) this.callbacks.reload?.();
        else this.emit("error",packet.code || "Falha na conexão");
      }
    });
    ws.addEventListener("close",async event=>{
      if (this.closed || ws !== this.socket) return;
      clearInterval(this.heartbeat);this.heartbeat=null;
      this.emit("status","disconnected");
      if (event.code === 1008) {
        try { await refreshSession(); }
        catch { this.close();this.emit("expired");return; }
      }
      if (this.closed) return;
      const delay=Math.min(30000,750*2**Math.min(this.attempts++,5))+Math.round(Math.random()*350);
      this.timer=setTimeout(()=>this.connect(),delay);
    });
    ws.addEventListener("error",()=>this.emit("status","disconnected"));
  }
  close() {
    this.closed=true;
    clearTimeout(this.timer);clearInterval(this.heartbeat);
    const ws=this.socket;this.socket=null;
    if(ws){try {ws.close(1000,"Conversa encerrada");}catch{}}
  }
}

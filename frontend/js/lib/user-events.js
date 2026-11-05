import { accessToken } from "./session.js";
import { refreshSession } from "./request.js";

export class UserEventsConnection {
  constructor(callbacks={}) {
    this.callbacks=callbacks;
    this.socket=null;
    this.closed=false;
    this.attempts=0;
    this.timer=null;
    this.heartbeat=null;
    this.connect();
  }

  emit(type,detail) {
    this.callbacks[type]?.(detail);
  }

  send(event) {
    if(this.socket?.readyState!==WebSocket.OPEN)return false;
    this.socket.send(JSON.stringify(event));
    return true;
  }

  async connect() {
    if(this.closed)return;
    const scheme=location.protocol==="https:"?"wss:":"ws:";
    const socket=new WebSocket(`${scheme}//${location.host}/api/v1/events/ws`);
    this.socket=socket;
    socket.addEventListener("open",()=>this.send({type:"auth",token:accessToken()}));
    socket.addEventListener("message",event=>{
      if(this.socket!==socket)return;
      let packet;
      try {
        packet=JSON.parse(event.data);
      } catch {
        this.emit("error","invalid_event");
        return;
      }
      if(packet.type==="ready") {
        this.attempts=0;
        this.emit("status","connected");
        clearInterval(this.heartbeat);
        this.heartbeat=setInterval(()=>this.send({type:"ping"}),25000);
      } else if(packet.type==="notification") {
        this.emit("notification",packet);
      } else if(packet.type==="message_status") {
        this.emit("message_status",packet.data);
      } else if(packet.type==="error") {
        this.emit("error",packet.code||"event_error");
      }
    });
    socket.addEventListener("close",async event=>{
      if(this.closed||socket!==this.socket)return;
      clearInterval(this.heartbeat);
      this.heartbeat=null;
      this.emit("status","disconnected");
      if(event.code===1008) {
        try {
          await refreshSession();
        } catch {
          this.close();
          this.emit("expired");
          return;
        }
      }
      if(this.closed)return;
      const delay=Math.min(30000,750*2**Math.min(this.attempts++,5))+Math.round(Math.random()*350);
      this.timer=setTimeout(()=>this.connect(),delay);
    });
    socket.addEventListener("error",()=>this.emit("status","disconnected"));
  }

  close() {
    this.closed=true;
    clearTimeout(this.timer);
    clearInterval(this.heartbeat);
    const socket=this.socket;
    this.socket=null;
    if(socket) {
      try {
        socket.close(1000,"Sessão encerrada");
      } catch {}
    }
  }
}

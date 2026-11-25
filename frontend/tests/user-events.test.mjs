import test from "node:test";
import assert from "node:assert/strict";

class MockWebSocket {
  static OPEN=1;

  constructor(url){
    this.url=url;
    this.readyState=MockWebSocket.OPEN;
    this.listeners=new Map();
    this.sent=[];
  }

  addEventListener(type,callback){
    const listeners=this.listeners.get(type)||[];
    listeners.push(callback);
    this.listeners.set(type,listeners);
  }

  send(data){
    this.sent.push(JSON.parse(data));
  }

  close(){
    this.readyState=3;
  }

  emit(type,event){
    for(const callback of this.listeners.get(type)||[])callback(event);
  }
}

globalThis.WebSocket=MockWebSocket;
globalThis.location={protocol:"http:",host:"localhost"};
const { UserEventsConnection }=await import("../js/lib/user-events.js");

test("dispatches message status events from the user event socket",()=>{
  const statuses=[];
  const connection=new UserEventsConnection({
    message_status:status=>statuses.push(status)
  });
  const socket=connection.socket;
  const status={
    message_id:"message-1",
    conversation_id:"conversation-1",
    sender_id:"user-1",
    delivered_at:"2026-11-05T12:00:00Z",
    read_at:null
  };

  socket.emit("message",{
    data:JSON.stringify({type:"message_status",data:status})
  });

  assert.deepEqual(statuses,[status]);
  connection.close();
});

test("dispatches typing start and stop events from the user event socket",()=>{
  const events=[];
  const connection=new UserEventsConnection({
    "typing:start":event=>events.push(event),
    "typing:stop":event=>events.push(event)
  });
  const socket=connection.socket;
  const start={
    type:"typing:start",
    conversation_id:"conversation-1",
    sender_id:"user-1"
  };
  const stop={...start,type:"typing:stop"};

  socket.emit("message",{data:JSON.stringify(start)});
  socket.emit("message",{data:JSON.stringify(stop)});

  assert.deepEqual(events,[start,stop]);
  connection.close();
});

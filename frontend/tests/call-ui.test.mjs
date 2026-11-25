import test from "node:test";
import assert from "node:assert/strict";
import { renderCallLayer } from "../js/views/call.js";
const base=(state,role="callee")=>({
  friends:[{id:"friend",username:"Contato"}],
  callDisplay:{callId:"call-1",peerId:"friend",role,state},
  callActionPending:false,callMuted:false,callManager:{rtc:{localStream:{}}},
});
test("chamada recebida oferece atender e recusar",()=>{
  const html=renderCallLayer(base("RINGING"));
  assert.match(html,/data-action="call-accept"/);
  assert.match(html,/data-action="call-reject"/);
  assert.doesNotMatch(html,/data-action="call-end"/);
});
test("chamada realizada oferece cancelar",()=>{
  const html=renderCallLayer(base("RINGING","caller"));
  assert.match(html,/data-action="call-cancel"/);
  assert.doesNotMatch(html,/data-action="call-accept"/);
});
test("chamada ativa oferece microfone e desligar",()=>{
  const html=renderCallLayer(base("ACTIVE"));
  assert.match(html,/data-action="call-mute"/);
  assert.match(html,/data-action="call-end"/);
});
test("chamada finalizada oferece fechar",()=>{
  const html=renderCallLayer(base("ENDED"));
  assert.match(html,/data-action="call-dismiss"/);
  assert.doesNotMatch(html,/data-action="call-end"/);
});
test("não renderiza sem chamada",()=>assert.equal(renderCallLayer({callDisplay:null}),""));

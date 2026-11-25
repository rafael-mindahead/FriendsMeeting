import test from "node:test";
import assert from "node:assert/strict";
import { renderMessageItems } from "../js/views/chat.js";

const state={
  user:{id:"me"},
  selectedId:"conversation-1",
  messages:new Map([["conversation-1",[{
    id:"message-1",
    sender_id:"me",
    body:"Mensagem enviada",
    created_at:"2026-11-05T12:00:00Z"
  }]]]),
  olderAvailable:new Map(),
  typingUsers:new Map([
    ["conversation-1",new Map([["friend-1",{timer:1}]])]
  ]),
  friends:[{id:"friend-1",username:"Amiga"}]
};

test("shows three animated typing dots without a message timestamp",()=>{
  const html=renderMessageItems(state);
  const indicator=html.match(/<article class="typing-indicator"[^]*?<\/article>/)?.[0];

  assert.ok(indicator);
  assert.match(indicator,/aria-label="Amiga está digitando"/);
  assert.equal((indicator.match(/<span><\/span>/g)||[]).length,3);
  assert.doesNotMatch(indicator,/<time|message-meta|message-time/);
  assert.ok(html.endsWith(indicator));
});

test("does not show the typing indicator for the current user",()=>{
  const ownTyping={
    ...state,
    typingUsers:new Map([
      ["conversation-1",new Map([["me",{timer:1}]])]
    ])
  };

  assert.doesNotMatch(renderMessageItems(ownTyping),/typing-indicator/);
});

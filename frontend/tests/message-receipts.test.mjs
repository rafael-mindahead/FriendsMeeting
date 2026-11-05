import test from "node:test";
import assert from "node:assert/strict";
import { mergedMessages } from "../js/lib/conversations.js";
import { renderMessageItems } from "../js/views/chat.js";

const user={id:"me"};
const message=(overrides={})=>({
  id:"message-1",
  sender_id:"me",
  body:"Oi",
  created_at:"2026-11-05T12:00:00Z",
  delivered_at:null,
  read_at:null,
  ...overrides
});

function render(item){
  return renderMessageItems({
    user,
    selectedId:"conversation-1",
    messages:new Map([["conversation-1",[item]]]),
    olderAvailable:new Map()
  });
}

test("shows one white check for a sent message",()=>{
  const html=render(message());
  assert.match(html,/message-receipt" role="img" aria-label="Enviada"/);
  assert.match(html,/class="message-receipt"[^]*<path d="m5 12\.5/);
  assert.doesNotMatch(html,/message-receipt read/);
});

test("shows two white checks after delivery",()=>{
  const html=render(message({delivered_at:"2026-11-05T12:00:01Z"}));
  assert.match(html,/message-receipt" role="img" aria-label="Entregue"/);
  assert.match(html,/<path d="m3 12\.5 4 4L17 6"\/><path d="m9 12\.5 4 4L23 6"\/>/);
  assert.doesNotMatch(html,/message-receipt read/);
});

test("shows blue double checks only after the message is read",()=>{
  const html=render(message({
    delivered_at:"2026-11-05T12:00:01Z",
    read_at:"2026-11-05T12:00:02Z"
  }));
  assert.match(html,/message-receipt read" role="img" aria-label="Visualizada"/);
});

test("does not show delivery receipts on received messages",()=>{
  const html=render(message({sender_id:"friend-1"}));
  assert.doesNotMatch(html,/message-receipt/);
  assert.match(html,/data-incoming="true"/);
});

test("message refresh cannot regress a saved delivery or read receipt",()=>{
  const merged=mergedMessages(
    [message({
      delivered_at:"2026-11-05T12:00:01Z",
      read_at:"2026-11-05T12:00:02Z"
    })],
    [message()]
  );
  assert.equal(merged[0].delivered_at,"2026-11-05T12:00:01Z");
  assert.equal(merged[0].read_at,"2026-11-05T12:00:02Z");
});

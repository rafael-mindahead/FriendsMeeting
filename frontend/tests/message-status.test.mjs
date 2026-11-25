import test from "node:test";
import assert from "node:assert/strict";
import {
  applyMessageStatus,
  applyPendingMessageStatuses,
  mergeMessageStatus
} from "../js/lib/message-status.js";

const deliveredAt="2026-11-05T12:00:01.000Z";
const readAt="2026-11-05T12:00:03.000Z";

test("applies an early delivery receipt when its message is added later",()=>{
  const pending=new Map([["message-1",{
    message_id:"message-1",
    delivered_at:deliveredAt,
    read_at:null
  }]]);
  const messages=[{id:"message-1",body:"Oi"}];

  applyPendingMessageStatuses(messages,pending);

  assert.equal(messages[0].delivered_at,deliveredAt);
  assert.equal(messages[0].read_at,undefined);
  assert.equal(pending.size,0);
});

test("a later delivery event cannot downgrade an already-read message",()=>{
  const message={id:"message-1"};
  applyMessageStatus(message,{
    message_id:"message-1",
    delivered_at:deliveredAt,
    read_at:readAt
  });
  applyMessageStatus(message,{
    message_id:"message-1",
    delivered_at:deliveredAt,
    read_at:null
  });

  assert.equal(message.delivered_at,deliveredAt);
  assert.equal(message.read_at,readAt);
});

test("pending receipt events preserve read state if delivery arrives later",()=>{
  const pending=mergeMessageStatus({
    message_id:"message-1",
    delivered_at:deliveredAt,
    read_at:readAt
  },{
    message_id:"message-1",
    delivered_at:deliveredAt,
    read_at:null
  });

  assert.equal(pending.delivered_at,deliveredAt);
  assert.equal(pending.read_at,readAt);
});

test("does not apply a receipt to a different message",()=>{
  const message={id:"message-2"};
  assert.equal(applyMessageStatus(message,{
    message_id:"message-1",
    delivered_at:deliveredAt,
    read_at:null
  }),false);
  assert.deepEqual(message,{id:"message-2"});
});

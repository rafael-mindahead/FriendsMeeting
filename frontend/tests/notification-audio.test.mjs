import test from "node:test";
import assert from "node:assert/strict";
import {
  claimNotificationSound,
  notificationVolume,
  playNotificationSound
} from "../js/lib/notification-audio.js";

test("combines global volume and sender factor as relative percentages",()=>{
  const preferences={
    muted:false,
    volume:60,
    senders:[{user_id:"friend-1",muted:false,volume_factor:30}]
  };
  assert.equal(notificationVolume(preferences,"friend-1"),18);
  assert.equal(notificationVolume(preferences,"friend-2"),60);
});

test("muted preferences and zero volume prevent sound",()=>{
  assert.equal(notificationVolume({muted:true,volume:100,senders:[]},"friend"),0);
  assert.equal(notificationVolume({
    muted:false,
    volume:80,
    senders:[{user_id:"friend",muted:true,volume_factor:100}]
  },"friend"),0);
  assert.equal(notificationVolume({muted:false,volume:0,senders:[]},"friend"),0);
});

test("claims a notification sound only once for a duplicate event id",async()=>{
  const values=new Map();
  const original=globalThis.localStorage;
  Object.defineProperty(globalThis,"localStorage",{
    configurable:true,
    value:{
      getItem:key=>values.get(key)||null,
      setItem:(key,value)=>values.set(key,value)
    }
  });
  try{
    const eventId=`event-${Date.now()}-${Math.random()}`;
    assert.equal(await claimNotificationSound(eventId),true);
    assert.equal(await claimNotificationSound(eventId),false);
  }finally{
    if(original===undefined)delete globalThis.localStorage;
    else Object.defineProperty(globalThis,"localStorage",{configurable:true,value:original});
  }
});

test("does not construct audio for silent notifications",async()=>{
  assert.equal(await playNotificationSound(0),false);
  assert.equal(await playNotificationSound(-1),false);
});

import test from "node:test";
import assert from "node:assert/strict";
import { esc, initials, safeUuid } from "../js/lib/dom.js";
import { mergedMessages } from "../js/lib/conversations.js";
import { accessToken, refreshToken, setTokens, clearTokens } from "../js/lib/session.js";
import { refreshSession } from "../js/lib/request.js";

test("escapa HTML de mensagens antes de exibir", () => {
  assert.equal(esc('<img src=x onerror="alert(1)">'), '&lt;img src=x onerror=&quot;alert(1)&quot;&gt;');
});
test("valida UUID de avatar e inicial de nome", () => {
  assert.equal(safeUuid("e2a211f5-9a24-42bb-8f6e-8b8aa2dd55bc"), true);
  assert.equal(safeUuid("../../etc/passwd"), false);
  assert.equal(initials("vinicius"),"V");
});
test("remove mensagens duplicadas apos reconexao", () => {
  const m={id:"1",body:"Olá",created_at:"2026-01-01T10:00:00Z"};
  const [merged]=mergedMessages([m],[m]);
  assert.equal(merged.id,m.id);
  assert.equal(merged.body,m.body);
  assert.equal(merged.delivered_at,null);
  assert.equal(merged.read_at,null);
});
test("ordena mensagens recebidas fora de ordem", () => {
  const newer={id:"b",body:"Segunda",created_at:"2026-01-01T10:00:01Z"};
  const older={id:"a",body:"Primeira",created_at:"2026-01-01T10:00:00Z"};
  assert.deepEqual(mergedMessages([newer],[older]).map(x=>x.id),["a","b"]);
});
test("guarda e apaga credenciais apenas em memoria", () => {
  setTokens({access_token:"access-test",refresh_token:"refresh-test"});
  assert.equal(accessToken(),"access-test");
  assert.equal(refreshToken(),"refresh-test");
  clearTokens();
  assert.equal(accessToken(),"");
  assert.equal(refreshToken(),"");
});
test("compartilha uma renovação de sessão entre sockets simultâneos",async()=>{
  const originalFetch=globalThis.fetch;
  let calls=0;
  setTokens({access_token:"old-access",refresh_token:"old-refresh"});
  globalThis.fetch=async()=>{
    calls+=1;
    await new Promise(resolve=>setTimeout(resolve,5));
    return new Response(JSON.stringify({
      access_token:"new-access",
      refresh_token:"new-refresh"
    }),{status:200,headers:{"Content-Type":"application/json"}});
  };
  try{
    const [first,second]=await Promise.all([refreshSession(),refreshSession()]);
    assert.equal(first,"new-access");
    assert.equal(second,"new-access");
    assert.equal(calls,1);
  }finally{
    globalThis.fetch=originalFetch;
    clearTokens();
  }
});

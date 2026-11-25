import test from "node:test";
import assert from "node:assert/strict";
import { esc, initials, safeUuid } from "../js/lib/dom.js";
import { mergedMessages } from "../js/lib/conversations.js";
import { accessToken, refreshToken, setTokens, clearTokens } from "../js/lib/session.js";

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
  assert.deepEqual(mergedMessages([m],[m]),[m]);
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

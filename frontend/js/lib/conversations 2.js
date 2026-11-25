import { api } from "./request.js";

export const createConversation = friend_id =>
  api("/conversations",{method:"POST",body:{friend_id}});
export const getHistory = (id,limit=100,offset=0) =>
  api(`/conversations/${encodeURIComponent(id)}/messages?limit=${limit}&offset=${offset}`);
export function mergedMessages(previous=[],incoming=[]) {
  const unique = new Map(previous.map(item=>[item.id,item]));
  for(const item of incoming){
    if(item && item.id && typeof item.body === "string")unique.set(item.id,item);
  }
  return [...unique.values()].sort((a,b)=>
    a.created_at===b.created_at ? String(a.id).localeCompare(String(b.id)) :
    String(a.created_at).localeCompare(String(b.created_at))
  );
}

import { api } from "./request.js";

export const getFriends = () => api("/friends");
export const getRequests = () => api("/friends/requests");
export const getConversations = () => api("/conversations");
export function sendInvite(rawCode) {
  const friend_code=String(rawCode||"").trim().toUpperCase();
  if (!/^FM-[A-Z2-9]{8}$/.test(friend_code)) {
    throw new Error("Use um código no formato FM-XXXXXXXX.");
  }
  return api("/friends/requests",{method:"POST",body:{friend_code}});
}
export const decideInvite = (id,action) =>
  api(`/friends/requests/${encodeURIComponent(id)}`,{method:"PATCH",body:{action}});

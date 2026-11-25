import { api } from "./request.js";

const defaults = Object.freeze({ muted:false, volume:100, senders:[] });
const cacheKey = userId => `friendsmeeting.notifications.${userId}`;

function normalize(preferences) {
  if (!preferences || typeof preferences !== "object") return {...defaults};
  return {
    muted:preferences.muted===true,
    volume:Number.isInteger(preferences.volume)?Math.min(100,Math.max(0,preferences.volume)):100,
    senders:Array.isArray(preferences.senders)?preferences.senders
      .filter(item=>item&&typeof item.user_id==="string")
      .map(item=>({
        user_id:item.user_id,
        muted:item.muted===true,
        volume_factor:Number.isInteger(item.volume_factor)
          ?Math.min(100,Math.max(0,item.volume_factor)):100
      })):[]
  };
}

function storeCache(userId, preferences) {
  try {
    localStorage.setItem(cacheKey(userId),JSON.stringify(normalize(preferences)));
  } catch(error) {
    console.warn("Não foi possível atualizar o cache das preferências de notificação.",error);
  }
}

export function cachedNotificationPreferences(userId) {
  try {
    const stored=localStorage.getItem(cacheKey(userId));
    return stored?normalize(JSON.parse(stored)):{...defaults};
  } catch(error) {
    console.warn("Não foi possível ler o cache das preferências de notificação.",error);
    return {...defaults};
  }
}

export async function loadNotificationPreferences(userId) {
  const preferences=normalize(await api("/notifications/preferences"));
  storeCache(userId,preferences);
  return preferences;
}

export async function saveNotificationPreferences(userId, update) {
  const preferences=normalize(await api("/notifications/preferences",{
    method:"PUT",
    body:update
  }));
  storeCache(userId,preferences);
  return preferences;
}

export async function saveSenderNotificationPreferences(userId,senderId,update) {
  const preferences=normalize(await api(
    `/notifications/preferences/senders/${encodeURIComponent(senderId)}`,
    {method:"PUT",body:update}
  ));
  storeCache(userId,preferences);
  return preferences;
}

export async function resetSenderNotificationPreferences(userId,senderId) {
  const preferences=normalize(await api(
    `/notifications/preferences/senders/${encodeURIComponent(senderId)}`,
    {method:"DELETE"}
  ));
  storeCache(userId,preferences);
  return preferences;
}

export function clearCachedNotificationPreferences(userId) {
  try {
    localStorage.removeItem(cacheKey(userId));
  } catch(error) {
    console.warn("Não foi possível remover o cache das preferências de notificação.",error);
  }
}

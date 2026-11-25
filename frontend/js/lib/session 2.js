// No access/refresh token is persisted to localStorage or written to the URL.
// A page refresh intentionally requires a fresh login until an HttpOnly cookie
// session is supported by the backend.
let currentAccess = "";
let currentRefresh = "";

export const accessToken = () => currentAccess;
export const refreshToken = () => currentRefresh;
export function setTokens(data) {
  if (!data || typeof data.access_token !== "string" || typeof data.refresh_token !== "string") {
    throw new Error("A API não retornou uma sessão válida.");
  }
  currentAccess = data.access_token;
  currentRefresh = data.refresh_token;
}
export function clearTokens() {
  currentAccess = "";
  currentRefresh = "";
}

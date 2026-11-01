import { accessToken, refreshToken, setTokens, clearTokens } from "./session.js";

export class ApiError extends Error {
  constructor(message, status) { super(message); this.name = "ApiError"; this.status = status; }
}
async function unpack(response) {
  if (response.status === 204) return null;
  const json = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = json?.detail;
    const message = typeof detail === "string" ? detail :
      Array.isArray(detail) ? detail.map(item => item.msg || "Campo inválido").join("; ") :
      "Não foi possível concluir esta ação.";
    throw new ApiError(message, response.status);
  }
  return json;
}
async function send(path,{method="GET",body,auth=true,retry=true}={}) {
  const headers = { Accept:"application/json" };
  if (body !== undefined && !(body instanceof FormData)) headers["Content-Type"]="application/json";
  if (auth && accessToken()) headers.Authorization = "Bearer " + accessToken();
  let response;
  try {
    response = await fetch("/api/v1" + path, {
      method, headers, body: body instanceof FormData ? body : body === undefined ? undefined : JSON.stringify(body),
      cache:"no-store", credentials:"same-origin"
    });
  } catch {
    throw new ApiError("Sem conexão. Verifique a API e o Docker.", 0);
  }
  if (response.status === 401 && auth && retry && refreshToken()) {
    await refreshSession();
    return send(path,{method,body,auth,retry:false});
  }
  return unpack(response);
}
export const api = send;
export async function refreshSession() {
  if (!refreshToken()) throw new ApiError("Sessão expirada. Entre novamente.",401);
  const tokens = await send("/auth/refresh",{
    method:"POST",body:{refresh_token:refreshToken()},auth:false
  });
  setTokens(tokens);
  return tokens.access_token;
}
export async function login(email,password) {
  const tokens=await send("/auth/login",{method:"POST",body:{email,password},auth:false});
  setTokens(tokens);
  return tokens;
}
export const register = (username,email,password) =>
  send("/auth/register",{method:"POST",body:{username,email,password},auth:false});
export async function logout() {
  const current = refreshToken();
  clearTokens();
  if (current) {
    try {await send("/auth/logout",{method:"POST",body:{refresh_token:current},auth:false});}
    catch {/* signing out locally always succeeds */}
  }
}
export const me = () => send("/users/me");

export const esc = value => String(value ?? "").replace(/[&<>"']/g, char => ({
  "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;"
}[char]));
export const $ = (selector, scope = document) => scope.querySelector(selector);
export const $$ = (selector, scope = document) => [...scope.querySelectorAll(selector)];
export const initials = name => (String(name || "F").trim().slice(0, 1) || "F").toUpperCase();
export const shortId = id => String(id || "").slice(0, 8);
export const fmtTime = value => {
  try { return new Intl.DateTimeFormat("pt-BR", { hour:"2-digit",minute:"2-digit" }).format(new Date(value)); }
  catch { return ""; }
};
export const fmtDate = value => {
  try { return new Intl.DateTimeFormat("pt-BR",{day:"2-digit",month:"long"}).format(new Date(value)); }
  catch { return ""; }
};
let toastTimer;
export function toast(message) {
  const node = $("#toast");
  if (!node) return;
  node.textContent = String(message);
  node.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => node.classList.remove("show"), 4600);
}
export function safeUuid(value) {
  return typeof value === "string" && /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value);
}

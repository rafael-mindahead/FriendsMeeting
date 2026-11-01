const KEY = "friendsmeeting.appearance";
const ALLOWED = new Set(["dark","light","system"]);
const media = window.matchMedia("(prefers-color-scheme: dark)");

export function preference() {
  const stored = localStorage.getItem(KEY);
  return ALLOWED.has(stored) ? stored : "system";
}
export function applyTheme(choice = preference()) {
  const resolved = choice === "system" ? (media.matches ? "dark" : "light") : choice;
  document.documentElement.dataset.theme = resolved;
  document.querySelector('meta[name="theme-color"]')?.setAttribute(
    "content", resolved === "dark" ? "#091311" : "#f7faf7"
  );
  return resolved;
}
export function setTheme(choice) {
  if (!ALLOWED.has(choice)) return;
  localStorage.setItem(KEY,choice);
  applyTheme(choice);
  window.dispatchEvent(new CustomEvent("friendsmeeting:theme",{detail:choice}));
}
export function initializeTheme() {
  applyTheme();
  media.addEventListener("change",()=>{if(preference()==="system")applyTheme();});
}

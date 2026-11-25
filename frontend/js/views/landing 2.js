import { initializeTheme, preference, setTheme } from "../lib/theme.js";

initializeTheme();
const button = document.querySelector("#landingTheme");
function label(){
  if(!button) return;
  const isDark=document.documentElement.dataset.theme==="dark";
  button.textContent=isDark?"☀":"☾";
  button.setAttribute("aria-label",isDark?"Ativar tema claro":"Ativar tema escuro");
}
label();
button?.addEventListener("click",()=>{
  setTheme(document.documentElement.dataset.theme==="dark"?"light":"dark");
  label();
});
window.addEventListener("friendsmeeting:theme",label);

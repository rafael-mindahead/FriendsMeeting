import { $, esc } from "../lib/dom.js";

const brand = `<a class="brand" href="/"><img src="/assets/logo.svg" alt="" width="36" height="36"><span>friends<span class="accent">meeting</span></span></a>`;

export function showAuth({mode="login",onMode,onSubmit,onDemo}) {
  const isRegister = mode === "register";
  const root = $("#appRoot");
  root.innerHTML = `
    <div class="auth-screen">
      <aside class="auth-left">
        ${brand}
        <div class="auth-story">
          <span class="eyebrow">As melhores conversas começam aqui</span>
          <h1>Mais perto de quem <em>importa.</em></h1>
          <p>Um espaço simples, bonito e privado para continuar o que você tem a dizer.</p>
          <div class="auth-quote"><small>Vinícius · agora</small>Bora continuar aquela conversa? ✨</div>
        </div>
        <a class="auth-back" href="/">← Voltar ao início</a>
      </aside>
      <main id="appMain" class="auth-right">
        <section class="auth-card" aria-label="${isRegister?"Cadastro":"Login"}">
          <span class="eyebrow">FriendsMeeting</span>
          <h2>${isRegister?"Seu espaço começa aqui.":"Bom ter você aqui."}</h2>
          <p>${isRegister?"Crie sua conta para encontrar seus amigos.":"Entre para continuar de onde a conversa parou."}</p>
          <div class="auth-tabs" role="group" aria-label="Acesso à conta">
            <button type="button" data-mode="login" class="${isRegister?"":"active"}" aria-pressed="${!isRegister}">Entrar</button>
            <button type="button" data-mode="register" class="${isRegister?"active":""}" aria-pressed="${isRegister}">Criar conta</button>
          </div>
          <form id="authForm">
            ${isRegister?`<div class="field"><label for="username">Nome de usuário</label><input id="username" name="username" autocomplete="username" required minlength="3" maxlength="32" pattern="[a-zA-Z0-9_]+" placeholder="seu_usuario"></div>`:""}
            <div class="field"><label for="email">E-mail</label><input id="email" name="email" type="email" autocomplete="email" required placeholder="voce@exemplo.com"></div>
            <div class="field"><label for="password">Senha</label><input id="password" name="password" type="password" autocomplete="${isRegister?"new-password":"current-password"}" required minlength="8" maxlength="128" placeholder="Pelo menos 8 caracteres"></div>
            <div id="authError" class="form-error" role="alert"></div>
            <button class="button primary auth-submit" type="submit">${isRegister?"Criar minha conta":"Entrar no FriendsMeeting"} <span aria-hidden="true">↗</span></button>
          </form>
          <p class="auth-footnote">${isRegister?"Seu nome de usuário pode ter letras, números e sublinhado.":"Sua sessão fica somente nesta aba."}</p>
          <button class="auth-demo" id="authDemo" type="button">Explorar demonstração sem login ↗</button>
        </section>
      </main>
    </div>`;
  root.querySelectorAll("[data-mode]").forEach(btn=>btn.addEventListener("click",()=>onMode(btn.dataset.mode)));
  $("#authDemo",root).addEventListener("click",onDemo);
  $("#authForm",root).addEventListener("submit",async event=>{
    event.preventDefault();
    const form=event.currentTarget;
    if(!form.reportValidity())return;
    const submit=form.querySelector('button[type="submit"]');
    const error=$("#authError",form);
    submit.disabled=true;error.textContent="";
    const data=new FormData(form);
    try{
      await onSubmit({mode,email:String(data.get("email")).trim(),password:String(data.get("password")),username:String(data.get("username")||"").trim()});
    }catch(err){
      error.textContent=err?.message || "Não foi possível acessar sua conta.";
    }finally{submit.disabled=false;}
  });
}

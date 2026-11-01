import { esc } from "../lib/dom.js";
import { avatar } from "../lib/avatars.js";

export function renderProfile(state){
  const user=state.user;
  return `<header class="panel-header"><div><h1>Meu perfil</h1><p>Seu jeito de estar aqui.</p></div></header>
  <div class="section-content">
    <section class="card-section">
      <div class="profile-hero">${avatar(user,"xlarge",state.avatarRevision)}
        <div class="profile-info"><h2>${esc(user.username)}</h2><p>${esc(user.email)}</p>
          <div class="profile-photo-actions">
            <label class="button primary" for="avatarUpload">Escolher foto</label>
            <input type="file" id="avatarUpload" accept="image/png,image/jpeg,image/webp" aria-label="Escolher foto de perfil" aria-describedby="avatarHelp">
            <button type="button" class="button ghost" data-action="remove-avatar" ${state.demo?"disabled":""}>Remover</button>
          </div>
        </div>
      </div>
      <p class="profile-upload-note" id="avatarHelp">PNG, JPG ou WebP, até 2 MB. A foto fica quadrada e você pode removê-la quando quiser.</p>
      <div class="profile-metadata">
        <div><span class="metadata-label">Nome de usuário</span><span class="metadata-value">${esc(user.username)}</span></div>
        <div><span class="metadata-label">E-mail</span><span class="metadata-value">${esc(user.email)}</span></div>
        <div><span class="metadata-label">Seu código de amizade</span><span class="metadata-value friend-code">${esc(user.friend_code)}</span></div>
        <div><span class="metadata-label">Compartilhar</span><button type="button" class="button ghost" data-action="copy-code">Copiar código</button></div>
      </div>
      <p class="privacy-disclaimer">A foto de perfil é pública para quem tiver o link ou seu identificador. Use uma imagem que você se sinta confortável em compartilhar.</p>
    </section>
    
  </div>`;
}

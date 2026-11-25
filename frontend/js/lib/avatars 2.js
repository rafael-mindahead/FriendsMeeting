import { esc, initials, safeUuid } from "./dom.js";

export function avatarUrl(user, revision = "") {
  if (!user || !safeUuid(user.id)) return "";
  const suffix = revision ? "?v="+encodeURIComponent(revision) : "";
  return "/api/v1/users/"+encodeURIComponent(user.id)+"/avatar"+suffix;
}
export function avatar(user, size = "", revision = "") {
  const name = user?.username || "Usuário";
  const src = avatarUrl(user,revision);
  return `<span class="avatar ${esc(size)}" aria-label="Foto de ${esc(name)}">
    ${esc(initials(name))}
    ${src ? `<img src="${esc(src)}" alt="" loading="lazy" decoding="async">` : ""}
  </span>`;
}
// Missing avatar is normal: remove broken <img> and leave initials visible.
export function bindAvatarFallbacks(scope = document) {
  scope.querySelectorAll(".avatar img").forEach(img => {
    img.addEventListener("error", () => img.remove(),{once:true});
  });
}
export async function uploadAvatar(file) {
  if (!file || file.size > 2 * 1024 * 1024) throw new Error("Escolha uma foto de até 2 MB.");
  if (!["image/png","image/jpeg","image/webp"].includes(file.type)) {
    throw new Error("Escolha uma imagem PNG, JPG ou WebP.");
  }
  const { api } = await import("./request.js");
  const form = new FormData();
  form.append("file",file,file.name);
  return api("/users/me/avatar",{method:"PUT",body:form});
}
export async function deleteAvatar() {
  const { api } = await import("./request.js");
  return api("/users/me/avatar",{method:"DELETE"});
}

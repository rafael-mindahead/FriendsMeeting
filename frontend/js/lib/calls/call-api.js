
import { api } from "../request.js";

export async function obterCredencialChamada() {
  const resposta = await api("/calls/auth/credential", {
    method: "POST"
  });

  if (
    !resposta ||
    typeof resposta.credential !== "string" ||
    !resposta.credential
  ) {
    throw new Error("Credencial de chamada inválida.");
  }

  return resposta.credential;
}

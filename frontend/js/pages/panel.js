import { getCurrentUser } from "../services/user-service.js";

const welcomeTitle = document.querySelector("#welcome-title");
const profileMessage = document.querySelector("#profile-message");

if (!welcomeTitle || !profileMessage) {
  throw new Error("Os elementos do perfil não foram encontrados na página.");
}

const accessToken = sessionStorage.getItem("access_token");

if (!accessToken) {
  welcomeTitle.textContent = "Sessão não encontrada";
  profileMessage.textContent = "Faça login para carregar seu perfil.";
} else {
  try {
    const user = await getCurrentUser(accessToken);

    welcomeTitle.textContent = `Olá, ${user.username}!`;
    profileMessage.textContent = user.email;
  } catch (error) {
    console.error("Falha ao carregar o perfil:", error);
    welcomeTitle.textContent = "Não foi possível carregar o perfil";
    profileMessage.textContent =
      error instanceof Error ? error.message : "Ocorreu um erro inesperado.";
  }
}   
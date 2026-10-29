import { apiRequest } from "../api.js";

const form = document.querySelector("#register-form");
const message = document.querySelector("#form-message");

if (!form || !message) {
  throw new Error("Não foi possível encontrar o formulário de cadastro.");
}

const submitButton = form.querySelector('button[type="submit"]');

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const formData = new FormData(form);
  const username = String(formData.get("username") ?? "").trim();
  const email = String(formData.get("email") ?? "").trim();
  const password = String(formData.get("password") ?? "");

  message.textContent = "Criando sua conta...";

  if (submitButton instanceof HTMLButtonElement) {
    submitButton.disabled = true;
  }

  try {
    await apiRequest("/auth/register", {
      method: "POST",
      body: { username, email, password },
    });

    message.textContent = "Cadastro realizado! Você já pode fazer login.";
    form.reset();
  } catch (error) {
    message.textContent =
      error instanceof Error ? error.message : "Ocorreu um erro inesperado.";
  } finally {
    if (submitButton instanceof HTMLButtonElement) {
      submitButton.disabled = false;
    }
  }
});
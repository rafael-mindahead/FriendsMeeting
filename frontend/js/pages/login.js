import {apiRequest} from "../api.js";

const form = document.querySelector("#login-form");
const message = document.querySelector("#form-message");

if (!form || !message) {
  throw new Error("Não foi possível encontrar o formulário de login.");
}

const submitButton = form.querySelector('button[type="submit"]');

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const formData = new FormData(form);
  const email = String(formData.get("email") ?? "").trim();
  const password = String(formData.get("password") ?? "");

  message.textContent = "Fazendo login...";
  
  if (submitButton instanceof HTMLButtonElement) {
    submitButton.disabled = true;
  }
  
  try {
    const tokens= await apiRequest("/auth/login", {
      method: "POST",
      body: { email, password },
    });
    
    if (
      typeof tokens.access_token !== "string" ||
      typeof tokens.refresh_token !== "string"
    ) {
      throw new Error("A API não retornou os tokens esperados.");
    }
    
    sessionStorage.setItem("access_token", tokens.access_token);
    sessionStorage.setItem("refresh_token", tokens.refresh_token);

    window.location.href = "./panel.html";
    
    message.textContent = "Login realizado!";

  } catch (error) {
    message.textContent =
    error instanceof Error ? error.message : "Não foi possivel fazer o login.";
  } finally {
    if (submitButton instanceof HTMLButtonElement) {
      submitButton.disabled = false;
    }
  }
});

const API_BASE_URL = "http://localhost:8000/api/v1";

export async function apiRequest(path, { method = "GET", body, token } = {}) {
  const headers = {};

  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  let response;

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new Error("Não foi possível conectar à API. Verifique se o backend está rodando.");
  }

  let data;

  try {
    data = await response.json();
  } catch {
    if (response.ok) {
      throw new Error("A API respondeu, mas enviou um conteúdo inesperado.");
    }
  }

  if (!response.ok) {
    const detail = data?.detail;

    if (typeof detail === "string") {
      throw new Error(detail);
    }

    if (Array.isArray(detail)) {
      throw new Error(detail.map((item) => item.msg).join(" "));
    }

    throw new Error("Não foi possível concluir a solicitação.");
  }

  return data;
}
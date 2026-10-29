import { apiRequest } from "../api.js";

export function getCurrentUser(accessToken) {
  return apiRequest("/users/me", {
    token: accessToken,
  });
}
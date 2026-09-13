const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function request(path, options = {}) {
  const resp = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!resp.ok) {
    let detail = `Request to ${path} failed (${resp.status})`;
    try {
      const body = await resp.json();
      detail = body.detail || detail;
    } catch {
      /* ignore parse errors */
    }
    throw new Error(detail);
  }
  return resp.json();
}

export function getOrCreateUserId() {
  const key = "lenny_assistant_user_id";
  let id = localStorage.getItem(key);
  if (!id) {
    id = `user_${crypto.randomUUID()}`;
    localStorage.setItem(key, id);
  }
  return id;
}

export const api = {
  createSession: (userId, llmProvider) =>
    request("/api/sessions", {
      method: "POST",
      body: JSON.stringify({ user_id: userId, llm_provider: llmProvider || null }),
    }),

  getHistory: (sessionId) => request(`/api/sessions/${sessionId}`),

  sendMessage: (sessionId, message, intent, artifactFormat) =>
    request("/api/chat", {
      method: "POST",
      body: JSON.stringify({
        session_id: sessionId,
        message,
        intent,
        artifact_format: artifactFormat || null,
      }),
    }),

  health: () => request("/health"),
};

import { useEffect, useRef, useState } from "react";
import { api, getOrCreateUserId } from "./lib/api";
import Message from "./components/Message";
import ArtifactViewer from "./components/ArtifactViewer";

const INTENTS = [
  { key: "chat", label: "Ask" },
  { key: "essay", label: "Turn into essay" },
  { key: "artifact", label: "Make a doc" },
];

export default function App() {
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [intent, setIntent] = useState("chat");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [health, setHealth] = useState(null);
  const [openArtifact, setOpenArtifact] = useState(null);
  const listRef = useRef(null);

  useEffect(() => {
    (async () => {
      try {
        const userId = getOrCreateUserId();
        const session = await api.createSession(userId);
        setSessionId(session.session_id);
      } catch (err) {
        setError(`Could not reach the backend: ${err.message}`);
      }
    })();

    const poll = async () => {
      try {
        const h = await api.health();
        setHealth(h);
      } catch {
        setHealth(null);
      }
    };
    poll();
    const interval = setInterval(poll, 15000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [messages]);

  async function handleSend() {
    if (!input.trim() || !sessionId || loading) return;
    const userText = input.trim();
    setInput("");
    setError(null);
    setMessages((prev) => [...prev, { role: "user", content: userText }]);
    setLoading(true);

    try {
      const artifactFormat = intent === "artifact" ? "html" : undefined;
      const res = await api.sendMessage(sessionId, userText, intent, artifactFormat);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: res.content,
          citations: res.citations,
          artifact: res.artifact,
          grounded: res.grounded,
        },
      ]);
      if (res.artifact) setOpenArtifact(res.artifact);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
      setIntent("chat");
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  const providerHealthy = health?.llm_provider_healthy;

  return (
    <div className="app-shell">
      <header className="app-header">
        <h1 className="app-title">
          The Lenny <em>Growth</em> Assistant
        </h1>
        <div className="provider-badge">
          <span className={`provider-dot ${providerHealthy ? "" : "offline"}`} />
          {health ? `${health.llm_provider} · ${health.knowledge_base_chunks} chunks indexed` : "connecting…"}
        </div>
      </header>

      <div className={`main-grid ${openArtifact ? "" : "no-artifact"}`}>
        <div className="chat-pane">
          {error && <div className="error-banner">{error}</div>}

          <div className="message-list" ref={listRef}>
            {messages.length === 0 && (
              <div className="empty-state">
                <h2>Ask about product & growth, sourced from Lenny's Podcast.</h2>
                <p>
                  Try: "How did Superhuman think about activation metrics?" — then ask to turn the
                  answer into an essay or a shareable one-pager.
                </p>
              </div>
            )}
            {messages.map((m, i) => (
              <Message key={i} message={m} onOpenArtifact={setOpenArtifact} />
            ))}
            {loading && (
              <div className="message-row assistant">
                <div className="message-role">Assistant</div>
                <div className="message-bubble">Thinking…</div>
              </div>
            )}
          </div>

          <div className="composer">
            <div className="intent-row">
              {INTENTS.map((it) => (
                <button
                  key={it.key}
                  className={`intent-pill ${intent === it.key ? "active" : ""}`}
                  onClick={() => setIntent(it.key)}
                >
                  {it.label}
                </button>
              ))}
            </div>
            <div className="composer-input-row">
              <textarea
                className="composer-textarea"
                placeholder="Ask a product or growth question…"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
              />
              <button className="send-button" onClick={handleSend} disabled={loading || !sessionId}>
                Send
              </button>
            </div>
          </div>
        </div>

        {openArtifact && (
          <>
            <div className="divider" />
            <ArtifactViewer artifact={openArtifact} onClose={() => setOpenArtifact(null)} />
          </>
        )}
      </div>
    </div>
  );
}

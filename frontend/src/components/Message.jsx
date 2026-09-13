import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export default function Message({ message, onOpenArtifact }) {
  const isUser = message.role === "user";

  return (
    <div className={`message-row ${isUser ? "user" : "assistant"}`}>
      <div className="message-role">{isUser ? "You" : "Assistant"}</div>
      <div className="message-bubble">
        {isUser ? (
          message.content
        ) : (
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
        )}
      </div>

      {!isUser && message.citations && message.citations.length > 0 && (
        <div className="citations">
          {message.citations.map((c) => (
            <span className="citation-chip" key={c.source_path + c.episode_title}>
              {c.episode_title}
            </span>
          ))}
        </div>
      )}

      {!isUser && message.grounded === false && !message.artifact && (
        <div className="not-grounded-note">Not covered in the transcripts I have.</div>
      )}

      {!isUser && message.artifact && (
        <div className="artifact-open-link" onClick={() => onOpenArtifact(message.artifact)}>
          Open generated {message.artifact.type === "html" ? "one-pager" : "document"} →
        </div>
      )}
    </div>
  );
}

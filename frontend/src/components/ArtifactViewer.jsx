import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

/**
 * Renders a generated artifact next to the chat.
 *
 * Security: HTML artifacts arrive already sanitized by the backend
 * (see app/skills/artifact_sanitizer.py), but we defend in depth here too —
 * the HTML is rendered inside an <iframe sandbox="allow-same-origin"> with
 * NO "allow-scripts", so even a sanitizer bypass cannot execute JS. Markdown
 * artifacts never touch dangerouslySetInnerHTML at all; react-markdown
 * renders them as React elements.
 */
export default function ArtifactViewer({ artifact, onClose }) {
  if (!artifact) return null;

  return (
    <div className="artifact-pane">
      <div className="artifact-header">
        <h3>{artifact.type === "html" ? "Generated one-pager" : "Generated document"}</h3>
        <button className="artifact-close" onClick={onClose}>
          Close ✕
        </button>
      </div>

      {artifact.type === "html" ? (
        <>
          <p className="sandbox-note">
            Rendered in a sandboxed frame with scripts disabled — generated HTML is treated as untrusted.
          </p>
          <div className="artifact-body">
            <iframe
              className="artifact-iframe"
              title="Generated artifact"
              sandbox="allow-same-origin"
              srcDoc={artifact.content}
            />
          </div>
        </>
      ) : (
        <div className="artifact-body markdown">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{artifact.content}</ReactMarkdown>
        </div>
      )}
    </div>
  );
}

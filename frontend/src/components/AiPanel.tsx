import type { ReactNode } from "react";
import { useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { Button, ButtonLink, ErrorBanner, Spinner } from "./ui";

// AI output rendered inline within a workflow step, not as a chat.
export function AiPanel({
  title,
  description,
  actionLabel,
  onRun,
  running,
  error,
  hasResult,
  children,
}: {
  title: string;
  description: string;
  actionLabel: string;
  onRun: () => void;
  running: boolean;
  error?: Error;
  hasResult: boolean;
  children?: ReactNode;
}) {
  // AI calls cost money, so they need an account; visitors get a sign-in link.
  const signedIn = !!useAuth().session;
  const location = useLocation();
  return (
    <section className="card ai-panel">
      <div className="card-header">
        <div>
          <h2>
            <span className="ai-tag">AI</span>
            {title}
          </h2>
          <p className="card-description">{description}</p>
        </div>
        <div className="card-actions">
          {signedIn ? (
            <Button onClick={onRun} loading={running} size="sm">
              {hasResult ? "Regenerate" : actionLabel}
            </Button>
          ) : (
            <ButtonLink to="/login" size="sm" state={{ from: location.pathname + location.search }}>
              Sign in to {actionLabel.charAt(0).toLowerCase() + actionLabel.slice(1)}
            </ButtonLink>
          )}
        </div>
      </div>
      {(running || error || hasResult) && (
        <div className="card-body">
          {running && !hasResult && (
            <div className="loading loading-inline">
              <Spinner small /> Generating with Gemini — this can take a few seconds…
            </div>
          )}
          <ErrorBanner error={error} />
          {hasResult && children}
          {hasResult && (
            <p className="ai-disclaimer">
              Generated from stored experiment data. Verify conclusions against the metrics.
            </p>
          )}
        </div>
      )}
    </section>
  );
}

// Render plain-text summaries with paragraph breaks and simple bullets.
export function AiText({ text }: { text: string }) {
  const blocks = text.split(/\n{2,}/).map((b) => b.trim()).filter(Boolean);
  return (
    <div className="ai-text">
      {blocks.map((block, i) => {
        const lines = block.split("\n");
        if (lines.every((l) => /^\s*([-*•]|\d+\.)\s+/.test(l))) {
          return (
            <ul key={i}>
              {lines.map((l, j) => (
                <li key={j}>{l.replace(/^\s*([-*•]|\d+\.)\s+/, "").replace(/\*\*/g, "")}</li>
              ))}
            </ul>
          );
        }
        return <p key={i}>{block.replace(/\*\*/g, "")}</p>;
      })}
    </div>
  );
}

import { useState } from "react";
import { Badge, ErrorBanner } from "./ui";

export function VisibilityBadge({ isPublic }: { isPublic: boolean | null | undefined }) {
  if (isPublic === null || isPublic === undefined) return null;
  return isPublic ? <Badge tone="accent-plain">Public</Badge> : <Badge tone="warning">Private</Badge>;
}

export function OwnerBadge({ name }: { name: string | null | undefined }) {
  return <span className="owner-chip">by {name ?? "another user"}</span>;
}

/** Owner-only public/private switch that saves immediately. */
export function VisibilityToggle({
  isPublic,
  onChange,
  description,
}: {
  isPublic: boolean;
  onChange: (next: boolean) => Promise<unknown>;
  description: string;
}) {
  const [value, setValue] = useState(isPublic);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<Error>();

  async function toggle(next: boolean) {
    setSaving(true);
    setError(undefined);
    setValue(next);
    try {
      await onChange(next);
    } catch (err) {
      setValue(!next);
      setError(err as Error);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="stack-sm">
      <div className="segmented segmented-sm" aria-busy={saving}>
        <button type="button" className={value ? "active" : ""} disabled={saving} onClick={() => !value && toggle(true)}>
          Public
        </button>
        <button type="button" className={!value ? "active" : ""} disabled={saving} onClick={() => value && toggle(false)}>
          Private
        </button>
      </div>
      <p className="muted small">{value ? description : "Only you can see this."}</p>
      <ErrorBanner error={error} />
    </div>
  );
}

import { useRef, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/endpoints";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorBanner,
  Field,
  Loading,
  PageHeader,
} from "../components/ui";
import { useUser } from "../context/AuthContext";
import { VisibilityBadge } from "../components/Visibility";
import { useAction, useAsync } from "../hooks/useAsync";
import { formatDate, formatInt } from "../lib/format";

const MAX_BYTES = 10 * 1024 * 1024;

export function Datasets() {
  const navigate = useNavigate();
  const state = useAsync(() => Promise.all([api.datasets.list(), api.experiments.list()]), []);

  const [datasets = [], experiments = []] = state.data ?? [];
  const visible = datasets
    .sort((a, b) => b.dataset_id - a.dataset_id);
  const runCount = new Map<number, number>();
  experiments.forEach((e) => runCount.set(e.dataset_id, (runCount.get(e.dataset_id) ?? 0) + 1));

  return (
    <>
      <PageHeader title="My datasets" subtitle="Upload CSV files, inspect them and prepare them for training. Looking for data to start with? Browse Discover." />
      <div className="grid-main-side">
        <Card
          title="Your datasets"
          flush
        >
          <ErrorBanner error={state.error} onRetry={state.reload} />
          {state.loading && !state.data ? (
            <Loading />
          ) : visible.length === 0 ? (
            <EmptyState
              title="No datasets yet"
              description="Upload a CSV file to start. Files up to 10 MiB, UTF-8 encoded."
            />
          ) : (
            <div className="table-wrap">
              <table className="table table-hover">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th className="num">Rows</th>
                    <th className="num">Columns</th>
                    <th className="num">Experiments</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {visible.map((d) => (
                    <tr key={d.dataset_id} onClick={() => navigate(`/datasets/${d.dataset_id}`)} className="clickable">
                      <td>
                        <Link to={`/datasets/${d.dataset_id}`} className="row-link">
                          {d.name}
                        </Link>
                        <div className="muted small">
                          #{d.dataset_id} · {formatDate(d.created_at)} {!d.is_public && <VisibilityBadge isPublic={false} />}
                          {d.cleaning_metadata && <> · cleaned from #{d.cleaning_metadata.source_dataset_id}</>}
                        </div>
                      </td>
                      <td className="num mono">{formatInt(d.rows)}</td>
                      <td className="num mono">{formatInt(d.cols)}</td>
                      <td className="num">
                        {runCount.get(d.dataset_id) ? <Badge tone="accent">{runCount.get(d.dataset_id)}</Badge> : <span className="muted">—</span>}
                      </td>
                      <td className="num muted">›</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        <UploadCard onUploaded={(id) => navigate(`/datasets/${id}`)} />
      </div>
    </>
  );
}

function UploadCard({ onUploaded }: { onUploaded: (id: number) => void }) {
  const { user } = useUser();
  const [name, setName] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [isPublic, setIsPublic] = useState(true);
  const [description, setDescription] = useState("");
  const [localError, setLocalError] = useState<string>();
  const inputRef = useRef<HTMLInputElement>(null);
  const upload = useAction(api.datasets.upload);

  function pick(f: File | undefined) {
    setLocalError(undefined);
    if (!f) return;
    if (!f.name.toLowerCase().endsWith(".csv")) {
      setLocalError("Only .csv files are supported.");
      return;
    }
    if (f.size > MAX_BYTES) {
      setLocalError("CSV file must not exceed 10 MiB.");
      return;
    }
    setFile(f);
    if (!name) setName(f.name.replace(/\.csv$/i, ""));
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!file || !user) return;
    const saved = await upload.run(name.trim(), file, isPublic, description.trim());
    if (saved) onUploaded(saved.dataset_id);
  }

  return (
    <Card title="Upload CSV" description="Stored in Supabase Storage and registered for this user.">
      <form onSubmit={submit} className="stack-sm">
        <div
          className={`dropzone ${dragging ? "dragging" : ""} ${file ? "has-file" : ""}`}
          onClick={() => inputRef.current?.click()}
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            pick(e.dataTransfer.files[0]);
          }}
        >
          <input
            ref={inputRef}
            type="file"
            accept=".csv,text/csv"
            hidden
            onChange={(e) => pick(e.target.files?.[0])}
          />
          {file ? (
            <>
              <strong>{file.name}</strong>
              <span className="muted small">{(file.size / 1024).toFixed(1)} KB · click to change</span>
            </>
          ) : (
            <>
              <strong>Drop a CSV here</strong>
              <span className="muted small">or click to browse · max 10 MiB</span>
            </>
          )}
        </div>
        <Field label="Dataset name" htmlFor="ds-name" hint="Must be unique among your datasets.">
          <input id="ds-name" value={name} onChange={(e) => setName(e.target.value)} required />
        </Field>
        <Field label="Description" htmlFor="ds-desc" hint="Optional. Shown in Discover if the dataset is public.">
          <textarea id="ds-desc" rows={2} value={description} onChange={(e) => setDescription(e.target.value)} maxLength={2000} />
        </Field>
        <label className="toggle">
          <input type="checkbox" checked={isPublic} onChange={(e) => setIsPublic(e.target.checked)} />
          <span>
            Public <span className="muted small">— listed in Discover for anyone to explore</span>
          </span>
        </label>
        <ErrorBanner error={localError ?? upload.error} />
        <Button type="submit" variant="primary" loading={upload.running} disabled={!file || !name.trim() || !user}>
          Upload dataset
        </Button>
      </form>
    </Card>
  );
}

import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { api } from "../api/endpoints";
import type { CleanDatasetResponse, CleanMissingStrategy, DatasetInspection, DatasetPreview, DatasetSummary } from "../api/types";
import { AiPanel, AiText } from "../components/AiPanel";
import {
  Alert,
  Badge,
  Button,
  ButtonLink,
  Card,
  ConfirmDelete,
  EmptyState,
  ErrorBanner,
  Field,
  KeyValue,
  Loading,
  Modal,
  PageHeader,
  Stat,
} from "../components/ui";
import { useAuth, useUser } from "../context/AuthContext";
import { OwnerBadge, VisibilityBadge, VisibilityToggle } from "../components/Visibility";
import { useAction, useAsync } from "../hooks/useAsync";
import { formatDate, formatInt, formatNumber, formatPercent, primaryMetric, type MetricDisplay } from "../lib/format";

interface ExperimentRow {
  experiment_id: number;
  algorithm: string;
  target: string;
  created_at: string;
  is_public: boolean;
  task_type: string;
  metric: MetricDisplay;
}

export function DatasetDetail() {
  const id = Number(useParams().datasetId);
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useUser();
  const signedIn = !!useAuth().session;
  const meta = useAsync(() => api.datasets.get(id), [id]);
  const inspection = useAsync(() => api.datasets.inspect(id), [id]);
  const preview = useAsync(() => api.datasets.preview(id), [id]);
  const ownerId = meta.data?.added_by;
  const isOwner = ownerId !== undefined && ownerId === user?.user_id;
  // Owners see all their runs on this dataset; others see the public ones.
  const experiments = useAsync<ExperimentRow[]>(async () => {
    if (ownerId === undefined) return [];
    if (isOwner) {
      const mine = await api.experiments.list();
      return mine
        .filter((e) => e.dataset_id === id)
        .map((e) => ({ ...e, task_type: e.parameters?.task_type ?? "classification", metric: primaryMetric(e) }));
    }
    const shared = await api.explore.experiments({ dataset_id: id });
    return shared.map((e) => ({
      ...e,
      is_public: true,
      metric:
        e.task_type === "regression"
          ? { label: "R²", value: formatNumber(e.results.r2) }
          : { label: "Accuracy", value: formatPercent(e.results.accuracy) },
    }));
  }, [id, ownerId, isOwner]);
  const [copying, setCopying] = useState(false);
  const explain = useAction(() => api.datasets.explain(id));
  const download = useAction(() => api.datasets.download(id));
  const [renaming, setRenaming] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const remove = useAction(() => api.datasets.remove(id));

  if (meta.loading && !meta.data) return <Loading />;
  if (meta.error || !meta.data)
    return (
      <>
        <PageHeader title="Dataset" breadcrumb={{ label: "Discover", to: "/discover" }} />
        <ErrorBanner error={meta.error ?? "Dataset not found"} onRetry={meta.reload} />
        {!signedIn && (
          <p className="muted small" style={{ marginTop: 12 }}>
            If this is one of your private datasets, <Link to="/login" state={{ from: location.pathname }}>sign in</Link> to open it.
          </p>
        )}
      </>
    );

  const dataset = meta.data;
  const owned = isOwner;

  return (
    <>
      <PageHeader
        breadcrumb={owned ? { label: "My datasets", to: "/datasets" } : { label: "Discover", to: "/discover" }}
        title={dataset.name}
        subtitle={
          <>
            {formatInt(dataset.rows)} rows × {formatInt(dataset.cols)} columns{" "}
            {owned && <VisibilityBadge isPublic={dataset.is_public} />}
            {dataset.is_featured ? <span className="owner-chip">Curated by MLens</span> : !owned && <OwnerBadge name={dataset.owner_name} />}
          </>
        }
        actions={
          <>
            {signedIn && (
              <Button onClick={() => download.run()} loading={download.running}>
                Download CSV
              </Button>
            )}
            {owned && <Button onClick={() => setRenaming(true)}>Edit details</Button>}
            {owned && (
              <Button variant="ghost" className="text-danger" onClick={() => setDeleting(true)}>
                Delete
              </Button>
            )}
            {owned ? (
              <ButtonLink to={`/experiments/new?dataset=${id}`} variant="primary">
                Train experiment
              </ButtonLink>
            ) : signedIn ? (
              <Button variant="primary" onClick={() => setCopying(true)}>
                Use this dataset
              </Button>
            ) : (
              <ButtonLink to="/login" state={{ from: location.pathname }} variant="primary">
                Sign in to use this dataset
              </ButtonLink>
            )}
          </>
        }
      />
      <ErrorBanner error={download.error} />

      <div className="stack">
        {(dataset.description || dataset.source || dataset.tags.length > 0) && (
          <AboutCard dataset={dataset} />
        )}

        <PreviewCard state={preview} />

        <InspectionSection state={inspection} />

        <AiPanel
          title="Explain dataset"
          description="Summarises structure, data quality issues and what to check before training."
          actionLabel="Explain dataset"
          onRun={() => explain.run()}
          running={explain.running}
          error={explain.error}
          hasResult={!!explain.result}
        >
          {explain.result && <AiText text={explain.result.summary} />}
        </AiPanel>

        {owned && (
          <Card title="Visibility">
            <VisibilityToggle
              isPublic={dataset.is_public}
              description="Anyone can find it in Discover and view its profile and preview. Signed-in users can download it and use it for their own experiments."
              onChange={async (next) => {
                await api.datasets.setPublic(id, next);
                meta.setData({ ...dataset, is_public: next });
              }}
            />
          </Card>
        )}

        {owned && inspection.data && (
          <CleanCard dataset={dataset} inspection={inspection.data}  />
        )}

        <Card
          title={owned ? "Experiments on this dataset" : "Example experiments"}
          description={owned ? undefined : "Runs already trained on this dataset. Open one to see its configuration and metrics."}
          actions={experiments.data && <CompareLinks rows={experiments.data} />}
          flush
        >
          {experiments.loading && !experiments.data ? (
            <Loading />
          ) : !experiments.data?.length ? (
            <EmptyState
              title="No experiments yet"
              description={owned ? "Train a classification or regression model using this dataset." : "Use this dataset to train your own models on it."}
              action={owned && <ButtonLink to={`/experiments/new?dataset=${id}`} variant="primary">Train experiment</ButtonLink>}
            />
          ) : (
            <div className="table-wrap">
              <table className="table table-hover">
                <thead>
                  <tr>
                    <th>Experiment</th>
                    <th>Target</th>
                    <th className="num">Score</th>
                    <th>Created</th>
                  </tr>
                </thead>
                <tbody>
                  {experiments.data.map((e) => {
                    const m = e.metric;
                    return (
                      <tr key={e.experiment_id}>
                        <td>
                          <Link className="row-link" to={`/experiments/${e.experiment_id}`}>
                            {e.algorithm}
                          </Link>
                          <div className="muted small">#{e.experiment_id} {owned && !e.is_public && <VisibilityBadge isPublic={false} />}</div>
                        </td>
                        <td className="mono">{e.target}</td>
                        <td className="num mono">
                          {m.value} <span className="muted small">{m.label}</span>
                        </td>
                        <td className="muted small">{formatDate(e.created_at)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>

      {copying && (
        <CopyDialog
          dataset={dataset}
          onClose={() => setCopying(false)}
          onCopied={(newId) => navigate(`/experiments/new?dataset=${newId}`)}
        />
      )}
      {renaming && (
        <EditDetailsDialog
          dataset={dataset}
          onClose={() => setRenaming(false)}
          onSaved={(changes) => {
            meta.setData({ ...dataset, ...changes });
            setRenaming(false);
          }}
        />
      )}
      {deleting && (
        <ConfirmDelete
          title="Delete dataset"
          message={
            <>
              This removes <strong>{dataset.name}</strong> and its stored CSV. Datasets referenced by experiments
              or prediction results cannot be deleted.
            </>
          }
          running={remove.running}
          error={remove.error}
          onClose={() => setDeleting(false)}
          onConfirm={async () => {
            if (await remove.run()) navigate("/datasets");
          }}
        />
      )}
    </>
  );
}

function InspectionSection({ state }: { state: ReturnType<typeof useAsync<DatasetInspection>> }) {
  if (state.loading && !state.data) return <Card title="Profile"><Loading label="Inspecting dataset…" /></Card>;
  if (state.error || !state.data)
    return (
      <Card title="Profile">
        <ErrorBanner error={state.error} onRetry={state.reload} title="Could not inspect dataset" />
      </Card>
    );

  const d = state.data;
  const cells = d.rows * d.cols;
  return (
    <>
      <div className="stats-row stats-cards">
        <Stat label="Rows" value={formatInt(d.rows)} />
        <Stat label="Columns" value={formatInt(d.cols)} />
        <Stat
          label="Missing values"
          value={formatInt(d.total_missing_values)}
          hint={cells ? `${formatPercent(d.total_missing_values / cells, 2)} of cells` : undefined}
        />
        <Stat
          label="Duplicate rows"
          value={formatInt(d.duplicate_rows)}
          hint={d.rows ? `${formatPercent(d.duplicate_rows / d.rows, 2)} of rows` : undefined}
        />
      </div>

      <Card title="Columns" description="Types as inferred by pandas when reading the CSV." flush>
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>#</th>
                <th>Column</th>
                <th>Type</th>
                <th className="num">Missing</th>
                <th className="bar-col">Completeness</th>
              </tr>
            </thead>
            <tbody>
              {d.column_names.map((col, i) => {
                const missing = d.missing_values[col] ?? 0;
                const complete = d.rows ? 1 - missing / d.rows : 1;
                return (
                  <tr key={col}>
                    <td className="muted mono small">{i + 1}</td>
                    <td className="mono">{col}</td>
                    <td>
                      <Badge tone={isNumericType(d.column_types[col]) ? "accent" : "neutral"}>
                        {d.column_types[col]}
                      </Badge>
                    </td>
                    <td className="num mono">{missing ? formatInt(missing) : <span className="muted">0</span>}</td>
                    <td className="bar-col">
                      <div className="bar-track">
                        <div
                          className={`bar-fill ${complete < 0.9 ? "bar-warn" : ""}`}
                          style={{ width: `${complete * 100}%` }}
                        />
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>
    </>
  );
}

export function isNumericType(dtype: string | undefined): boolean {
  return !!dtype && /^(u?int|float|Int|Float|UInt)/.test(dtype);
}

function CleanCard({
  dataset,
  inspection,
}: {
  dataset: DatasetSummary;
  inspection: DatasetInspection;
}) {
  const [name, setName] = useState(`${dataset.name}_cleaned`);
  const [dropDuplicates, setDropDuplicates] = useState(inspection.duplicate_rows > 0);
  const [strategy, setStrategy] = useState<CleanMissingStrategy>("none");
  const [limitColumns, setLimitColumns] = useState(false);
  const [columns, setColumns] = useState<string[]>([]);
  const clean = useAction(api.datasets.clean);

  const columnsWithMissing = inspection.column_names.filter((c) => (inspection.missing_values[c] ?? 0) > 0);
  const nothingSelected = !dropDuplicates && strategy === "none";

  async function submit(e: FormEvent) {
    e.preventDefault();
    await clean.run(dataset.dataset_id, {
      name: name.trim(),
      drop_duplicates: dropDuplicates,
      missing_strategy: strategy,
      columns: strategy !== "none" && limitColumns && columns.length ? columns : null,
    });
  }

  return (
    <Card
      title="Clean dataset"
      description="Creates a new dataset; the original is kept unchanged."
    >
      {clean.result ? (
        <CleanResult result={clean.result} onReset={clean.reset} />
      ) : (
        <form onSubmit={submit} className="stack-sm">
          <div className="grid-2">
            <Field label="Remove duplicate rows" hint={`${formatInt(inspection.duplicate_rows)} duplicates found`}>
              <label className="toggle">
                <input type="checkbox" checked={dropDuplicates} onChange={(e) => setDropDuplicates(e.target.checked)} />
                Drop duplicates
              </label>
            </Field>
            <Field label="Missing values" htmlFor="clean-strategy" hint={`${formatInt(inspection.total_missing_values)} missing cells`}>
              <select id="clean-strategy" value={strategy} onChange={(e) => setStrategy(e.target.value as CleanMissingStrategy)}>
                <option value="none">Leave as is</option>
                <option value="drop">Drop rows with missing values</option>
                <option value="mean">Fill with column mean</option>
                <option value="median">Fill with column median</option>
              </select>
            </Field>
          </div>

          {strategy !== "none" && (
            <div className="subtle-box">
              <label className="toggle">
                <input type="checkbox" checked={limitColumns} onChange={(e) => setLimitColumns(e.target.checked)} />
                Only apply to selected columns
              </label>
              {limitColumns && (
                <div className="check-grid" style={{ marginTop: 10 }}>
                  {(columnsWithMissing.length ? columnsWithMissing : inspection.column_names).map((c) => (
                    <label key={c} className="check-item">
                      <input
                        type="checkbox"
                        checked={columns.includes(c)}
                        onChange={(e) =>
                          setColumns(e.target.checked ? [...columns, c] : columns.filter((x) => x !== c))
                        }
                      />
                      <span className="mono">{c}</span>
                      <span className="muted small">{inspection.missing_values[c] ?? 0}</span>
                    </label>
                  ))}
                </div>
              )}
              {(strategy === "mean" || strategy === "median") && (
                <p className="muted small" style={{ marginTop: 10 }}>
                  Imputing across the full dataset leaks test information into training. For evaluation, prefer
                  training-pipeline imputation in the experiment settings.
                </p>
              )}
            </div>
          )}

          <Field label="New dataset name" htmlFor="clean-name">
            <input id="clean-name" value={name} onChange={(e) => setName(e.target.value)} required />
          </Field>
          <ErrorBanner error={clean.error} />
          <div>
            <Button type="submit" variant="primary" loading={clean.running} disabled={nothingSelected || !name.trim()}>
              Create cleaned dataset
            </Button>
            {nothingSelected && <span className="muted small" style={{ marginLeft: 12 }}>Select at least one operation.</span>}
          </div>
        </form>
      )}
    </Card>
  );
}

function CleanResult({ result, onReset }: { result: CleanDatasetResponse; onReset: () => void }) {
  const m = result.cleaning_metadata;
  return (
    <div className="stack-sm">
      <Alert tone="success">
        Created <strong>{result.name}</strong> (#{result.dataset_id}) — {formatInt(m.rows_before)} →{" "}
        {formatInt(m.rows_after)} rows.
      </Alert>
      {m.warnings.map((w) => (
        <Alert key={w} tone="warning">
          {w}
        </Alert>
      ))}
      <KeyValue
        items={[
          ["Duplicates removed", formatInt(m.duplicates_removed)],
          ["Rows removed for missing values", formatInt(m.missing_rows_removed)],
          ["Missing values", `${formatInt(m.missing_values_before)} → ${formatInt(m.missing_values_after)}`],
          ["Strategy", m.missing_strategy],
        ]}
      />
      <div className="row-gap">
        <ButtonLink to={`/datasets/${result.dataset_id}`} variant="primary">
          Open cleaned dataset
        </ButtonLink>
        <Button variant="ghost" onClick={onReset}>
          Clean again
        </Button>
      </div>
    </div>
  );
}

function EditDetailsDialog({
  dataset,
  onClose,
  onSaved,
}: {
  dataset: DatasetSummary;
  onClose: () => void;
  onSaved: (changes: Partial<DatasetSummary>) => void;
}) {
  const [name, setName] = useState(dataset.name);
  const [description, setDescription] = useState(dataset.description ?? "");
  const [source, setSource] = useState(dataset.source ?? "");
  const [tags, setTags] = useState(dataset.tags.join(", "));
  const save = useAction(api.datasets.update);

  async function submit() {
    const changes = {
      name: name.trim(),
      description: description.trim() || null,
      source: source.trim() || null,
      tags: tags.split(",").map((t) => t.trim()).filter(Boolean).slice(0, 8),
    };
    if (await save.run(dataset.dataset_id, changes)) onSaved(changes);
  }

  return (
    <Modal
      title="Edit dataset details"
      onClose={onClose}
      footer={
        <>
          <Button onClick={onClose}>Cancel</Button>
          <Button variant="primary" loading={save.running} disabled={!name.trim()} onClick={submit}>
            Save details
          </Button>
        </>
      }
    >
      <Field label="Name" htmlFor="ed-name">
        <input id="ed-name" value={name} onChange={(e) => setName(e.target.value)} autoFocus />
      </Field>
      <Field label="Description" htmlFor="ed-desc" hint="Shown in Discover when the dataset is public.">
        <textarea id="ed-desc" rows={3} value={description} onChange={(e) => setDescription(e.target.value)} maxLength={2000} />
      </Field>
      <Field label="Source" htmlFor="ed-source" hint="Where the data comes from, and its licence if known.">
        <input id="ed-source" value={source} onChange={(e) => setSource(e.target.value)} maxLength={500} />
      </Field>
      <Field label="Tags" htmlFor="ed-tags" hint="Comma-separated, up to 8. For example: regression, missing values">
        <input id="ed-tags" value={tags} onChange={(e) => setTags(e.target.value)} />
      </Field>
      <ErrorBanner error={save.error} />
    </Modal>
  );
}

function CopyDialog({
  dataset,
  onClose,
  onCopied,
}: {
  dataset: DatasetSummary;
  onClose: () => void;
  onCopied: (id: number) => void;
}) {
  const [name, setName] = useState(dataset.name);
  const [isPublic, setIsPublic] = useState(false);
  const copy = useAction(api.datasets.copy);
  return (
    <Modal
      title="Use this dataset"
      onClose={onClose}
      footer={
        <>
          <Button onClick={onClose}>Cancel</Button>
          <Button
            variant="primary"
            loading={copy.running}
            disabled={!name.trim()}
            onClick={async () => {
              const saved = await copy.run(dataset.dataset_id, name.trim(), isPublic);
              if (saved) onCopied(saved.dataset_id);
            }}
          >
            Add and start an experiment
          </Button>
        </>
      }
    >
      <p className="muted small">
        MLens adds your own copy to My datasets, so you can clean it and train on it. Your experiments keep working even if
        the original is changed or deleted, and the original stays exactly as it is.
      </p>
      <Field label="Name in My datasets" htmlFor="copy-name">
        <input id="copy-name" value={name} onChange={(e) => setName(e.target.value)} autoFocus />
      </Field>
      <label className="toggle">
        <input type="checkbox" checked={isPublic} onChange={(e) => setIsPublic(e.target.checked)} />
        Share my copy publicly in Discover
      </label>
      <ErrorBanner error={copy.error} />
    </Modal>
  );
}

function AboutCard({ dataset }: { dataset: DatasetSummary }) {
  return (
    <Card title="About this dataset">
      {dataset.description && <p className="about-text">{dataset.description}</p>}
      {dataset.tags.length > 0 && (
        <div className="chips">
          {dataset.tags.map((t) => (
            <span key={t} className="chip chip-tag">{t}</span>
          ))}
        </div>
      )}
      {dataset.source && (
        <p className="muted small">
          <strong>Source:</strong> {dataset.source}
        </p>
      )}
    </Card>
  );
}

function PreviewCard({ state }: { state: ReturnType<typeof useAsync<DatasetPreview>> }) {
  return (
    <Card
      title="Data preview"
      description={state.data ? `First ${state.data.rows.length} of ${formatInt(state.data.total_rows)} rows.` : undefined}
      flush
    >
      {state.loading && !state.data ? (
        <Loading label="Loading preview…" />
      ) : state.error || !state.data ? (
        <div style={{ padding: 20 }}>
          <ErrorBanner error={state.error ?? "Preview unavailable"} onRetry={state.reload} />
        </div>
      ) : (
        <div className="table-wrap preview-grid">
          <table className="table table-compact">
            <thead>
              <tr>
                {state.data.columns.map((c) => (
                  <th key={c} className="mono">{c}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {state.data.rows.map((row, i) => (
                <tr key={i}>
                  {row.map((cell, j) => (
                    <td key={j} className={cell === null ? "cell-null" : "mono"}>
                      {cell === null ? "missing" : typeof cell === "number" && !Number.isInteger(cell) ? formatNumber(cell, 4) : String(cell)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

// Links to compare runs that share a target and task (what the API can compare).
function CompareLinks({ rows }: { rows: ExperimentRow[] }) {
  const groups = new Map<string, ExperimentRow[]>();
  rows.forEach((r) => {
    const key = `${r.target}|${r.task_type}`;
    groups.set(key, [...(groups.get(key) ?? []), r]);
  });
  const comparable = [...groups.values()].filter((g) => g.length >= 2);
  if (!comparable.length) return null;
  return (
    <div className="row-gap">
      {comparable.map((g) => (
        <ButtonLink
          key={g[0].target + g[0].task_type}
          size="sm"
          to={`/experiments/compare?ids=${g.slice(0, 10).map((r) => r.experiment_id).sort((a, b) => a - b).join(",")}`}
        >
          Compare {Math.min(g.length, 10)} runs on {g[0].target}
        </ButtonLink>
      ))}
    </div>
  );
}

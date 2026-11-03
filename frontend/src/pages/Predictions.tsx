import { useMemo, useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api/endpoints";
import type { PredictResponse, PredictionResultRecord } from "../api/types";
import {
  Alert,
  Button,
  ButtonLink,
  Card,
  Chips,
  EmptyState,
  ErrorBanner,
  Field,
  KeyValue,
  Loading,
  PageHeader,
  Stat,
} from "../components/ui";
import { useUser } from "../context/AuthContext";
import { useAction, useAsync } from "../hooks/useAsync";
import { formatDate, formatInt, formatNumber, taskTypeOf } from "../lib/format";

export function Predictions() {
  const { user } = useUser();
  const [search, setSearch] = useSearchParams();
  const state = useAsync(
    () => Promise.all([api.models.list(), api.experiments.list(), api.datasets.list()]),
    [],
  );
  const [modelId, setModelId] = useState<number | undefined>(Number(search.get("model")) || undefined);
  const [datasetId, setDatasetId] = useState<number>();
  const [saveResults, setSaveResults] = useState(true);
  const predict = useAction(api.predictions.run);
  const saved = useAsync(() => api.predictions.list(), []);

  // A public model from another user, opened via ?model= (e.g. from Explore).
  // Kept from the first load so the option stays while switching models.
  const [urlModel] = useState(() => Number(search.get("model")) || undefined);
  const ownModelIds = state.data?.[0].map((m) => m.model_id);
  const shared = useAsync(async () => {
    if (!urlModel || !ownModelIds || ownModelIds.includes(urlModel)) return undefined;
    const sharedModel = await api.models.get(urlModel);
    const sharedExperiment = await api.experiments.get(sharedModel.experiment_id);
    return { model: sharedModel, experiment: sharedExperiment };
  }, [urlModel, ownModelIds?.join(",")]);

  const [ownModels = [], experiments = [], datasets = []] = state.data ?? [];
  const experimentById = new Map(experiments.map((e) => [e.experiment_id, e]));
  if (shared.data) experimentById.set(shared.data.experiment.experiment_id, shared.data.experiment);
  const myModels = [...ownModels, ...(shared.data ? [shared.data.model] : [])].sort((a, b) => b.model_id - a.model_id);
  const myDatasets = [...datasets].sort((a, b) => b.dataset_id - a.dataset_id);
  const datasetName = new Map(datasets.map((d) => [d.dataset_id, d.name]));
  const model = myModels.find((m) => m.model_id === modelId);
  const experiment = model ? experimentById.get(model.experiment_id) : undefined;

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!user || !modelId || !datasetId) return;
    const result = await predict.run({ model_id: modelId, dataset_id: datasetId, save_results: saveResults });
    if (result?.prediction_result_id) saved.reload();
  }

  if (state.loading && !state.data) return <Loading />;

  return (
    <>
      <PageHeader
        title="Predictions"
        subtitle="Apply a saved model to a dataset that contains the model's feature columns."
      />
      <ErrorBanner error={state.error} onRetry={state.reload} />
      <ErrorBanner error={shared.error} title="Could not open the shared model" />

      {myModels.length === 0 ? (
        <Card>
          <EmptyState
            title="No models yet"
            description="Save a model when training an experiment, or use a public model shared by someone else."
            action={
              <div className="row-gap">
                <ButtonLink to="/discover?tab=models">Browse public models</ButtonLink>
                <ButtonLink to="/experiments/new" variant="primary">Train a model</ButtonLink>
              </div>
            }
          />
        </Card>
      ) : (
        <div className="stack">
          <div className="grid-main-side">
            <Card title="Run prediction">
              <form onSubmit={submit} className="stack-sm">
                <div className="grid-2">
                  <Field label="Model" htmlFor="p-model">
                    <select
                      id="p-model"
                      value={modelId ?? ""}
                      onChange={(e) => {
                        const v = Number(e.target.value) || undefined;
                        setModelId(v);
                        predict.reset();
                        setSearch(v ? { model: String(v) } : {}, { replace: true });
                      }}
                    >
                      <option value="">Select a model…</option>
                      {myModels.map((m) => {
                        const exp = experimentById.get(m.experiment_id);
                        return (
                          <option key={m.model_id} value={m.model_id}>
                            #{m.model_id} · {exp?.algorithm} → {exp?.target}
                            {exp && exp.user_id !== user?.user_id ? ` (shared by ${exp.owner_name ?? "another user"})` : ""}
                          </option>
                        );
                      })}
                    </select>
                  </Field>
                  <Field label="Input dataset" htmlFor="p-dataset" hint="Upload new data on the Datasets page first.">
                    <select
                      id="p-dataset"
                      value={datasetId ?? ""}
                      onChange={(e) => {
                        setDatasetId(Number(e.target.value) || undefined);
                        predict.reset();
                      }}
                    >
                      <option value="">Select a dataset…</option>
                      {myDatasets.map((d) => (
                        <option key={d.dataset_id} value={d.dataset_id}>
                          {d.name} — {formatInt(d.rows)} rows
                        </option>
                      ))}
                    </select>
                  </Field>
                </div>
                <label className="toggle">
                  <input type="checkbox" checked={saveResults} onChange={(e) => setSaveResults(e.target.checked)} />
                  Save results as a downloadable CSV (input rows + prediction column)
                </label>
                <ErrorBanner error={predict.error} title="Prediction failed" />
                <div>
                  <Button type="submit" variant="primary" loading={predict.running} disabled={!modelId || !datasetId}>
                    Run prediction
                  </Button>
                </div>
              </form>
            </Card>

            <Card title="Model requirements">
              {experiment ? (
                <div className="stack-sm">
                  <KeyValue
                    items={[
                      ["Experiment", <Link to={`/experiments/${experiment.experiment_id}`}>#{experiment.experiment_id} · {experiment.algorithm}</Link>],
                      ["Task", taskTypeOf(experiment)],
                      ["Predicts", <span className="mono">{experiment.target}</span>],
                      ["Trained on", datasetName.get(experiment.dataset_id) ?? `#${experiment.dataset_id}`],
                    ]}
                  />
                  <h3 className="section-label">Required columns ({experiment.features.length})</h3>
                  <Chips items={experiment.features} max={40} />
                  {experiment.parameters?.missing_strategy === "drop_rows" && (
                    <Alert tone="warning">This model was trained with drop_rows, so input features must have no missing values.</Alert>
                  )}
                </div>
              ) : (
                <p className="muted small">Select a model to see which columns the input dataset must contain.</p>
              )}
            </Card>
          </div>

          {predict.result && <PredictionResult result={predict.result} task={experiment ? taskTypeOf(experiment) : "classification"} />}

          <Card
            title="Saved results"
            description="Prediction CSVs stored for your account."
            flush
          >
            <ErrorBanner error={saved.error} onRetry={saved.reload} />
            {saved.loading && !saved.data ? (
              <Loading />
            ) : !saved.data?.length ? (
              <EmptyState title="No saved results" description="Run a prediction with “Save results” enabled." />
            ) : (
              <SavedResults
                records={saved.data}
                datasetName={datasetName}
                onRemoved={() => saved.reload()}
              />
            )}
          </Card>
        </div>
      )}
    </>
  );
}

function PredictionResult({ result, task }: { result: PredictResponse; task: "classification" | "regression" }) {
  const download = useAction(() => api.predictions.download(result.prediction_result_id!));
  const numeric = result.predictions.every((p) => typeof p === "number");
  const summary = useMemo(() => {
    if (task === "regression" && numeric) {
      const values = result.predictions as number[];
      const sum = values.reduce((a, b) => a + b, 0);
      return { kind: "numeric" as const, min: Math.min(...values), max: Math.max(...values), mean: sum / values.length };
    }
    const counts = new Map<string, number>();
    result.predictions.forEach((p) => counts.set(String(p), (counts.get(String(p)) ?? 0) + 1));
    return { kind: "classes" as const, counts: [...counts.entries()].sort((a, b) => b[1] - a[1]) };
  }, [result, task, numeric]);

  return (
    <Card
      title="Prediction output"
      description={`Model #${result.model_id} applied to dataset #${result.dataset_id}`}
      actions={
        result.prediction_result_id ? (
          <Button variant="primary" size="sm" onClick={() => download.run()} loading={download.running}>
            Download CSV
          </Button>
        ) : undefined
      }
    >
      <div className="stack-sm">
        <ErrorBanner error={download.error} />
        {result.prediction_result_id ? (
          <Alert tone="success">
            Saved as prediction result #{result.prediction_result_id} with column <span className="mono">{result.prediction_column}</span>.
          </Alert>
        ) : (
          <Alert tone="info">Results were not saved. Enable “Save results” to download them as CSV.</Alert>
        )}

        {summary.kind === "numeric" ? (
          <div className="stats-row">
            <Stat label="Rows" value={formatInt(result.rows)} />
            <Stat label="Mean" value={formatNumber(summary.mean)} />
            <Stat label="Min" value={formatNumber(summary.min)} />
            <Stat label="Max" value={formatNumber(summary.max)} />
          </div>
        ) : (
          <div className="grid-2">
            <Stat label="Rows predicted" value={formatInt(result.rows)} emphasis />
            <div className="hbars">
              {summary.counts.slice(0, 8).map(([label, count]) => (
                <div key={label} className="hbar-row">
                  <span className="hbar-label mono">{label}</span>
                  <div className="bar-track">
                    <div className="bar-fill" style={{ width: `${(count / result.rows) * 100}%` }} />
                  </div>
                  <span className="hbar-value mono">{formatInt(count)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        <h3 className="section-label">First {Math.min(20, result.predictions.length)} predictions</h3>
        <div className="table-wrap preview-table">
          <table className="table table-compact">
            <thead>
              <tr>
                <th>Row</th>
                <th>{result.prediction_column ?? "prediction"}</th>
              </tr>
            </thead>
            <tbody>
              {result.predictions.slice(0, 20).map((p, i) => (
                <tr key={i}>
                  <td className="muted mono">{i + 1}</td>
                  <td className="mono">{typeof p === "number" ? formatNumber(p, 4) : String(p)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </Card>
  );
}

function SavedResults({
  records,
  datasetName,
  onRemoved,
}: {
  records: PredictionResultRecord[];
  datasetName: Map<number, string>;
  onRemoved: (id: number) => void;
}) {
  const download = useAction(api.predictions.download);
  const remove = useAction(api.predictions.remove);
  const [busyId, setBusyId] = useState<number>();

  return (
    <>
      <div style={{ padding: "0 20px" }}>
        <ErrorBanner error={download.error ?? remove.error} />
      </div>
      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>Result</th>
              <th>Model</th>
              <th>Dataset</th>
              <th className="num">Rows</th>
              <th>Saved</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {records.map((r) => (
              <tr key={r.prediction_result_id}>
                <td className="mono">#{r.prediction_result_id}</td>
                <td>{r.model_id ? `#${r.model_id}` : <span className="muted small">deleted</span>}</td>
                <td>{datasetName.get(r.dataset_id) ?? `#${r.dataset_id}`}</td>
                <td className="num mono">{formatInt(r.rows)}</td>
                <td className="muted small nowrap">{formatDate(r.created_at)}</td>
                <td className="num">
                  <div className="row-gap justify-end">
                    <Button
                      size="sm"
                      variant="ghost"
                      className="text-danger"
                      loading={remove.running && busyId === r.prediction_result_id}
                      onClick={async () => {
                        setBusyId(r.prediction_result_id);
                        const done = await remove.run(r.prediction_result_id);
                        if (done) onRemoved(r.prediction_result_id);
                      }}
                    >
                      Delete
                    </Button>
                    <Button
                      size="sm"
                      loading={download.running && busyId === r.prediction_result_id}
                      onClick={() => {
                        setBusyId(r.prediction_result_id);
                        void download.run(r.prediction_result_id);
                      }}
                    >
                      Download
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

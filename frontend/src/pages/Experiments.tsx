import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/endpoints";
import type { Experiment } from "../api/types";
import { Badge, Button, ButtonLink, Card, EmptyState, ErrorBanner, Loading, PageHeader } from "../components/ui";
import { useUser } from "../context/AuthContext";
import { VisibilityBadge } from "../components/Visibility";
import { useAsync } from "../hooks/useAsync";
import { formatDate, formatMetric, macroF1Of, taskTypeOf } from "../lib/format";

// Comparison requires the same dataset, target and task type.
function groupKey(e: Experiment) {
  return `${e.dataset_id}|${e.target}|${taskTypeOf(e)}`;
}

export function Experiments() {
  const { user } = useUser();
  const navigate = useNavigate();
  const state = useAsync(
    () => Promise.all([api.experiments.list(), api.datasets.list(), api.models.list()]),
    [],
  );
  const [selected, setSelected] = useState<number[]>([]);
  const [datasetFilter, setDatasetFilter] = useState<number | "">("");

  const [all = [], datasets = [], models = []] = state.data ?? [];
  const datasetName = new Map(datasets.map((d) => [d.dataset_id, d.name]));
  const savedFor = new Set(models.map((m) => m.experiment_id));

  const experiments = useMemo(
    () =>
      all
        .filter((e) => e.user_id === user?.user_id)
        .filter((e) => datasetFilter === "" || e.dataset_id === datasetFilter)
        .sort((a, b) => b.experiment_id - a.experiment_id),
    [all, user, datasetFilter],
  );
  const usedDatasets = [...new Set(all.filter((e) => e.user_id === user?.user_id).map((e) => e.dataset_id))];

  const selectedExperiments = all.filter((e) => selected.includes(e.experiment_id));
  const selectionKey = selectedExperiments[0] ? groupKey(selectedExperiments[0]) : undefined;

  function toggle(e: Experiment) {
    setSelected((s) => (s.includes(e.experiment_id) ? s.filter((x) => x !== e.experiment_id) : [...s, e.experiment_id]));
  }

  return (
    <>
      <PageHeader
        title="Experiments"
        subtitle="Every training run is recorded with its configuration and test-set metrics."
        actions={<ButtonLink to="/experiments/new" variant="primary">New experiment</ButtonLink>}
      />

      {selected.length > 0 && (
        <div className="selection-bar">
          <span>
            <strong>{selected.length}</strong> selected
            {selectionKey && (
              <span className="muted">
                {" "}· {datasetName.get(selectedExperiments[0].dataset_id)} → <span className="mono">{selectedExperiments[0].target}</span>
              </span>
            )}
          </span>
          <div className="row-gap">
            <Button size="sm" variant="ghost" onClick={() => setSelected([])}>Clear</Button>
            <Button
              size="sm"
              variant="primary"
              disabled={selected.length < 2 || selected.length > 10}
              onClick={() => navigate(`/experiments/compare?ids=${[...selected].sort((a, b) => a - b).join(",")}`)}
            >
              Compare {selected.length >= 2 ? selected.length : ""}
            </Button>
          </div>
        </div>
      )}

      <Card
        flush
        title="Runs"
        description="Select 2–10 runs on the same dataset, target and task to compare them."
        actions={
          usedDatasets.length > 1 && (
            <select
              className="select-sm"
              value={datasetFilter}
              onChange={(e) => setDatasetFilter(e.target.value ? Number(e.target.value) : "")}
            >
              <option value="">All datasets</option>
              {usedDatasets.map((id) => (
                <option key={id} value={id}>{datasetName.get(id) ?? `Dataset #${id}`}</option>
              ))}
            </select>
          )
        }
      >
        <ErrorBanner error={state.error} onRetry={state.reload} />
        {state.loading && !state.data ? (
          <Loading />
        ) : experiments.length === 0 ? (
          <EmptyState
            title="No experiments yet"
            description="Train a model to create your first experiment."
            action={<ButtonLink to="/experiments/new" variant="primary">New experiment</ButtonLink>}
          />
        ) : (
          <div className="table-wrap">
            <table className="table table-hover">
              <thead>
                <tr>
                  <th style={{ width: 40 }} />
                  <th>Experiment</th>
                  <th>Dataset → target</th>
                  <th>Task</th>
                  <th className="num">Metric 1</th>
                  <th className="num">Metric 2</th>
                  <th>Model</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {experiments.map((e) => {
                  const regression = taskTypeOf(e) === "regression";
                  const compatible = !selectionKey || groupKey(e) === selectionKey;
                  const checked = selected.includes(e.experiment_id);
                  return (
                    <tr key={e.experiment_id} className={!compatible && !checked ? "row-disabled" : ""}>
                      <td>
                        <input
                          type="checkbox"
                          checked={checked}
                          disabled={!compatible && !checked}
                          onChange={() => toggle(e)}
                          aria-label={`Select experiment ${e.experiment_id}`}
                          title={compatible ? "" : "Different dataset, target or task"}
                        />
                      </td>
                      <td>
                        <Link to={`/experiments/${e.experiment_id}`} className="row-link">{e.algorithm}</Link>
                        <div className="muted small">#{e.experiment_id} · {e.features.length} features {!e.is_public && <VisibilityBadge isPublic={false} />}</div>
                      </td>
                      <td>
                        {datasetName.get(e.dataset_id) ?? `#${e.dataset_id}`}
                        <div className="mono small">{e.target}</div>
                      </td>
                      <td><Badge>{taskTypeOf(e)}</Badge></td>
                      <td className="num mono">
                        {regression ? formatMetric("r2", e.results.r2) : formatMetric("accuracy", e.results.accuracy)}
                        <div className="muted small">{regression ? "R²" : "Accuracy"}</div>
                      </td>
                      <td className="num mono">
                        {regression ? formatMetric("rmse", e.results.rmse) : formatMetric("macro_f1", macroF1Of(e))}
                        <div className="muted small">{regression ? "RMSE" : "Macro F1"}</div>
                      </td>
                      <td>{savedFor.has(e.experiment_id) ? <Badge tone="success">Saved</Badge> : <span className="muted small">—</span>}</td>
                      <td className="muted small nowrap">{formatDate(e.created_at)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </>
  );
}

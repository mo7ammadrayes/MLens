import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api/endpoints";
import { useAuth } from "../context/AuthContext";
import type { ComparedExperiment, ComparisonResponse } from "../api/types";
import { AiPanel, AiText } from "../components/AiPanel";
import { Alert, Badge, Card, ErrorBanner, Loading, PageHeader } from "../components/ui";
import { useAction, useAsync } from "../hooks/useAsync";
import { METRIC_LABELS, formatMetric } from "../lib/format";

function bestId(comparison: ComparisonResponse, metric: string): number | undefined {
  const higher = comparison.metric_directions[metric] === "higher";
  let best: ComparedExperiment | undefined;
  for (const e of comparison.experiments) {
    const v = e.metrics[metric];
    if (v === null || v === undefined) continue;
    const bv = best?.metrics[metric];
    if (best === undefined || bv === null || bv === undefined || (higher ? v > bv : v < bv)) best = e;
  }
  return best?.experiment_id;
}

export function Compare() {
  const [search] = useSearchParams();
  const ids = (search.get("ids") ?? "")
    .split(",")
    .map(Number)
    .filter((n) => Number.isInteger(n) && n > 0);
  const key = ids.join(",");

  const crumb = useAuth().session
    ? { label: "Experiments", to: "/experiments" }
    : { label: "Discover", to: "/discover?tab=experiments" };
  const state = useAsync(async () => {
    const comparison = await api.experiments.compare(ids);
    // The dataset may be private to someone else; its name is optional.
    const dataset = await api.datasets.get(comparison.dataset_id).catch(() => undefined);
    return [comparison, dataset] as const;
  }, [key]);
  const explain = useAction(() => api.experiments.explainComparison(ids));

  if (ids.length < 2)
    return (
      <>
        <PageHeader title="Compare experiments" breadcrumb={crumb} />
        <Alert tone="info">Select between 2 and 10 experiments on the Experiments page to compare them.</Alert>
      </>
    );

  if (state.loading && !state.data) return <Loading label="Comparing experiments…" />;
  if (state.error || !state.data)
    return (
      <>
        <PageHeader title="Compare experiments" breadcrumb={crumb} />
        <ErrorBanner error={state.error} onRetry={state.reload} title="Comparison failed" />
      </>
    );

  const [comparison, dataset] = state.data;
  const metrics = Object.keys(comparison.metric_directions);
  const datasetName = dataset?.name;
  const winners = Object.fromEntries(metrics.map((m) => [m, bestId(comparison, m)]));

  return (
    <>
      <PageHeader
        breadcrumb={crumb}
        title={`Comparing ${comparison.experiments.length} experiments`}
        subtitle={
          <>
            <Badge>{comparison.task_type}</Badge> predicting <span className="mono">{comparison.target}</span> on{" "}
            <Link to={`/datasets/${comparison.dataset_id}`}>{datasetName ?? `dataset #${comparison.dataset_id}`}</Link>
          </>
        }
      />

      <div className="stack">
        {comparison.warnings.length > 0 && (
          <Alert tone="warning">
            <strong>Check comparability</strong>
            <ul className="tight-list">
              {comparison.warnings.map((w) => <li key={w}>{w}</li>)}
            </ul>
          </Alert>
        )}

        <Card title="Metrics" description="Best value per metric is highlighted." flush>
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Experiment</th>
                  {metrics.map((m) => (
                    <th key={m} className="num">
                      {METRIC_LABELS[m] ?? m}
                      <div className="muted small">{comparison.metric_directions[m] === "higher" ? "↑ higher" : "↓ lower"} is better</div>
                    </th>
                  ))}
                  <th>Features</th>
                  <th className="num">Train</th>
                </tr>
              </thead>
              <tbody>
                {comparison.experiments.map((e) => (
                  <tr key={e.experiment_id}>
                    <td>
                      <Link className="row-link" to={`/experiments/${e.experiment_id}`}>{e.algorithm}</Link>
                      <div className="muted small">#{e.experiment_id}</div>
                    </td>
                    {metrics.map((m) => (
                      <td key={m} className={`num mono ${winners[m] === e.experiment_id ? "cell-best" : ""}`}>
                        {formatMetric(m, e.metrics[m])}
                      </td>
                    ))}
                    <td>{e.features.length}</td>
                    <td className="num mono">{e.split?.train_size ? `${Math.round(e.split.train_size * 100)}%` : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        <div className="grid-auto">
          {metrics.map((m) => (
            <MetricBars key={m} comparison={comparison} metric={m} winner={winners[m]} />
          ))}
        </div>

        <AiPanel
          title="Explain comparison"
          description="Explains the trade-offs between these runs, taking the comparability warnings into account."
          actionLabel="Explain comparison"
          onRun={() => explain.run()}
          running={explain.running}
          error={explain.error}
          hasResult={!!explain.result}
        >
          {explain.result && <AiText text={explain.result.summary} />}
        </AiPanel>
      </div>
    </>
  );
}

function MetricBars({
  comparison,
  metric,
  winner,
}: {
  comparison: ComparisonResponse;
  metric: string;
  winner: number | undefined;
}) {
  const values = comparison.experiments.map((e) => e.metrics[metric] ?? null);
  const finite = values.filter((v): v is number => v !== null);
  const max = Math.max(...finite.map(Math.abs), 1e-9);
  const isPercent = metric === "accuracy" || metric === "macro_f1";
  const scale = isPercent ? 1 : max;

  return (
    <Card title={METRIC_LABELS[metric] ?? metric} description={comparison.metric_directions[metric] === "higher" ? "Higher is better" : "Lower is better"}>
      <div className="hbars">
        {comparison.experiments.map((e) => {
          const v = e.metrics[metric];
          const width = v === null || v === undefined ? 0 : Math.max(0, Math.min(1, Math.abs(v) / scale)) * 100;
          return (
            <div key={e.experiment_id} className="hbar-row">
              <span className="hbar-label" title={e.algorithm}>
                #{e.experiment_id} {e.algorithm}
              </span>
              <div className="bar-track">
                <div className={`bar-fill ${winner === e.experiment_id ? "bar-best" : ""} ${v !== null && v !== undefined && v < 0 ? "bar-warn" : ""}`} style={{ width: `${width}%` }} />
              </div>
              <span className="hbar-value mono">{formatMetric(metric, v)}</span>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

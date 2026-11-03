import type { ClassReport, Experiment } from "../api/types";
import { formatInt, formatNumber, formatPercent, macroF1Of, taskTypeOf } from "../lib/format";
import { Stat } from "./ui";

export function MetricSummary({ experiment }: { experiment: Experiment }) {
  const r = experiment.results;
  if (taskTypeOf(experiment) === "regression") {
    return (
      <div className="stats-row">
        <Stat label="R²" value={formatNumber(r.r2)} hint="Higher is better" emphasis />
        <Stat label="MAE" value={formatNumber(r.mae)} hint="Lower is better" />
        <Stat label="RMSE" value={formatNumber(r.rmse)} hint="Lower is better" />
      </div>
    );
  }
  const support = classRows(experiment).reduce((sum, [, row]) => sum + row.support, 0);
  return (
    <div className="stats-row">
      <Stat label="Accuracy" value={formatPercent(r.accuracy)} emphasis />
      <Stat label="Macro F1" value={formatPercent(macroF1Of(experiment))} hint="Unweighted mean across classes" />
      <Stat label="Test rows" value={support ? formatInt(support) : "—"} />
    </div>
  );
}

function classRows(experiment: Experiment): [string, ClassReport][] {
  const report = experiment.results.classification_report ?? {};
  return Object.entries(report).filter(
    (entry): entry is [string, ClassReport] =>
      typeof entry[1] === "object" && entry[0] !== "macro avg" && entry[0] !== "weighted avg",
  );
}

export function ClassificationReport({ experiment }: { experiment: Experiment }) {
  const report = experiment.results.classification_report;
  if (!report) return <p className="muted">No per-class report was stored for this experiment.</p>;
  const rows = classRows(experiment);
  const averages = (["macro avg", "weighted avg"] as const)
    .map((k) => [k, report[k]] as const)
    .filter((e): e is readonly [typeof e[0], ClassReport] => typeof e[1] === "object");

  return (
    <div className="table-wrap">
      <table className="table">
        <thead>
          <tr>
            <th>Class</th>
            <th className="num">Precision</th>
            <th className="num">Recall</th>
            <th className="num">F1</th>
            <th className="bar-col">F1</th>
            <th className="num">Support</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([label, row]) => (
            <tr key={label}>
              <td className="mono">{label}</td>
              <td className="num">{formatNumber(row.precision)}</td>
              <td className="num">{formatNumber(row.recall)}</td>
              <td className="num">{formatNumber(row["f1-score"])}</td>
              <td className="bar-col">
                <div className="bar-track">
                  <div className="bar-fill" style={{ width: `${Math.max(0, row["f1-score"]) * 100}%` }} />
                </div>
              </td>
              <td className="num">{formatInt(row.support)}</td>
            </tr>
          ))}
          {averages.map(([label, row]) => (
            <tr key={label} className="row-muted">
              <td>{label}</td>
              <td className="num">{formatNumber(row.precision)}</td>
              <td className="num">{formatNumber(row.recall)}</td>
              <td className="num">{formatNumber(row["f1-score"])}</td>
              <td />
              <td className="num">{formatInt(row.support)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

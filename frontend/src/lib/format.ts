import type { Experiment, TaskType } from "../api/types";

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatNumber(value: number | null | undefined, digits = 3): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  if (Number.isInteger(value) && Math.abs(value) >= 1000) return value.toLocaleString();
  return Number(value.toFixed(digits)).toString();
}

export function formatPercent(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined) return "—";
  return `${(value * 100).toFixed(digits)}%`;
}

export function formatInt(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return value.toLocaleString();
}

// The backend defaults missing task_type to classification (experiment/service.py).
export function taskTypeOf(experiment: Pick<Experiment, "parameters">): TaskType {
  return experiment.parameters?.task_type ?? "classification";
}

export function macroF1Of(experiment: Experiment): number | undefined {
  const results = experiment.results;
  if (typeof results.macro_f1 === "number") return results.macro_f1;
  const avg = results.classification_report?.["macro avg"];
  return typeof avg === "object" ? avg["f1-score"] : undefined;
}

export interface MetricDisplay {
  label: string;
  value: string;
}

export function primaryMetric(experiment: Experiment): MetricDisplay {
  if (taskTypeOf(experiment) === "regression") {
    return { label: "R²", value: formatNumber(experiment.results.r2) };
  }
  return { label: "Accuracy", value: formatPercent(experiment.results.accuracy) };
}

export const METRIC_LABELS: Record<string, string> = {
  accuracy: "Accuracy",
  macro_f1: "Macro F1",
  mae: "MAE",
  rmse: "RMSE",
  r2: "R²",
};

export function formatMetric(metric: string, value: number | null | undefined): string {
  if (metric === "accuracy" || metric === "macro_f1") return formatPercent(value);
  return formatNumber(value);
}

export function plural(count: number, word: string): string {
  return `${count.toLocaleString()} ${word}${count === 1 ? "" : "s"}`;
}

import type { DatasetInspection } from "../api/types";

// Matches the backend limit in services/ml_service.py (MAX_ONE_HOT_COLUMNS).
export const MAX_ONE_HOT_COLUMNS = 1000;
const MANY_CATEGORIES = 50;

export interface ColumnRisk {
  label: string;
  detail: string;
}

const isNumeric = (dtype: string | undefined) => !!dtype && /^(u?int|float|Int|Float|UInt|bool)/.test(dtype);

/**
 * Flags columns that usually hurt a model if used as features: IDs, dates
 * stored as text, and text columns with very many categories.
 */
export function columnRisk(insp: DatasetInspection, column: string): ColumnRisk | undefined {
  const unique = insp.unique_values?.[column];
  if (unique === undefined || insp.rows < 20) return undefined;
  const dtype = insp.column_types[column];
  const text = !isNumeric(dtype);

  if (text && (/datetime/.test(dtype ?? "") || /(^|_)(date|time|timestamp|datetime)($|_)/i.test(column)) && unique > 12) {
    return {
      label: "Looks like a date",
      detail: "Each date would become its own category. Use a numeric column such as year or month instead.",
    };
  }
  if (unique >= insp.rows * 0.95) {
    return {
      label: "Looks like an ID",
      detail: "Almost every row has its own value, so the model can't learn anything general from it.",
    };
  }
  if (text && unique > MANY_CATEGORIES) {
    return {
      label: `${unique.toLocaleString()} categories`,
      detail: "Each category becomes its own one-hot column, which makes the model large and slow.",
    };
  }
  return undefined;
}

/** Total one-hot columns the categorical features would create. */
export function oneHotColumns(insp: DatasetInspection, categorical: string[]): number {
  return categorical.reduce((sum, c) => sum + (insp.unique_values?.[c] ?? 0), 0);
}

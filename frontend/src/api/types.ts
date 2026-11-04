// Types mirror the dict responses built in backend/features/*/router.py
// and the Pydantic request schemas in backend/features/*/schemas.py.

export type TaskType = "classification" | "regression";

// ---------- Users ----------
export interface User {
  user_id: number;
  name: string;
  email: string;
  phone: string | null;
}

export interface UpdateUserRequest {
  name?: string;
  phone?: string | null;
}

// ---------- Datasets ----------
export interface DatasetSummary {
  dataset_id: number;
  name: string;
  rows: number;
  cols: number;
  added_by: number;
  original_filename: string;
  created_at: string;
  is_public: boolean;
  is_featured: boolean;
  description: string | null;
  source: string | null;
  tags: string[];
  cleaning_metadata: CleaningMetadata | null;
  /** Only on GET /datasets/{id}. */
  owner_name?: string | null;
}

export type UploadedDataset = DatasetSummary;

// services/data_analysis_service.inspect_dataset
export interface DatasetInspection {
  rows: number;
  cols: number;
  column_names: string[];
  column_types: Record<string, string>;
  missing_values: Record<string, number>;
  /** Distinct non-missing values per column (older APIs may omit it). */
  unique_values?: Record<string, number>;
  total_missing_values: number;
  duplicate_rows: number;
}

export type CleanMissingStrategy = "none" | "drop" | "mean" | "median";

export interface CleanDatasetRequest {
  name: string;
  drop_duplicates: boolean;
  missing_strategy: CleanMissingStrategy;
  columns?: string[] | null;
}

export interface CleaningMetadata {
  source_dataset_id: number;
  drop_duplicates: boolean;
  missing_strategy: CleanMissingStrategy;
  columns: string[] | null;
  rows_before: number;
  rows_after: number;
  duplicates_removed: number;
  missing_rows_removed: number;
  missing_values_before: number;
  missing_values_after: number;
  warnings: string[];
}

export interface CleanDatasetResponse {
  dataset_id: number;
  name: string;
  rows: number;
  cols: number;
  cleaning_metadata: CleaningMetadata;
}

export interface DeleteWithFileResponse {
  message: string;
  file_cleanup_pending: boolean;
  cleanup_id: number | null;
}

// ---------- Model options ----------
export interface ParameterRule {
  type: "number" | "integer" | "boolean";
  default: number | boolean | null;
  min?: number;
  max?: number;
  nullable?: boolean;
}

export type ParameterValue = number | boolean | null;

export interface ModelOptions {
  tasks: Record<
    TaskType,
    { algorithms: Record<string, { parameters: Record<string, ParameterRule> }> }
  >;
  preprocessing: {
    numerical_strategy: { allowed: NumericalStrategy[]; default: NumericalStrategy };
    missing_strategy: { allowed: TrainMissingStrategy[]; default: TrainMissingStrategy };
    drop_duplicates: { type: "boolean"; default: boolean };
  };
}

export type NumericalStrategy = "mean" | "median";
export type TrainMissingStrategy = "impute" | "drop_rows";

// ---------- Training ----------
export interface TrainModelRequest {
  dataset_id: number;
  target: string;
  features: string[];
  categorical: string[];
  train_size: number;
  task_type: TaskType;
  algorithm: string;
  save_model: boolean;
  /** Omit to follow the dataset's visibility. */
  is_public?: boolean;
  numerical_strategy: NumericalStrategy;
  drop_duplicates: boolean;
  missing_strategy: TrainMissingStrategy;
  model_parameters: Record<string, ParameterValue>;
}

export interface TrainModelResponse {
  experiment_id: number;
  model_id: number | null;
  is_public: boolean;
  /** Set when saving was requested but the model could not be stored. */
  model_error: string | null;
  results: ExperimentResults;
}

// ---------- Experiments ----------
export interface ClassReport {
  precision: number;
  recall: number;
  "f1-score": number;
  support: number;
}

export interface ClassificationResults {
  accuracy: number;
  macro_f1?: number;
  classification_report?: Record<string, ClassReport | number>;
}

export interface RegressionResults {
  mae: number;
  rmse: number;
  r2: number;
}

export type ExperimentResults = Partial<ClassificationResults & RegressionResults> &
  Record<string, unknown>;

// Configuration saved by run_ml_workflow.train_and_save_model.
// Older rows may lack some keys, so everything is optional.
export interface ExperimentConfiguration {
  classifier?: Record<string, unknown>;
  categorical_features?: string[];
  random_state?: number;
  numerical_strategy?: NumericalStrategy | null;
  categorical_strategy?: string | null;
  drop_duplicates?: boolean;
  missing_strategy?: TrainMissingStrategy;
  duplicates_removed?: number;
  missing_rows_removed?: number;
  task_type?: TaskType;
  [key: string]: unknown;
}

export interface Experiment {
  experiment_id: number;
  algorithm: string;
  split: { train_size?: number; random_state?: number };
  parameters: ExperimentConfiguration;
  results: ExperimentResults;
  target: string;
  features: string[];
  created_at: string;
  dataset_id: number;
  user_id: number;
  is_public: boolean;
  /** Only on GET /experiments/{id}. */
  owner_name?: string | null;
}

export interface ComparedExperiment {
  experiment_id: number;
  algorithm: string;
  features: string[];
  split: Experiment["split"];
  parameters: ExperimentConfiguration;
  metrics: Record<string, number | null>;
  created_at: string;
}

export interface ComparisonResponse {
  dataset_id: number;
  target: string;
  task_type: TaskType;
  metric_directions: Record<string, "higher" | "lower">;
  warnings: string[];
  experiments: ComparedExperiment[];
}

// ---------- AI ----------
export interface Explanation {
  summary: string;
}

export interface ModelRecommendation {
  algorithm: string;
  parameters: Record<string, ParameterValue>;
  reason: string;
  uncertainty: string;
}

export interface ExperimentRecommendations {
  summary: string;
  recommendations: ModelRecommendation[];
}

// ---------- Models ----------
export interface SavedModel {
  model_id: number;
  /** Inherited from the model's experiment. */
  is_public: boolean | null;
  storage_bucket: string;
  artifact_path: string;
  experiment_id: number;
  created_at: string;
}

// ---------- Predictions ----------
export interface PredictRequest {
  model_id: number;
  dataset_id: number;
  save_results: boolean;
}

export interface PredictResponse {
  prediction_result_id: number | null;
  user_id: number;
  model_id: number;
  dataset_id: number;
  rows: number;
  prediction_column: string | null;
  predictions: (string | number | boolean | null)[];
}

export interface PredictionResultRecord {
  prediction_result_id: number;
  user_id: number;
  /** Null when the model has since been deleted. */
  model_id: number | null;
  dataset_id: number;
  rows: number;
  prediction_column: string;
  created_at: string;
}

// ---------- Explore (public items from all users) ----------
export interface PublicDataset {
  dataset_id: number;
  name: string;
  rows: number;
  cols: number;
  added_by: number;
  owner_name: string;
  is_mine: boolean;
  created_at: string;
  description: string | null;
  source: string | null;
  tags: string[];
  is_featured: boolean;
  /** Number of public experiments on this dataset. */
  example_experiments: number;
}

export interface PublicExperimentSummary {
  experiment_id: number;
  algorithm: string;
  target: string;
  task_type: TaskType;
  features: string[];
  split: Experiment["split"];
  results: ExperimentResults;
  dataset_id: number;
  user_id: number;
  created_at: string;
}

export interface PublicExperiment extends PublicExperimentSummary {
  owner_name: string;
  is_mine: boolean;
  dataset_name: string | null;
  dataset_is_public: boolean;
}

export interface PublicModel {
  model_id: number;
  experiment_id: number;
  created_at: string;
  owner_name: string;
  is_mine: boolean;
  experiment: PublicExperimentSummary;
}

export interface DatasetPreview {
  columns: string[];
  rows: (string | number | boolean | null)[][];
  total_rows: number;
}

export interface UpdateDatasetRequest {
  name?: string;
  description?: string | null;
  source?: string | null;
  tags?: string[];
}

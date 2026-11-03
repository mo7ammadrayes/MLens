import type {
  Experiment,
  ModelOptions,
  NumericalStrategy,
  ParameterValue,
  TaskType,
  TrainMissingStrategy,
} from "../api/types";
import { taskTypeOf } from "./format";

// Passed through router state to pre-populate the New Experiment form,
// e.g. when re-running an experiment or applying an AI recommendation.
export interface ExperimentPrefill {
  datasetId: number;
  target?: string;
  taskType?: TaskType;
  features?: string[];
  categorical?: string[];
  algorithm?: string;
  parameters?: Record<string, ParameterValue>;
  trainSize?: number;
  numericalStrategy?: NumericalStrategy;
  missingStrategy?: TrainMissingStrategy;
  dropDuplicates?: boolean;
  saveModel?: boolean;
  sourceLabel?: string;
}

// Only keep parameters the backend accepts for this algorithm; the stored
// configuration holds the estimator's full get_params() output.
export function tunableParameters(
  options: ModelOptions | undefined,
  taskType: TaskType,
  algorithm: string,
  source: Record<string, unknown> | undefined,
): Record<string, ParameterValue> {
  const rules = options?.tasks[taskType]?.algorithms[algorithm]?.parameters;
  if (!rules || !source) return {};
  const picked: Record<string, ParameterValue> = {};
  for (const name of Object.keys(rules)) {
    if (name in source) picked[name] = source[name] as ParameterValue;
  }
  return picked;
}

export function prefillFromExperiment(
  experiment: Experiment,
  options: ModelOptions | undefined,
  overrides: Partial<ExperimentPrefill> = {},
): ExperimentPrefill {
  const config = experiment.parameters ?? {};
  const taskType = taskTypeOf(experiment);
  const algorithm = overrides.algorithm ?? experiment.algorithm;
  return {
    datasetId: experiment.dataset_id,
    target: experiment.target,
    taskType,
    features: experiment.features,
    categorical: config.categorical_features ?? [],
    algorithm,
    parameters: tunableParameters(options, taskType, algorithm, config.classifier),
    trainSize: experiment.split?.train_size,
    numericalStrategy: config.numerical_strategy ?? undefined,
    missingStrategy: config.missing_strategy,
    dropDuplicates: config.drop_duplicates,
    ...overrides,
  };
}

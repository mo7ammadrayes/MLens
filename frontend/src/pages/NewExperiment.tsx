import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api/endpoints";
import type {
  DatasetInspection,
  ModelOptions,
  NumericalStrategy,
  ParameterRule,
  ParameterValue,
  TaskType,
  TrainMissingStrategy,
} from "../api/types";
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorBanner,
  Field,
  Loading,
  PageHeader,
  ButtonLink,
} from "../components/ui";
import { useUser } from "../context/AuthContext";
import { useAction, useAsync } from "../hooks/useAsync";
import { formatInt } from "../lib/format";
import type { ExperimentPrefill } from "../lib/prefill";
import { isNumericType } from "./DatasetDetail";

function defaultsFor(options: ModelOptions | undefined, task: TaskType, algorithm: string) {
  const rules = options?.tasks[task]?.algorithms[algorithm]?.parameters ?? {};
  return Object.fromEntries(Object.entries(rules).map(([k, r]) => [k, r.default])) as Record<string, ParameterValue>;
}

export function NewExperiment() {
  const { user } = useUser();
  const navigate = useNavigate();
  const location = useLocation();
  const [search] = useSearchParams();
  const prefill = (location.state as { prefill?: ExperimentPrefill } | null)?.prefill;
  // State (not a ref) so other effects in the same commit still see the prefill as pending.
  const [prefillDone, setPrefillDone] = useState(!prefill);

  const options = useAsync(() => api.models.options(), []);
  const datasets = useAsync(() => api.datasets.list(), []);
  const myDatasets = useMemo(
    () => [...(datasets.data ?? [])].sort((a, b) => b.dataset_id - a.dataset_id),
    [datasets.data, user],
  );

  const [datasetId, setDatasetId] = useState<number | undefined>(
    prefill?.datasetId ?? (Number(search.get("dataset")) || undefined),
  );
  const inspection = useAsync<DatasetInspection | undefined>(
    () => (datasetId ? api.datasets.inspect(datasetId) : Promise.resolve(undefined)),
    [datasetId],
  );

  const [target, setTarget] = useState("");
  const [taskType, setTaskType] = useState<TaskType>("classification");
  const [features, setFeatures] = useState<string[]>([]);
  const [categorical, setCategorical] = useState<string[]>([]);
  const [algorithm, setAlgorithm] = useState("");
  const [params, setParams] = useState<Record<string, ParameterValue>>({});
  const [trainSize, setTrainSize] = useState(0.8);
  const [numericalStrategy, setNumericalStrategy] = useState<NumericalStrategy>("median");
  const [missingStrategy, setMissingStrategy] = useState<TrainMissingStrategy>("impute");
  const [dropDuplicates, setDropDuplicates] = useState(false);
  const [visibility, setVisibility] = useState<"inherit" | "public" | "private">("inherit");
  const [saveModel, setSaveModel] = useState(prefill?.saveModel ?? false);
  const train = useAction(api.models.train);

  const insp = inspection.data;
  const selectedDataset = myDatasets.find((d) => d.dataset_id === datasetId);
  const columns = insp?.column_names ?? [];
  const dtype = (c: string) => insp?.column_types[c];
  const algorithms = Object.keys(options.data?.tasks[taskType]?.algorithms ?? {});
  const rules = options.data?.tasks[taskType]?.algorithms[algorithm]?.parameters ?? {};

  // Apply preprocessing defaults from the options endpoint.
  useEffect(() => {
    if (!options.data || prefill) return;
    setNumericalStrategy(options.data.preprocessing.numerical_strategy.default);
    setMissingStrategy(options.data.preprocessing.missing_strategy.default);
    setDropDuplicates(options.data.preprocessing.drop_duplicates.default);
  }, [options.data, prefill]);

  // Apply a prefill (re-run / AI recommendation) once its dataset is inspected.
  useEffect(() => {
    if (!prefill || prefillDone || !insp || !options.data) return;
    if (prefill.datasetId !== datasetId) return;
    setPrefillDone(true);
    const exists = (c: string) => insp.column_names.includes(c);
    const task = prefill.taskType ?? "classification";
    const algo = prefill.algorithm && options.data.tasks[task]?.algorithms[prefill.algorithm] ? prefill.algorithm : Object.keys(options.data.tasks[task].algorithms)[0];
    setTaskType(task);
    if (prefill.target && exists(prefill.target)) setTarget(prefill.target);
    setFeatures((prefill.features ?? []).filter(exists));
    setCategorical((prefill.categorical ?? []).filter(exists));
    setAlgorithm(algo);
    setParams({ ...defaultsFor(options.data, task, algo), ...(prefill.parameters ?? {}) });
    if (prefill.trainSize) setTrainSize(prefill.trainSize);
    if (prefill.numericalStrategy) setNumericalStrategy(prefill.numericalStrategy);
    if (prefill.missingStrategy) setMissingStrategy(prefill.missingStrategy);
    if (prefill.dropDuplicates !== undefined) setDropDuplicates(prefill.dropDuplicates);
  }, [prefill, prefillDone, insp, options.data, datasetId]);

  // Keep the algorithm valid for the selected task.
  useEffect(() => {
    if (!options.data || !algorithms.length || !prefillDone) return;
    if (!algorithms.includes(algorithm)) {
      setAlgorithm(algorithms[0]);
      setParams(defaultsFor(options.data, taskType, algorithms[0]));
    }
  }, [options.data, taskType, algorithm, algorithms, prefillDone]);

  function chooseDataset(id: number | undefined) {
    setPrefillDone(true); // a manual change discards any prefill
    setDatasetId(id);
    setTarget("");
    setFeatures([]);
    setCategorical([]);
  }

  function chooseTarget(t: string) {
    setTarget(t);
    const feats = columns.filter((c) => c !== t);
    setFeatures(feats);
    setCategorical(feats.filter((c) => !isNumericType(dtype(c))));
    const tType = dtype(t) ?? "";
    if (/float/i.test(tType)) setTaskType("regression");
    else if (!isNumericType(tType)) setTaskType("classification");
  }

  function toggleFeature(c: string, on: boolean) {
    setFeatures(on ? [...features, c] : features.filter((x) => x !== c));
    if (!on) setCategorical(categorical.filter((x) => x !== c));
    else if (!isNumericType(dtype(c))) setCategorical([...categorical, c]);
  }

  function chooseAlgorithm(a: string) {
    setAlgorithm(a);
    setParams(defaultsFor(options.data, taskType, a));
  }

  const problems: string[] = [];
  if (!datasetId) problems.push("Select a dataset.");
  else if (insp) {
    if (!target) problems.push("Select a target column.");
    if (target && !features.length) problems.push("Select at least one feature.");
    if (target && insp.missing_values[target] > 0)
      problems.push(`Target '${target}' has ${insp.missing_values[target]} missing values; clean the dataset first.`);
    if (taskType === "regression" && target && !isNumericType(dtype(target)))
      problems.push("Regression requires a numerical target.");
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!user || !datasetId || problems.length) return;
    const response = await train.run({
      dataset_id: datasetId,
      target,
      features,
      categorical: categorical.filter((c) => features.includes(c)),
      train_size: trainSize,
      task_type: taskType,
      algorithm,
      save_model: saveModel,
      numerical_strategy: numericalStrategy,
      drop_duplicates: dropDuplicates,
      missing_strategy: missingStrategy,
      model_parameters: params,
      is_public: visibility === "inherit" ? undefined : visibility === "public",
    });
    if (response) {
      navigate(`/experiments/${response.experiment_id}`, {
        state: { justTrained: true, modelId: response.model_id },
      });
    }
  }

  if (options.loading || datasets.loading) return <Loading />;

  return (
    <>
      <PageHeader
        breadcrumb={{ label: "Experiments", to: "/experiments" }}
        title="New experiment"
        subtitle="Configure a scikit-learn pipeline, train it on a stratified/random split and record the evaluation."
      />
      <ErrorBanner error={options.error ?? datasets.error} />
      {prefill?.sourceLabel && <Alert tone="info">Pre-filled from {prefill.sourceLabel}. Review before training.</Alert>}

      {myDatasets.length === 0 ? (
        <Card>
          <EmptyState
            title="Upload a dataset first"
            description="Experiments train on one of your uploaded CSV datasets."
            action={<ButtonLink to="/datasets" variant="primary">Go to datasets</ButtonLink>}
          />
        </Card>
      ) : (
        <form onSubmit={submit} className="form-layout">
          <div className="stack">
            <Card title="1. Data">
              <div className="grid-2">
                <Field label="Dataset" htmlFor="ne-dataset">
                  <select
                    id="ne-dataset"
                    value={datasetId ?? ""}
                    onChange={(e) => chooseDataset(Number(e.target.value) || undefined)}
                  >
                    <option value="">Select a dataset…</option>
                    {myDatasets.map((d) => (
                      <option key={d.dataset_id} value={d.dataset_id}>
                        {d.name} — {formatInt(d.rows)} rows
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label="Target column" htmlFor="ne-target">
                  <select id="ne-target" value={target} onChange={(e) => chooseTarget(e.target.value)} disabled={!insp}>
                    <option value="">{inspection.loading ? "Loading columns…" : "Select target…"}</option>
                    {columns.map((c) => (
                      <option key={c} value={c}>
                        {c} ({dtype(c)})
                      </option>
                    ))}
                  </select>
                </Field>
              </div>
              <ErrorBanner error={inspection.error} onRetry={inspection.reload} />
              <Field label="Task type">
                <div className="segmented">
                  {(["classification", "regression"] as TaskType[]).map((t) => (
                    <button
                      type="button"
                      key={t}
                      className={taskType === t ? "active" : ""}
                      onClick={() => setTaskType(t)}
                    >
                      {t === "classification" ? "Classification" : "Regression"}
                    </button>
                  ))}
                </div>
              </Field>
            </Card>

            {insp && target && (
              <Card
                title="2. Features"
                description="Non-numeric columns must be encoded as categorical (one-hot)."
                actions={
                  <div className="row-gap">
                    <Button type="button" size="sm" variant="ghost" onClick={() => {
                      const all = columns.filter((c) => c !== target);
                      setFeatures(all);
                      setCategorical(all.filter((c) => !isNumericType(dtype(c))));
                    }}>
                      Select all
                    </Button>
                    <Button type="button" size="sm" variant="ghost" onClick={() => { setFeatures([]); setCategorical([]); }}>
                      Clear
                    </Button>
                  </div>
                }
                flush
              >
                <div className="table-wrap">
                  <table className="table">
                    <thead>
                      <tr>
                        <th style={{ width: 40 }} />
                        <th>Column</th>
                        <th>Type</th>
                        <th className="num">Missing</th>
                        <th>Categorical</th>
                      </tr>
                    </thead>
                    <tbody>
                      {columns.filter((c) => c !== target).map((c) => {
                        const selected = features.includes(c);
                        const numeric = isNumericType(dtype(c));
                        return (
                          <tr key={c} className={selected ? "" : "row-muted"}>
                            <td>
                              <input type="checkbox" checked={selected} onChange={(e) => toggleFeature(c, e.target.checked)} aria-label={`Use ${c}`} />
                            </td>
                            <td className="mono">{c}</td>
                            <td><Badge tone={numeric ? "accent" : "neutral"}>{dtype(c)}</Badge></td>
                            <td className="num mono">{insp.missing_values[c] || <span className="muted">0</span>}</td>
                            <td>
                              <label className="toggle small">
                                <input
                                  type="checkbox"
                                  disabled={!selected || !numeric}
                                  checked={categorical.includes(c)}
                                  onChange={(e) =>
                                    setCategorical(e.target.checked ? [...categorical, c] : categorical.filter((x) => x !== c))
                                  }
                                />
                                {selected && !numeric ? <span className="muted">text → one-hot</span> : ""}
                              </label>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </Card>
            )}

            <Card title="3. Model">
              <Field label="Algorithm" htmlFor="ne-algo">
                <select id="ne-algo" value={algorithm} onChange={(e) => chooseAlgorithm(e.target.value)}>
                  {algorithms.map((a) => (
                    <option key={a} value={a}>{a}</option>
                  ))}
                </select>
              </Field>
              {Object.keys(rules).length > 0 && (
                <div className="grid-3">
                  {Object.entries(rules).map(([name, rule]) => (
                    <ParameterInput
                      key={name}
                      name={name}
                      rule={rule}
                      value={params[name] ?? rule.default}
                      onChange={(v) => setParams({ ...params, [name]: v })}
                    />
                  ))}
                </div>
              )}
            </Card>

            <Card title="4. Evaluation & preprocessing">
              <Field
                label={<>Train size <span className="mono muted">{Math.round(trainSize * 100)}% / {Math.round((1 - trainSize) * 100)}%</span></>}
                hint={taskType === "classification" ? "Stratified split, random_state = 42." : "Random split, random_state = 42."}
              >
                <input
                  type="range"
                  min={0.5}
                  max={0.95}
                  step={0.05}
                  value={trainSize}
                  onChange={(e) => setTrainSize(Number(e.target.value))}
                />
              </Field>
              <div className="grid-2">
                <Field label="Missing feature values" htmlFor="ne-missing">
                  <select id="ne-missing" value={missingStrategy} onChange={(e) => setMissingStrategy(e.target.value as TrainMissingStrategy)}>
                    {(options.data?.preprocessing.missing_strategy.allowed ?? ["impute", "drop_rows"]).map((s) => (
                      <option key={s} value={s}>{s === "impute" ? "Impute inside the pipeline" : "Drop rows with missing features"}</option>
                    ))}
                  </select>
                </Field>
                <Field label="Numerical imputation" htmlFor="ne-num" hint={missingStrategy !== "impute" ? "Only used with imputation." : "Categoricals use most frequent."}>
                  <select id="ne-num" value={numericalStrategy} disabled={missingStrategy !== "impute"} onChange={(e) => setNumericalStrategy(e.target.value as NumericalStrategy)}>
                    {(options.data?.preprocessing.numerical_strategy.allowed ?? ["mean", "median"]).map((s) => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                </Field>
              </div>
              <label className="toggle">
                <input type="checkbox" checked={dropDuplicates} onChange={(e) => setDropDuplicates(e.target.checked)} />
                Drop duplicate rows before splitting
              </label>
            </Card>
          </div>

          <aside className="form-summary">
            <Card title="Summary">
              <dl className="kv kv-compact">
                <div className="kv-row"><dt>Task</dt><dd>{taskType}</dd></div>
                <div className="kv-row"><dt>Target</dt><dd className="mono">{target || "—"}</dd></div>
                <div className="kv-row"><dt>Features</dt><dd>{features.length} ({categorical.filter((c) => features.includes(c)).length} categorical)</dd></div>
                <div className="kv-row"><dt>Algorithm</dt><dd>{algorithm || "—"}</dd></div>
                <div className="kv-row"><dt>Split</dt><dd>{Math.round(trainSize * 100)} / {Math.round((1 - trainSize) * 100)}</dd></div>
              </dl>
              <label className="toggle save-toggle">
                <input type="checkbox" checked={saveModel} onChange={(e) => setSaveModel(e.target.checked)} />
                <span>
                  <strong>Save trained model</strong>
                  <span className="muted small block">Stores the fitted pipeline so it can be used for predictions.</span>
                </span>
              </label>
              <Field label="Visibility" htmlFor="ne-vis" hint="Public results (and the saved model) are listed in Explore.">
                <select id="ne-vis" value={visibility} onChange={(e) => setVisibility(e.target.value as typeof visibility)}>
                  <option value="inherit">
                    Same as dataset{selectedDataset ? ` (${selectedDataset.is_public ? "public" : "private"})` : ""}
                  </option>
                  <option value="public">Public</option>
                  <option value="private">Private</option>
                </select>
              </Field>
              {problems.length > 0 && insp && (
                <ul className="problems">
                  {problems.map((p) => <li key={p}>{p}</li>)}
                </ul>
              )}
              <ErrorBanner error={train.error} title="Training failed" />
              <Button type="submit" variant="primary" loading={train.running} disabled={problems.length > 0 || !user} className="btn-block">
                {train.running ? "Training…" : "Train experiment"}
              </Button>
              {datasetId && (
                <p className="muted small center" style={{ marginTop: 10 }}>
                  <Link to={`/datasets/${datasetId}`}>View dataset profile</Link>
                </p>
              )}
            </Card>
          </aside>
        </form>
      )}
    </>
  );
}

function ParameterInput({
  name,
  rule,
  value,
  onChange,
}: {
  name: string;
  rule: ParameterRule;
  value: ParameterValue;
  onChange: (value: ParameterValue) => void;
}) {
  const id = `param-${name}`;
  if (rule.type === "boolean") {
    return (
      <Field label={<span className="mono">{name}</span>}>
        <label className="toggle">
          <input type="checkbox" checked={!!value} onChange={(e) => onChange(e.target.checked)} />
          {value ? "true" : "false"}
        </label>
      </Field>
    );
  }
  const isNull = value === null;
  return (
    <Field
      label={<span className="mono">{name}</span>}
      htmlFor={id}
      hint={`${rule.type} · ${rule.min} – ${rule.max}${rule.nullable ? " · or None" : ""}`}
    >
      <div className="input-with-addon">
        <input
          id={id}
          type="number"
          min={rule.min}
          max={rule.max}
          step={rule.type === "integer" ? 1 : "any"}
          disabled={isNull}
          value={isNull ? "" : String(value)}
          placeholder={isNull ? "None" : undefined}
          onChange={(e) => {
            const raw = e.target.value;
            if (raw === "") return;
            const n = rule.type === "integer" ? parseInt(raw, 10) : parseFloat(raw);
            if (!Number.isNaN(n)) onChange(n);
          }}
        />
        {rule.nullable && (
          <label className="addon">
            <input
              type="checkbox"
              checked={isNull}
              onChange={(e) => onChange(e.target.checked ? null : (rule.min ?? 1))}
            />
            None
          </label>
        )}
      </div>
    </Field>
  );
}

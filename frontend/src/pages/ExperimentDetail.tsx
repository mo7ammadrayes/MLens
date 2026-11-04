import { useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { api } from "../api/endpoints";
import type { Experiment, ModelOptions } from "../api/types";
import { AiPanel, AiText } from "../components/AiPanel";
import { ClassificationReport, MetricSummary } from "../components/Metrics";
import {
  Alert,
  Badge,
  Button,
  ButtonLink,
  Card,
  Chips,
  ConfirmDelete,
  ErrorBanner,
  KeyValue,
  Loading,
  PageHeader,
} from "../components/ui";
import { useAuth, useUser } from "../context/AuthContext";
import { OwnerBadge, VisibilityBadge, VisibilityToggle } from "../components/Visibility";
import { useAction, useAsync } from "../hooks/useAsync";
import { formatDate, formatInt, taskTypeOf } from "../lib/format";
import { prefillFromExperiment, tunableParameters } from "../lib/prefill";

export function ExperimentDetail() {
  const id = Number(useParams().experimentId);
  const navigate = useNavigate();
  const location = useLocation();
  const flash = location.state as { justTrained?: boolean; modelId?: number | null; modelError?: string | null } | null;
  const { user } = useUser();
  const signedIn = !!useAuth().session;

  const state = useAsync(async () => {
    const [experiment, options] = await Promise.all([api.experiments.get(id), api.models.options()]);
    // Owners see their saved models; others see the models shared with the experiment.
    const models =
      experiment.user_id === user?.user_id
        ? (await api.models.list()).filter((m) => m.experiment_id === id)
        : await api.explore.models({ experiment_id: id });
    const saved = models.map((m) => ({ model_id: m.model_id, created_at: m.created_at }));
    return [experiment, saved, options] as const;
  }, [id, user?.user_id]);
  const dataset = useAsync(
    () => (state.data ? api.datasets.get(state.data[0].dataset_id) : Promise.resolve(undefined)),
    [state.data?.[0].dataset_id],
  );
  const explain = useAction(() => api.experiments.explain(id));
  const recommend = useAction(() => api.experiments.recommend(id));
  const [deleting, setDeleting] = useState(false);
  const remove = useAction(() => api.experiments.remove(id));

  if (state.loading && !state.data) return <Loading />;
  if (state.error || !state.data)
    return (
      <>
        <PageHeader title="Experiment" breadcrumb={{ label: "Experiments", to: "/experiments" }} />
        <ErrorBanner error={state.error} onRetry={state.reload} />
      </>
    );

  const [experiment, savedModels, options] = state.data;
  const task = taskTypeOf(experiment);
  const owned = experiment.user_id === user?.user_id;
  const config = experiment.parameters ?? {};

  return (
    <>
      <PageHeader
        breadcrumb={owned ? { label: "Experiments", to: "/experiments" } : { label: "Discover", to: "/discover?tab=experiments" }}
        title={
          <>
            {experiment.algorithm} <span className="title-muted">#{experiment.experiment_id}</span>
          </>
        }
        subtitle={
          <>
            <Badge>{task}</Badge> predicting <span className="mono">{experiment.target}</span> on{" "}
            {dataset.error ? (
              <span className="muted">a private dataset</span>
            ) : (
              <Link to={`/datasets/${experiment.dataset_id}`}>{dataset.data?.name ?? `dataset #${experiment.dataset_id}`}</Link>
            )}{" "}
            · {formatDate(experiment.created_at)} <VisibilityBadge isPublic={experiment.is_public} />
            {!owned && <OwnerBadge name={experiment.owner_name} />}
          </>
        }
        actions={
          owned && (
            <>
              <Button variant="ghost" className="text-danger" onClick={() => setDeleting(true)}>
                Delete
              </Button>
              <ButtonLink
                to="/experiments/new"
                state={{ prefill: prefillFromExperiment(experiment, options, { sourceLabel: `experiment #${id}` }) }}
              >
                Re-run with changes
              </ButtonLink>
            </>
          )
        }
      />

      {flash?.justTrained && flash.modelError && (
        <Alert tone="warning">
          <strong>Training complete, but the model wasn't saved.</strong> {flash.modelError}
        </Alert>
      )}
      {flash?.justTrained && !flash.modelError && (
        <Alert tone="success">
          Training complete.{" "}
          {flash.modelId ? (
            <>Model #{flash.modelId} was saved and is ready for predictions.</>
          ) : (
            <>The model was not saved; use “Re-run & save model” below if you want to keep it.</>
          )}
        </Alert>
      )}

      <div className="grid-main-side">
        <div className="stack">
          <Card title="Test-set results">
            <MetricSummary experiment={experiment} />
          </Card>

          {task === "classification" && (
            <Card title="Per-class performance" flush>
              <ClassificationReport experiment={experiment} />
            </Card>
          )}

          <AiPanel
            title="Explain results"
            description="Interprets the metrics in the context of this configuration."
            actionLabel="Explain results"
            onRun={() => explain.run()}
            running={explain.running}
            error={explain.error}
            hasResult={!!explain.result}
          >
            {explain.result && <AiText text={explain.result.summary} />}
          </AiPanel>

          <AiPanel
            title="Suggest next experiment"
            description="Uses this run and earlier runs on the same dataset and target. Suggestions are validated against supported algorithms and parameter ranges."
            actionLabel="Suggest next experiment"
            onRun={() => recommend.run()}
            running={recommend.running}
            error={recommend.error}
            hasResult={!!recommend.result}
          >
            {recommend.result && (
              <div className="stack-sm">
                <AiText text={recommend.result.summary} />
                <div className="rec-grid">
                  {recommend.result.recommendations.map((rec, i) => (
                    <div key={i} className="rec-card">
                      <div className="rec-head">
                        <span className="rec-index">{i + 1}</span>
                        <strong>{rec.algorithm}</strong>
                      </div>
                      <div className="param-list">
                        {Object.entries(rec.parameters).map(([k, v]) => (
                          <span key={k} className="chip mono">
                            {k}={v === null ? "None" : String(v)}
                          </span>
                        ))}
                      </div>
                      <p>{rec.reason}</p>
                      <p className="muted small"><strong>Uncertainty:</strong> {rec.uncertainty}</p>
                      {owned && (
                        <Button
                          size="sm"
                          onClick={() =>
                            navigate("/experiments/new", {
                              state: {
                                prefill: prefillFromExperiment(experiment, options, {
                                  algorithm: rec.algorithm,
                                  parameters: rec.parameters,
                                  sourceLabel: `AI recommendation ${i + 1} for experiment #${id}`,
                                }),
                              },
                            })
                          }
                        >
                          Run this experiment →
                        </Button>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </AiPanel>
        </div>

        <div className="stack">
          {owned && (
            <Card title="Visibility">
              <VisibilityToggle
                isPublic={experiment.is_public}
                description="Anyone signed in can view these results, run AI explanations and use its saved model."
                onChange={async (next) => {
                  const updated = await api.experiments.setPublic(id, next);
                  state.setData([{ ...experiment, is_public: updated.is_public }, savedModels, options]);
                }}
              />
            </Card>
          )}
          <Card title="Saved model">
            {savedModels.length ? (
              <div className="stack-sm">
                {savedModels.map((m) => (
                  <div key={m.model_id} className="model-row">
                    <div>
                      <strong>Model #{m.model_id}</strong>
                      <div className="muted small">{formatDate(m.created_at)}</div>
                    </div>
                    {signedIn ? (
                      <ButtonLink to={`/predictions?model=${m.model_id}`} size="sm" variant="primary">
                        Predict
                      </ButtonLink>
                    ) : (
                      <ButtonLink to="/login" state={{ from: `/predictions?model=${m.model_id}` }} size="sm">
                        Sign in to use
                      </ButtonLink>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="stack-sm">
                {!owned && <p className="muted small">The owner did not save a model for this run.</p>}
                {owned && <p className="muted small">
                  This run's fitted pipeline was not stored. Re-running with identical settings reproduces it
                  (fixed random_state) and saves the model.
                </p>}
                {owned && (
                  <ButtonLink
                    to="/experiments/new"
                    variant="primary"
                    state={{
                      prefill: prefillFromExperiment(experiment, options, {
                        saveModel: true,
                        sourceLabel: `experiment #${id} (saving model)`,
                      }),
                    }}
                  >
                    Re-run & save model
                  </ButtonLink>
                )}
              </div>
            )}
          </Card>

          <Card title="Configuration">
            <KeyValue
              items={[
                ["Train / test", experiment.split?.train_size ? `${Math.round(experiment.split.train_size * 100)}% / ${Math.round((1 - experiment.split.train_size) * 100)}%` : "—"],
                ["Random state", experiment.split?.random_state ?? config.random_state ?? "—"],
                ["Missing values", config.missing_strategy === "drop_rows" ? "Drop rows" : config.missing_strategy === "impute" ? `Impute (${config.numerical_strategy ?? "—"} / ${config.categorical_strategy ?? "—"})` : "—"],
                ["Drop duplicates", config.drop_duplicates === undefined ? "—" : config.drop_duplicates ? "Yes" : "No"],
                ["Rows removed", `${formatInt(config.duplicates_removed ?? 0)} dup · ${formatInt(config.missing_rows_removed ?? 0)} missing`],
              ]}
            />
          </Card>

          <Card title="Hyperparameters">
            <HyperParameters experiment={experiment} options={options} />
          </Card>

          <Card title={`Features (${experiment.features.length})`}>
            <Chips items={experiment.features} max={30} />
            {!!config.categorical_features?.length && (
              <>
                <h3 className="section-label" style={{ marginTop: 14 }}>Categorical (one-hot)</h3>
                <Chips items={config.categorical_features} max={30} />
              </>
            )}
          </Card>
        </div>
      </div>

      {deleting && (
        <ConfirmDelete
          title="Delete experiment"
          message="This removes the experiment record. Experiments with saved models cannot be deleted until the model is deleted."
          running={remove.running}
          error={remove.error}
          onClose={() => setDeleting(false)}
          onConfirm={async () => {
            if (await remove.run()) navigate("/experiments");
          }}
        />
      )}
    </>
  );
}

function HyperParameters({ experiment, options }: { experiment: Experiment; options: ModelOptions }) {
  const [showAll, setShowAll] = useState(false);
  const all = (experiment.parameters?.classifier ?? {}) as Record<string, unknown>;
  const tunable = tunableParameters(options, taskTypeOf(experiment), experiment.algorithm, all);
  const entries = showAll ? Object.entries(all) : Object.entries(tunable);
  if (!Object.keys(all).length) return <p className="muted small">No estimator parameters stored.</p>;
  return (
    <>
      <KeyValue items={entries.map(([k, v]) => [<span className="mono">{k}</span>, <span className="mono">{v === null ? "None" : String(v)}</span>])} />
      <button className="link-btn small" onClick={() => setShowAll((s) => !s)}>
        {showAll ? "Show tunable only" : `Show all ${Object.keys(all).length} estimator parameters`}
      </button>
    </>
  );
}

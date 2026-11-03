import { Link } from "react-router-dom";
import { api } from "../api/endpoints";
import { Badge, ButtonLink, Card, EmptyState, ErrorBanner, Loading, PageHeader, Stat } from "../components/ui";
import { useUser } from "../context/AuthContext";
import { useAsync } from "../hooks/useAsync";
import { formatDate, primaryMetric, taskTypeOf } from "../lib/format";

export function Dashboard() {
  const { user } = useUser();
  const state = useAsync(
    () => Promise.all([api.datasets.list(), api.experiments.list(), api.models.list()]),
    [],
  );

  const [allDatasets = [], allExperiments = [], allModels = []] = state.data ?? [];
  const datasets = allDatasets;
  const experiments = allExperiments.filter((e) => e.user_id === user?.user_id);
  const experimentIds = new Set(experiments.map((e) => e.experiment_id));
  const models = allModels.filter((m) => experimentIds.has(m.experiment_id));
  const datasetName = new Map(allDatasets.map((d) => [d.dataset_id, d.name]));
  const recent = [...experiments]
    .sort((a, b) => b.created_at.localeCompare(a.created_at))
    .slice(0, 6);

  const steps = [
    { done: datasets.length > 0, label: "Upload a CSV dataset", to: "/datasets" },
    { done: experiments.length > 0, label: "Train your first experiment", to: "/experiments/new" },
    { done: models.length > 0, label: "Save a model", to: "/experiments" },
    { done: false, label: "Run predictions on new data", to: "/predictions" },
  ];

  return (
    <>
      <PageHeader
        title={user ? `Welcome back, ${user.name.split(" ")[0]}` : "Dashboard"}
        subtitle="Your datasets, experiments and saved models at a glance."
        actions={
          <>
            <ButtonLink to="/datasets">Upload dataset</ButtonLink>
            <ButtonLink to="/experiments/new" variant="primary">
              New experiment
            </ButtonLink>
          </>
        }
      />

      <ErrorBanner error={state.error} onRetry={state.reload} title="Could not load workspace" />
      {state.loading && !state.data ? (
        <Loading />
      ) : (
        <div className="stack">
          <div className="stats-row stats-cards">
            <Link to="/datasets" className="stat-link">
              <Stat label="Datasets" value={datasets.length} hint="Uploaded and cleaned CSVs" />
            </Link>
            <Link to="/experiments" className="stat-link">
              <Stat label="Experiments" value={experiments.length} hint="Training runs evaluated" />
            </Link>
            <Link to="/models" className="stat-link">
              <Stat label="Saved models" value={models.length} hint="Ready for prediction" />
            </Link>
          </div>

          <div className="grid-main-side">
            <Card
              title="Recent experiments"
              actions={experiments.length > 0 && <ButtonLink to="/experiments" size="sm" variant="ghost">View all</ButtonLink>}
              flush
            >
              {recent.length === 0 ? (
                <EmptyState
                  title="No experiments yet"
                  description="Train a model on one of your datasets to see results here."
                  action={<ButtonLink to="/experiments/new" variant="primary">New experiment</ButtonLink>}
                />
              ) : (
                <div className="table-wrap">
                  <table className="table table-hover">
                    <thead>
                      <tr>
                        <th>Experiment</th>
                        <th>Dataset</th>
                        <th>Target</th>
                        <th className="num">Score</th>
                        <th>Created</th>
                      </tr>
                    </thead>
                    <tbody>
                      {recent.map((e) => {
                        const metric = primaryMetric(e);
                        return (
                          <tr key={e.experiment_id}>
                            <td>
                              <Link to={`/experiments/${e.experiment_id}`} className="row-link">
                                {e.algorithm}
                              </Link>
                              <div className="muted small">
                                #{e.experiment_id} · <Badge>{taskTypeOf(e)}</Badge>
                              </div>
                            </td>
                            <td>{datasetName.get(e.dataset_id) ?? `#${e.dataset_id}`}</td>
                            <td className="mono">{e.target}</td>
                            <td className="num">
                              <span className="mono">{metric.value}</span>
                              <div className="muted small">{metric.label}</div>
                            </td>
                            <td className="muted small nowrap">{formatDate(e.created_at)}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>

            <Card title="Workflow">
              <ol className="checklist">
                {steps.map((s, i) => (
                  <li key={s.label} className={s.done ? "done" : ""}>
                    <span className="check">{s.done ? "✓" : i + 1}</span>
                    <Link to={s.to}>{s.label}</Link>
                  </li>
                ))}
              </ol>
              <p className="muted small" style={{ marginTop: 16 }}>
                Each step offers in-context AI help: explain a dataset, explain results, compare runs and get
                suggested next experiments.
              </p>
            </Card>
          </div>
        </div>
      )}
    </>
  );
}

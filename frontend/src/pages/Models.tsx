import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/endpoints";
import type { SavedModel } from "../api/types";
import { Badge, ButtonLink, Button, Card, ConfirmDelete, EmptyState, ErrorBanner, Loading, PageHeader } from "../components/ui";
import { useUser } from "../context/AuthContext";
import { VisibilityBadge } from "../components/Visibility";
import { useAction, useAsync } from "../hooks/useAsync";
import { formatDate, primaryMetric, taskTypeOf } from "../lib/format";

export function Models() {
  const { user } = useUser();
  const state = useAsync(
    () => Promise.all([api.models.list(), api.experiments.list(), api.datasets.list()]),
    [],
  );
  const [toDelete, setToDelete] = useState<SavedModel>();
  const remove = useAction(api.models.remove);

  const [models = [], experiments = [], datasets = []] = state.data ?? [];
  const experimentById = new Map(experiments.map((e) => [e.experiment_id, e]));
  const datasetName = new Map(datasets.map((d) => [d.dataset_id, d.name]));
  const mine = models
    .filter((m) => experimentById.get(m.experiment_id)?.user_id === user?.user_id)
    .sort((a, b) => b.model_id - a.model_id);

  return (
    <>
      <PageHeader
        title="Models"
        subtitle="Fitted scikit-learn pipelines (preprocessing + estimator) stored with joblib, ready for prediction."
      />
      <Card flush>
        <ErrorBanner error={state.error} onRetry={state.reload} />
        {state.loading && !state.data ? (
          <Loading />
        ) : mine.length === 0 ? (
          <EmptyState
            title="No saved models"
            description="Enable “Save trained model” when training, or re-run an existing experiment and save it."
            action={<ButtonLink to="/experiments" variant="primary">View experiments</ButtonLink>}
          />
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Model</th>
                  <th>Algorithm</th>
                  <th>Dataset → target</th>
                  <th className="num">Score</th>
                  <th>Saved</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {mine.map((m) => {
                  const e = experimentById.get(m.experiment_id);
                  const metric = e ? primaryMetric(e) : undefined;
                  return (
                    <tr key={m.model_id}>
                      <td>
                        <strong>Model #{m.model_id}</strong>
                        <div className="muted small">
                          from <Link to={`/experiments/${m.experiment_id}`}>experiment #{m.experiment_id}</Link>{" "}
                          <VisibilityBadge isPublic={m.is_public} />
                        </div>
                      </td>
                      <td>
                        {e?.algorithm ?? "—"}
                        {e && <div><Badge>{taskTypeOf(e)}</Badge></div>}
                      </td>
                      <td>
                        {e ? datasetName.get(e.dataset_id) ?? `#${e.dataset_id}` : "—"}
                        <div className="mono small">{e?.target}</div>
                      </td>
                      <td className="num mono">
                        {metric?.value ?? "—"}
                        <div className="muted small">{metric?.label}</div>
                      </td>
                      <td className="muted small nowrap">{formatDate(m.created_at)}</td>
                      <td className="num">
                        <div className="row-gap justify-end">
                          <Button size="sm" variant="ghost" className="text-danger" onClick={() => { remove.reset(); setToDelete(m); }}>
                            Delete
                          </Button>
                          <ButtonLink to={`/predictions?model=${m.model_id}`} size="sm" variant="primary">
                            Predict
                          </ButtonLink>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {toDelete && (
        <ConfirmDelete
          title={`Delete model #${toDelete.model_id}`}
          message="This removes the stored model artifact. Models referenced by saved prediction results cannot be deleted."
          running={remove.running}
          error={remove.error}
          onClose={() => setToDelete(undefined)}
          onConfirm={async () => {
            if (await remove.run(toDelete.model_id)) {
              setToDelete(undefined);
              state.reload();
            }
          }}
        />
      )}
    </>
  );
}

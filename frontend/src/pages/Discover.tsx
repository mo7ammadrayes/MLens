import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api/endpoints";
import type { PublicDataset, PublicExperimentSummary } from "../api/types";
import { DatasetCard } from "../components/DatasetCard";
import { Badge, ButtonLink, Card, EmptyState, ErrorBanner, Loading, PageHeader } from "../components/ui";
import { useAuth } from "../context/AuthContext";
import { useAsync } from "../hooks/useAsync";
import { formatDate, formatInt, formatNumber, formatPercent } from "../lib/format";

type Tab = "datasets" | "experiments" | "models";

const TABS: { id: Tab; label: string }[] = [
  { id: "datasets", label: "Datasets" },
  { id: "experiments", label: "Experiments" },
  { id: "models", label: "Models" },
];

function score(e: PublicExperimentSummary) {
  if (e.task_type === "regression") return { value: formatNumber(e.results.r2), label: "R²" };
  return { value: formatPercent(e.results.accuracy), label: "Accuracy" };
}

function Owner({ name, mine }: { name: string; mine: boolean }) {
  return mine ? <Badge tone="accent-plain">You</Badge> : <span className="muted">{name}</span>;
}

export function Discover() {
  const [params, setParams] = useSearchParams();
  const tab = (params.get("tab") as Tab) || "datasets";
  const q = params.get("q") ?? "";
  const [draft, setDraft] = useState(q);
  useEffect(() => setDraft(q), [q]);

  function update(next: { tab?: Tab; q?: string }) {
    const p = new URLSearchParams(params);
    if (next.tab) p.set("tab", next.tab);
    if (next.q !== undefined) (next.q ? p.set("q", next.q) : p.delete("q"));
    setParams(p, { replace: true });
  }

  return (
    <>
      <PageHeader
        title="Discover"
        subtitle="Real public datasets with example experiments. Open one to inspect the data, see how models perform on it, and use it for your own runs."
      />
      <div className="explore-bar">
        <div className="tabs" role="tablist">
          {TABS.map((t) => (
            <button key={t.id} role="tab" aria-selected={tab === t.id} className={tab === t.id ? "active" : ""} onClick={() => update({ tab: t.id })}>
              {t.label}
            </button>
          ))}
        </div>
        <form
          className="search"
          onSubmit={(e) => {
            e.preventDefault();
            update({ q: draft.trim() });
          }}
        >
          <input
            type="search"
            placeholder={tab === "datasets" ? "Search datasets…" : "Search by algorithm or target…"}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            aria-label="Search"
          />
        </form>
      </div>

      {tab === "datasets" && <DatasetsTab q={q} />}
      {tab === "experiments" && <ExperimentsTab q={q} />}
      {tab === "models" && <ModelsTab q={q} />}
    </>
  );
}

function DatasetsTab({ q }: { q: string }) {
  const state = useAsync(() => api.explore.datasets({ q }), [q]);
  const [tag, setTag] = useState<string>();

  const all = state.data ?? [];
  const tags = useMemo(() => {
    const counts = new Map<string, number>();
    all.forEach((d) => d.tags.forEach((t) => counts.set(t, (counts.get(t) ?? 0) + 1)));
    return [...counts.entries()].sort((a, b) => b[1] - a[1]).map(([t]) => t).slice(0, 10);
  }, [all]);
  const filtered = tag ? all.filter((d) => d.tags.includes(tag)) : all;
  const featured = filtered.filter((d) => d.is_featured);
  const shared = filtered.filter((d) => !d.is_featured);

  if (state.loading && !state.data) return <Loading />;
  if (state.error) return <ErrorBanner error={state.error} onRetry={state.reload} />;
  if (!all.length)
    return (
      <Card>
        <EmptyState title={q ? "No matching datasets" : "No public datasets yet"} description="Public datasets appear here." />
      </Card>
    );

  return (
    <div className="stack">
      {tags.length > 0 && (
        <div className="tag-filter" aria-label="Filter by tag">
          <button className={!tag ? "active" : ""} onClick={() => setTag(undefined)}>All</button>
          {tags.map((t) => (
            <button key={t} className={tag === t ? "active" : ""} onClick={() => setTag(tag === t ? undefined : t)}>
              {t}
            </button>
          ))}
        </div>
      )}

      {featured.length > 0 && (
        <section>
          <h2 className="discover-h2">Featured datasets</h2>
          <p className="muted small discover-sub">Curated by MLens to cover different machine-learning problems.</p>
          <div className="ds-grid">
            {featured.map((d) => <DatasetCard key={d.dataset_id} dataset={d} />)}
          </div>
        </section>
      )}

      {shared.length > 0 && (
        <section>
          <h2 className="discover-h2">Shared by users</h2>
          <SharedDatasetsTable datasets={shared} />
        </section>
      )}

      {!featured.length && !shared.length && <p className="muted">No datasets with this tag.</p>}
    </div>
  );
}

function SharedDatasetsTable({ datasets }: { datasets: PublicDataset[] }) {
  return (
    <Card flush>
      <div className="table-wrap">
        <table className="table table-hover">
          <thead>
            <tr>
              <th>Dataset</th>
              <th className="num">Rows</th>
              <th className="num">Columns</th>
              <th className="num">Example runs</th>
              <th>Owner</th>
              <th>Added</th>
            </tr>
          </thead>
          <tbody>
            {datasets.map((d) => (
              <tr key={d.dataset_id}>
                <td>
                  <Link className="row-link" to={`/datasets/${d.dataset_id}`}>{d.name}</Link>
                  {d.description && <div className="muted small clamp-1">{d.description}</div>}
                </td>
                <td className="num mono">{formatInt(d.rows)}</td>
                <td className="num mono">{formatInt(d.cols)}</td>
                <td className="num mono">{d.example_experiments || <span className="muted">0</span>}</td>
                <td><Owner name={d.owner_name} mine={d.is_mine} /></td>
                <td className="muted small nowrap">{formatDate(d.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

function ExperimentsTab({ q }: { q: string }) {
  const state = useAsync(() => api.explore.experiments({ q }), [q]);
  return (
    <Card flush>
      <ErrorBanner error={state.error} onRetry={state.reload} />
      {state.loading && !state.data ? (
        <Loading />
      ) : !state.data?.length ? (
        <EmptyState title={q ? "No matching experiments" : "No public experiments yet"} description="Experiments are listed here when their owner makes them public." />
      ) : (
        <div className="table-wrap">
          <table className="table table-hover">
            <thead>
              <tr>
                <th>Experiment</th>
                <th>Target</th>
                <th>Dataset</th>
                <th className="num">Score</th>
                <th>Owner</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {state.data.map((e) => {
                const s = score(e);
                return (
                  <tr key={e.experiment_id}>
                    <td>
                      <Link className="row-link" to={`/experiments/${e.experiment_id}`}>{e.algorithm}</Link>
                      <div className="muted small"><Badge>{e.task_type}</Badge></div>
                    </td>
                    <td className="mono">{e.target}</td>
                    <td>
                      {e.dataset_name ? (
                        <Link to={`/datasets/${e.dataset_id}`}>{e.dataset_name}</Link>
                      ) : (
                        <span className="muted small">Private dataset</span>
                      )}
                    </td>
                    <td className="num mono">
                      {s.value}
                      <div className="muted small">{s.label}</div>
                    </td>
                    <td><Owner name={e.owner_name} mine={e.is_mine} /></td>
                    <td className="muted small nowrap">{formatDate(e.created_at)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

function ModelsTab({ q }: { q: string }) {
  const state = useAsync(() => api.explore.models({ q }), [q]);
  const signedIn = !!useAuth().session;
  return (
    <Card flush>
      <ErrorBanner error={state.error} onRetry={state.reload} />
      {state.loading && !state.data ? (
        <Loading />
      ) : !state.data?.length ? (
        <EmptyState title={q ? "No matching models" : "No public models yet"} description="Saved models are public when their experiment is public." />
      ) : (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Model</th>
                <th>Predicts</th>
                <th className="num">Score</th>
                <th>Inputs</th>
                <th>Owner</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {state.data.map((m) => {
                const s = score(m.experiment);
                return (
                  <tr key={m.model_id}>
                    <td>
                      <strong>{m.experiment.algorithm}</strong>
                      <div className="muted small">
                        Model #{m.model_id}, from <Link to={`/experiments/${m.experiment_id}`}>experiment #{m.experiment_id}</Link>
                      </div>
                    </td>
                    <td className="mono">{m.experiment.target}</td>
                    <td className="num mono">
                      {s.value}
                      <div className="muted small">{s.label}</div>
                    </td>
                    <td className="muted small">{m.experiment.features.length} columns</td>
                    <td><Owner name={m.owner_name} mine={m.is_mine} /></td>
                    <td className="num">
                      <ButtonLink
                        to={signedIn ? `/predictions?model=${m.model_id}` : "/login"}
                        state={signedIn ? undefined : { from: `/predictions?model=${m.model_id}` }}
                        size="sm"
                        variant={signedIn ? "primary" : "secondary"}
                      >
                        {signedIn ? "Use model" : "Sign in to use"}
                      </ButtonLink>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

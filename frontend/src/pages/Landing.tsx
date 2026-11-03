import { useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import { scrollToHowItWorks } from "../components/PublicLayout";
import { api } from "../api/endpoints";
import { DatasetCard } from "../components/DatasetCard";
import { useAuth } from "../context/AuthContext";
import { useAsync } from "../hooks/useAsync";
import { formatNumber, formatPercent } from "../lib/format";
import snapshot from "../lib/heroSnapshot.json";

// A real curated example run, saved as a snapshot so the hero renders
// instantly with no API calls (see lib/heroSnapshot.json).
const RUN = snapshot;

function cell(v: string | number | boolean | null | undefined) {
  if (v === null || v === undefined) return "missing";
  return typeof v === "number" && !Number.isInteger(v) ? formatNumber(v, 2) : String(v);
}

function HeroRun() {
  const { dataset, experiment, preview } = RUN;
  const categorical = new Set(experiment.categorical_features);
  const shownFeatures = experiment.features.slice(0, 3);
  const columns = [...shownFeatures, experiment.target];
  const indexOf = (c: string) => preview.columns.indexOf(c);
  const extra = experiment.features.length - shownFeatures.length;
  const testPct = 100 - Math.round(experiment.train_size * 100);

  return (
    <figure className="run" aria-label={`Example run on ${dataset.name}`}>
      <div className="run-head">
        <span className="run-file">{dataset.name}</span>
        <Link to={`/discover?q=${encodeURIComponent(dataset.name)}`} className="run-tag">Real example run</Link>
      </div>

      <div className="run-stage run-stage-1 run-table-wrap">
        <table className="run-table">
          <thead>
            <tr>
              {columns.map((c) => {
                const isTarget = c === experiment.target;
                const kind = isTarget ? "target" : categorical.has(c) ? "text" : "number";
                return (
                  <th key={c} className={`kind-${kind}`}>
                    {c}
                    <span>{isTarget ? "target" : kind === "text" ? "text, one-hot" : "number, scaled"}</span>
                  </th>
                );
              })}
              {extra > 0 && <th className="run-more">+{extra}<span>more</span></th>}
            </tr>
          </thead>
          <tbody>
            {preview.rows.map((row, i) => (
              <tr key={i}>
                {columns.map((c) => {
                  const v = row[indexOf(c)];
                  return <td key={c} className={v === null ? "cell-missing" : ""}>{cell(v)}</td>;
                })}
                {extra > 0 && <td className="run-more">…</td>}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <ol className="run-stage run-stage-2 run-pipeline">
        <li>{experiment.missing_strategy === "drop_rows" ? "Drop incomplete rows" : "Fill missing values"}</li>
        <li>Scale numbers</li>
        {categorical.size > 0 && <li>One-hot encode text</li>}
        <li className="run-model">{experiment.algorithm}</li>
      </ol>

      <div className="run-stage run-stage-3 run-result">
        <div className="run-score">
          <span className="run-score-value">{formatPercent(experiment.accuracy)}</span>
          <span className="run-score-label">accuracy on the {testPct}% held out</span>
        </div>
        <div className="run-classes">
          <span className="run-classes-label">F1 by class, macro {formatNumber(experiment.macro_f1, 2)}</span>
          {experiment.classes.map(([label, f1]) => (
            <div key={label} className="run-class">
              <span title={String(label)}>{label}</span>
              <div className="run-bar"><i style={{ width: `${Math.max(0, Number(f1)) * 100}%` }} /></div>
              <span className="run-f1">{Number(f1).toFixed(2)}</span>
            </div>
          ))}
        </div>
      </div>

      <Link to={`/discover?q=${encodeURIComponent(dataset.name)}`} className="run-stage run-stage-4 run-ai">
        <span className="run-ai-mark">Explain results</span>
        Sign in to get a grounded AI explanation of these metrics.
      </Link>
    </figure>
  );
}

const STEPS = [
  { title: "Discover", text: "Browse curated public datasets, inspect their columns and missing values, and see how example models perform." },
  { title: "Train", text: "Upload your own CSV or use a public one. Pick a target, features and a scikit-learn model; preprocessing runs inside the pipeline." },
  { title: "Compare", text: "Put runs on the same target side by side, with warnings when the comparison isn't like for like." },
  { title: "Understand", text: "Get plain-language explanations grounded in the stored metrics, and suggestions for what to try next." },
  { title: "Predict", text: "Save a model and run it on new data. Download the predictions as CSV." },
];

const AI_ACTIONS = [
  { name: "Explain dataset", where: "Dataset page", text: "What the columns are, where the gaps are, what to fix before training. Uses the profile, not the raw rows." },
  { name: "Explain results", where: "Experiment page", text: "What the accuracy, F1 or R² actually say about this model, class by class." },
  { name: "Explain comparison", where: "Compare page", text: "Which run is better, by how much, and whether the comparison is fair." },
  { name: "Suggest next experiment", where: "Experiment page", text: "Up to three configurations to try next, checked against the supported settings." },
];

function FeaturedDatasets() {
  const state = useAsync(() => api.explore.datasets({ featured: true }), []);
  const list = (state.data ?? []).slice(0, 6);
  if (state.error || (state.data && !list.length)) return null;
  return (
    <section className="lp-section">
      <div className="lp-wrap">
        <div className="lp-section-head lp-head-row">
          <div>
            <h2>Featured datasets</h2>
            <p>Real, openly licensed data chosen to cover different problems: binary and multiclass classification, regression, text columns and missing values.</p>
          </div>
          <Link to="/discover" className="lp-link">See all in Discover</Link>
        </div>
        {state.loading ? (
          <div className="ds-grid" aria-busy="true" aria-label="Loading datasets">
            {Array.from({ length: 6 }, (_, i) => <div key={i} className="ds-card ds-card-skeleton" />)}
          </div>
        ) : (
          <div className="ds-grid">
            {list.map((d) => <DatasetCard key={d.dataset_id} dataset={d} />)}
          </div>
        )}
      </div>
    </section>
  );
}

export function Landing() {
  const signedIn = !!useAuth().session;
  const { hash } = useLocation();
  // Arriving from another page via "How it works" (/#how-it-works).
  useEffect(() => {
    if (hash === "#how-it-works") scrollToHowItWorks();
  }, [hash]);
  const uploadLink = signedIn
    ? { to: "/datasets" }
    : { to: "/login", state: { from: "/datasets" } };

  return (
    <main>
      <section className="lp-hero">
        <div className="lp-wrap lp-hero-grid">
          <div className="lp-hero-copy">
            <h1 aria-label="Discover, train, compare, and understand.">
              <span>Discover,</span>
              <span>train,</span>
              <span>compare,</span>
              <span>and understand.</span>
            </h1>
            <p className="lp-lede">
              MLens is a platform for exploring data, running machine-learning experiments, comparing models and
              understanding the results, with AI explanations grounded in your actual metrics.
            </p>
            <div className="lp-actions">
              <Link to="/discover" className="lp-btn lp-btn-dark">Explore public datasets</Link>
              <Link to={uploadLink.to} state={uploadLink.state} className="lp-btn lp-btn-line">Upload your dataset</Link>
            </div>
            <p className="lp-note">No account needed to explore.</p>
          </div>
          <HeroRun />
        </div>
      </section>

      <FeaturedDatasets />

      <section className="lp-section" id="how-it-works">
        <div className="lp-wrap">
          <div className="lp-section-head">
            <h2>How it works</h2>
            <p>Every run follows the same path, so results are easy to repeat, compare and explain.</p>
          </div>
          <ol className="lp-steps">
            {STEPS.map((step, i) => (
              <li key={step.title}>
                <span className="lp-step-n">{i + 1}</span>
                <h3>{step.title}</h3>
                <p>{step.text}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className="lp-section lp-ai">
        <div className="lp-wrap lp-ai-grid">
          <div className="lp-section-head">
            <h2>Explanations next to the numbers</h2>
            <p>
              The metrics come from the ML pipeline and are always shown as they are. The AI sits beside them on the
              page you're already on and explains them; it never replaces them. Explanations are available once you
              sign in.
            </p>
          </div>
          <dl className="lp-ai-list">
            {AI_ACTIONS.map((a) => (
              <div key={a.name}>
                <dt>
                  {a.name}
                  <span>{a.where}</span>
                </dt>
                <dd>{a.text}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      <section className="lp-close">
        <div className="lp-wrap lp-close-inner">
          <h2>Start with a public dataset, or bring your own.</h2>
          <div className="lp-actions lp-actions-tight">
            <Link to="/discover" className="lp-btn lp-btn-light">Explore public datasets</Link>
            <Link to="/signup" className="lp-btn lp-btn-ghost-light">Create an account</Link>
          </div>
        </div>
      </section>
    </main>
  );
}

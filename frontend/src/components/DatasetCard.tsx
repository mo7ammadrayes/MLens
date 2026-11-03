import { Link } from "react-router-dom";
import type { PublicDataset } from "../api/types";
import { formatInt } from "../lib/format";

const RowsIcon = () => (
  <svg width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden>
    <rect x="2" y="2.5" width="12" height="11" rx="1" />
    <path d="M2 6.2h12M2 9.8h12" />
  </svg>
);
const ColsIcon = () => (
  <svg width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden>
    <rect x="2" y="2.5" width="12" height="11" rx="1" />
    <path d="M6 2.5v11M10 2.5v11" />
  </svg>
);
const RunsIcon = () => (
  <svg width="15" height="15" viewBox="0 0 16 16" fill="currentColor" aria-hidden>
    <rect x="2" y="9" width="3" height="5" />
    <rect x="6.5" y="6" width="3" height="8" />
    <rect x="11" y="2.5" width="3" height="11.5" />
  </svg>
);

// A dataset in the Discover catalogue: what it is, how big, what it's good for.
export function DatasetCard({ dataset }: { dataset: PublicDataset }) {
  return (
    <Link to={`/datasets/${dataset.dataset_id}`} className="ds-card">
      <h3>{dataset.name}</h3>
      <div className="ds-card-meta">
        <span><RowsIcon /> {formatInt(dataset.rows)} rows</span>
        <span><ColsIcon /> {dataset.cols} cols</span>
        {dataset.example_experiments > 0 && (
          <span><RunsIcon /> {dataset.example_experiments} runs</span>
        )}
      </div>
      {dataset.description && <p className="ds-card-desc">{dataset.description}</p>}
      <div className="ds-card-tags">
        {dataset.tags.slice(0, 3).map((tag) => (
          <span key={tag}>{tag}</span>
        ))}
      </div>
      <div className="ds-card-foot">
        <span className="ds-card-sub">{dataset.is_featured ? "Curated by MLens" : `by ${dataset.owner_name}`}</span>
        <span className="ds-card-cta">
          See details
          <svg width="18" height="18" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
            <path d="M3.5 10h12M11 5.5l4.5 4.5-4.5 4.5" />
          </svg>
        </span>
      </div>
    </Link>
  );
}

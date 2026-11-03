# MLens — frontend

React + TypeScript (Vite) client for the FastAPI ML platform in `../backend`.

## Run locally

```bash
# 1. Backend (from the repository root)
uvicorn backend.main:app --reload          # http://127.0.0.1:8000

# 2. Frontend
cd frontend
cp .env.example .env    # then fill in VITE_SUPABASE_URL and VITE_SUPABASE_PUBLISHABLE_KEY
npm install
npm run dev
# open http://localhost:5173
```

The Vite dev server proxies `/api/*` to FastAPI (`BACKEND_URL`, default
`http://127.0.0.1:8000`), so the backend needs no CORS configuration in development.
Copy `.env.example` to `.env` to change it.

For a deployed build that calls the API on another origin, set
`VITE_API_BASE_URL` and add FastAPI's `CORSMiddleware` for the frontend origin.

```bash
npm run typecheck
npm run build      # output in dist/
```

## Structure

```text
src/
  api/          types.ts (mirrors backend schemas/responses), client.ts (fetch + error mapping), endpoints.ts
  context/      AuthContext — Supabase session + GET /users/me profile
  components/   Layout, UI primitives, AiPanel, metric views
  hooks/        useAsync / useAction
  lib/          supabase client, formatting, re-run/recommendation prefill
  pages/        Dashboard, Datasets, DatasetDetail, NewExperiment, Experiments,
                ExperimentDetail, Compare, Models, Predictions
```

## Screens → endpoints

| Screen | Endpoints |
|---|---|
| Account | `GET /users/me`, `PATCH /users/me` |
| Dashboard | `GET /datasets`, `GET /experiments`, `GET /models` |
| Datasets | `GET /datasets`, `POST /datasets` (multipart) |
| Dataset detail | `GET /datasets/{id}`, `GET …/inspect`, `POST …/clean`, `GET …/download`, `PATCH`, `DELETE`, `POST …/explanation` |
| New experiment | `GET /models/options`, `GET /datasets/{id}/inspect`, `POST /models/train` |
| Experiments | `GET /experiments`, `GET /models` |
| Experiment detail | `GET /experiments/{id}`, `POST …/explanation`, `POST …/recommendations`, `DELETE` |
| Compare | `POST /experiments/compare`, `POST /experiments/compare/explanation` |
| Models | `GET /models`, `DELETE /models/{id}` |
| Discover (public, no sign-in) | `GET /explore/datasets`, `/explore/experiments`, `/explore/models`, `/explore/stats`, `GET /datasets/{id}`, `/inspect`, `/preview`, `GET /experiments/{id}`, `POST /experiments/compare` |
| Predictions | `GET /predictions`, `POST /predictions`, `GET /predictions/{id}/download`, `DELETE /predictions/{id}` |

## Authentication

Sign-in uses Supabase Auth (`@supabase/supabase-js`). Every API request sends
`Authorization: Bearer <access token>`; FastAPI verifies it and scopes all data
to the signed-in user. A 401 from the API signs the browser out.

Routes: `/login`, `/signup`, `/forgot-password`, `/reset-password`; everything
else requires a session.

## Public experience and sharing

Signed-out visitors can open the landing page, Discover, and any **public**
dataset, experiment or comparison page (read-only: profile, preview, metrics).
Everything that costs compute, storage or Gemini calls needs sign-in: uploads,
training, predictions, downloads and all AI explanations.

Users choose public or private for each dataset and experiment; saved models
follow their experiment. "Use this dataset" makes a private copy owned by the
user, so the original owner can still edit or delete theirs.

Curated datasets (`is_featured`) are loaded by
`python -m backend.scripts.seed_discover` from `backend/scripts/discover_data/`.

## Remaining backend limitation

- **No "save model for an existing experiment".** Saving happens at training time
  (`save_model: true`). The experiment page offers *Re-run & save model*, which
  pre-fills the form with the same configuration (fixed `random_state = 42`).

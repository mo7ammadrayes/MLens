import { downloadFile, request } from "./client";
import type {
  CleanDatasetRequest,
  CleanDatasetResponse,
  ComparisonResponse,
  DatasetInspection,
  DatasetPreview,
  DatasetSummary,
  DeleteWithFileResponse,
  Experiment,
  ExperimentRecommendations,
  Explanation,
  ModelOptions,
  PredictRequest,
  PredictResponse,
  PredictionResultRecord,
  PublicDataset,
  PublicExperiment,
  PublicModel,
  SavedModel,
  TrainModelRequest,
  TrainModelResponse,
  UploadedDataset,
  UpdateDatasetRequest,
  UpdateUserRequest,
  User,
} from "./types";

export const api = {
  users: {
    me: () => request<User>("/users/me"),
    updateMe: (body: UpdateUserRequest) => request<User>("/users/me", { method: "PATCH", body }),
  },

  datasets: {
    list: () => request<DatasetSummary[]>("/datasets"),
    get: (id: number) => request<DatasetSummary>(`/datasets/${id}`),
    upload: (name: string, file: File, isPublic: boolean, description = "") => {
      const form = new FormData();
      form.append("name", name);
      form.append("is_public", String(isPublic));
      if (description) form.append("description", description);
      form.append("file", file);
      return request<UploadedDataset>("/datasets", { method: "POST", form });
    },
    rename: (id: number, name: string) =>
      request<{ dataset_id: number; updated_fields: { name: string } }>(`/datasets/${id}`, {
        method: "PATCH",
        body: { name },
      }),
    setPublic: (id: number, isPublic: boolean) =>
      request<{ dataset_id: number }>(`/datasets/${id}`, { method: "PATCH", body: { is_public: isPublic } }),
    copy: (id: number, name: string, isPublic = false) =>
      request<DatasetSummary>(`/datasets/${id}/copy`, { method: "POST", body: { name, is_public: isPublic } }),
    remove: (id: number) =>
      request<DeleteWithFileResponse & { dataset_id: number }>(`/datasets/${id}`, {
        method: "DELETE",
      }),
    inspect: (id: number) => request<DatasetInspection>(`/datasets/${id}/inspect`),
    preview: (id: number) => request<DatasetPreview>(`/datasets/${id}/preview`),
    update: (id: number, body: UpdateDatasetRequest) =>
      request<{ dataset_id: number }>(`/datasets/${id}`, { method: "PATCH", body }),
    clean: (id: number, body: CleanDatasetRequest) =>
      request<CleanDatasetResponse>(`/datasets/${id}/clean`, { method: "POST", body }),
    download: (id: number) => downloadFile(`/datasets/${id}/download`, `dataset_${id}.csv`),
    explain: (id: number) =>
      request<Explanation>(`/datasets/${id}/explanation`, { method: "POST" }),
  },

  experiments: {
    list: () => request<Experiment[]>("/experiments"),
    get: (id: number) => request<Experiment>(`/experiments/${id}`),
    setPublic: (id: number, isPublic: boolean) =>
      request<Experiment>(`/experiments/${id}`, { method: "PATCH", body: { is_public: isPublic } }),
    remove: (id: number) =>
      request<{ message: string }>(`/experiments/${id}`, { method: "DELETE" }),
    compare: (ids: number[]) =>
      request<ComparisonResponse>("/experiments/compare", {
        method: "POST",
        body: { experiment_ids: ids },
      }),
    explainComparison: (ids: number[]) =>
      request<Explanation>("/experiments/compare/explanation", {
        method: "POST",
        body: { experiment_ids: ids },
      }),
    explain: (id: number) =>
      request<Explanation>(`/experiments/${id}/explanation`, { method: "POST" }),
    recommend: (id: number) =>
      request<ExperimentRecommendations>(`/experiments/${id}/recommendations`, {
        method: "POST",
      }),
  },

  models: {
    options: () => request<ModelOptions>("/models/options"),
    list: () => request<SavedModel[]>("/models"),
    get: (id: number) => request<SavedModel>(`/models/${id}`),
    train: (body: TrainModelRequest) =>
      request<TrainModelResponse>("/models/train", { method: "POST", body }),
    remove: (id: number) =>
      request<DeleteWithFileResponse & { model_id: number }>(`/models/${id}`, {
        method: "DELETE",
      }),
  },

  predictions: {
    list: () => request<PredictionResultRecord[]>("/predictions"),
    get: (id: number) => request<PredictionResultRecord>(`/predictions/${id}`),
    run: (body: PredictRequest) =>
      request<PredictResponse>("/predictions", { method: "POST", body }),
    download: (id: number) =>
      downloadFile(`/predictions/${id}/download`, `prediction_result_${id}.csv`),
    remove: (id: number) =>
      request<DeleteWithFileResponse & { prediction_result_id: number }>(`/predictions/${id}`, {
        method: "DELETE",
      }),
  },

  explore: {
    stats: () =>
      request<{ experiments: number; models: number; datasets: number; contributors: number }>("/explore/stats"),
    datasets: (params: { q?: string; featured?: boolean } = {}) =>
      request<PublicDataset[]>(
        `/explore/datasets${query({ q: params.q, featured: params.featured === undefined ? undefined : String(params.featured) })}`,
      ),
    experiments: (params: { q?: string; dataset_id?: number } = {}) =>
      request<PublicExperiment[]>(`/explore/experiments${query(params)}`),
    models: (params: { q?: string; experiment_id?: number } = {}) =>
      request<PublicModel[]>(`/explore/models${query(params)}`),
  },
};

function query(params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") search.set(key, String(value));
  }
  const text = search.toString();
  return text ? `?${text}` : "";
}


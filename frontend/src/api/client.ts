import { getAccessToken, supabase } from "../lib/supabase";

const BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "/api";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

// FastAPI errors are {"detail": string} for HTTPException,
// or {"detail": [{loc, msg}]} for request validation failures.
function describeDetail(detail: unknown): string | null {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        const loc = Array.isArray(item?.loc)
          ? item.loc.filter((part: unknown) => part !== "body").join(".")
          : "";
        return loc ? `${loc}: ${item?.msg}` : String(item?.msg ?? item);
      })
      .join("; ");
  }
  return null;
}

async function toApiError(response: Response): Promise<ApiError> {
  let message = `Request failed (${response.status})`;
  try {
    const body = await response.json();
    message = describeDetail(body?.detail) ?? message;
  } catch {
    if (response.status === 500) message = "The server encountered an error.";
    if (response.status === 502 || response.status === 504) {
      message = "The API server could not be reached. Is the backend running?";
    }
  }
  if (response.status === 401) {
    // Token rejected by the API: end the local session so the app returns to sign-in.
    void supabase.auth.signOut({ scope: "local" });
  }
  return new ApiError(response.status, message);
}

async function send(path: string, init: RequestInit): Promise<Response> {
  const token = await getAccessToken();
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  try {
    return await fetch(`${BASE_URL}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(0, "Could not reach the API. Check that the backend is running.");
  }
}

export async function request<T>(
  path: string,
  options: { method?: string; body?: unknown; form?: FormData } = {},
): Promise<T> {
  const init: RequestInit = { method: options.method ?? "GET" };

  if (options.form) {
    init.body = options.form;
  } else if (options.body !== undefined) {
    init.body = JSON.stringify(options.body);
    init.headers = { "Content-Type": "application/json" };
  }

  const response = await send(path, init);
  if (!response.ok) throw await toApiError(response);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

// Fetch a file endpoint and hand it to the browser as a download.
export async function downloadFile(path: string, fallbackName: string): Promise<void> {
  const response = await send(path, { method: "GET" });
  if (!response.ok) throw await toApiError(response);

  const disposition = response.headers.get("Content-Disposition") ?? "";
  const match = disposition.match(/filename="?([^"]+)"?/);
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = match?.[1] ?? fallbackName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

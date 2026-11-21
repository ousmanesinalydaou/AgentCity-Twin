export class ApiError extends Error {
  constructor(message: string, public status: number) { super(message); }
}

let refreshing: Promise<Response> | null = null;
export async function api<T>(path: string, method = "GET", payload?: unknown, retry = true): Promise<T> {
  const response = await fetch("/api/v1" + path, {
    method, credentials: "same-origin",
    ...(payload === undefined ? {} : { headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }),
  });
  if (response.status === 401 && retry && !["/auth/login", "/auth/demo", "/auth/refresh"].includes(path)) {
    refreshing ??= fetch("/api/v1/auth/refresh", { method: "POST" }).finally(() => { refreshing = null; });
    if ((await refreshing).ok) return api(path, method, payload, false);
  }
  if (!response.ok) {
    const error = await response.json().catch(() => null);
    const detail = error?.detail;
    const message = typeof detail === "string" ? detail : Array.isArray(detail) ? detail.map((field) => {
      const name = field.loc?.slice(1).join(".");
      return [name, field.msg].filter(Boolean).join(" — ");
    }).join(" · ") : "The service is unavailable. Try again.";
    throw new ApiError(message, response.status);
  }
  return response.status === 204 ? undefined as T : response.json() as Promise<T>;
}
export function messageOf(error: unknown) {
  return error instanceof Error ? error.message : "Something went wrong.";
}


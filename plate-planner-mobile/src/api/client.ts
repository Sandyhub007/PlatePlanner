import { API_BASE_URL } from "./config";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

const apiUrl = API_BASE_URL;

type RequestOptions = {
  token?: string | null;
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  headers?: Record<string, string>;
};

export async function apiRequest<T>(
  path: string,
  options: RequestOptions = {}
): Promise<T> {
  const { token, method = "GET", body, headers = {} } = options;
  const res = await fetch(`${apiUrl}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    const text = await res.text();
    throw new ApiError(text || "Request failed", res.status);
  }

  if (res.status === 204) {
    return {} as T;
  }

  return res.json() as Promise<T>;
}

export async function apiFormRequest<T>(
  path: string,
  form: Record<string, string>
): Promise<T> {
  const body = new URLSearchParams(form);
  const res = await fetch(`${apiUrl}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });

  if (!res.ok) {
    const text = await res.text();
    throw new ApiError(text || "Request failed", res.status);
  }

  return res.json() as Promise<T>;
}

export async function apiUploadRequest<T>(
  path: string,
  formData: FormData,
  token?: string | null
): Promise<T> {
  const headers: Record<string, string> = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers,
    body: formData,
  });

  if (!res.ok) {
    const text = await res.text();
    throw new ApiError(text || "Upload failed", res.status);
  }

  return res.json() as Promise<T>;
}

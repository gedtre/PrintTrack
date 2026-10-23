import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
export type Cell = string | number | boolean | null;
export type Row = Record<string, Cell> & { id: number };
export interface User {
  id: number;
  username: string;
  role: "admin" | "it" | "viewer";
  language: "lt" | "en";
  active: boolean;
}
export class ApiError extends Error {
  constructor(
    public code: string,
    public status: number,
  ) {
    super(code);
  }
}
export async function api<T>(
  path: string,
  body?: unknown,
  method?: string,
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api${path}`, {
      credentials: "same-origin",
      method: method ?? (body === undefined ? "GET" : "POST"),
      headers: body === undefined ? {} : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError("NETWORK", 0);
  }
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new ApiError(
      typeof data.detail === "string" ? data.detail : "UNKNOWN",
      response.status,
    );
  }
  return response.json();
}
export function useRows(resource: string) {
  return useQuery({
    queryKey: [resource],
    queryFn: () => api<Row[]>(`/${resource}`),
  });
}
export function useWrite() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({
      path,
      body,
      method,
    }: {
      path: string;
      body?: unknown;
      method?: string;
    }) => api(path, body, method),
    onSuccess: () => client.invalidateQueries(),
  });
}
export const resources = [
  "departments",
  "buildings",
  "rooms",
  "models",
  "printers",
  "cartridges",
  "compatibility",
] as const;
export function useCatalog() {
  return useQuery({
    queryKey: ["catalog"],
    queryFn: async () =>
      Object.fromEntries(
        await Promise.all(
          resources.map(async (resource) => [
            resource,
            await api<Row[]>(`/${resource}`),
          ]),
        ),
      ) as Record<(typeof resources)[number], Row[]>,
  });
}
export function label(row: Row | undefined): string {
  return row
    ? String(
        row.inventory_number ?? row.code ?? row.name ?? row.username ?? row.id,
      )
    : "—";
}
export function errorCode(error: unknown) {
  return error instanceof ApiError ? error.code : "UNKNOWN";
}

import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { api, ApiError, label, useCatalog, useWrite, type Row } from "../api";
import { ErrorMessage, Loading, Table } from "./Shared";
export function ReportsPage({
  history = false,
  canEdit = false,
}: {
  history?: boolean;
  canEdit?: boolean;
}) {
  const { t, i18n } = useTranslation();
  const [params] = useSearchParams();
  const catalog = useCatalog();
  const write = useWrite();
  const [report, setReport] = useState("history");
  const [filters, setFilters] = useState<Record<string, string>>({
    printer_id: params.get("printer") ?? "",
  });
  const [downloadError, setDownloadError] = useState<unknown>();
  const stock = ["stock", "low"].includes(report);
  const actualFilters = Object.fromEntries(
    Object.entries(filters).filter(
      ([key, v]) => v && (!stock || key === "cartridge_id"),
    ),
  );
  const query = new URLSearchParams({ report, ...actualFilters }).toString();
  const result = useQuery({
    queryKey: ["report", query],
    queryFn: () => api<{ columns: string[]; rows: Row[] }>(`/reports?${query}`),
  });
  async function download() {
    try {
      setDownloadError(undefined);
      const response = await fetch(
        `/api/reports/export?${query}&language=${i18n.resolvedLanguage}`,
        { credentials: "same-origin" },
      );
      if (!response.ok) throw new ApiError("UNKNOWN", response.status);
      const url = URL.createObjectURL(await response.blob());
      const a = document.createElement("a");
      a.href = url;
      a.download = `printtrack-${report}.csv`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (error) {
      setDownloadError(error);
    }
  }
  return (
    <>
      <h1>{t(history ? "nav.history" : "nav.reports")}</h1>
      <section className="card">
        <div className="form-grid">
          {!history && (
            <label>
              {t("app.reportType")}
              <select
                value={report}
                onChange={(e) => setReport(e.target.value)}
              >
                {[
                  "history",
                  "stock",
                  "low",
                  "monthly",
                  "printer",
                  "department",
                ].map((r) => (
                  <option key={r} value={r}>
                    {t(`reportTypes.${r}`)}
                  </option>
                ))}
              </select>
            </label>
          )}
          {!stock &&
            ["start", "end"].map((key) => (
              <label key={key}>
                {t(key === "start" ? "reports.from" : "reports.to")}
                <input
                  type="date"
                  value={filters[key] ?? ""}
                  onChange={(e) =>
                    setFilters({ ...filters, [key]: e.target.value })
                  }
                />
              </label>
            ))}
          {(["department_id", "printer_id", "cartridge_id"] as const)
            .filter((key) => !stock || key === "cartridge_id")
            .map((key) => {
              const resource =
                key === "department_id"
                  ? "departments"
                  : key === "printer_id"
                    ? "printers"
                    : "cartridges";
              return (
                <label key={key}>
                  {t(`fields.${key}`)}
                  <select
                    value={filters[key] ?? ""}
                    onChange={(e) =>
                      setFilters({ ...filters, [key]: e.target.value })
                    }
                  >
                    <option value="">{t("app.all")}</option>
                    {catalog.data?.[resource].map((row) => (
                      <option key={row.id} value={row.id}>
                        {label(row)}
                      </option>
                    ))}
                  </select>
                </label>
              );
            })}
        </div>
        <p>{t(stock ? "app.stockReportHelp" : "app.reportHelp")}</p>
        <button onClick={() => void download()} disabled={!result.data}>
          {t("reports.export")}
        </button>
      </section>
      <ErrorMessage
        error={result.error ?? catalog.error ?? write.error ?? downloadError}
      />
      {write.isSuccess && <p role="status">{t("app.operationSaved")}</p>}
      {result.isLoading ? (
        <Loading />
      ) : (
        result.data && (
          <section className="card">
            <Table
              rows={result.data.rows.map((r, index) => ({
                ...r,
                id: r.id ?? index + 1,
              }))}
              columns={result.data.columns}
              actions={
                canEdit && report === "history"
                  ? (row) => (
                      <button
                        disabled={
                          write.isPending ||
                          !!row.correction_of_id ||
                          result.data!.rows.some(
                            (r) => r.correction_of_id === row.id,
                          )
                        }
                        onClick={() => {
                          const reason = window.prompt(t("app.reverseReason"));
                          if (reason?.trim())
                            write.mutate({
                              path: `/transactions/${row.id}/reverse`,
                              body: {
                                notes: reason,
                                request_id: crypto.randomUUID(),
                              },
                            });
                        }}
                      >
                        {t("app.reverse")}
                      </button>
                    )
                  : undefined
              }
            />
          </section>
        )
      )}
    </>
  );
}

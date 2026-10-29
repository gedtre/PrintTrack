import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { api, ApiError, useRows } from "../api";
import { ErrorMessage } from "./Shared";
interface ImportRow {
  line: number;
  number: string;
  name: string;
  department: string;
  building: string;
  floor: string;
  source: string;
  status: string;
  issues: string[];
}
interface Preview {
  rows: ImportRow[];
  valid: boolean;
  counts: Record<string, number>;
  new_departments: string[];
}
interface Result {
  created: number;
  existing: number;
  skipped: number;
}
export function RoomImport() {
  const { t } = useTranslation();
  const client = useQueryClient();
  const buildings = useRows("buildings");
  const [csv, setCsv] = useState("");
  const [building, setBuilding] = useState("");
  const [floor, setFloor] = useState("");
  const [fileError, setFileError] = useState<unknown>();
  const [reading, setReading] = useState(false);
  const preview = useMutation({
    mutationFn: () =>
      api<Preview>("/room-import/preview", {
        csv_text: csv,
        default_building_id: building ? Number(building) : null,
        default_floor: floor,
      }),
  });
  const commit = useMutation({
    mutationFn: () =>
      api<Result>("/room-import/commit", {
        csv_text: csv,
        default_building_id: building ? Number(building) : null,
        default_floor: floor,
      }),
    onSuccess: async () => {
      preview.reset();
      await client.invalidateQueries();
    },
  });
  function reset() {
    preview.reset();
    commit.reset();
    setFileError(undefined);
  }
  const busy = reading || preview.isPending || commit.isPending;
  return (
    <details className="card">
      <summary>{t("roomImport.title")}</summary>
      <p>{t("roomImport.help")}</p>
      <p className="notice">{t("roomImport.warning")}</p>
      <label>
        {t("roomImport.file")}
        <input
          type="file"
          accept=".csv,text/csv"
          disabled={busy}
          onChange={async (e) => {
            reset();
            setCsv("");
            const file = e.target.files?.[0];
            if (!file) return;
            if (file.size > 1000000) {
              setFileError(new ApiError("IMPORT_LIMIT", 422));
              return;
            }
            setReading(true);
            try {
              setCsv(await file.text());
            } catch {
              setFileError(new ApiError("IMPORT_FORMAT", 422));
            } finally {
              setReading(false);
            }
          }}
        />
      </label>
      <div className="form-grid">
        <label>
          {t("roomImport.building")}
          <select
            disabled={busy}
            value={building}
            onChange={(e) => {
              setBuilding(e.target.value);
              reset();
            }}
          >
            <option value="">{t("roomImport.fromFile")}</option>
            {buildings.data?.map((b) => (
              <option key={b.id} value={b.id}>
                {String(b.name)}
              </option>
            ))}
          </select>
        </label>
        <label>
          {t("roomImport.floor")}
          <input
            disabled={busy}
            value={floor}
            maxLength={40}
            onChange={(e) => {
              setFloor(e.target.value);
              reset();
            }}
          />
        </label>
      </div>
      <p>{t("roomImport.columns")}</p>
      <button
        disabled={!csv || busy}
        onClick={() => {
          commit.reset();
          preview.mutate();
        }}
      >
        {t("roomImport.preview")}
      </button>
      <ErrorMessage
        error={fileError ?? preview.error ?? commit.error ?? buildings.error}
      />
      {commit.data && (
        <p role="status">{t("roomImport.done", { ...commit.data })}</p>
      )}
      {preview.data && (
        <>
          <p role="status">{t("roomImport.counts", preview.data.counts)}</p>
          {preview.data.new_departments.length > 0 && (
            <p>
              {t("roomImport.newDepartments")}:{" "}
              {preview.data.new_departments.join("; ")}
            </p>
          )}
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  {[
                    "line",
                    "number",
                    "name",
                    "department",
                    "building",
                    "floor",
                    "status",
                    "issues",
                  ].map((key) => (
                    <th key={key}>{t(`roomImport.${key}`)}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {preview.data.rows.map((row) => (
                  <tr key={row.line}>
                    <td>{row.line}</td>
                    <td>{row.number}</td>
                    <td>{row.name}</td>
                    <td>{row.department}</td>
                    <td>{row.building || "—"}</td>
                    <td>{row.floor || "—"}</td>
                    <td>{t(`roomImport.states.${row.status}`)}</td>
                    <td>
                      {row.issues
                        .map((code) => t(`roomImport.issues.${code}`))
                        .join(" ")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p>{t("roomImport.atomic")}</p>
          <button
            className="primary"
            disabled={
              busy || !preview.data.valid || preview.data.counts.ready === 0
            }
            onClick={() => {
              if (window.confirm(t("roomImport.confirm"))) commit.mutate();
            }}
          >
            {t("roomImport.commit")}
          </button>
        </>
      )}
    </details>
  );
}

import { RoomImport } from "./RoomImport";
import { useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import { api, label, useCatalog, useRows, useWrite, type Row } from "../api";
import { ErrorMessage, Loading, Table } from "./Shared";
export type Field = {
  key: string;
  type?: string;
  ref?: string;
  options?: string[];
  optional?: boolean;
};
export const definitions: Record<string, Field[]> = {
  departments: [{ key: "name" }],
  buildings: [{ key: "name" }],
  rooms: [
    { key: "name" },
    { key: "number" },
    { key: "floor" },
    { key: "building_id", ref: "buildings" },
    { key: "department_id", ref: "departments" },
  ],
  models: [{ key: "manufacturer" }, { key: "name" }],
  printers: [
    { key: "model_id", ref: "models" },
    { key: "serial_number" },
    { key: "inventory_number" },
    { key: "ip_address", optional: true },
    { key: "room_id", ref: "rooms" },
    { key: "status", options: ["active", "repair", "unused"] },
    { key: "installation_date", type: "date" },
    { key: "notes", type: "textarea", optional: true },
    { key: "archived", type: "checkbox", optional: true },
  ],
  cartridges: [
    { key: "code" },
    { key: "manufacturer" },
    { key: "kind", options: ["original", "compatible"] },
    { key: "color", options: ["black", "cyan", "magenta", "yellow"] },
    { key: "minimum_stock", type: "number" },
    { key: "description", type: "textarea", optional: true },
    { key: "notes", type: "textarea", optional: true },
  ],
};
export function Fields({
  fields,
  values,
  setValues,
  catalog,
}: {
  fields: Field[];
  values: Record<string, string>;
  setValues: (v: Record<string, string>) => void;
  catalog: Record<string, Row[]>;
}) {
  const { t } = useTranslation();
  return (
    <div className="form-grid">
      {fields.map((field) => {
        const props = {
          id: `field-${field.key}`,
          name: field.key,
          required: !field.optional,
          value: values[field.key] ?? "",
          onChange: (
            e: React.ChangeEvent<
              HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement
            >,
          ) => setValues({ ...values, [field.key]: e.target.value }),
        };
        return (
          <div key={field.key}>
            <label htmlFor={props.id}>{t(`fields.${field.key}`)}</label>
            {field.ref || field.options ? (
              <select {...props}>
                <option value="">{t("app.select")}</option>
                {field.ref
                  ? (catalog[field.ref] ?? []).map((row) => (
                      <option key={row.id} value={row.id}>
                        {field.ref === "rooms" ? `${row.number} · ` : ""}
                        {label(row)}
                      </option>
                    ))
                  : field.options?.map((value) => (
                      <option key={value} value={value}>
                        {t(`values.${value}`)}
                      </option>
                    ))}
              </select>
            ) : field.type === "textarea" ? (
              <textarea {...props} maxLength={4000} />
            ) : field.type === "checkbox" ? (
              <input
                id={props.id}
                type="checkbox"
                checked={values[field.key] === "true"}
                onChange={(e) =>
                  setValues({
                    ...values,
                    [field.key]: String(e.target.checked),
                  })
                }
              />
            ) : (
              <input
                {...props}
                type={field.type ?? "text"}
                maxLength={
                  field.key === "name"
                    ? 120
                    : field.key === "password"
                      ? 200
                      : 120
                }
                min={field.type === "number" ? 0 : undefined}
                step={field.type === "number" ? 1 : undefined}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
function initialValues(resource: string): Record<string, string> {
  return resource === "printers"
    ? {
        status: "active",
        archived: "false",
        installation_date: new Date().toISOString().slice(0, 10),
      }
    : resource === "cartridges"
      ? { kind: "compatible", color: "black", minimum_stock: "2" }
      : resource === "rooms"
        ? { floor: "1" }
        : {};
}
export function ResourcePage({
  resource,
  canEdit,
  search,
}: {
  resource: string;
  canEdit: boolean;
  search: string;
}) {
  const { t } = useTranslation();
  const data = useRows(resource);
  const catalog = useCatalog();
  const write = useWrite();
  const [editing, setEditing] = useState<number | null | undefined>();
  const [values, setValues] = useState<Record<string, string>>({});
  const [detail, setDetail] = useState<Row | null>(null);
  const [localSearch, setLocalSearch] = useState("");
  const [showArchived, setShowArchived] = useState(false);
  const history = useQuery({
    queryKey: ["assignments", detail?.id],
    queryFn: () => api<Row[]>(`/printers/${detail?.id}/history`),
    enabled: resource === "printers" && !!detail,
  });
  if (data.isLoading || catalog.isLoading) return <Loading />;
  if (data.error || catalog.error)
    return <ErrorMessage error={data.error ?? catalog.error} />;
  const refs = catalog.data!;
  const enriched = (data.data ?? []).map((row) => ({
    ...row,
    ...Object.fromEntries(
      definitions[resource]
        .filter((f) => f.ref)
        .map((f) => [
          f.key.replace("_id", "_label"),
          label(
            refs[f.ref as keyof typeof refs].find((r) => r.id === row[f.key]),
          ),
        ]),
    ),
  }));
  const filtered = enriched.filter(
    (row) =>
      (showArchived || !row.archived) &&
      `${search} ${localSearch}`
        .trim()
        .toLowerCase()
        .split(/\s+/)
        .every((term) =>
          Object.values(row).join(" ").toLowerCase().includes(term),
        ),
  );
  const columns: Record<string, string[]> = {
    departments: ["name"],
    buildings: ["name"],
    models: ["manufacturer", "name"],
    rooms: ["number", "name", "floor", "building_label", "department_label"],
    printers: [
      "inventory_number",
      "model_label",
      "serial_number",
      "room_label",
      "status",
      "archived",
    ],
    cartridges: [
      "code",
      "manufacturer",
      "kind",
      "color",
      "balance",
      "minimum_stock",
    ],
  };
  function edit(row?: Row) {
    setEditing(row?.id ?? null);
    setValues(
      row
        ? Object.fromEntries(
            definitions[resource].map((f) => [f.key, String(row[f.key] ?? "")]),
          )
        : initialValues(resource),
    );
    write.reset();
  }
  return (
    <>
      <div className="page-heading">
        <h1>{t(`nav.${resource}`)}</h1>
        {canEdit && (
          <button className="primary" onClick={() => edit()}>
            {t("app.add")}
          </button>
        )}
      </div>
      {resource === "rooms" && canEdit && <RoomImport />}
      <div className="toolbar">
        <input
          aria-label={t("common.search")}
          placeholder={t("common.search")}
          value={localSearch}
          onChange={(e) => setLocalSearch(e.target.value)}
        />
        {resource === "printers" && (
          <label className="inline">
            <input
              type="checkbox"
              checked={showArchived}
              onChange={(e) => setShowArchived(e.target.checked)}
            />
            {t("app.showArchived")}
          </label>
        )}
      </div>
      <ErrorMessage error={write.error} />
      {write.isSuccess && <p role="status">{t("app.saved")}</p>}
      {editing !== undefined && (
        <section className="card">
          <h2>{t(editing === null ? "app.add" : "app.edit")}</h2>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              const body = Object.fromEntries(
                definitions[resource].map((f) => [
                  f.key,
                  f.type === "checkbox"
                    ? values[f.key] === "true"
                    : f.ref || f.type === "number"
                      ? Number(values[f.key])
                      : f.key === "ip_address" && !values[f.key]
                        ? null
                        : (values[f.key] ?? ""),
                ]),
              );
              write.mutate(
                {
                  path: `/${resource}${editing === null ? "" : `/${editing}`}`,
                  method: editing === null ? "POST" : "PUT",
                  body,
                },
                { onSuccess: () => setEditing(undefined) },
              );
            }}
          >
            <Fields
              fields={definitions[resource]}
              values={values}
              setValues={setValues}
              catalog={refs}
            />
            <div className="row-actions">
              <button className="primary" disabled={write.isPending}>
                {t("common.save")}
              </button>
              <button type="button" onClick={() => setEditing(undefined)}>
                {t("common.cancel")}
              </button>
            </div>
          </form>
        </section>
      )}
      <section className="card">
        <Table
          rows={filtered}
          columns={columns[resource]}
          actions={(row) => (
            <>
              {canEdit && (
                <button onClick={() => edit(row)}>{t("app.edit")}</button>
              )}
              {["rooms", "printers"].includes(resource) && (
                <button onClick={() => setDetail(row)}>
                  {t("app.details")}
                </button>
              )}
              {resource === "printers" && canEdit && !row.archived && (
                <Link
                  className="button"
                  to={`/inventory?printer=${row.id}&kind=issue`}
                >
                  {t("app.issue")}
                </Link>
              )}
            </>
          )}
        />
      </section>
      {detail && (
        <section className="card">
          <div className="page-heading">
            <h2>{label(detail)}</h2>
            <button onClick={() => setDetail(null)}>{t("app.close")}</button>
          </div>
          {resource === "rooms" && (
            <>
              <h3>{t("nav.printers")}</h3>
              {refs.printers
                .filter((p) => p.room_id === detail.id && !p.archived)
                .map((p) => (
                  <div className="detail-item" key={p.id}>
                    <strong>{label(p)}</strong>
                    <p>
                      {t("app.verifiedCartridges")}:{" "}
                      {refs.compatibility
                        .filter((c) => c.model_id === p.model_id && c.verified)
                        .map((c) =>
                          label(
                            refs.cartridges.find(
                              (t) => t.id === c.cartridge_id,
                            ),
                          ),
                        )
                        .join(", ") || t("common.empty")}
                    </p>
                  </div>
                ))}
            </>
          )}
          {resource === "printers" && (
            <>
              <h3>{t("app.assignments")}</h3>
              <ErrorMessage error={history.error} />
              <Table
                rows={history.data ?? []}
                columns={["occurred_at", "from_label", "to_label"]}
              />
              <Link to={`/history?printer=${detail.id}`}>
                {t("nav.history")}
              </Link>
            </>
          )}
        </section>
      )}
    </>
  );
}
export function CompatibilityPage({ canEdit }: { canEdit: boolean }) {
  const { t } = useTranslation();
  const catalog = useCatalog();
  const write = useWrite();
  const [values, setValues] = useState<Record<string, string>>({
    verified: "false",
  });
  if (catalog.isLoading) return <Loading />;
  if (catalog.error) return <ErrorMessage error={catalog.error} />;
  const data = catalog.data!;
  return (
    <section className="card">
      <h2>{t("app.compatibility")}</h2>
      <p>{t("app.compatibilityHelp")}</p>
      <ErrorMessage error={write.error} />
      {write.isSuccess && <p role="status">{t("app.saved")}</p>}
      {canEdit && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (!window.confirm(t("app.confirmCompatibility"))) return;
            write.mutate({
              path: "/compatibility",
              body: {
                model_id: Number(values.model_id),
                cartridge_id: Number(values.cartridge_id),
                verified: values.verified === "true",
                evidence: values.evidence ?? "",
              },
            });
          }}
        >
          <Fields
            fields={[
              { key: "model_id", ref: "models" },
              { key: "cartridge_id", ref: "cartridges" },
              { key: "verified", type: "checkbox", optional: true },
              { key: "evidence", type: "textarea" },
            ]}
            values={values}
            setValues={setValues}
            catalog={data}
          />
          <button className="primary" disabled={write.isPending}>
            {t("common.save")}
          </button>
        </form>
      )}
      <Table
        rows={data.compatibility.map((c) => ({
          ...c,
          model_label: label(data.models.find((m) => m.id === c.model_id)),
          cartridge_code: label(
            data.cartridges.find((t) => t.id === c.cartridge_id),
          ),
        }))}
        columns={[
          "model_label",
          "cartridge_code",
          "verified",
          "verified_at",
          "evidence",
        ]}
      />
    </section>
  );
}

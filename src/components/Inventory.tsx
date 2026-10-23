import { useLocaleFormat } from "../format";
import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { label, useCatalog, useWrite } from "../api";
import { ErrorMessage, Loading, Table } from "./Shared";
export function InventoryPage({ canEdit }: { canEdit: boolean }) {
  const { t } = useTranslation();
  const format = useLocaleFormat();
  const catalog = useCatalog();
  const write = useWrite();
  const [params] = useSearchParams();
  const [kind, setKind] = useState(params.get("kind") ?? "receive");
  const [printer, setPrinter] = useState(params.get("printer") ?? "");
  const [cartridge, setCartridge] = useState("");
  const [quantity, setQuantity] = useState("1");
  const [notes, setNotes] = useState("");
  const [document, setDocument] = useState("");
  const [requestId, setRequestId] = useState(() => crypto.randomUUID());
  function changed() {
    setRequestId(crypto.randomUUID());
    write.reset();
  }
  if (catalog.isLoading) return <Loading />;
  if (catalog.error) return <ErrorMessage error={catalog.error} />;
  const data = catalog.data!;
  const selectedPrinter = data.printers.find((p) => p.id === Number(printer));
  const choices = data.cartridges.filter(
    (c) =>
      kind !== "issue" ||
      data.compatibility.some(
        (link) =>
          link.cartridge_id === c.id &&
          link.model_id === selectedPrinter?.model_id &&
          link.verified,
      ),
  );
  return (
    <>
      <h1>{t("nav.inventory")}</h1>
      <p>{t("app.ledgerHelp")}</p>
      {canEdit && (
        <section className="card">
          <h2>{t("app.newOperation")}</h2>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (
                !window.confirm(
                  t("app.confirmOperation", {
                    quantity,
                    cartridge: label(
                      data.cartridges.find((c) => c.id === Number(cartridge)),
                    ),
                  }),
                )
              )
                return;
              write.mutate(
                {
                  path: "/transactions",
                  body: {
                    kind,
                    printer_id: printer ? Number(printer) : null,
                    cartridge_id: Number(cartridge),
                    quantity: Number(quantity),
                    notes,
                    document_reference: document,
                    request_id: requestId,
                  },
                },
                {
                  onSuccess: () => {
                    setRequestId(crypto.randomUUID());
                    setNotes("");
                    setDocument("");
                  },
                },
              );
            }}
          >
            <div className="form-grid">
              <label>
                {t("fields.kind")}
                <select
                  value={kind}
                  onChange={(e) => {
                    setKind(e.target.value);
                    setCartridge("");
                    changed();
                  }}
                >
                  {["receive", "issue", "return", "adjustment", "writeoff"].map(
                    (k) => (
                      <option key={k} value={k}>
                        {t(`values.${k}`)}
                      </option>
                    ),
                  )}
                </select>
              </label>
              <label>
                {t("fields.printer_id")}
                <select
                  value={printer}
                  required={kind === "issue"}
                  onChange={(e) => {
                    setPrinter(e.target.value);
                    setCartridge("");
                    changed();
                  }}
                >
                  <option value="">{t("app.select")}</option>
                  {data.printers
                    .filter(
                      (p) =>
                        !p.archived &&
                        (kind !== "issue" || p.status === "active"),
                    )
                    .map((p) => (
                      <option key={p.id} value={p.id}>
                        {label(p)}
                      </option>
                    ))}
                </select>
              </label>
              <label>
                {t("fields.cartridge_id")}
                <select
                  value={cartridge}
                  required
                  onChange={(e) => {
                    setCartridge(e.target.value);
                    changed();
                  }}
                >
                  <option value="">{t("app.select")}</option>
                  {choices.map((c) => (
                    <option key={c.id} value={c.id}>
                      {label(c)} · {t("fields.balance")}:{" "}
                      {format.number(Number(c.balance))}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                {t("fields.quantity")}
                <input
                  type="number"
                  required
                  step="1"
                  min={kind === "adjustment" ? -1000000 : 1}
                  max="1000000"
                  value={quantity}
                  onChange={(e) => {
                    setQuantity(e.target.value);
                    changed();
                  }}
                />
              </label>
              <label>
                {t("fields.document_reference")}
                <input
                  maxLength={160}
                  value={document}
                  onChange={(e) => {
                    setDocument(e.target.value);
                    changed();
                  }}
                />
              </label>
              <label>
                {t("fields.notes")}
                <textarea
                  required={kind === "adjustment"}
                  maxLength={4000}
                  value={notes}
                  onChange={(e) => {
                    setNotes(e.target.value);
                    changed();
                  }}
                />
              </label>
            </div>
            {kind === "issue" && (
              <p className="notice">
                {t("app.verifiedOnly")}
                {printer &&
                  choices.length === 0 &&
                  ` ${t("errors.UNVERIFIED_COMPATIBILITY")}`}
              </p>
            )}
            <ErrorMessage error={write.error} />
            {write.isSuccess && <p role="status">{t("app.operationSaved")}</p>}
            <button
              className="primary"
              disabled={write.isPending || !cartridge}
            >
              {t("app.confirm")}
            </button>
          </form>
        </section>
      )}
      <section className="card">
        <Table
          rows={data.cartridges}
          columns={["code", "color", "balance", "minimum_stock"]}
        />
      </section>
    </>
  );
}

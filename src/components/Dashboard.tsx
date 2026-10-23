import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  BarChart,
  Bar,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { api, type Row } from "../api";
import { useLocaleFormat } from "../format";
import { ErrorMessage, Loading, Table } from "./Shared";
interface DashboardData {
  total: number;
  active: number;
  stock: number;
  types: number;
  low: number;
  issued: number;
  monthly: Row[];
  departments: Row[];
  popular: Row[];
  distribution: Row[];
  low_stock: Row[];
  attention: Row[];
  recent: Row[];
}
export function Dashboard() {
  const { t } = useTranslation();
  const f = useLocaleFormat();
  const result = useQuery({
    queryKey: ["dashboard"],
    queryFn: () => api<DashboardData>("/dashboard"),
  });
  if (result.isLoading) return <Loading />;
  if (result.error) return <ErrorMessage error={result.error} />;
  const data = result.data!;
  return (
    <>
      <h1>{t("dashboard.title")}</h1>
      <p>{t("dashboard.subtitle")}</p>
      <div className="metrics">
        {(["total", "active", "stock", "types", "low", "issued"] as const).map(
          (key) => (
            <section className="card" key={key}>
              <p>{t(`dashboard.${key}`)}</p>
              <strong>{f.number(data[key])}</strong>
            </section>
          ),
        )}
      </div>
      <div className="columns">
        {(["monthly", "departments", "popular", "distribution"] as const).map(
          (key) => (
            <section className="card" key={key}>
              <h2>{t(`charts.${key}`)}</h2>
              {data[key].length ? (
                <div
                  className="chart"
                  role="img"
                  aria-label={t(`charts.${key}`)}
                >
                  <ResponsiveContainer width="100%" height={240}>
                    <BarChart data={data[key]}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="label" tick={{ fontSize: 11 }} />
                      <YAxis allowDecimals={false} />
                      <Tooltip
                        formatter={(value) => [
                          f.number(Number(value)),
                          t("fields.quantity"),
                        ]}
                      />
                      <Bar
                        dataKey="quantity"
                        fill="#315cbb"
                        radius={[4, 4, 0, 0]}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <p>{t("common.empty")}</p>
              )}
            </section>
          ),
        )}
      </div>
      <section className="card">
        <h2>{t("dashboard.low")}</h2>
        <Table
          rows={data.low_stock}
          columns={["code", "balance", "minimum_stock"]}
        />
      </section>
      <section className="card">
        <h2>{t("app.attention")}</h2>
        <Table rows={data.attention} columns={["inventory_number", "status"]} />
      </section>
      <section className="card">
        <h2>{t("dashboard.recent")}</h2>
        <Table
          rows={data.recent}
          columns={[
            "occurred_at",
            "cartridge_code",
            "kind",
            "quantity",
            "printer_label",
            "user_label",
          ]}
        />
      </section>
    </>
  );
}

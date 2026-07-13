import { redirect } from "next/navigation";
import { getAdminSession } from "@/lib/auth";
import { AdminNav } from "@/components/admin-nav";
import { prisma } from "@/lib/db";
import { getDateRangeFromValue } from "@/lib/date-filters";

function formatSelectedDate(value: string) {
  const [year, month, day] = value.split("-").map(Number);
  return new Intl.DateTimeFormat(undefined, { dateStyle: "full" }).format(new Date(year, month - 1, day));
}

export default async function AdminDashboardPage({
  searchParams
}: {
  searchParams: Promise<{ date?: string }>;
}) {
  const session = await getAdminSession();
  if (!session) redirect("/admin/login");

  const params = await searchParams;
  const { value: selectedDate, start, end } = getDateRangeFromValue(params.date);

  const orders = await prisma.order.findMany({
    where: {
      createdAt: { gte: start, lt: end },
      status: { not: "CANCELLED" }
    },
    include: { items: true }
  });

  const totalOrders = orders.length;
  const totalSales = orders.reduce((sum, order) => sum + Number(order.totalTala), 0);
  const deliveryOrders = orders.filter((order) => order.fulfillmentType === "DELIVERY");
  const pickupOrders = orders.filter((order) => order.fulfillmentType === "PICKUP");
  const deliverySales = deliveryOrders.reduce((sum, order) => sum + Number(order.totalTala), 0);
  const pickupSales = pickupOrders.reduce((sum, order) => sum + Number(order.totalTala), 0);
  const totalDeliveryFees = orders.reduce((sum, order) => sum + Number(order.deliveryFeeTala), 0);

  const soldMap = new Map<string, number>();
  const salesMap = new Map<string, number>();
  for (const order of orders) {
    for (const item of order.items) {
      soldMap.set(item.itemNameSnapshot, (soldMap.get(item.itemNameSnapshot) ?? 0) + item.quantity);
      salesMap.set(item.itemNameSnapshot, (salesMap.get(item.itemNameSnapshot) ?? 0) + Number(item.lineTotalTala));
    }
  }

  const topItems = [...soldMap.entries()].sort((a, b) => b[1] - a[1]).slice(0, 5);
  const itemSalesReport = [...soldMap.entries()]
    .map(([name, qty]) => ({
      name,
      qty,
      salesTala: salesMap.get(name) ?? 0
    }))
    .sort((a, b) => b.qty - a.qty || b.salesTala - a.salesTala);

  return (
    <main className="container-page">
      <h1 className="mb-4 text-3xl font-bold">Admin Dashboard</h1>
      <AdminNav />
      <section className="card admin-dashboard-filter">
        <div>
          <p className="label">Dashboard date</p>
          <p className="font-semibold">{formatSelectedDate(selectedDate)}</p>
        </div>
        <form className="admin-date-form" method="GET">
          <input className="input" type="date" name="date" defaultValue={selectedDate} />
          <button className="btn-secondary" type="submit">Apply</button>
        </form>
      </section>
      <section className="card admin-report-card">
        <div className="admin-report-header">
          <div>
            <p className="text-sm text-gray-500">Sales report</p>
            <p className="font-semibold">Download item sales for {formatSelectedDate(selectedDate)}</p>
          </div>
          <a className="btn-primary" href={`/api/admin/reports/sales?date=${selectedDate}`}>
            Download CSV
          </a>
        </div>

        {itemSalesReport.length === 0 ? (
          <p className="text-gray-600">No items sold for this date yet.</p>
        ) : (
          <div className="admin-report-table">
            <div className="admin-report-row admin-report-row-head">
              <span>Item</span>
              <span>Qty sold</span>
              <span>Sales</span>
            </div>
            {itemSalesReport.map((item) => (
              <div key={item.name} className="admin-report-row">
                <span>{item.name}</span>
                <span>{item.qty}</span>
                <span>{item.salesTala.toFixed(2)} tala</span>
              </div>
            ))}
          </div>
        )}
      </section>
      <div className="grid gap-4 md:grid-cols-3">
        <section className="card">
          <p className="text-sm text-gray-500">Total Orders</p>
          <p className="mt-2 text-3xl font-bold">{totalOrders}</p>
        </section>
        <section className="card">
          <p className="text-sm text-gray-500">Total Sales</p>
          <p className="mt-2 text-3xl font-bold">{totalSales.toFixed(2)} tala</p>
        </section>
        <section className="card">
          <p className="text-sm text-gray-500">Delivery Orders</p>
          <p className="mt-2 text-3xl font-bold">{deliveryOrders.length}</p>
          <p className="mt-2 text-sm text-gray-600">{deliverySales.toFixed(2)} tala including fees</p>
        </section>
        <section className="card">
          <p className="text-sm text-gray-500">Self Pickup Orders</p>
          <p className="mt-2 text-3xl font-bold">{pickupOrders.length}</p>
          <p className="mt-2 text-sm text-gray-600">{pickupSales.toFixed(2)} tala</p>
        </section>
        <section className="card">
          <p className="text-sm text-gray-500">Delivery Fees</p>
          <p className="mt-2 text-3xl font-bold">{totalDeliveryFees.toFixed(2)} tala</p>
        </section>
        <section className="card">
          <p className="text-sm text-gray-500">Best Sellers</p>
          <div className="mt-2 space-y-1">
            {topItems.length === 0 ? (
              <p className="text-gray-600">No sales yet.</p>
            ) : (
              topItems.map(([name, qty]) => (
                <p key={name} className="font-medium">{name} - {qty}</p>
              ))
            )}
          </div>
        </section>
      </div>
    </main>
  );
}

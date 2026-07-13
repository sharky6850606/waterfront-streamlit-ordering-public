import { prisma } from "@/lib/db";
import { getAdminSession } from "@/lib/auth";
import { getDateRangeFromValue } from "@/lib/date-filters";

function escapeCsv(value: string | number) {
  const stringValue = String(value);
  if (stringValue.includes(",") || stringValue.includes('"') || stringValue.includes("\n")) {
    return `"${stringValue.replace(/"/g, '""')}"`;
  }

  return stringValue;
}

export async function GET(request: Request) {
  const session = await getAdminSession();
  if (!session) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const url = new URL(request.url);
  const { value: selectedDate, start, end } = getDateRangeFromValue(url.searchParams.get("date"));

  const orders = await prisma.order.findMany({
    where: {
      createdAt: { gte: start, lt: end },
      status: { not: "CANCELLED" }
    },
    include: {
      items: {
        orderBy: { id: "asc" }
      }
    },
    orderBy: { createdAt: "asc" }
  });

  const itemMap = new Map<string, { quantity: number; salesTala: number }>();
  let totalSales = 0;
  let totalDeliveryFees = 0;
  let deliveryOrders = 0;
  let pickupOrders = 0;
  let deliverySales = 0;
  let pickupSales = 0;

  for (const order of orders) {
    const orderTotal = Number(order.totalTala);
    const deliveryFee = Number(order.deliveryFeeTala);
    totalSales += orderTotal;
    totalDeliveryFees += deliveryFee;

    if (order.fulfillmentType === "DELIVERY") {
      deliveryOrders += 1;
      deliverySales += orderTotal;
    } else {
      pickupOrders += 1;
      pickupSales += orderTotal;
    }

    for (const item of order.items) {
      const current = itemMap.get(item.itemNameSnapshot) ?? { quantity: 0, salesTala: 0 };
      current.quantity += item.quantity;
      current.salesTala += Number(item.lineTotalTala);
      itemMap.set(item.itemNameSnapshot, current);
    }
  }

  const rows = [
    ["Sales Report Date", selectedDate],
    ["Total Orders", orders.length],
    ["Total Sales Tala", totalSales.toFixed(2)],
    ["Delivery Orders", deliveryOrders],
    ["Delivery Sales Tala", deliverySales.toFixed(2)],
    ["Total Delivery Fees Tala", totalDeliveryFees.toFixed(2)],
    ["Self Pickup Orders", pickupOrders],
    ["Self Pickup Sales Tala", pickupSales.toFixed(2)],
    [],
    ["Item", "Quantity Sold", "Sales Tala"]
  ];

  for (const [itemName, totals] of [...itemMap.entries()].sort((a, b) => b[1].quantity - a[1].quantity)) {
    rows.push([itemName, totals.quantity, totals.salesTala.toFixed(2)]);
  }

  const csv = rows
    .map((row) => row.map((value) => escapeCsv(value)).join(","))
    .join("\n");

  return new Response(csv, {
    headers: {
      "Content-Type": "text/csv; charset=utf-8",
      "Content-Disposition": `attachment; filename="sales-report-${selectedDate}.csv"`
    }
  });
}

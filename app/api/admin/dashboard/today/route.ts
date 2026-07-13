import { prisma } from "@/lib/db";
import { getAdminSession } from "@/lib/auth";

export async function GET() {
  const session = await getAdminSession();
  if (!session) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const start = new Date();
  start.setHours(0, 0, 0, 0);

  const end = new Date(start);
  end.setDate(end.getDate() + 1);

  const orders = await prisma.order.findMany({
    where: {
      createdAt: {
        gte: start,
        lt: end
      },
      status: { not: "CANCELLED" }
    },
    include: { items: true }
  });

  const totalOrders = orders.length;
  const totalSales = orders.reduce((sum, order) => sum + Number(order.totalTala), 0);

  const counts = new Map<string, number>();
  for (const order of orders) {
    for (const item of order.items) {
      counts.set(item.itemNameSnapshot, (counts.get(item.itemNameSnapshot) ?? 0) + item.quantity);
    }
  }

  const topItems = [...counts.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([name, quantity]) => ({ name, quantity }));

  const newOrdersCount = orders.filter((o) => o.status === "NEW").length;

  return Response.json({
    totalOrders,
    totalSales,
    topItems,
    newOrdersCount
  });
}

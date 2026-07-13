import { prisma } from "@/lib/db";
import { getAdminSession } from "@/lib/auth";
import { getDateRangeFromValue } from "@/lib/date-filters";

export async function GET(request: Request) {
  const session = await getAdminSession();
  if (!session) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const url = new URL(request.url);
  const status = url.searchParams.get("status");
  const date = url.searchParams.get("date");
  const { start, end } = getDateRangeFromValue(date);

  const orders = await prisma.order.findMany({
    where: {
      createdAt: { gte: start, lt: end },
      status: status ? (status as never) : { not: "CANCELLED" }
    },
    include: { items: true },
    orderBy: { createdAt: "desc" }
  });

  return Response.json(orders);
}

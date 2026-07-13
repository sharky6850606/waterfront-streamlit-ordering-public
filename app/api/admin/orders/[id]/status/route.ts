import { prisma } from "@/lib/db";
import { getAdminSession } from "@/lib/auth";

export async function PATCH(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const session = await getAdminSession();
  if (!session) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const { id } = await params;
  const body = await request.json();
  const status = body.status as string;

  const completedAt = status === "COMPLETED" ? new Date() : null;

  const order = await prisma.order.update({
    where: { id: Number(id) },
    data: {
      status: status as never,
      isSeenByAdmin: true,
      completedAt
    }
  });

  return Response.json(order);
}

import { prisma } from "@/lib/db";

export async function GET() {
  const categories = await prisma.category.findMany({
    where: { isActive: true },
    orderBy: { sortOrder: "asc" },
    include: {
      items: { orderBy: { name: "asc" } }
    }
  });

  return Response.json(categories);
}

import { prisma } from "@/lib/db";
import { getAdminSession } from "@/lib/auth";
import { menuItemSchema } from "@/lib/validators";

export async function PATCH(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const session = await getAdminSession();
  if (!session) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const { id } = await params;
  const body = await request.json();
  const parsed = menuItemSchema.safeParse(body);
  if (!parsed.success) {
    return Response.json({ error: parsed.error.issues[0]?.message ?? "Invalid menu item" }, { status: 400 });
  }

  const data = parsed.data;

  const item = await prisma.menuItem.update({
    where: { id: Number(id) },
    data: {
      name: data.name,
      description: data.description || null,
      priceTala: data.priceTala,
      imageUrl: data.imageUrl || null,
      isAvailable: data.isAvailable,
      categoryId: data.categoryId,
      options: {
        deleteMany: {},
        create: (data.options ?? []).map((option, index) => ({
          name: option.name,
          priceTala: option.priceTala,
          sortOrder: index,
          isActive: option.isActive ?? true
        }))
      }
    },
    include: {
      options: {
        orderBy: { sortOrder: "asc" }
      }
    }
  });

  return Response.json(item);
}

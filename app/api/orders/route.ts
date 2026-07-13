import { prisma } from "@/lib/db";
import { generateOrderNumber } from "@/lib/order-number";
import { serializeCustomerOrder, serializeCustomerOrderSummary } from "@/lib/order-tracking";
import { orderSchema } from "@/lib/validators";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const phone = searchParams.get("phone")?.trim();
  const orderNumbers = [
    ...searchParams.getAll("orderNumber"),
    ...searchParams
      .getAll("orderNumbers")
      .flatMap((value) => value.split(","))
  ]
    .map((value) => value.trim())
    .filter(Boolean);

  const uniqueOrderNumbers = Array.from(new Set(orderNumbers)).slice(0, 12);

  if (phone) {
    const orders = await prisma.order.findMany({
      where: {
        customerPhone: phone,
        status: {
          in: ["NEW", "PREPARING", "READY_FOR_PICKUP", "OUT_FOR_DELIVERY"]
        }
      },
      orderBy: { createdAt: "desc" },
      take: 10,
      include: {
        items: {
          orderBy: { id: "asc" }
        }
      }
    });

    return Response.json(orders.map(serializeCustomerOrder));
  }

  if (uniqueOrderNumbers.length === 0) {
    return Response.json([], { status: 400 });
  }

  const orders = await prisma.order.findMany({
    where: {
      orderNumber: {
        in: uniqueOrderNumbers
      }
    },
    orderBy: { createdAt: "desc" },
    include: {
      items: {
        orderBy: { id: "asc" }
      }
    }
  });

  return Response.json(orders.map(serializeCustomerOrder));
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const parsed = orderSchema.parse(body);

    const ids = parsed.items.map((item) => item.menuItemId);
    const menuItems = await prisma.menuItem.findMany({
      where: { id: { in: ids } },
      include: {
        options: {
          where: { isActive: true },
          orderBy: { sortOrder: "asc" }
        }
      }
    });

    const itemMap = new Map(menuItems.map((item) => [item.id, item]));

    let subtotal = 0;
    const orderItemsData = [];

    for (const cartItem of parsed.items) {
      const menuItem = itemMap.get(cartItem.menuItemId);

      if (!menuItem) {
        return Response.json({ error: "Menu item not found" }, { status: 400 });
      }

      if (!menuItem.isAvailable) {
        return Response.json({ error: `${menuItem.name} is unavailable` }, { status: 400 });
      }

      const hasOptions = menuItem.options.length > 0;
      const selectedOption = cartItem.selectedOptionId
        ? menuItem.options.find((option) => option.id === cartItem.selectedOptionId)
        : null;

      if (hasOptions && !selectedOption) {
        return Response.json({ error: `Please choose an option for ${menuItem.name}` }, { status: 400 });
      }

      const unitPrice = selectedOption ? Number(selectedOption.priceTala) : Number(menuItem.priceTala);
      const lineTotal = unitPrice * cartItem.quantity;
      subtotal += lineTotal;

      orderItemsData.push({
        menuItemId: menuItem.id,
        itemNameSnapshot: selectedOption ? `${menuItem.name} - ${selectedOption.name}` : menuItem.name,
        unitPriceTala: unitPrice,
        quantity: cartItem.quantity,
        lineTotalTala: lineTotal
      });
    }

    const deliveryFee = parsed.fulfillmentType === "DELIVERY" ? 2 : 0;
    const total = subtotal + deliveryFee;
    const orderNumber = generateOrderNumber();

    const order = await prisma.order.create({
      data: {
        orderNumber,
        customerName: parsed.customerName,
        customerPhone: parsed.customerPhone,
        fulfillmentType: parsed.fulfillmentType,
        deliveryAddress: parsed.fulfillmentType === "DELIVERY" ? parsed.deliveryAddress ?? "" : null,
        notes: parsed.notes ?? null,
        subtotalTala: subtotal,
        deliveryFeeTala: deliveryFee,
        totalTala: total,
        items: {
          create: orderItemsData
        }
      },
      include: {
        items: true
      }
    });

    return Response.json({
      orderNumber: order.orderNumber,
      id: order.id,
      order: serializeCustomerOrderSummary(order)
    });
  } catch (error) {
    console.error(error);
    return Response.json({ error: "Invalid order request" }, { status: 400 });
  }
}

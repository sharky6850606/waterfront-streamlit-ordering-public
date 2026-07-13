export type FulfillmentType = "DELIVERY" | "PICKUP";

export type OrderStatus =
  | "NEW"
  | "PREPARING"
  | "READY_FOR_PICKUP"
  | "OUT_FOR_DELIVERY"
  | "COMPLETED"
  | "CANCELLED";

export type PaymentMethod = "CASH";

export type CustomerOrderSummary = {
  id: number;
  orderNumber: string;
  fulfillmentType: FulfillmentType;
  status: OrderStatus;
  totalTala: number;
  createdAt: string;
  updatedAt: string;
};

export type CustomerOrderItem = {
  id: number;
  itemNameSnapshot: string;
  quantity: number;
  lineTotalTala: number;
};

export type CustomerOrder = CustomerOrderSummary & {
  customerName: string;
  customerPhone: string;
  deliveryAddress: string | null;
  paymentMethod: PaymentMethod;
  subtotalTala: number;
  deliveryFeeTala: number;
  notes: string | null;
  items: CustomerOrderItem[];
};

const DELIVERY_TIMELINE: OrderStatus[] = ["NEW", "PREPARING", "OUT_FOR_DELIVERY", "COMPLETED"];
const PICKUP_TIMELINE: OrderStatus[] = ["NEW", "PREPARING", "READY_FOR_PICKUP", "COMPLETED"];

export function formatOrderStatus(status: OrderStatus) {
  return status
    .toLowerCase()
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function formatFulfillmentType(fulfillmentType: FulfillmentType) {
  return fulfillmentType === "DELIVERY" ? "Delivery" : "Self pickup";
}

export function getOrderTimeline(fulfillmentType: FulfillmentType) {
  return fulfillmentType === "DELIVERY" ? DELIVERY_TIMELINE : PICKUP_TIMELINE;
}

export function isOrderActive(status: OrderStatus) {
  return status !== "COMPLETED" && status !== "CANCELLED";
}

export function serializeCustomerOrderSummary(order: {
  id: number;
  orderNumber: string;
  fulfillmentType: FulfillmentType;
  status: OrderStatus;
  totalTala: unknown;
  createdAt: Date;
  updatedAt: Date;
}): CustomerOrderSummary {
  return {
    id: order.id,
    orderNumber: order.orderNumber,
    fulfillmentType: order.fulfillmentType,
    status: order.status,
    totalTala: Number(order.totalTala),
    createdAt: order.createdAt.toISOString(),
    updatedAt: order.updatedAt.toISOString()
  };
}

export function serializeCustomerOrder(order: {
  id: number;
  orderNumber: string;
  customerName: string;
  customerPhone: string;
  fulfillmentType: FulfillmentType;
  deliveryAddress: string | null;
  status: OrderStatus;
  paymentMethod: PaymentMethod;
  subtotalTala: unknown;
  deliveryFeeTala: unknown;
  totalTala: unknown;
  notes: string | null;
  createdAt: Date;
  updatedAt: Date;
  items: Array<{
    id: number;
    itemNameSnapshot: string;
    quantity: number;
    lineTotalTala: unknown;
  }>;
}): CustomerOrder {
  return {
    ...serializeCustomerOrderSummary(order),
    customerName: order.customerName,
    customerPhone: order.customerPhone,
    deliveryAddress: order.deliveryAddress,
    paymentMethod: order.paymentMethod,
    subtotalTala: Number(order.subtotalTala),
    deliveryFeeTala: Number(order.deliveryFeeTala),
    notes: order.notes,
    items: order.items.map((item) => ({
      id: item.id,
      itemNameSnapshot: item.itemNameSnapshot,
      quantity: item.quantity,
      lineTotalTala: Number(item.lineTotalTala)
    }))
  };
}

"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { getTodayDateValue } from "@/lib/date-filters";
import { formatFulfillmentType, formatOrderStatus } from "@/lib/order-tracking";

type OrderItem = {
  id: number;
  itemNameSnapshot: string;
  quantity: number;
  lineTotalTala: number;
};

type Order = {
  id: number;
  orderNumber: string;
  customerName: string;
  customerPhone: string;
  fulfillmentType: "DELIVERY" | "PICKUP";
  deliveryAddress: string | null;
  status: "NEW" | "PREPARING" | "READY_FOR_PICKUP" | "OUT_FOR_DELIVERY" | "COMPLETED" | "CANCELLED";
  subtotalTala: number;
  deliveryFeeTala: number;
  totalTala: number;
  createdAt: string;
  items: OrderItem[];
};

const statuses = ["NEW", "PREPARING", "READY_FOR_PICKUP", "OUT_FOR_DELIVERY", "COMPLETED"] as const;
const completedStatus = "COMPLETED";

function playNotificationTone() {
  const ctx = new AudioContext();
  const o = ctx.createOscillator();
  const g = ctx.createGain();
  o.connect(g);
  g.connect(ctx.destination);
  o.type = "sine";
  o.frequency.value = 880;
  g.gain.value = 0.05;
  o.start();
  setTimeout(() => o.stop(), 300);
}

function formatTimestamp(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit"
  }).format(new Date(value));
}

function totalItems(order: Order) {
  return order.items.reduce((sum, item) => sum + item.quantity, 0);
}

type Props = {
  initialDate?: string;
};

export function AdminLiveOrders({ initialDate = getTodayDateValue() }: Props) {
  const [orders, setOrders] = useState<Order[]>([]);
  const [banner, setBanner] = useState("");
  const [query, setQuery] = useState("");
  const [selectedDate, setSelectedDate] = useState(initialDate);
  const [expandedOrderId, setExpandedOrderId] = useState<number | null>(null);
  const [showCompleted, setShowCompleted] = useState(false);
  const seenIds = useRef<Set<number>>(new Set());

  async function loadOrders(dateValue: string) {
    const response = await fetch(`/api/admin/orders?date=${encodeURIComponent(dateValue)}`, {
      cache: "no-store"
    });
    const data = await response.json();
    if (!response.ok) return;

    const nextOrders = data as Order[];
    const newUnseen = nextOrders.filter((order) => order.status === "NEW" && !seenIds.current.has(order.id));

    if (seenIds.current.size > 0 && newUnseen.length > 0) {
      setBanner(newUnseen.length === 1 ? "New order received" : `${newUnseen.length} new orders received`);
      playNotificationTone();
      setTimeout(() => setBanner(""), 4000);
    }

    nextOrders.forEach((order) => seenIds.current.add(order.id));
    setOrders(nextOrders);
  }

  useEffect(() => {
    seenIds.current = new Set();
    setBanner("");
    void loadOrders(selectedDate);
    const id = window.setInterval(() => {
      void loadOrders(selectedDate);
    }, 5000);

    return () => window.clearInterval(id);
  }, [selectedDate]);

  useEffect(() => {
    const url = new URL(window.location.href);
    url.searchParams.set("date", selectedDate);
    window.history.replaceState({}, "", url);
  }, [selectedDate]);

  async function updateStatus(orderId: number, status: Order["status"]) {
    await fetch(`/api/admin/orders/${orderId}/status`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status })
    });

    await loadOrders(selectedDate);
  }

  const filteredOrders = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    if (!normalizedQuery) return orders;

    return orders.filter((order) =>
      [
        order.orderNumber,
        order.customerName,
        order.customerPhone,
        order.deliveryAddress ?? "",
        ...order.items.map((item) => item.itemNameSnapshot)
      ].some((value) => value.toLowerCase().includes(normalizedQuery))
    );
  }, [orders, query]);

  const grouped = useMemo(
    () =>
      statuses.map((status) => ({
        status,
        orders: filteredOrders.filter((order) => order.status === status)
      })),
    [filteredOrders]
  );

  const activeCount = orders.filter((order) => order.status !== "COMPLETED").length;

  return (
    <div className="space-y-4">
      {banner && (
        <div className="rounded-2xl border border-green-200 bg-green-50 p-4 font-semibold text-green-800">
          {banner}
        </div>
      )}

      <section className="card admin-orders-toolbar">
        <div className="admin-orders-summary">
          <div className="admin-summary-pill">
            <span className="label">Live now</span>
            <strong>{activeCount}</strong>
          </div>
          <div className="admin-summary-pill">
            <span className="label">Visible</span>
            <strong>{filteredOrders.length}</strong>
          </div>
        </div>

        <div className="admin-orders-filters">
          <input
            className="input admin-orders-date"
            type="date"
            value={selectedDate}
            onChange={(event) => setSelectedDate(event.target.value || getTodayDateValue())}
          />
          <input
            className="input admin-orders-search"
            placeholder="Search order, phone, customer, item"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </div>
      </section>

      <div className="admin-status-stack">
        {grouped.map((group) => (
          <section key={group.status} className="admin-status-section">
            <div className="admin-status-section-header">
              <div className="admin-status-heading">
                <h2 className="text-lg font-bold">{formatOrderStatus(group.status)}</h2>
                <span className="badge bg-gray-100 text-gray-700">{group.orders.length}</span>
              </div>
              {group.status === completedStatus && (
                <button
                  className="btn-secondary"
                  type="button"
                  onClick={() => setShowCompleted((current) => !current)}
                >
                  {showCompleted ? "Hide completed" : "Show completed"}
                </button>
              )}
            </div>

            {(group.status !== completedStatus || showCompleted) && (
              <div className="admin-status-row">
                {group.orders.length === 0 ? (
                  <div className="admin-empty-lane">No orders.</div>
                ) : (
                  group.orders.map((order) => {
                    const isExpanded = expandedOrderId === order.id;

                    return (
                      <article
                        key={order.id}
                        className={`admin-order-card ${order.status === "NEW" ? "is-new" : ""}`}
                      >
                        <div className="admin-order-top">
                          <p className="font-bold">{order.orderNumber}</p>
                          <span className="badge bg-white text-gray-700">
                            {Number(order.totalTala).toFixed(2)} tala
                          </span>
                        </div>

                        <div className="space-y-1">
                          <p className="font-medium">{order.customerName}</p>
                          <p className="text-sm text-gray-600">{order.customerPhone}</p>
                        </div>

                        <div className="admin-order-meta-line">
                          <span>{formatFulfillmentType(order.fulfillmentType)}</span>
                          <span>{formatTimestamp(order.createdAt)}</span>
                        </div>

                        <div className="admin-order-tags">
                          <span className="badge bg-gray-100 text-gray-700">{totalItems(order)} items</span>
                          {order.deliveryAddress && (
                            <span className="badge bg-gray-100 text-gray-700">Address</span>
                          )}
                        </div>

                        <div className="admin-order-actions">
                          <button
                            className="btn-secondary"
                            type="button"
                            onClick={() =>
                              setExpandedOrderId((current) => (current === order.id ? null : order.id))
                            }
                          >
                            {isExpanded ? "Hide" : "Details"}
                          </button>

                          {order.status !== "PREPARING" && order.status !== "COMPLETED" && (
                            <button className="btn-secondary" type="button" onClick={() => updateStatus(order.id, "PREPARING")}>
                              Preparing
                            </button>
                          )}

                          {order.fulfillmentType === "PICKUP" &&
                            order.status !== "READY_FOR_PICKUP" &&
                            order.status !== "COMPLETED" && (
                              <button
                                className="btn-secondary"
                                type="button"
                                onClick={() => updateStatus(order.id, "READY_FOR_PICKUP")}
                              >
                                Ready
                              </button>
                            )}

                          {order.fulfillmentType === "DELIVERY" &&
                            order.status !== "OUT_FOR_DELIVERY" &&
                            order.status !== "COMPLETED" && (
                              <button
                                className="btn-secondary"
                                type="button"
                                onClick={() => updateStatus(order.id, "OUT_FOR_DELIVERY")}
                              >
                                Dispatch
                              </button>
                            )}

                          {order.status !== "COMPLETED" && (
                            <button className="btn-primary" type="button" onClick={() => updateStatus(order.id, "COMPLETED")}>
                              Complete
                            </button>
                          )}
                        </div>

                        {isExpanded && (
                          <div className="order-tracker-details">
                            {order.deliveryAddress && (
                              <p className="rounded-xl bg-gray-50 p-2 text-sm">
                                <span className="font-semibold">Address:</span> {order.deliveryAddress}
                              </p>
                            )}

                            <div className="space-y-2">
                              {order.items.map((item) => (
                                <div key={item.id} className="order-item-row">
                                  <span>
                                    {item.quantity} x {item.itemNameSnapshot}
                                  </span>
                                  <span>{Number(item.lineTotalTala).toFixed(2)} tala</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </article>
                    );
                  })
                )}
              </div>
            )}
          </section>
        ))}
      </div>
    </div>
  );
}

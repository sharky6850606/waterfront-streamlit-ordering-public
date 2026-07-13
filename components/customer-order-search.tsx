"use client";

import { FormEvent, useEffect, useState } from "react";
import {
  CustomerOrder,
  formatFulfillmentType,
  formatOrderStatus,
  getOrderTimeline
} from "@/lib/order-tracking";

function formatOrderTime(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(value));
}

function totalItems(order: CustomerOrder) {
  return order.items.reduce((sum, item) => sum + item.quantity, 0);
}

type Props = {
  initialPhone?: string;
};

export function CustomerOrderSearch({ initialPhone = "" }: Props) {
  const [phone, setPhone] = useState(initialPhone);
  const [searchedPhone, setSearchedPhone] = useState(initialPhone);
  const [orders, setOrders] = useState<CustomerOrder[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [expandedOrderNumber, setExpandedOrderNumber] = useState<string | null>(null);

  async function loadOrders(phoneNumber: string) {
    if (!phoneNumber.trim()) {
      setOrders([]);
      setError("");
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(`/api/orders?phone=${encodeURIComponent(phoneNumber.trim())}`, {
        cache: "no-store"
      });
      const data = (await response.json()) as CustomerOrder[];

      if (!response.ok) {
        throw new Error("Could not load your orders");
      }

      setOrders(data);
      setExpandedOrderNumber(data[0]?.orderNumber ?? null);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load your orders");
    } finally {
      setLoading(false);
    }
  }

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedPhone = phone.trim();
    setSearchedPhone(normalizedPhone);
    loadOrders(normalizedPhone);
  }

  useEffect(() => {
    if (!searchedPhone || orders.length === 0) return;

    const intervalId = window.setInterval(() => {
      loadOrders(searchedPhone);
    }, 7000);

    return () => window.clearInterval(intervalId);
  }, [orders.length, searchedPhone]);

  return (
    <section className="card space-y-4">
      <form className="track-order-form" onSubmit={submitSearch}>
        <div className="track-order-copy">
          <h2 className="text-xl font-semibold">Track your live orders</h2>
          <p className="text-sm text-gray-600">
            Enter the same phone number used at checkout to see your active orders only.
          </p>
        </div>
        <div className="track-order-controls">
          <input
            className="input"
            placeholder="Enter phone number"
            value={phone}
            onChange={(event) => setPhone(event.target.value)}
          />
          <button className="btn-primary" type="submit" disabled={loading}>
            {loading ? "Checking..." : "Track order"}
          </button>
        </div>
      </form>

      {error && <p className="text-sm text-red-600">{error}</p>}

      {searchedPhone && !loading && orders.length === 0 && !error && (
        <div className="track-order-empty">
          <p className="font-semibold">No live orders found</p>
          <p className="text-sm text-gray-600">
            We could not find active orders for {searchedPhone}. Check the number and try again.
          </p>
        </div>
      )}

      {orders.length > 0 && (
        <div className="space-y-3">
          {orders.map((order) => {
            const isExpanded = expandedOrderNumber === order.orderNumber;
            const timeline = getOrderTimeline(order.fulfillmentType);

            return (
              <article key={order.orderNumber} className="order-tracker-card">
                <div className="order-tracker-head">
                  <div className="space-y-2">
                    <div className="order-tracker-line">
                      <p className="order-tracker-number">{order.orderNumber}</p>
                      <span className={`order-status-pill status-${order.status.toLowerCase()}`}>
                        {formatOrderStatus(order.status)}
                      </span>
                    </div>
                    <div className="order-tracker-meta">
                      <span>{formatFulfillmentType(order.fulfillmentType)}</span>
                      <span>{formatOrderTime(order.createdAt)}</span>
                      <span>{totalItems(order)} items</span>
                    </div>
                  </div>

                  <div className="order-tracker-side">
                    <p className="order-tracker-total">{order.totalTala.toFixed(2)} tala</p>
                    <button
                      className="btn-secondary"
                      type="button"
                      onClick={() =>
                        setExpandedOrderNumber((current) =>
                          current === order.orderNumber ? null : order.orderNumber
                        )
                      }
                    >
                      {isExpanded ? "Hide details" : "Show details"}
                    </button>
                  </div>
                </div>

                <div className="order-tracker-progress">
                  {timeline.map((step, index) => {
                    const currentIndex = timeline.indexOf(order.status);
                    const state =
                      index < currentIndex
                        ? "is-complete"
                        : index === currentIndex
                          ? "is-current"
                          : "is-pending";

                    return (
                      <div key={step} className={`order-progress-step ${state}`}>
                        {formatOrderStatus(step)}
                      </div>
                    );
                  })}
                </div>

                {isExpanded && (
                  <div className="order-tracker-details">
                    {order.deliveryAddress && (
                      <div className="order-summary-wide">
                        <p className="label">Address</p>
                        <p>{order.deliveryAddress}</p>
                      </div>
                    )}

                    {order.notes && (
                      <div className="order-summary-wide">
                        <p className="label">Notes</p>
                        <p>{order.notes}</p>
                      </div>
                    )}

                    <div className="space-y-2">
                      {order.items.map((item) => (
                        <div key={item.id} className="order-item-row">
                          <span>
                            {item.quantity} x {item.itemNameSnapshot}
                          </span>
                          <span>{item.lineTotalTala.toFixed(2)} tala</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}

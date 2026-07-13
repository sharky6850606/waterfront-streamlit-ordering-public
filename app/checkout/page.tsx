"use client";

import { SiteHeader } from "@/components/site-header";
import { useCart } from "@/components/cart-context";
import { useState } from "react";
import { useRouter } from "next/navigation";

export default function CheckoutPage() {
  const {
    items,
    fulfillmentType,
    setFulfillmentType,
    updateQuantity,
    removeItem,
    clearCart,
    subtotal,
    deliveryFee,
    total
  } = useCart();

  const router = useRouter();
  const [customerName, setCustomerName] = useState("");
  const [customerPhone, setCustomerPhone] = useState("");
  const [deliveryAddress, setDeliveryAddress] = useState("");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  async function submitOrder() {
    try {
      setSubmitting(true);
      setError("");

      const response = await fetch("/api/orders", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          customerName,
          customerPhone,
          deliveryAddress,
          notes,
          fulfillmentType,
          items: items.map((item) => ({
            menuItemId: item.menuItemId,
            selectedOptionId: item.selectedOptionId ?? null,
            quantity: item.quantity
          }))
        })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error ?? "Could not place order");
      }

      const orderNumber = data.order?.orderNumber ?? data.orderNumber;
      clearCart();
      router.push(`/confirm/${orderNumber}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div>
      <SiteHeader />
      <main className="container-page checkout-layout">
        <section className="card space-y-4">
          <div className="checkout-header">
            <h1 className="text-2xl font-bold">Checkout</h1>
            <button className="btn-secondary" type="button" onClick={() => router.push("/")}>
              Back to menu
            </button>
          </div>

          <div>
            <label className="label">Order type</label>
            <div className="toggle-row">
              <button
                type="button"
                className={fulfillmentType === "DELIVERY" ? "btn-primary" : "btn-secondary"}
                onClick={() => setFulfillmentType("DELIVERY")}
              >
                Delivery
              </button>
              <button
                type="button"
                className={fulfillmentType === "PICKUP" ? "btn-primary" : "btn-secondary"}
                onClick={() => setFulfillmentType("PICKUP")}
              >
                Self Pickup
              </button>
            </div>
          </div>

          <div>
            <label className="label">Name</label>
            <input className="input" value={customerName} onChange={(e) => setCustomerName(e.target.value)} />
          </div>

          <div>
            <label className="label">Phone number</label>
            <input className="input" value={customerPhone} onChange={(e) => setCustomerPhone(e.target.value)} />
          </div>

          {fulfillmentType === "DELIVERY" && (
            <div>
              <label className="label">Delivery location / address</label>
              <textarea className="input min-h-28" value={deliveryAddress} onChange={(e) => setDeliveryAddress(e.target.value)} />
              <p className="mt-2 text-sm font-medium text-amber-700">2 tala will be added as a delivery fee.</p>
            </div>
          )}

          <div>
            <label className="label">Notes (optional)</label>
            <textarea className="input min-h-24" value={notes} onChange={(e) => setNotes(e.target.value)} />
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}

          <button className="btn-primary w-full" disabled={submitting || items.length === 0} onClick={submitOrder}>
            {submitting ? "Submitting..." : "Confirm order"}
          </button>
        </section>

        <aside className="card sticky-panel space-y-4">
          <h2 className="text-xl font-semibold">Your Order</h2>
          {items.length === 0 ? (
            <p className="text-gray-600">Your cart is empty.</p>
          ) : (
            <div className="space-y-3">
              {items.map((item) => (
                <div key={item.cartItemId} className="rounded-xl border border-gray-200 p-3">
                  <div className="flex items-center justify-between gap-2">
                    <div>
                      <p className="font-medium">{item.name}</p>
                      <p className="text-sm text-gray-600">{item.priceTala.toFixed(2)} tala each</p>
                    </div>
                    <button className="text-sm text-red-600" type="button" onClick={() => removeItem(item.cartItemId)}>
                      Remove
                    </button>
                  </div>
                  <div className="quantity-row">
                    <button className="btn-secondary" type="button" onClick={() => updateQuantity(item.cartItemId, item.quantity - 1)}>
                      -
                    </button>
                    <span className="min-w-8 text-center">{item.quantity}</span>
                    <button className="btn-secondary" type="button" onClick={() => updateQuantity(item.cartItemId, item.quantity + 1)}>
                      +
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="space-y-2 border-t border-gray-200 pt-4">
            <div className="flex justify-between">
              <span>Subtotal</span>
              <span>{subtotal.toFixed(2)} tala</span>
            </div>
            <div className="flex justify-between">
              <span>Delivery fee</span>
              <span>{deliveryFee.toFixed(2)} tala</span>
            </div>
            <div className="flex justify-between text-lg font-bold">
              <span>Total</span>
              <span>{total.toFixed(2)} tala</span>
            </div>
            <p className="text-sm text-gray-600">Payment method: Cash</p>
          </div>
        </aside>
      </main>
    </div>
  );
}

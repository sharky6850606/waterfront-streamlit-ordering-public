"use client";

import Link from "next/link";
import { useCart } from "@/components/cart-context";

export function SiteHeader() {
  const { items } = useCart();
  const count = items.reduce((sum, item) => sum + item.quantity, 0);
  const goTo = (href: string) => {
    window.location.assign(href);
  };

  return (
    <header className="site-header">
      <div className="container-page site-header-row">
        <Link href="/" className="site-brand">
          <span className="site-brand-kicker">Waterfront</span>
          <span className="site-brand-title">Restaurant Orders</span>
        </Link>
        <nav className="site-nav">
          <button type="button" className="btn-secondary" onClick={() => goTo("/track-order")}>
            Track Order
          </button>
          <button type="button" className="btn-secondary" onClick={() => goTo("/admin/login")}>
            Admin Login
          </button>
          <button type="button" className="btn-primary" onClick={() => goTo("/checkout")}>
            Cart ({count})
          </button>
        </nav>
      </div>
    </header>
  );
}

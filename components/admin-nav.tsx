import Link from "next/link";

export function AdminNav() {
  return (
    <nav className="mb-6 flex flex-wrap gap-2">
      <Link href="/admin" className="btn-secondary">Dashboard</Link>
      <Link href="/admin/orders" className="btn-secondary">Live Orders</Link>
      <Link href="/admin/menu" className="btn-secondary">Menu</Link>
    </nav>
  );
}

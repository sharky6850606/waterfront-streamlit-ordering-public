import { SiteHeader } from "@/components/site-header";
import { prisma } from "@/lib/db";
import { formatFulfillmentType, formatOrderStatus } from "@/lib/order-tracking";
import Link from "next/link";
import { notFound } from "next/navigation";

export default async function ConfirmPage({
  params
}: {
  params: Promise<{ orderNumber: string }>;
}) {
  const { orderNumber } = await params;

  const order = await prisma.order.findUnique({
    where: { orderNumber },
    include: {
      items: {
        orderBy: { id: "asc" }
      }
    }
  });

  if (!order) notFound();

  return (
    <div>
      <SiteHeader />
      <main className="container-page section-stack">
        <section className="card confirmation-banner">
          <div className="space-y-2">
            <p className="confirmation-kicker">Order confirmed</p>
            <h1 className="text-2xl font-bold">Your order has been received</h1>
            <p className="text-gray-600">
              Keep your phone number handy. You can use it on the tracking page to check the latest live status.
            </p>
          </div>
          <div className="confirmation-actions">
            <Link href="/" className="btn-secondary">
              Home
            </Link>
            <Link href="/track-order" className="btn-primary">
              Track order
            </Link>
          </div>
        </section>
        <section className="card space-y-4">
          <div className="grid gap-3 md:grid-cols-2">
            <div className="rounded-xl bg-green-50 p-4">
              <p className="text-sm text-gray-600">Order number</p>
              <p className="text-2xl font-bold">{order.orderNumber}</p>
            </div>
            <div className="rounded-xl bg-gray-50 p-4">
              <p className="text-sm text-gray-600">Current status</p>
              <p className="text-xl font-semibold">{formatOrderStatus(order.status)}</p>
            </div>
          </div>

          <div className="grid gap-3 md:grid-cols-2">
            <div>
              <p className="label">Customer</p>
              <p>{order.customerName}</p>
            </div>
            <div>
              <p className="label">Phone</p>
              <p>{order.customerPhone}</p>
            </div>
            <div>
              <p className="label">Order type</p>
              <p>{formatFulfillmentType(order.fulfillmentType)}</p>
            </div>
            <div>
              <p className="label">Total</p>
              <p>{Number(order.totalTala).toFixed(2)} tala</p>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}

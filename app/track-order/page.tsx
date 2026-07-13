import { CustomerOrderSearch } from "@/components/customer-order-search";
import { SiteHeader } from "@/components/site-header";

export default function TrackOrderPage() {
  return (
    <div>
      <SiteHeader />
      <main className="container-page section-stack">
        <section className="card confirmation-banner">
          <div className="space-y-2">
            <p className="confirmation-kicker">Private tracking</p>
            <h1 className="text-2xl font-bold">Find your live orders</h1>
            <p className="text-gray-600">
              Search by the phone number used at checkout to see only your active orders.
            </p>
          </div>
        </section>

        <CustomerOrderSearch />
      </main>
    </div>
  );
}

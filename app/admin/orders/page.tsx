import { redirect } from "next/navigation";
import { getAdminSession } from "@/lib/auth";
import { AdminNav } from "@/components/admin-nav";
import { AdminLiveOrders } from "@/components/admin-live-orders";
import { getDateRangeFromValue } from "@/lib/date-filters";

export default async function AdminOrdersPage({
  searchParams
}: {
  searchParams: Promise<{ date?: string }>;
}) {
  const session = await getAdminSession();
  if (!session) redirect("/admin/login");
  const params = await searchParams;
  const { value } = getDateRangeFromValue(params.date);

  return (
    <main className="container-page">
      <h1 className="mb-4 text-3xl font-bold">Live Orders</h1>
      <AdminNav />
      <AdminLiveOrders initialDate={value} />
    </main>
  );
}

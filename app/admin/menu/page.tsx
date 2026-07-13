import { redirect } from "next/navigation";
import { getAdminSession } from "@/lib/auth";
import { AdminNav } from "@/components/admin-nav";
import { AdminMenuManager } from "@/components/admin-menu-manager";

export default async function AdminMenuPage() {
  const session = await getAdminSession();
  if (!session) redirect("/admin/login");

  return (
    <main className="container-page">
      <h1 className="mb-4 text-3xl font-bold">Menu Management</h1>
      <AdminNav />
      <AdminMenuManager />
    </main>
  );
}

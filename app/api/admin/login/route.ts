import bcrypt from "bcryptjs";
import { prisma } from "@/lib/db";
import { setAdminSession } from "@/lib/auth";
import { adminLoginSchema } from "@/lib/validators";

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const parsed = adminLoginSchema.parse(body);

    const user = await prisma.adminUser.findUnique({
      where: { username: parsed.username }
    });

    if (!user) {
      return Response.json({ error: "Invalid credentials" }, { status: 401 });
    }

    const ok = await bcrypt.compare(parsed.password, user.passwordHash);

    if (!ok) {
      return Response.json({ error: "Invalid credentials" }, { status: 401 });
    }

    await setAdminSession(user.username);
    return Response.json({ success: true });
  } catch {
    return Response.json({ error: "Login failed" }, { status: 400 });
  }
}

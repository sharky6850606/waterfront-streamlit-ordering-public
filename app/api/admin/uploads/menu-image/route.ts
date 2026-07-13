import { getAdminSession } from "@/lib/auth";
import { mkdir, writeFile } from "fs/promises";
import path from "path";
import { randomUUID } from "crypto";

const MAX_IMAGE_SIZE = 5 * 1024 * 1024;
const ALLOWED_TYPES = new Set(["image/jpeg", "image/png", "image/webp", "image/gif"]);

export async function POST(request: Request) {
  const session = await getAdminSession();
  if (!session) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const formData = await request.formData();
  const file = formData.get("file");

  if (!(file instanceof File)) {
    return Response.json({ error: "Please choose an image to upload" }, { status: 400 });
  }

  if (!ALLOWED_TYPES.has(file.type)) {
    return Response.json({ error: "Only JPG, PNG, WEBP, or GIF images are allowed" }, { status: 400 });
  }

  if (file.size > MAX_IMAGE_SIZE) {
    return Response.json({ error: "Image must be 5MB or smaller" }, { status: 400 });
  }

  const extension = path.extname(file.name || "").toLowerCase() || (
    file.type === "image/png" ? ".png" :
    file.type === "image/webp" ? ".webp" :
    file.type === "image/gif" ? ".gif" :
    ".jpg"
  );

  const safeBaseName = path
    .basename(file.name || "menu-image", extension)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 40) || "menu-image";

  const fileName = `${safeBaseName}-${randomUUID()}${extension}`;
  const uploadsDir = path.join(process.cwd(), "public", "uploads", "menu");
  await mkdir(uploadsDir, { recursive: true });

  const arrayBuffer = await file.arrayBuffer();
  await writeFile(path.join(uploadsDir, fileName), Buffer.from(arrayBuffer));

  return Response.json({
    imageUrl: `/uploads/menu/${fileName}`
  });
}

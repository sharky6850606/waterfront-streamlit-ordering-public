import { SiteHeader } from "@/components/site-header";
import { prisma } from "@/lib/db";
import { AddToCartButton } from "@/components/add-to-cart-button";
import Image from "next/image";
import { existsSync } from "fs";
import path from "path";

export default async function HomePage() {
  const categories = await prisma.category.findMany({
    where: { isActive: true },
    orderBy: { sortOrder: "asc" },
    include: {
      items: {
        orderBy: { name: "asc" },
        include: {
          options: {
            where: { isActive: true },
            orderBy: { sortOrder: "asc" }
          }
        }
      }
    }
  });

  function hasLocalImage(imageUrl?: string | null) {
    if (!imageUrl || !imageUrl.startsWith("/")) return false;
    return existsSync(path.join(process.cwd(), "public", imageUrl));
  }

  return (
    <div>
      <SiteHeader />
      <main className="container-page space-y-8">
        <section className="card hero-panel">
          <h1 className="text-2xl font-bold">Order Food Online</h1>
          <p className="mt-2 text-gray-600">
            Choose your items, select delivery or self pickup, then place your cash order.
          </p>
        </section>

        {categories.map((category, categoryIndex) => (
          <section key={category.id} className="space-y-4">
            <h2 className="text-xl font-semibold">{category.name}</h2>
            <div className="menu-grid">
              {category.items.map((item, itemIndex) => {
                const imageUrl = hasLocalImage(item.imageUrl) ? item.imageUrl : null;
                const itemOptions = item.options.map((option) => ({
                  id: option.id,
                  name: option.name,
                  priceTala: Number(option.priceTala)
                }));
                const lowestPrice = itemOptions.length > 0
                  ? Math.min(...itemOptions.map((option) => option.priceTala))
                  : Number(item.priceTala);
                const shouldEagerLoadImage = categoryIndex === 0 && itemIndex < 2;

                return (
                  <article key={item.id} className="card flex flex-col overflow-hidden p-0">
                    <div className="relative h-48 w-full bg-gray-100">
                      {imageUrl ? (
                        <Image
                          src={imageUrl}
                          alt={item.name}
                          fill
                          className="object-cover"
                          loading={shouldEagerLoadImage ? "eager" : "lazy"}
                          sizes="(max-width: 720px) 100vw, (max-width: 1024px) 50vw, 33vw"
                        />
                      ) : (
                        <div className="menu-image">
                          <div>
                            <span className="menu-image-title">{item.name}</span>
                            <span className="menu-image-subtitle">Add a photo later in admin</span>
                          </div>
                        </div>
                      )}
                    </div>
                    <div className="flex flex-1 flex-col gap-3 p-4">
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <h3 className="font-semibold">{item.name}</h3>
                          <p className="text-sm text-gray-600">{item.description}</p>
                          {itemOptions.length > 0 && (
                            <p className="mt-2 text-sm text-gray-600">
                              Options: {itemOptions.map((option) => option.name).join(", ")}
                            </p>
                          )}
                        </div>
                        {!item.isAvailable && (
                          <span className="badge bg-red-100 text-red-700">Unavailable</span>
                        )}
                      </div>
                      <div className="mt-auto flex items-center justify-between">
                        <span className="text-lg font-bold">
                          {itemOptions.length > 0 ? `From ${lowestPrice.toFixed(2)} tala` : `${lowestPrice.toFixed(2)} tala`}
                        </span>
                        <AddToCartButton
                          item={{
                            menuItemId: item.id,
                            name: item.name,
                            priceTala: Number(item.priceTala),
                            imageUrl: item.imageUrl,
                            isAvailable: item.isAvailable,
                            options: itemOptions
                          }}
                        />
                      </div>
                    </div>
                  </article>
                );
              })}
            </div>
          </section>
        ))}
      </main>
    </div>
  );
}

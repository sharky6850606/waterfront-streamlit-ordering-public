import bcrypt from "bcryptjs";
import { PrismaClient } from "@prisma/client";

const prisma = new PrismaClient();

async function main() {
  const passwordHash = await bcrypt.hash("admin123", 10);

  await prisma.adminUser.upsert({
    where: { username: "admin" },
    update: {},
    create: {
      username: "admin",
      passwordHash
    }
  });

  const burgers = await prisma.category.upsert({
    where: { name: "Burgers" },
    update: {},
    create: { name: "Burgers", sortOrder: 1 }
  });

  const drinks = await prisma.category.upsert({
    where: { name: "Drinks" },
    update: {},
    create: { name: "Drinks", sortOrder: 2 }
  });

  const items = [
    {
      categoryId: burgers.id,
      name: "Classic Burger",
      description: "Beef patty, lettuce, tomato, sauce",
      priceTala: "12",
      imageUrl: "/uploads/menu/classic-burger.jpg",
      isAvailable: true
    },
    {
      categoryId: burgers.id,
      name: "Chicken Burger",
      description: "Crispy chicken fillet with mayo",
      priceTala: "11",
      imageUrl: "/uploads/menu/chicken-burger.jpg",
      isAvailable: true
    },
    {
      categoryId: drinks.id,
      name: "Coke",
      description: "Can drink",
      priceTala: "4",
      imageUrl: "/uploads/menu/coke.jpg",
      isAvailable: true
    }
  ];

  for (const item of items) {
    await prisma.menuItem.upsert({
      where: { id: -1 },
      update: {},
      create: item
    }).catch(async () => {
      const existing = await prisma.menuItem.findFirst({ where: { name: item.name } });
      if (!existing) {
        await prisma.menuItem.create({ data: item });
      }
    });
  }
}

main()
  .then(async () => {
    await prisma.$disconnect();
    console.log("Seed complete.");
  })
  .catch(async (e) => {
    console.error(e);
    await prisma.$disconnect();
    process.exit(1);
  });

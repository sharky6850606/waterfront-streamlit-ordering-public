import { z } from "zod";

export const orderSchema = z.object({
  customerName: z.string().min(2, "Name is required"),
  customerPhone: z.string().min(5, "Phone is required"),
  fulfillmentType: z.enum(["DELIVERY", "PICKUP"]),
  deliveryAddress: z.string().optional().nullable(),
  notes: z.string().optional().nullable(),
  items: z.array(
    z.object({
      menuItemId: z.number().int().positive(),
      selectedOptionId: z.number().int().positive().optional().nullable(),
      quantity: z.number().int().min(1).max(50)
    })
  ).min(1, "Cart is empty")
}).superRefine((data, ctx) => {
  if (data.fulfillmentType === "DELIVERY" && !data.deliveryAddress?.trim()) {
    ctx.addIssue({
      code: "custom",
      message: "Address is required for delivery",
      path: ["deliveryAddress"]
    });
  }
});

export const adminLoginSchema = z.object({
  username: z.string().min(1),
  password: z.string().min(1)
});

export const menuItemSchema = z.object({
  categoryId: z.coerce.number().int().positive("Category is required"),
  name: z.string().trim().min(1, "Name is required"),
  description: z.string().trim().optional().nullable(),
  priceTala: z.coerce.number().positive("Price must be greater than 0"),
  imageUrl: z.string().trim().optional().nullable(),
  isAvailable: z.boolean().optional().default(true),
  options: z.array(
    z.object({
      name: z.string().trim().min(1, "Option name is required"),
      priceTala: z.coerce.number().positive("Option price must be greater than 0"),
      isActive: z.boolean().optional().default(true)
    })
  ).optional().default([])
});

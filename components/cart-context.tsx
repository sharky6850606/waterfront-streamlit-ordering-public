"use client";

import React, { createContext, useContext, useEffect, useMemo, useRef, useState } from "react";
import { FulfillmentType } from "@/lib/order-tracking";

export type CartItem = {
  cartItemId: string;
  menuItemId: number;
  selectedOptionId?: number | null;
  name: string;
  priceTala: number;
  imageUrl?: string | null;
  quantity: number;
  isAvailable: boolean;
};

type CartContextValue = {
  items: CartItem[];
  fulfillmentType: FulfillmentType;
  setFulfillmentType: (value: FulfillmentType) => void;
  addItem: (item: Omit<CartItem, "quantity" | "cartItemId">) => void;
  updateQuantity: (cartItemId: string, quantity: number) => void;
  removeItem: (cartItemId: string) => void;
  clearCart: () => void;
  subtotal: number;
  deliveryFee: number;
  total: number;
};

const CartContext = createContext<CartContextValue | null>(null);

const STORAGE_KEY = "food-order-cart";
const FULFILLMENT_KEY = "food-order-fulfillment";

function buildCartItemId(menuItemId: number, selectedOptionId?: number | null) {
  return `${menuItemId}:${selectedOptionId ?? "base"}`;
}

function readSavedJson<T>(value: string | null, fallback: T) {
  if (!value) return fallback;

  try {
    return JSON.parse(value) as T;
  } catch {
    return fallback;
  }
}

function normalizeCartItems(items: CartItem[]) {
  return items.map((item) => ({
    ...item,
    cartItemId: item.cartItemId ?? buildCartItemId(item.menuItemId, item.selectedOptionId),
    selectedOptionId: item.selectedOptionId ?? null
  }));
}

export function CartProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = useState<CartItem[]>([]);
  const [fulfillmentType, setFulfillmentTypeState] = useState<FulfillmentType>("DELIVERY");
  const itemsRef = useRef<CartItem[]>([]);

  function persistItems(nextItems: CartItem[]) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(nextItems));
  }

  function persistFulfillment(value: FulfillmentType) {
    localStorage.setItem(FULFILLMENT_KEY, value);
  }

  useEffect(() => {
    const savedItems = localStorage.getItem(STORAGE_KEY);
    const savedFulfillment = localStorage.getItem(FULFILLMENT_KEY) as FulfillmentType | null;

    if (savedItems) {
      const normalizedItems = normalizeCartItems(readSavedJson(savedItems, [] as CartItem[]));
      itemsRef.current = normalizedItems;
      setItems(normalizedItems);
      persistItems(normalizedItems);
    }
    if (savedFulfillment === "DELIVERY" || savedFulfillment === "PICKUP") {
      setFulfillmentTypeState(savedFulfillment);
    }
  }, []);

  const addItem = (item: Omit<CartItem, "quantity" | "cartItemId">) => {
    const cartItemId = buildCartItemId(item.menuItemId, item.selectedOptionId);
    const existing = itemsRef.current.find((entry) => entry.cartItemId === cartItemId);
    const nextItems = existing
      ? itemsRef.current.map((entry) =>
        entry.cartItemId === cartItemId ? { ...entry, quantity: entry.quantity + 1 } : entry
      )
      : [...itemsRef.current, { ...item, cartItemId, quantity: 1 }];

    itemsRef.current = nextItems;
    persistItems(nextItems);
    setItems(nextItems);
  };

  const updateQuantity = (cartItemId: string, quantity: number) => {
    const nextItems = itemsRef.current
      .map((item) => (item.cartItemId === cartItemId ? { ...item, quantity } : item))
      .filter((item) => item.quantity > 0);

    itemsRef.current = nextItems;
    persistItems(nextItems);
    setItems(nextItems);
  };

  const removeItem = (cartItemId: string) => {
    const nextItems = itemsRef.current.filter((item) => item.cartItemId !== cartItemId);
    itemsRef.current = nextItems;
    persistItems(nextItems);
    setItems(nextItems);
  };

  const clearCart = () => {
    setItems([]);
    itemsRef.current = [];
    persistItems([]);
  };
  const setFulfillmentType = (value: FulfillmentType) => {
    persistFulfillment(value);
    setFulfillmentTypeState(value);
  };

  const subtotal = useMemo(
    () => items.reduce((sum, item) => sum + item.priceTala * item.quantity, 0),
    [items]
  );

  const deliveryFee = fulfillmentType === "DELIVERY" ? 2 : 0;
  const total = subtotal + deliveryFee;

  return (
    <CartContext.Provider
      value={{
        items,
        fulfillmentType,
        setFulfillmentType,
        addItem,
        updateQuantity,
        removeItem,
        clearCart,
        subtotal,
        deliveryFee,
        total
      }}
    >
      {children}
    </CartContext.Provider>
  );
}

export function useCart() {
  const value = useContext(CartContext);
  if (!value) throw new Error("useCart must be used within CartProvider");
  return value;
}

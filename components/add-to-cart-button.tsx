"use client";

import { useMemo, useState } from "react";
import { useCart } from "@/components/cart-context";

type Props = {
  item: {
    menuItemId: number;
    name: string;
    priceTala: number;
    imageUrl?: string | null;
    isAvailable: boolean;
    options?: Array<{
      id: number;
      name: string;
      priceTala: number;
    }>;
  };
};

export function AddToCartButton({ item }: Props) {
  const { addItem } = useCart();
  const [isPickerOpen, setIsPickerOpen] = useState(false);
  const optionChoices = useMemo(() => item.options ?? [], [item.options]);
  const [selectedOptionId, setSelectedOptionId] = useState<number | null>(optionChoices[0]?.id ?? null);

  function addDefaultItem() {
    addItem({
      menuItemId: item.menuItemId,
      selectedOptionId: null,
      name: item.name,
      priceTala: item.priceTala,
      imageUrl: item.imageUrl,
      isAvailable: item.isAvailable
    });
  }

  function openPicker() {
    setSelectedOptionId(optionChoices[0]?.id ?? null);
    setIsPickerOpen(true);
  }

  function confirmOption() {
    const selectedOption = optionChoices.find((option) => option.id === selectedOptionId);
    if (!selectedOption) return;

    addItem({
      menuItemId: item.menuItemId,
      selectedOptionId: selectedOption.id,
      name: `${item.name} - ${selectedOption.name}`,
      priceTala: selectedOption.priceTala,
      imageUrl: item.imageUrl,
      isAvailable: item.isAvailable
    });

    setIsPickerOpen(false);
  }

  return (
    <>
      <button
        type="button"
        className={item.isAvailable ? "btn-primary" : "btn-secondary cursor-not-allowed opacity-50"}
        disabled={!item.isAvailable}
        onClick={optionChoices.length > 0 ? openPicker : addDefaultItem}
      >
        Add
      </button>

      {isPickerOpen && (
        <div className="option-modal-backdrop" role="presentation" onClick={() => setIsPickerOpen(false)}>
          <div className="option-modal card" role="dialog" aria-modal="true" onClick={(event) => event.stopPropagation()}>
            <div className="space-y-2">
              <p className="text-xl font-bold">{item.name}</p>
              <p className="text-sm text-gray-600">Choose the option you want to add to cart.</p>
            </div>

            <div className="option-list">
              {optionChoices.map((option) => (
                <button
                  key={option.id}
                  type="button"
                  className={`option-pill ${selectedOptionId === option.id ? "is-selected" : ""}`}
                  onClick={() => setSelectedOptionId(option.id)}
                >
                  <span>{option.name}</span>
                  <strong>{option.priceTala.toFixed(2)} tala</strong>
                </button>
              ))}
            </div>

            <div className="confirmation-actions">
              <button className="btn-secondary" type="button" onClick={() => setIsPickerOpen(false)}>
                Cancel
              </button>
              <button className="btn-primary" type="button" onClick={confirmOption}>
                Add to cart
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

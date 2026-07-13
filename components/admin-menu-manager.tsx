"use client";

import { useEffect, useState } from "react";

type Category = { id: number; name: string };
type MenuOption = {
  id: number;
  name: string;
  priceTala: number;
  isActive: boolean;
};
type MenuItem = {
  id: number;
  categoryId: number;
  name: string;
  description: string | null;
  priceTala: number;
  imageUrl: string | null;
  isAvailable: boolean;
  options: MenuOption[];
  category?: Category;
};

type OptionFormState = {
  name: string;
  priceTala: string;
  isActive: boolean;
};

type MenuFormState = {
  categoryId: string;
  name: string;
  description: string;
  priceTala: string;
  imageUrl: string;
  isAvailable: boolean;
  options: OptionFormState[];
};

const emptyOption: OptionFormState = {
  name: "",
  priceTala: "",
  isActive: true
};

const emptyForm: MenuFormState = {
  categoryId: "",
  name: "",
  description: "",
  priceTala: "",
  imageUrl: "",
  isAvailable: true,
  options: []
};

function itemToForm(item: MenuItem): MenuFormState {
  return {
    categoryId: String(item.categoryId),
    name: item.name,
    description: item.description ?? "",
    priceTala: String(Number(item.priceTala)),
    imageUrl: item.imageUrl ?? "",
    isAvailable: item.isAvailable,
    options: item.options.map((option) => ({
      name: option.name,
      priceTala: String(Number(option.priceTala)),
      isActive: option.isActive
    }))
  };
}

function buildPayload(form: MenuFormState) {
  return {
    categoryId: Number(form.categoryId),
    name: form.name,
    description: form.description,
    priceTala: Number(form.priceTala),
    imageUrl: form.imageUrl.trim() || null,
    isAvailable: form.isAvailable,
    options: form.options
      .filter((option) => option.name.trim() && option.priceTala.trim())
      .map((option) => ({
        name: option.name.trim(),
        priceTala: Number(option.priceTala),
        isActive: option.isActive
      }))
  };
}

export function AdminMenuManager() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [items, setItems] = useState<MenuItem[]>([]);
  const [form, setForm] = useState<MenuFormState>(emptyForm);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  async function load() {
    const [catRes, itemRes] = await Promise.all([
      fetch("/api/admin/categories"),
      fetch("/api/admin/menu")
    ]);

    if (catRes.ok) setCategories(await catRes.json());
    if (itemRes.ok) setItems(await itemRes.json());
  }

  useEffect(() => {
    void load();
  }, []);

  function resetForm() {
    setForm(emptyForm);
    setEditingId(null);
    setError("");
    setSuccess("");
  }

  function addOptionRow() {
    setForm((prev) => ({ ...prev, options: [...prev.options, emptyOption] }));
  }

  function updateOption(index: number, patch: Partial<OptionFormState>) {
    setForm((prev) => ({
      ...prev,
      options: prev.options.map((option, optionIndex) =>
        optionIndex === index ? { ...option, ...patch } : option
      )
    }));
  }

  function removeOption(index: number) {
    setForm((prev) => ({
      ...prev,
      options: prev.options.filter((_, optionIndex) => optionIndex !== index)
    }));
  }

  async function saveItem() {
    try {
      setSaving(true);
      setError("");
      setSuccess("");

      const response = await fetch(editingId ? `/api/admin/menu/${editingId}` : "/api/admin/menu", {
        method: editingId ? "PATCH" : "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(buildPayload(form))
      });

      const data = await response.json();
      if (!response.ok) throw new Error(data.error ?? "Could not save menu item");

      setSuccess(editingId ? "Menu item updated." : "Menu item added.");
      resetForm();
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save menu item");
    } finally {
      setSaving(false);
    }
  }

  async function uploadImage(file: File) {
    try {
      setUploading(true);
      setError("");
      setSuccess("");

      const body = new FormData();
      body.append("file", file);

      const response = await fetch("/api/admin/uploads/menu-image", {
        method: "POST",
        body
      });

      const data = await response.json();
      if (!response.ok) throw new Error(data.error ?? "Could not upload image");

      setForm((prev) => ({ ...prev, imageUrl: data.imageUrl }));
      setSuccess("Image uploaded. Save the item to keep it.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not upload image");
    } finally {
      setUploading(false);
    }
  }

  async function toggleAvailability(item: MenuItem) {
    setError("");
    setSuccess("");

    const response = await fetch(`/api/admin/menu/${item.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        categoryId: item.categoryId,
        name: item.name,
        description: item.description ?? "",
        priceTala: Number(item.priceTala),
        imageUrl: item.imageUrl ?? "",
        isAvailable: !item.isAvailable,
        options: item.options.map((option) => ({
          name: option.name,
          priceTala: Number(option.priceTala),
          isActive: option.isActive
        }))
      })
    });

    const data = await response.json();
    if (!response.ok) {
      setError(data.error ?? "Could not update availability");
      return;
    }

    setSuccess("Availability updated.");
    await load();
  }

  function startEdit(item: MenuItem) {
    setEditingId(item.id);
    setForm(itemToForm(item));
    setError("");
    setSuccess("");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[0.95fr_1.05fr]">
      <section className="card space-y-4">
        <div className="flex items-center justify-between gap-2">
          <h2 className="text-xl font-bold">{editingId ? "Edit Menu Item" : "Add Menu Item"}</h2>
          {editingId && (
            <button className="btn-secondary" onClick={resetForm} type="button">
              Cancel Edit
            </button>
          )}
        </div>

        <div>
          <label className="label">Category</label>
          <select
            className="input"
            value={form.categoryId}
            onChange={(e) => setForm((prev) => ({ ...prev, categoryId: e.target.value }))}
          >
            <option value="">Select category</option>
            {categories.map((category) => (
              <option key={category.id} value={category.id}>{category.name}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="label">Name</label>
          <input
            className="input"
            value={form.name}
            onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))}
          />
        </div>

        <div>
          <label className="label">Description</label>
          <textarea
            className="input min-h-24"
            value={form.description}
            onChange={(e) => setForm((prev) => ({ ...prev, description: e.target.value }))}
          />
        </div>

        <div>
          <label className="label">Base / starting price (tala)</label>
          <input
            className="input"
            inputMode="decimal"
            type="number"
            min="0"
            step="0.01"
            value={form.priceTala}
            onChange={(e) => setForm((prev) => ({ ...prev, priceTala: e.target.value }))}
          />
          <p className="mt-2 text-sm text-gray-600">
            Use this as the normal price, or the lowest starting price if this item has option choices.
          </p>
        </div>

        <div className="space-y-3">
          <div className="flex items-center justify-between gap-2">
            <div>
              <p className="label">Item options</p>
              <p className="text-sm text-gray-600">Add choices like 2pc, 3pc, single, or combo.</p>
            </div>
            <button className="btn-secondary" type="button" onClick={addOptionRow}>
              Add option
            </button>
          </div>

          {form.options.length === 0 ? (
            <div className="option-editor-empty">No options added. Leave this blank for a standard single-price item.</div>
          ) : (
            <div className="space-y-3">
              {form.options.map((option, index) => (
                <div key={`${index}-${option.name}`} className="option-editor-row">
                  <input
                    className="input"
                    placeholder="Option name"
                    value={option.name}
                    onChange={(e) => updateOption(index, { name: e.target.value })}
                  />
                  <input
                    className="input"
                    type="number"
                    min="0"
                    step="0.01"
                    inputMode="decimal"
                    placeholder="Price"
                    value={option.priceTala}
                    onChange={(e) => updateOption(index, { priceTala: e.target.value })}
                  />
                  <label className="option-editor-toggle">
                    <input
                      checked={option.isActive}
                      type="checkbox"
                      onChange={(e) => updateOption(index, { isActive: e.target.checked })}
                    />
                    <span>Active</span>
                  </label>
                  <button className="btn-secondary" type="button" onClick={() => removeOption(index)}>
                    Remove
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="space-y-2">
          <label className="label">Menu Image</label>
          <input
            className="input"
            type="file"
            accept="image/png,image/jpeg,image/webp,image/gif"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) {
                void uploadImage(file);
              }
              e.currentTarget.value = "";
            }}
          />
          <input
            className="input"
            placeholder="/uploads/menu/your-photo.jpg"
            value={form.imageUrl}
            onChange={(e) => setForm((prev) => ({ ...prev, imageUrl: e.target.value }))}
          />
          {uploading && <p className="text-sm text-gray-600">Uploading image...</p>}
          {form.imageUrl && (
            <div className="rounded-xl border border-gray-200 p-3">
              <p className="text-sm text-gray-600">Preview</p>
              <div className="mt-2">
                <img
                  src={form.imageUrl}
                  alt="Menu preview"
                  style={{ width: "100%", maxHeight: "12rem", objectFit: "cover", borderRadius: "0.75rem" }}
                />
              </div>
              <p className="mt-2 text-sm text-gray-600">{form.imageUrl}</p>
            </div>
          )}
        </div>

        <label className="flex items-center gap-2">
          <input
            checked={form.isAvailable}
            type="checkbox"
            onChange={(e) => setForm((prev) => ({ ...prev, isAvailable: e.target.checked }))}
          />
          <span className="font-medium">Available for ordering</span>
        </label>

        {error && <p className="text-sm text-red-600">{error}</p>}
        {success && <p className="text-sm text-green-700">{success}</p>}

        <button className="btn-primary" disabled={saving || uploading} onClick={saveItem} type="button">
          {saving ? "Saving..." : editingId ? "Save Changes" : "Add Item"}
        </button>
      </section>

      <section className="card space-y-4">
        <h2 className="text-xl font-bold">Current Menu</h2>
        <div className="space-y-3">
          {items.map((item) => (
            <article key={item.id} className="rounded-2xl border border-gray-200 p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-3">
                  {item.imageUrl ? (
                    <img
                      src={item.imageUrl}
                      alt={item.name}
                      style={{ width: "88px", height: "88px", objectFit: "cover", borderRadius: "1rem", background: "#efe6d9" }}
                    />
                  ) : (
                    <div className="menu-image" style={{ width: "88px", minHeight: "88px", borderRadius: "1rem", padding: "0.5rem" }}>
                      <span className="text-sm font-semibold">No photo</span>
                    </div>
                  )}

                  <div className="space-y-2">
                    <div>
                      <p className="font-semibold">{item.name}</p>
                      <p className="text-sm text-gray-600">{item.category?.name ?? "Uncategorized"}</p>
                    </div>
                    <p className="text-sm text-gray-600">{item.description}</p>
                    <p className="text-sm">{Number(item.priceTala).toFixed(2)} tala</p>
                    {item.options.length > 0 && (
                      <div className="menu-option-summary">
                        {item.options.map((option) => (
                          <span key={option.id} className="badge bg-gray-100 text-gray-700">
                            {option.name} {Number(option.priceTala).toFixed(2)}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex flex-col gap-2">
                  <span className={item.isAvailable ? "badge bg-green-100 text-green-700" : "badge bg-red-100 text-red-700"}>
                    {item.isAvailable ? "Available" : "Unavailable"}
                  </span>
                  <button className="btn-secondary" onClick={() => startEdit(item)} type="button">
                    Edit
                  </button>
                  <button className="btn-secondary" onClick={() => toggleAvailability(item)} type="button">
                    Toggle
                  </button>
                </div>
              </div>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}

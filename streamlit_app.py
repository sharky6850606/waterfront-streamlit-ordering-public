from __future__ import annotations

import csv
import base64
import html
import mimetypes
import os
import random
import sqlite3
from datetime import datetime, timedelta
from io import StringIO
from pathlib import Path
from typing import Any

import streamlit as st


APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "prisma" / "dev.db"
PUBLIC_DIR = APP_DIR / "public"
DELIVERY_FEE_TALA = 2.0
ADMIN_PASSWORD = os.getenv("STREAMLIT_ADMIN_PASSWORD", "admin123")

STATUS_LABELS = {
    "NEW": "New",
    "PREPARING": "Preparing",
    "READY_FOR_PICKUP": "Ready for pickup",
    "OUT_FOR_DELIVERY": "Out for delivery",
    "COMPLETED": "Completed",
    "CANCELLED": "Cancelled",
}

ACTIVE_STATUSES = ("NEW", "PREPARING", "READY_FOR_PICKUP", "OUT_FOR_DELIVERY")


def connect() -> sqlite3.Connection:
    ensure_database()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def ensure_database() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    timestamp = now_value()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS Category (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                sortOrder INTEGER NOT NULL DEFAULT 0,
                isActive BOOLEAN NOT NULL DEFAULT 1,
                createdAt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updatedAt DATETIME NOT NULL
            );

            CREATE TABLE IF NOT EXISTS MenuItem (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                categoryId INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                priceTala DECIMAL NOT NULL,
                imageUrl TEXT,
                isAvailable BOOLEAN NOT NULL DEFAULT 1,
                isFeatured BOOLEAN NOT NULL DEFAULT 0,
                isNew BOOLEAN NOT NULL DEFAULT 0,
                newUntil TEXT,
                isSpecial BOOLEAN NOT NULL DEFAULT 0,
                specialLabel TEXT,
                specialUntil TEXT,
                createdAt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updatedAt DATETIME NOT NULL,
                FOREIGN KEY (categoryId) REFERENCES Category (id)
            );

            CREATE TABLE IF NOT EXISTS MenuItemOption (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                menuItemId INTEGER NOT NULL,
                name TEXT NOT NULL,
                priceTala DECIMAL NOT NULL,
                sortOrder INTEGER NOT NULL DEFAULT 0,
                isActive BOOLEAN NOT NULL DEFAULT 1,
                createdAt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updatedAt DATETIME NOT NULL,
                FOREIGN KEY (menuItemId) REFERENCES MenuItem (id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS "Order" (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                orderNumber TEXT NOT NULL UNIQUE,
                customerName TEXT NOT NULL,
                customerPhone TEXT NOT NULL,
                fulfillmentType TEXT NOT NULL,
                deliveryAddress TEXT,
                status TEXT NOT NULL DEFAULT 'NEW',
                paymentMethod TEXT NOT NULL DEFAULT 'CASH',
                subtotalTala DECIMAL NOT NULL,
                deliveryFeeTala DECIMAL NOT NULL,
                totalTala DECIMAL NOT NULL,
                notes TEXT,
                isSeenByAdmin BOOLEAN NOT NULL DEFAULT 0,
                createdAt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updatedAt DATETIME NOT NULL,
                completedAt DATETIME
            );

            CREATE TABLE IF NOT EXISTS OrderItem (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                orderId INTEGER NOT NULL,
                menuItemId INTEGER NOT NULL,
                itemNameSnapshot TEXT NOT NULL,
                unitPriceTala DECIMAL NOT NULL,
                quantity INTEGER NOT NULL,
                lineTotalTala DECIMAL NOT NULL,
                FOREIGN KEY (orderId) REFERENCES "Order" (id) ON DELETE CASCADE,
                FOREIGN KEY (menuItemId) REFERENCES MenuItem (id)
            );

            CREATE INDEX IF NOT EXISTS MenuItem_categoryId_isAvailable_idx
                ON MenuItem(categoryId, isAvailable);
            CREATE INDEX IF NOT EXISTS Order_status_createdAt_idx
                ON "Order"(status, createdAt);
            CREATE INDEX IF NOT EXISTS Order_customerPhone_createdAt_idx
                ON "Order"(customerPhone, createdAt);
            CREATE INDEX IF NOT EXISTS OrderItem_orderId_idx
                ON OrderItem(orderId);
            """
        )

        existing_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(MenuItem)").fetchall()
        }
        promotion_columns = {
            "isFeatured": "BOOLEAN NOT NULL DEFAULT 0",
            "isNew": "BOOLEAN NOT NULL DEFAULT 0",
            "newUntil": "TEXT",
            "isSpecial": "BOOLEAN NOT NULL DEFAULT 0",
            "specialLabel": "TEXT",
            "specialUntil": "TEXT",
        }
        for column_name, column_definition in promotion_columns.items():
            if column_name not in existing_columns:
                conn.execute(f"ALTER TABLE MenuItem ADD COLUMN {column_name} {column_definition}")

        if conn.execute("SELECT COUNT(*) FROM MenuItem").fetchone()[0] > 0:
            conn.commit()
            return

        food_id = conn.execute(
            """
            INSERT INTO Category (name, sortOrder, isActive, createdAt, updatedAt)
            VALUES ('Food', 1, 1, ?, ?)
            """,
            (timestamp, timestamp),
        ).lastrowid
        drinks_id = conn.execute(
            """
            INSERT INTO Category (name, sortOrder, isActive, createdAt, updatedAt)
            VALUES ('Drinks', 2, 1, ?, ?)
            """,
            (timestamp, timestamp),
        ).lastrowid
        conn.executemany(
            """
            INSERT INTO MenuItem (
                categoryId, name, description, priceTala, imageUrl,
                isAvailable, isFeatured, createdAt, updatedAt
            )
            VALUES (?, ?, ?, ?, ?, 1, 0, ?, ?)
            """,
            [
                (
                    food_id,
                    "Waterfront Snack Plate",
                    "A quick plate for pickup or delivery.",
                    15.0,
                    "/uploads/menu/waterfront-snack-menu-by-the-pier-fcbba7ed-11fb-4417-a90a-1cccdb1bbd73.png",
                    timestamp,
                    timestamp,
                ),
                (
                    food_id,
                    "Island Burger",
                    "Burger with fresh salad and sauce.",
                    12.0,
                    "/uploads/menu/chatgpt-image-mar-26-2026-12-10-44-pm-570b3024-c873-4d93-8ba0-545a521e4012.png",
                    timestamp,
                    timestamp,
                ),
                (
                    drinks_id,
                    "Cold Drink",
                    "Chilled canned drink.",
                    4.0,
                    "/uploads/menu/chatgpt-image-mar-24-2026-03-09-57-pm-05c0bb11-2096-4985-a32f-2a4084983e06.png",
                    timestamp,
                    timestamp,
                ),
            ],
        )
        conn.commit()


def now_value() -> str:
    return datetime.now().isoformat(timespec="seconds")


def money(value: float | int | str | None) -> str:
    return f"{float(value or 0):.2f} tala"


def today_iso() -> str:
    return datetime.now().date().isoformat()


def parse_iso_date(value: str | None, fallback_days: int = 7):
    if value:
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            pass
    return (datetime.now().date() + timedelta(days=fallback_days))


def escape(value: Any) -> str:
    return html.escape(str(value or ""))


def generate_order_number() -> str:
    stamp = datetime.now().strftime("%y%m%d")
    return f"ORD-{stamp}-{random.randint(1000, 9999)}"


def image_path(image_url: str | None) -> Path | None:
    if not image_url or not image_url.startswith("/"):
        return None
    candidate = PUBLIC_DIR / image_url.lstrip("/")
    return candidate if candidate.exists() else None


@st.cache_data(show_spinner=False)
def image_data_uri(path_value: str) -> str:
    path = Path(path_value)
    mime_type = mimetypes.guess_type(path.name)[0] or "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def is_active_until(value: str | None) -> bool:
    return not value or value >= today_iso()


@st.cache_data(ttl=5)
def get_menu() -> list[dict[str, Any]]:
    with connect() as conn:
        categories = conn.execute(
            """
            SELECT id, name
            FROM Category
            WHERE isActive = 1
            ORDER BY sortOrder ASC, name ASC
            """
        ).fetchall()

        output = []
        for category in categories:
            items = conn.execute(
                """
                SELECT
                    id, categoryId, name, description, priceTala, imageUrl, isAvailable,
                    isFeatured, isNew, newUntil, isSpecial, specialLabel, specialUntil
                FROM MenuItem
                WHERE categoryId = ?
                ORDER BY isAvailable DESC, name ASC
                """,
                (category["id"],),
            ).fetchall()

            hydrated_items = []
            for item in items:
                options = conn.execute(
                    """
                    SELECT id, name, priceTala
                    FROM MenuItemOption
                    WHERE menuItemId = ? AND isActive = 1
                    ORDER BY sortOrder ASC, name ASC
                    """,
                    (item["id"],),
                ).fetchall()
                hydrated_items.append(
                    {
                        **dict(item),
                        "options": [dict(option) for option in options],
                    }
                )

            output.append({**dict(category), "items": hydrated_items})
        return output


@st.cache_data(ttl=5)
def get_categories() -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, name FROM Category WHERE isActive = 1 ORDER BY sortOrder ASC, name ASC"
        ).fetchall()
    return [dict(row) for row in rows]


@st.cache_data(ttl=10)
def get_best_seller_ids(limit: int = 6) -> list[int]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT oi.menuItemId, SUM(oi.quantity) AS sold
            FROM OrderItem oi
            JOIN "Order" o ON o.id = oi.orderId
            WHERE o.status != 'CANCELLED'
            GROUP BY oi.menuItemId
            ORDER BY sold DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [int(row["menuItemId"]) for row in rows]


def promotion_badges(item: dict[str, Any], best_seller_ids: set[int] | None = None) -> list[str]:
    badges = []
    best_seller_ids = best_seller_ids or set()
    if item["id"] in best_seller_ids:
        badges.append("Best seller")
    if item.get("isFeatured"):
        badges.append("Featured")
    if item.get("isNew") and is_active_until(item.get("newUntil")):
        badges.append("New")
    if item.get("isSpecial") and is_active_until(item.get("specialUntil")):
        badges.append(item.get("specialLabel") or "Special")
    return badges


def badge_class(label: str) -> str:
    normalized = label.lower()
    if "best" in normalized:
        return "is-best"
    if "featured" in normalized:
        return "is-featured"
    if "new" in normalized:
        return "is-new"
    return "is-special"


def promoted_menu_items(menu: list[dict[str, Any]], limit: int = 8) -> list[dict[str, Any]]:
    best_seller_ids = set(get_best_seller_ids())
    promoted = []
    seen = set()
    for category in menu:
        for item in category["items"]:
            if not item["isAvailable"]:
                continue
            badges = promotion_badges(item, best_seller_ids)
            if not badges or item["id"] in seen:
                continue
            promoted.append({**item, "promoBadges": badges[:3]})
            seen.add(item["id"])
    return promoted[:limit]


@st.cache_data(ttl=5)
def get_recent_orders(limit: int = 60) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM "Order"
            ORDER BY createdAt DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_order_items(order_id: int) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT itemNameSnapshot, unitPriceTala, quantity, lineTotalTala
            FROM OrderItem
            WHERE orderId = ?
            ORDER BY id ASC
            """,
            (order_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def find_orders(phone: str = "", order_number: str = "") -> list[dict[str, Any]]:
    phone = phone.strip()
    order_number = order_number.strip().upper()
    with connect() as conn:
        if order_number:
            rows = conn.execute(
                """
                SELECT *
                FROM "Order"
                WHERE upper(orderNumber) = ?
                ORDER BY createdAt DESC
                """,
                (order_number,),
            ).fetchall()
        elif phone:
            rows = conn.execute(
                """
                SELECT *
                FROM "Order"
                WHERE customerPhone = ?
                ORDER BY createdAt DESC
                LIMIT 10
                """,
                (phone,),
            ).fetchall()
        else:
            rows = []
    return [dict(row) for row in rows]


def cart_total() -> tuple[float, float, float]:
    subtotal = sum(float(item["unit_price"]) * int(item["quantity"]) for item in st.session_state.cart)
    delivery_fee = DELIVERY_FEE_TALA if st.session_state.fulfillment_type == "DELIVERY" and subtotal > 0 else 0.0
    return subtotal, delivery_fee, subtotal + delivery_fee


def cart_count() -> int:
    return sum(int(item["quantity"]) for item in st.session_state.cart)


def add_to_cart(item: dict[str, Any], quantity: int, option_id: int | None = None) -> None:
    option = None
    if option_id:
        option = next((candidate for candidate in item["options"] if candidate["id"] == option_id), None)

    name = item["name"] if option is None else f"{item['name']} - {option['name']}"
    unit_price = float(item["priceTala"] if option is None else option["priceTala"])
    cart_key = f"{item['id']}:{option_id or 'base'}"

    for cart_item in st.session_state.cart:
        if cart_item["cart_key"] == cart_key:
            cart_item["quantity"] += quantity
            st.session_state.cart_notice = f"Updated {name} in cart"
            return

    st.session_state.cart.append(
        {
            "cart_key": cart_key,
            "menu_item_id": item["id"],
            "option_id": option_id,
            "name": name,
            "unit_price": unit_price,
            "quantity": quantity,
            "image_url": item.get("imageUrl"),
        }
    )
    st.session_state.cart_notice = f"Added {name} to cart"


def validate_order(name: str, phone: str, address: str) -> str | None:
    if not st.session_state.cart:
        return "Your cart is empty."
    if len(name.strip()) < 2:
        return "Please enter the customer's name."
    if len(phone.strip()) < 5:
        return "Please enter a valid phone number."
    if st.session_state.fulfillment_type == "DELIVERY" and not address.strip():
        return "Please enter a delivery location for delivery orders."
    return None


def create_order(name: str, phone: str, address: str, notes: str) -> str:
    subtotal, delivery_fee, total = cart_total()
    timestamp = now_value()

    with connect() as conn:
        for _ in range(10):
            order_number = generate_order_number()
            exists = conn.execute(
                'SELECT 1 FROM "Order" WHERE orderNumber = ?',
                (order_number,),
            ).fetchone()
            if not exists:
                break
        else:
            raise RuntimeError("Could not create a unique order number.")

        order_items = []
        for cart_item in st.session_state.cart:
            menu_item = conn.execute(
                """
                SELECT id, name, isAvailable
                FROM MenuItem
                WHERE id = ?
                """,
                (cart_item["menu_item_id"],),
            ).fetchone()

            if not menu_item:
                raise ValueError(f"{cart_item['name']} is no longer on the menu.")
            if not menu_item["isAvailable"]:
                raise ValueError(f"{menu_item['name']} is currently unavailable.")

            if cart_item["option_id"] is not None:
                option = conn.execute(
                    """
                    SELECT id
                    FROM MenuItemOption
                    WHERE id = ? AND menuItemId = ? AND isActive = 1
                    """,
                    (cart_item["option_id"], cart_item["menu_item_id"]),
                ).fetchone()
                if not option:
                    raise ValueError(f"The selected option for {menu_item['name']} is unavailable.")

            line_total = float(cart_item["unit_price"]) * int(cart_item["quantity"])
            order_items.append(
                (
                    cart_item["menu_item_id"],
                    cart_item["name"],
                    float(cart_item["unit_price"]),
                    int(cart_item["quantity"]),
                    line_total,
                )
            )

        cursor = conn.execute(
            """
            INSERT INTO "Order" (
                orderNumber, customerName, customerPhone, fulfillmentType,
                deliveryAddress, status, paymentMethod, subtotalTala,
                deliveryFeeTala, totalTala, notes, isSeenByAdmin,
                createdAt, updatedAt
            )
            VALUES (?, ?, ?, ?, ?, 'NEW', 'CASH', ?, ?, ?, ?, 0, ?, ?)
            """,
            (
                order_number,
                name.strip(),
                phone.strip(),
                st.session_state.fulfillment_type,
                address.strip() if st.session_state.fulfillment_type == "DELIVERY" else None,
                subtotal,
                delivery_fee,
                total,
                notes.strip() or None,
                timestamp,
                timestamp,
            ),
        )
        order_id = cursor.lastrowid

        conn.executemany(
            """
            INSERT INTO OrderItem (
                orderId, menuItemId, itemNameSnapshot, unitPriceTala, quantity, lineTotalTala
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [(order_id, *item) for item in order_items],
        )
        conn.commit()

    st.cache_data.clear()
    st.session_state.cart = []
    st.session_state.last_order_number = order_number
    return order_number


def update_order_status(order_id: int, status: str) -> None:
    completed_at = now_value() if status == "COMPLETED" else None
    with connect() as conn:
        conn.execute(
            """
            UPDATE "Order"
            SET status = ?, updatedAt = ?, completedAt = ?
            WHERE id = ?
            """,
            (status, now_value(), completed_at, order_id),
        )
        conn.commit()
    st.cache_data.clear()


def update_item_availability(item_id: int, is_available: bool) -> None:
    with connect() as conn:
        conn.execute(
            """
            UPDATE MenuItem
            SET isAvailable = ?, updatedAt = ?
            WHERE id = ?
            """,
            (1 if is_available else 0, now_value(), item_id),
        )
        conn.commit()
    st.cache_data.clear()


def update_item_promotions(
    item_id: int,
    is_featured: bool,
    is_new: bool,
    new_until: str | None,
    is_special: bool,
    special_label: str,
    special_until: str | None,
) -> None:
    with connect() as conn:
        conn.execute(
            """
            UPDATE MenuItem
            SET isFeatured = ?,
                isNew = ?,
                newUntil = ?,
                isSpecial = ?,
                specialLabel = ?,
                specialUntil = ?,
                updatedAt = ?
            WHERE id = ?
            """,
            (
                1 if is_featured else 0,
                1 if is_new else 0,
                new_until if is_new else None,
                1 if is_special else 0,
                special_label.strip() if is_special and special_label.strip() else None,
                special_until if is_special else None,
                now_value(),
                item_id,
            ),
        )
        conn.commit()
    st.cache_data.clear()


def add_category(name: str) -> None:
    name = name.strip()
    if not name:
        return
    with connect() as conn:
        next_order = conn.execute("SELECT COALESCE(MAX(sortOrder), 0) + 1 FROM Category").fetchone()[0]
        conn.execute(
            """
            INSERT OR IGNORE INTO Category (name, sortOrder, isActive, createdAt, updatedAt)
            VALUES (?, ?, 1, ?, ?)
            """,
            (name, next_order, now_value(), now_value()),
        )
        conn.commit()
    st.cache_data.clear()


def add_menu_item(category_id: int, name: str, description: str, price: float, image_url: str) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO MenuItem (
                categoryId, name, description, priceTala, imageUrl,
                isAvailable, isFeatured, createdAt, updatedAt
            )
            VALUES (?, ?, ?, ?, ?, 1, 0, ?, ?)
            """,
            (
                category_id,
                name.strip(),
                description.strip() or None,
                float(price),
                image_url.strip() or None,
                now_value(),
                now_value(),
            ),
        )
        conn.commit()
    st.cache_data.clear()


def order_csv(orders: list[dict[str, Any]]) -> str:
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Order", "Customer", "Phone", "Type", "Status", "Total", "Created"])
    for order in orders:
        writer.writerow(
            [
                order["orderNumber"],
                order["customerName"],
                order["customerPhone"],
                order["fulfillmentType"],
                STATUS_LABELS.get(order["status"], order["status"]),
                float(order["totalTala"]),
                order["createdAt"],
            ]
        )
    return buffer.getvalue()


def ensure_state() -> None:
    st.session_state.setdefault("cart", [])
    st.session_state.setdefault("fulfillment_type", "DELIVERY")
    st.session_state.setdefault("admin_authenticated", False)
    st.session_state.setdefault("last_order_number", "")
    st.session_state.setdefault("view", "Order")
    st.session_state.setdefault("cart_notice", "")


def render_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --brand: #0e5967;
            --brand-dark: #102a33;
            --accent: #d46f2c;
            --surface: #fffdf8;
            --line: #e7dbc8;
            --muted: #617080;
            --page: #f7f2e8;
        }
        .stApp {
            background:
                radial-gradient(circle at 8% 0%, rgba(212, 111, 44, .13), transparent 28rem),
                linear-gradient(180deg, #fbf7ef 0%, var(--page) 100%);
            color: #17212b;
        }
        section[data-testid="stSidebar"] { display: none; }
        button[kind="header"] { color: var(--brand-dark); }
        .block-container {
            max-width: 1240px;
            padding-top: 1rem;
            padding-bottom: 3rem;
        }
        div[data-testid="stHorizontalBlock"] {
            align-items: stretch;
        }
        h1, h2, h3 {
            color: var(--brand-dark);
            letter-spacing: 0;
        }
        h1 { font-size: clamp(2rem, 4vw, 3.8rem); line-height: 1.02; }
        h2 { font-size: clamp(1.35rem, 2vw, 2rem); }
        div[data-testid="stMetric"] {
            background: rgba(255, 253, 248, .92);
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: .85rem 1rem;
            box-shadow: 0 12px 30px rgba(52, 39, 23, .06);
        }
        .hero {
            border: 1px solid var(--line);
            background:
                linear-gradient(135deg, rgba(14, 89, 103, .94), rgba(16, 42, 51, .9)),
                rgba(255, 253, 248, .94);
            border-radius: 8px;
            padding: clamp(1.4rem, 4vw, 3rem);
            box-shadow: 0 22px 54px rgba(52, 39, 23, .12);
            margin-bottom: 1.1rem;
            overflow: hidden;
        }
        .hero h1, .hero p { color: #fffaf1; }
        .hero p {
            max-width: 44rem;
            font-size: 1.08rem;
            margin-bottom: 0;
        }
        .muted {
            color: var(--muted);
        }
        .topbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            padding: .9rem 0 1.25rem;
            position: sticky;
            top: 0;
            z-index: 10;
            background: rgba(247, 242, 232, .86);
            backdrop-filter: blur(14px);
        }
        .brand-lockup {
            display: grid;
            gap: .05rem;
        }
        .brand-kicker {
            color: var(--accent);
            font-size: .78rem;
            font-weight: 800;
            letter-spacing: .08em;
            text-transform: uppercase;
        }
        .brand-title {
            color: var(--brand-dark);
            font-weight: 900;
            font-size: 1.55rem;
        }
        .nav-card {
            border: 1px solid var(--line);
            background: rgba(255, 253, 248, .92);
            border-radius: 8px;
            padding: .85rem 1rem;
            box-shadow: 0 16px 34px rgba(52, 39, 23, .07);
            font-size: 1rem;
        }
        .nav-spacer { margin-top: .25rem; margin-bottom: .4rem; }
        .order-card, .cart-card {
            border: 1px solid var(--line);
            background: rgba(255, 253, 248, .95);
            border-radius: 8px;
            padding: 1rem;
            box-shadow: 0 14px 34px rgba(52, 39, 23, .07);
            margin-bottom: .8rem;
        }
        .menu-card {
            border: 0;
            background: transparent;
            border-radius: 8px;
            padding: 0;
            box-shadow: none;
            display: grid;
            gap: .7rem;
            margin-bottom: .35rem;
        }
        .menu-card-media {
            position: relative;
            overflow: hidden;
            border-radius: 8px;
        }
        .menu-card-media img {
            width: 100%;
            aspect-ratio: 5 / 3;
            object-fit: cover;
            display: block;
            border-radius: 8px;
            border: 1px solid var(--line);
        }
        .menu-badge-row {
            display: flex;
            flex-wrap: wrap;
            gap: .4rem;
            margin-bottom: .25rem;
        }
        .menu-badge {
            display: inline-flex;
            align-items: center;
            border-radius: 999px;
            padding: .22rem .62rem;
            font-size: .76rem;
            font-weight: 850;
            background: rgba(14, 89, 103, .1);
            color: var(--brand);
        }
        .menu-badge.is-price {
            background: rgba(212, 111, 44, .14);
            color: #94460e;
        }
        .menu-badge.is-best {
            background: #fef3c7;
            color: #92400e;
        }
        .menu-badge.is-featured {
            background: #dbeafe;
            color: #1d4ed8;
        }
        .menu-badge.is-new {
            background: #dcfce7;
            color: #166534;
        }
        .menu-badge.is-special {
            background: #fae8ff;
            color: #86198f;
        }
        .menu-badge.is-unavailable {
            background: #fee2e2;
            color: #991b1b;
        }
        .promo-strip {
            display: grid;
            grid-auto-flow: column;
            grid-auto-columns: minmax(14rem, 18rem);
            gap: .85rem;
            overflow-x: auto;
            padding: .15rem .05rem .85rem;
            margin-bottom: 1rem;
        }
        .promo-card {
            border: 1px solid var(--line);
            border-radius: 8px;
            background: rgba(255, 253, 248, .98);
            box-shadow: 0 14px 34px rgba(52, 39, 23, .08);
            overflow: hidden;
        }
        .promo-card img,
        .promo-card .menu-image {
            width: 100%;
            aspect-ratio: 5 / 3;
            object-fit: cover;
            border: 0;
            border-radius: 0;
        }
        .promo-card-body {
            display: grid;
            gap: .35rem;
            padding: .8rem;
        }
        .menu-card-body {
            display: grid;
            gap: .45rem;
            min-height: 8rem;
        }
        .menu-card-actions {
            display: grid;
            gap: .55rem;
            padding-top: .2rem;
        }
        .cart-card {
            display: grid;
            grid-template-columns: 5.5rem minmax(0, 1fr);
            gap: .85rem;
            align-items: center;
        }
        .cart-thumb {
            width: 5.5rem;
            height: 5.5rem;
            object-fit: cover;
            border-radius: 8px;
            border: 1px solid var(--line);
            background: #f3eadc;
        }
        .cart-thumb-placeholder {
            display: grid;
            place-items: center;
            color: var(--muted);
            font-weight: 800;
        }
        .stat-strip {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: .85rem;
            margin: .9rem 0 1.25rem;
        }
        .stat-tile {
            border: 1px solid rgba(14, 89, 103, .12);
            background: rgba(255, 253, 248, .88);
            border-radius: 8px;
            padding: .9rem 1rem;
        }
        .stat-tile strong {
            display: block;
            color: var(--brand-dark);
            font-size: 1.35rem;
            line-height: 1.15;
        }
        .stat-tile span {
            color: var(--muted);
            font-size: .88rem;
        }
        .menu-title {
            font-weight: 800;
            color: var(--brand-dark);
            font-size: 1.04rem;
        }
        .price {
            color: var(--brand);
            font-weight: 800;
        }
        .pill {
            display: inline-flex;
            align-items: center;
            border-radius: 999px;
            padding: .22rem .6rem;
            font-size: .78rem;
            font-weight: 800;
            background: rgba(15, 76, 92, .1);
            color: var(--brand);
        }
        .pill-new { background: #fff0c2; color: #8a5a00; }
        .pill-preparing { background: #dbeafe; color: #1d4ed8; }
        .pill-ready { background: #dcfce7; color: #166534; }
        .pill-cancelled { background: #fee2e2; color: #991b1b; }
        .stButton > button, .stDownloadButton > button {
            border-radius: 8px;
            font-weight: 750;
            border: 1px solid rgba(15, 76, 92, .18);
        }
        .stButton > button[kind="primary"] {
            background: var(--brand);
            border-color: var(--brand);
        }
        .stTextInput input, .stTextArea textarea, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {
            border-radius: 8px;
        }
        .checkout-shell {
            margin-top: .4rem;
        }
        .checkout-shell h1 {
            font-size: clamp(2.25rem, 4vw, 3rem);
            margin-bottom: .25rem;
        }
        .segment-label {
            margin: 1.4rem 0 .55rem;
            font-weight: 700;
        }
        .checkout-form-card {
            border: 1px solid var(--line);
            background: rgba(255, 253, 248, .72);
            border-radius: 8px;
            padding: 1.45rem 1.3rem;
            box-shadow: 0 14px 36px rgba(52, 39, 23, .05);
        }
        .checkout-form-card h2 {
            margin-top: 0;
            font-size: 1.85rem;
        }
        .admin-hero {
            border-radius: 8px;
            padding: 1.35rem 1.45rem;
            margin-bottom: 1rem;
            color: #fffaf1;
            background:
                linear-gradient(135deg, rgba(14, 89, 103, .96), rgba(212, 111, 44, .82)),
                #0e5967;
            box-shadow: 0 22px 54px rgba(52, 39, 23, .14);
        }
        .admin-hero h1 {
            margin: 0 0 .35rem;
            color: #fffaf1;
            font-size: clamp(2rem, 4vw, 3.1rem);
        }
        .admin-hero p {
            margin: 0;
            color: rgba(255, 250, 241, .86);
            font-size: 1.05rem;
        }
        .admin-stat-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: .85rem;
            margin: 1rem 0 1.25rem;
        }
        .admin-stat-card {
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 1rem;
            background: rgba(255, 253, 248, .96);
            box-shadow: 0 16px 38px rgba(52, 39, 23, .08);
            border-top: 5px solid var(--brand);
        }
        .admin-stat-card.is-new { border-top-color: #d46f2c; }
        .admin-stat-card.is-ready { border-top-color: #167a4a; }
        .admin-stat-card.is-sales { border-top-color: #7c3aed; }
        .admin-stat-card span {
            display: block;
            color: var(--muted);
            font-size: .86rem;
            font-weight: 700;
        }
        .admin-stat-card strong {
            display: block;
            margin-top: .25rem;
            color: var(--brand-dark);
            font-size: 1.65rem;
        }
        .admin-panel {
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 1rem;
            background: rgba(255, 253, 248, .66);
            box-shadow: 0 14px 36px rgba(52, 39, 23, .05);
        }
        div[data-testid="stImage"] img {
            border-radius: 8px;
            border: 1px solid var(--line);
            aspect-ratio: 4 / 3;
            object-fit: cover;
        }
        [data-testid="stRadio"] > div {
            gap: .5rem;
        }
        @media (max-width: 760px) {
            .topbar { position: static; align-items: flex-start; flex-direction: column; }
            .admin-stat-grid { grid-template-columns: 1fr 1fr; }
            .stat-strip { grid-template-columns: 1fr; }
            .cart-card { grid-template-columns: 4.75rem minmax(0, 1fr); }
            .cart-thumb { width: 4.75rem; height: 4.75rem; }
            .block-container { padding-left: .9rem; padding-right: .9rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def status_class(status: str) -> str:
    if status == "NEW":
        return "pill-new"
    if status == "PREPARING":
        return "pill-preparing"
    if status in {"READY_FOR_PICKUP", "OUT_FOR_DELIVERY", "COMPLETED"}:
        return "pill-ready"
    if status == "CANCELLED":
        return "pill-cancelled"
    return ""


def render_order(order: dict[str, Any], admin: bool = False) -> None:
    items = get_order_items(order["id"])
    st.markdown(
        f"""
        <div class="order-card">
          <div style="display:flex;justify-content:space-between;gap:1rem;align-items:flex-start;flex-wrap:wrap;">
            <div>
              <div class="menu-title">{escape(order["orderNumber"])}</div>
              <div class="muted">{escape(order["customerName"])} - {escape(order["customerPhone"])}</div>
              <div class="muted">{escape(order["fulfillmentType"].title())} - {escape(order["createdAt"])}</div>
            </div>
            <div style="text-align:right;">
              <span class="pill {status_class(order["status"])}">{escape(STATUS_LABELS.get(order["status"], order["status"]))}</span>
              <div class="price" style="margin-top:.35rem;">{money(order["totalTala"])}</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("Order details", expanded=admin and order["status"] == "NEW"):
        for item in items:
            st.write(
                f"{item['quantity']} x {item['itemNameSnapshot']} - "
                f"{money(item['lineTotalTala'])}"
            )
        if order["deliveryAddress"]:
            st.info(f"Delivery location: {order['deliveryAddress']}")
        if order["notes"]:
            st.caption(f"Notes: {order['notes']}")


def render_promo_strip(menu: list[dict[str, Any]]) -> None:
    items = promoted_menu_items(menu)
    if not items:
        return

    cards = []
    for item in items:
        path = image_path(item["imageUrl"])
        image_markup = (
            f'<img src="{image_data_uri(str(path))}" alt="{escape(item["name"])}">'
            if path
            else f'<div class="menu-image"><div><span class="menu-image-title">{escape(item["name"])}</span><span class="menu-image-subtitle">Photo coming soon</span></div></div>'
        )
        badges = "".join(
            f'<span class="menu-badge {badge_class(badge)}">{escape(badge)}</span>'
            for badge in item.get("promoBadges", [])
        )
        cards.append(
            f"""
            <div class="promo-card">
              {image_markup}
              <div class="promo-card-body">
                <div class="menu-badge-row">{badges}</div>
                <div class="menu-title">{escape(item["name"])}</div>
                <div class="price">{money(item["priceTala"])}</div>
              </div>
            </div>
            """
        )

    st.subheader("Featured, New & Specials")
    st.markdown(f'<div class="promo-strip">{"".join(cards)}</div>', unsafe_allow_html=True)


def render_menu() -> None:
    st.markdown(
        """
        <div class="hero">
          <h1>Order waterfront favorites without the wait.</h1>
          <p>Browse the menu, choose delivery or self pickup, and get an order number you can track from your phone.</p>
          <div class="stat-strip">
            <div class="stat-tile"><strong>Cash</strong><span>Pay when your order arrives</span></div>
            <div class="stat-tile"><strong>2 tala</strong><span>Flat delivery fee</span></div>
            <div class="stat-tile"><strong>{cart_count}</strong><span>Items currently in cart</span></div>
          </div>
        </div>
        """.format(cart_count=cart_count()),
        unsafe_allow_html=True,
    )

    menu = get_menu()
    if not menu:
        st.warning("No active menu categories found. Add menu items in Admin.")
        return

    render_promo_strip(menu)

    best_seller_ids = set(get_best_seller_ids())
    for category in menu:
        if not category["items"]:
            continue
        st.subheader(category["name"])
        columns = st.columns(2)
        for index, item in enumerate(category["items"]):
            with columns[index % 2]:
                with st.container(border=True):
                    path = image_path(item["imageUrl"])
                    image_markup = (
                        f'<img src="{image_data_uri(str(path))}" alt="{escape(item["name"])}">'
                        if path
                        else f'<div class="menu-image"><div><span class="menu-image-title">{escape(item["name"])}</span><span class="menu-image-subtitle">Photo coming soon</span></div></div>'
                    )
                    badge_labels = promotion_badges(item, best_seller_ids)
                    badge_markup = "".join(
                        f'<span class="menu-badge {badge_class(label)}">{escape(label)}</span>'
                        for label in badge_labels[:3]
                    )
                    availability_badge = (
                        '<span class="menu-badge">Available today</span>'
                        if item["isAvailable"]
                        else '<span class="menu-badge is-unavailable">Unavailable</span>'
                    )
                    st.markdown(
                        f"""
                        <div class="menu-card">
                          <div class="menu-card-media">{image_markup}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f"""
                        <div class="menu-badge-row">
                          {availability_badge}
                          <span class="menu-badge is-price">{money(item["priceTala"])}</span>
                          {badge_markup}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    st.markdown(f"### {item['name']}")
                    if item["description"]:
                        st.write(item["description"])

                    if not item["isAvailable"]:
                        continue

                    option_id = None
                    if item["options"]:
                        option_choices = {option["id"]: f"{option['name']} - {money(option['priceTala'])}" for option in item["options"]}
                        option_id = st.selectbox(
                            "Choose option",
                            list(option_choices.keys()),
                            format_func=lambda option_key, choices=option_choices: choices[option_key],
                            key=f"option-{item['id']}",
                        )

                    quantity = st.number_input(
                        "Qty",
                        min_value=1,
                        max_value=50,
                        value=1,
                        step=1,
                        key=f"qty-{item['id']}",
                    )
                    if st.button("Add to cart", key=f"add-{item['id']}", type="primary", use_container_width=True):
                        add_to_cart(item, int(quantity), option_id)
                        st.rerun()


def render_checkout() -> None:
    st.markdown('<div class="checkout-shell"><h1>Checkout</h1></div>', unsafe_allow_html=True)
    if not st.session_state.cart:
        st.info("Your cart is empty. Add items from Order first.")

    st.markdown('<div class="segment-label">Order type</div>', unsafe_allow_html=True)
    delivery_col, pickup_col, _ = st.columns([0.12, 0.14, 0.74])
    with delivery_col:
        if st.button(
            "Delivery",
            type="primary" if st.session_state.fulfillment_type == "DELIVERY" else "secondary",
            use_container_width=True,
        ):
            st.session_state.fulfillment_type = "DELIVERY"
            st.rerun()
    with pickup_col:
        if st.button(
            "Self pickup",
            type="primary" if st.session_state.fulfillment_type == "PICKUP" else "secondary",
            use_container_width=True,
        ):
            st.session_state.fulfillment_type = "PICKUP"
            st.rerun()

    subtotal, delivery_fee, total = cart_total()
    left, right = st.columns([1.2, 0.8])

    with left:
        st.markdown('<div class="checkout-form-card">', unsafe_allow_html=True)
        with st.form("checkout-form", clear_on_submit=False):
            st.markdown("<h2>Customer details</h2>", unsafe_allow_html=True)
            name = st.text_input("Name")
            phone = st.text_input("Phone number")
            address = ""
            if st.session_state.fulfillment_type == "DELIVERY":
                address = st.text_area("Delivery location / address")
                st.caption("A fixed 2 tala delivery fee is added to delivery orders.")
            notes = st.text_area("Notes for the kitchen or driver", placeholder="Optional")
            submitted = st.form_submit_button("Confirm order", type="primary", use_container_width=True)

        if submitted:
            message = validate_order(name, phone, address)
            if message:
                st.error(message)
            else:
                try:
                    order_number = create_order(name, phone, address, notes)
                    st.success(f"Order placed. Your order number is {order_number}.")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.subheader("Your cart")
        if not st.session_state.cart:
            st.info("Your cart is empty. Add items from the Menu tab.")
        for index, item in enumerate(list(st.session_state.cart)):
            thumb_path = image_path(item.get("image_url"))
            thumb_markup = (
                f'<img class="cart-thumb" src="{image_data_uri(str(thumb_path))}" alt="{escape(item["name"])}">'
                if thumb_path
                else '<div class="cart-thumb cart-thumb-placeholder">WF</div>'
            )
            st.markdown(
                f"""
                <div class="cart-card">
                  {thumb_markup}
                  <div>
                    <div class="menu-title">{escape(item["name"])}</div>
                    <div class="muted">{money(item["unit_price"])} each</div>
                    <div class="price">{money(float(item["unit_price"]) * int(item["quantity"]))}</div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            quantity = st.number_input(
                "Quantity",
                min_value=1,
                max_value=50,
                value=int(item["quantity"]),
                key=f"cart-qty-{index}-{item['cart_key']}",
            )
            st.session_state.cart[index]["quantity"] = int(quantity)
            if st.button("Remove", key=f"remove-{index}-{item['cart_key']}"):
                st.session_state.cart.pop(index)
                st.rerun()

        st.divider()
        st.write(f"Subtotal: **{money(subtotal)}**")
        st.write(f"Delivery fee: **{money(delivery_fee)}**")
        st.write(f"Total: **{money(total)}**")
        st.caption("Payment method: Cash")

        if st.session_state.last_order_number:
            st.success(f"Last order: {st.session_state.last_order_number}")


def render_track_order() -> None:
    st.header("Track an order")
    st.caption("Search by order number for the exact order, or by phone number for recent orders.")
    col_a, col_b = st.columns(2)
    with col_a:
        order_number = st.text_input("Order number", placeholder="ORD-260714-1234")
    with col_b:
        phone = st.text_input("Phone number")

    if st.button("Search orders", type="primary"):
        st.session_state.tracked_orders = find_orders(phone=phone, order_number=order_number)

    orders = st.session_state.get("tracked_orders", [])
    if orders:
        for order in orders:
            render_order(order)
    elif "tracked_orders" in st.session_state:
        st.warning("No matching orders found.")


def render_admin_login() -> bool:
    if st.session_state.admin_authenticated:
        return True

    st.markdown(
        """
        <div class="hero">
          <h1>Admin login</h1>
          <p>Staff access for live orders, order status updates, and menu availability.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    left, right = st.columns([0.8, 1.2])
    with left:
        password = st.text_input("Admin password", type="password")
        if st.button("Unlock admin", type="primary", use_container_width=True):
            if password == ADMIN_PASSWORD:
                st.session_state.admin_authenticated = True
                st.session_state.view = "Admin"
                st.rerun()
            else:
                st.error("Incorrect admin password.")
        st.caption("Default password is admin123. Set STREAMLIT_ADMIN_PASSWORD before launch.")
    with right:
        st.info("Customers do not see the admin dashboard. It only appears after staff login.")
    return False


def render_admin_orders() -> None:
    orders = get_recent_orders()
    active = [order for order in orders if order["status"] in ACTIVE_STATUSES]

    st.download_button(
        "Download recent orders CSV",
        data=order_csv(orders),
        file_name=f"waterfront-orders-{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
    )

    status_filter = st.selectbox(
        "Filter",
        ["ACTIVE", "ALL", *STATUS_LABELS.keys()],
        format_func=lambda value: "Active orders" if value == "ACTIVE" else STATUS_LABELS.get(value, value.title()),
    )
    if status_filter == "ACTIVE":
        visible_orders = active
    elif status_filter == "ALL":
        visible_orders = orders
    else:
        visible_orders = [order for order in orders if order["status"] == status_filter]

    if not visible_orders:
        st.info("No orders in this view.")
        return

    for order in visible_orders:
        render_order(order, admin=True)
        next_statuses = list(STATUS_LABELS.keys())
        selected_status = st.selectbox(
            "Set status",
            next_statuses,
            index=next_statuses.index(order["status"]),
            format_func=lambda value: STATUS_LABELS[value],
            key=f"status-{order['id']}",
        )
        if st.button("Update status", key=f"update-{order['id']}"):
            update_order_status(order["id"], selected_status)
            st.success(f"Updated {order['orderNumber']} to {STATUS_LABELS[selected_status]}.")
            st.rerun()


def render_admin_menu() -> None:
    st.subheader("Menu availability")
    for category in get_menu():
        st.write(f"**{category['name']}**")
        for item in category["items"]:
            current = bool(item["isAvailable"])
            updated = st.toggle(
                f"{item['name']} available",
                value=current,
                key=f"available-{item['id']}",
            )
            if updated != current:
                update_item_availability(item["id"], updated)
                st.rerun()
            active_badges = promotion_badges(item, set(get_best_seller_ids()))
            summary = ", ".join(active_badges) if active_badges else "No active badges"
            with st.expander(f"Promotions for {item['name']} - {summary}"):
                with st.form(f"promo-form-{item['id']}"):
                    promo_col_a, promo_col_b, promo_col_c = st.columns(3)
                    with promo_col_a:
                        is_featured = st.checkbox(
                            "Featured",
                            value=bool(item.get("isFeatured")),
                            key=f"featured-{item['id']}",
                        )
                    with promo_col_b:
                        is_new = st.checkbox(
                            "New item",
                            value=bool(item.get("isNew")),
                            key=f"is-new-{item['id']}",
                        )
                        new_until = st.date_input(
                            "Show as new until",
                            value=parse_iso_date(item.get("newUntil"), 7),
                            key=f"new-until-{item['id']}",
                        )
                    with promo_col_c:
                        is_special = st.checkbox(
                            "Special",
                            value=bool(item.get("isSpecial")),
                            key=f"is-special-{item['id']}",
                        )
                        special_label = st.text_input(
                            "Special badge text",
                            value=item.get("specialLabel") or "Special",
                            key=f"special-label-{item['id']}",
                        )
                        special_until = st.date_input(
                            "Show special until",
                            value=parse_iso_date(item.get("specialUntil"), 7),
                            key=f"special-until-{item['id']}",
                        )
                    if st.form_submit_button("Save promotions", type="primary"):
                        update_item_promotions(
                            item["id"],
                            is_featured,
                            is_new,
                            new_until.isoformat(),
                            is_special,
                            special_label,
                            special_until.isoformat(),
                        )
                        st.success("Promotions saved.")
                        st.rerun()

    st.divider()
    st.subheader("Add category")
    with st.form("add-category"):
        category_name = st.text_input("Category name")
        if st.form_submit_button("Add category"):
            add_category(category_name)
            st.success("Category saved.")
            st.rerun()

    st.subheader("Add menu item")
    categories = get_categories()
    if not categories:
        st.info("Add a category before adding menu items.")
        return

    category_lookup = {category["id"]: category["name"] for category in categories}
    with st.form("add-menu-item"):
        category_id = st.selectbox(
            "Category",
            list(category_lookup.keys()),
            format_func=lambda key: category_lookup[key],
        )
        name = st.text_input("Item name")
        description = st.text_area("Description")
        price = st.number_input("Price in tala", min_value=0.01, value=10.0, step=0.5)
        image_url = st.text_input("Image URL", placeholder="/uploads/menu/example.jpg")
        if st.form_submit_button("Add item", type="primary"):
            if not name.strip():
                st.error("Item name is required.")
            else:
                add_menu_item(category_id, name, description, price, image_url)
                st.success("Menu item added.")
                st.rerun()


def render_admin() -> None:
    if not render_admin_login():
        return

    orders = get_recent_orders()
    active = [order for order in orders if order["status"] in ACTIVE_STATUSES]
    new_count = sum(1 for order in orders if order["status"] == "NEW")
    ready_count = sum(1 for order in orders if order["status"] in {"READY_FOR_PICKUP", "OUT_FOR_DELIVERY"})
    today_total = sum(float(order["totalTala"]) for order in orders if str(order["createdAt"])[:10] == now_value()[:10])

    st.markdown(
        f"""
        <div class="admin-hero">
          <h1>Admin dashboard</h1>
          <p>Live order control room for Waterfront staff and kitchen prep.</p>
        </div>
        <div class="admin-stat-grid">
          <div class="admin-stat-card"><span>Active orders</span><strong>{len(active)}</strong></div>
          <div class="admin-stat-card is-new"><span>New orders</span><strong>{new_count}</strong></div>
          <div class="admin-stat-card is-ready"><span>Ready / on the way</span><strong>{ready_count}</strong></div>
          <div class="admin-stat-card is-sales"><span>Today's sales</span><strong>{money(today_total)}</strong></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_action, col_logout, _ = st.columns([0.18, 0.18, 0.64])
    with col_action:
        if st.button("Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    with col_logout:
        if st.button("Log out", use_container_width=True):
            st.session_state.admin_authenticated = False
            st.session_state.view = "Order"
            st.rerun()

    st.markdown('<div class="admin-panel">', unsafe_allow_html=True)
    tab_orders, tab_menu = st.tabs(["Live orders", "Menu"])
    with tab_orders:
        render_admin_orders()
    with tab_menu:
        render_admin_menu()
    st.markdown("</div>", unsafe_allow_html=True)


def render_topbar() -> None:
    subtotal, _, total = cart_total()
    st.markdown(
        f"""
        <div class="topbar">
          <div class="brand-lockup">
            <span class="brand-kicker">Waterfront</span>
            <span class="brand-title">Restaurant Orders</span>
          </div>
          <div class="nav-card">
            <strong>{cart_count()} item(s)</strong> - {money(total)}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_navigation() -> str:
    admin_label = "Admin dashboard" if st.session_state.admin_authenticated else "Staff login"
    nav_items = [
        ("Order", "Order"),
        ("Checkout", f"Checkout ({cart_count()})"),
        ("Track", "Track"),
        ("Admin", admin_label),
    ]
    st.markdown('<div class="nav-spacer"></div>', unsafe_allow_html=True)
    columns = st.columns([0.11, 0.15, 0.11, 0.16, 0.47])
    for column, (view, label) in zip(columns, nav_items):
        with column:
            if st.button(
                label,
                key=f"nav-{view}",
                type="primary" if st.session_state.view == view else "secondary",
                use_container_width=True,
            ):
                st.session_state.view = view
                st.rerun()
    return st.session_state.view


def main() -> None:
    st.set_page_config(
        page_title="Waterfront Orders",
        page_icon="WF",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    ensure_state()
    render_css()
    if st.session_state.cart_notice:
        st.toast(st.session_state.cart_notice)
        st.session_state.cart_notice = ""
    if st.session_state.view == "Admin" and st.session_state.admin_authenticated:
        render_admin()
        return
    render_topbar()
    view = render_navigation()

    if view == "Order":
        render_menu()
    elif view == "Checkout":
        render_checkout()
    elif view == "Track":
        render_track_order()
    elif view == "Admin":
        render_admin()


if __name__ == "__main__":
    main()

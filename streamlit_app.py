from __future__ import annotations

import csv
import hashlib
import hmac
import html
import os
import random
import sqlite3
from datetime import datetime, timedelta
from io import StringIO
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import streamlit as st


APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "prisma" / "dev.db"
PUBLIC_DIR = APP_DIR / "public"
ASSETS_DIR = APP_DIR / "assets"
LOGO_PATH = ASSETS_DIR / "waterfront_logo.png"
DELIVERY_FEE_TALA = 2.0
SAMOA_TZ = ZoneInfo("Pacific/Apia")
BUSINESS_NAME = "Waterfront Snack Bar"
SYSTEM_NAME = "Waterfront Business Manager"
DEFAULT_ADMIN_USERNAME = "admin"

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
    if DB_PATH.exists():
        return

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
    return datetime.now(SAMOA_TZ).isoformat(timespec="seconds")


def money(value: float | int | str | None) -> str:
    return f"SAT ${float(value or 0):,.2f}"


def business_today() -> str:
    return datetime.now(SAMOA_TZ).date().isoformat()


def escape(value: Any) -> str:
    return html.escape(str(value or ""))


def get_secret_value(section: str, key: str, default: str = "") -> str:
    try:
        value = st.secrets.get(section, {}).get(key, default)
        return str(value) if value is not None else default
    except Exception:
        return default


def get_admin_credentials() -> tuple[str, str, str]:
    username = (
        get_secret_value("admin", "username")
        or os.getenv("STREAMLIT_ADMIN_USERNAME")
        or DEFAULT_ADMIN_USERNAME
    )
    password_hash = get_secret_value("admin", "password_hash") or os.getenv("STREAMLIT_ADMIN_PASSWORD_HASH", "")
    password = get_secret_value("admin", "password") or os.getenv("STREAMLIT_ADMIN_PASSWORD", "admin123")
    return username, password_hash, password


def verify_password(password: str, password_hash: str, fallback_password: str) -> bool:
    if password_hash:
        if password_hash.startswith("sha256$"):
            expected = password_hash.split("sha256$", 1)[1]
            actual = hashlib.sha256(password.encode("utf-8")).hexdigest()
            return hmac.compare_digest(actual, expected)
        if password_hash.startswith("pbkdf2_sha256$"):
            try:
                _, iterations, salt, expected = password_hash.split("$", 3)
                actual = hashlib.pbkdf2_hmac(
                    "sha256",
                    password.encode("utf-8"),
                    salt.encode("utf-8"),
                    int(iterations),
                ).hex()
                return hmac.compare_digest(actual, expected)
            except ValueError:
                return False
        actual = hashlib.sha256(password.encode("utf-8")).hexdigest()
        return hmac.compare_digest(actual, password_hash)
    return hmac.compare_digest(password, fallback_password)


def verify_admin_login(username: str, password: str) -> bool:
    saved_username, password_hash, fallback_password = get_admin_credentials()
    return hmac.compare_digest(username.strip(), saved_username) and verify_password(
        password,
        password_hash,
        fallback_password,
    )


def require_admin() -> None:
    if not st.session_state.get("admin_authenticated", False):
        st.warning("Administrator login is required.")
        st.session_state.current_area = "public"
        st.stop()


def generate_order_number() -> str:
    stamp = datetime.now(SAMOA_TZ).strftime("%y%m%d")
    return f"ORD-{stamp}-{random.randint(1000, 9999)}"


def image_path(image_url: str | None) -> Path | None:
    if not image_url or not image_url.startswith("/"):
        return None
    candidate = PUBLIC_DIR / image_url.lstrip("/")
    return candidate if candidate.exists() else None


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
                SELECT id, categoryId, name, description, priceTala, imageUrl, isAvailable
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
            st.toast(f"Updated {name} in cart")
            return

    st.session_state.cart.append(
        {
            "cart_key": cart_key,
            "menu_item_id": item["id"],
            "option_id": option_id,
            "name": name,
            "unit_price": unit_price,
            "quantity": quantity,
        }
    )
    st.toast(f"Added {name}")


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
    require_admin()
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
    require_admin()
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


def add_category(name: str) -> None:
    require_admin()
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
    require_admin()
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
    st.session_state.setdefault("current_area", "public")
    st.session_state.setdefault("public_page", "Home")
    st.session_state.setdefault("admin_page", "Dashboard")


def render_css(show_admin_sidebar: bool = False) -> None:
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
        section[data-testid="stSidebar"] {
            display: __SIDEBAR_DISPLAY__;
            background: #fffaf1;
            border-right: 1px solid var(--line);
        }
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
            padding: .8rem 0 1rem;
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
            font-size: 1.35rem;
        }
        .nav-card {
            border: 1px solid var(--line);
            background: rgba(255, 253, 248, .86);
            border-radius: 8px;
            padding: .35rem .55rem;
            box-shadow: 0 10px 24px rgba(52, 39, 23, .05);
        }
        .menu-card, .order-card, .cart-card {
            border: 1px solid var(--line);
            background: rgba(255, 253, 248, .95);
            border-radius: 8px;
            padding: 1rem;
            box-shadow: 0 14px 34px rgba(52, 39, 23, .07);
            margin-bottom: .8rem;
        }
        .menu-card {
            min-height: 9.5rem;
            display: grid;
            align-content: start;
            gap: .45rem;
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
        .kitchen-card {
            border: 1px solid var(--line);
            background: rgba(255, 253, 248, .98);
            border-radius: 8px;
            padding: .9rem;
            box-shadow: 0 14px 30px rgba(52, 39, 23, .08);
            margin-bottom: .8rem;
        }
        .kitchen-head {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: .65rem;
            margin-bottom: .55rem;
        }
        .order-number {
            font-size: 1.05rem;
            font-weight: 900;
            color: var(--brand-dark);
        }
        .kitchen-meta {
            display: flex;
            flex-wrap: wrap;
            gap: .45rem;
            color: var(--muted);
            font-size: .84rem;
            margin-bottom: .55rem;
        }
        .kitchen-items {
            margin: .5rem 0 .65rem 1.1rem;
            padding: 0;
        }
        .kitchen-items li {
            margin-bottom: .25rem;
            font-size: .96rem;
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
            .stat-strip { grid-template-columns: 1fr; }
            .block-container { padding-left: .9rem; padding-right: .9rem; }
        }
        </style>
        """.replace("__SIDEBAR_DISPLAY__", "block" if show_admin_sidebar else "none"),
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


def render_kitchen_order_card(order: dict[str, Any]) -> None:
    items = get_order_items(order["id"])
    item_lines = "".join(
        f"<li><strong>{int(item['quantity'])}x</strong> {escape(item['itemNameSnapshot'])}</li>"
        for item in items
    )
    fulfilment = "Delivery" if order["fulfillmentType"] == "DELIVERY" else "Pickup"
    address = f"<p><strong>Location:</strong> {escape(order['deliveryAddress'])}</p>" if order["deliveryAddress"] else ""
    notes = f"<p><strong>Notes:</strong> {escape(order['notes'])}</p>" if order["notes"] else ""
    st.markdown(
        f"""
        <div class="kitchen-card">
          <div class="kitchen-head">
            <div>
              <div class="order-number">{escape(order["orderNumber"])}</div>
              <div class="muted">{escape(order["customerName"])} - {escape(order["customerPhone"])}</div>
            </div>
            <span class="pill {status_class(order["status"])}">{escape(STATUS_LABELS.get(order["status"], order["status"]))}</span>
          </div>
          <div class="kitchen-meta">
            <span>{escape(fulfilment)}</span>
            <span>{money(order["totalTala"])}</span>
            <span>{escape(order["createdAt"])}</span>
          </div>
          <ul class="kitchen-items">{item_lines}</ul>
          {address}
          {notes}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_admin_order_board(orders: list[dict[str, Any]]) -> None:
    st.subheader("Kitchen order board")
    st.caption("New and active orders are grouped for quick kitchen/admin handling.")
    lanes = [
        ("NEW", "New"),
        ("PREPARING", "Preparing"),
        ("READY_FOR_PICKUP", "Ready / Pickup"),
        ("OUT_FOR_DELIVERY", "Out for Delivery"),
    ]
    columns = st.columns(len(lanes))
    for column, (status, label) in zip(columns, lanes):
        with column:
            lane_orders = [order for order in orders if order["status"] == status]
            st.markdown(f"#### {label} ({len(lane_orders)})")
            if not lane_orders:
                st.info("No orders")
            for order in lane_orders:
                render_kitchen_order_card(order)
                next_statuses = list(STATUS_LABELS.keys())
                selected_status = st.selectbox(
                    "Move order",
                    next_statuses,
                    index=next_statuses.index(order["status"]),
                    format_func=lambda value: STATUS_LABELS[value],
                    key=f"board-status-{order['id']}",
                )
                if st.button("Update", key=f"board-update-{order['id']}", use_container_width=True):
                    update_order_status(order["id"], selected_status)
                    st.rerun()


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

    for category in menu:
        if not category["items"]:
            continue
        st.subheader(category["name"])
        columns = st.columns(2)
        for index, item in enumerate(category["items"]):
            with columns[index % 2]:
                path = image_path(item["imageUrl"])
                if path:
                    st.image(str(path), use_container_width=True)
                st.markdown(
                    f"""
                    <div class="menu-card">
                      <div class="menu-title">{escape(item["name"])}</div>
                      <div class="muted">{escape(item["description"])}</div>
                      <div class="price">{money(item["priceTala"])}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                if not item["isAvailable"]:
                    st.warning("Currently unavailable")
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
    st.header("Checkout")
    if not st.session_state.cart:
        st.info("Your cart is empty. Add items from Order first.")

    st.session_state.fulfillment_type = st.radio(
        "Order type",
        ["DELIVERY", "PICKUP"],
        format_func=lambda value: "Delivery" if value == "DELIVERY" else "Self pickup",
        horizontal=True,
        index=0 if st.session_state.fulfillment_type == "DELIVERY" else 1,
    )

    subtotal, delivery_fee, total = cart_total()
    left, right = st.columns([1.2, 0.8])

    with left:
        with st.form("checkout-form", clear_on_submit=False):
            st.subheader("Customer details")
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

    with right:
        st.subheader("Your cart")
        if not st.session_state.cart:
            st.info("Your cart is empty. Add items from the Menu tab.")
        for index, item in enumerate(list(st.session_state.cart)):
            st.markdown(
                f"""
                <div class="cart-card">
                  <div class="menu-title">{escape(item["name"])}</div>
                  <div class="muted">{money(item["unit_price"])} each</div>
                  <div class="price">{money(float(item["unit_price"]) * int(item["quantity"]))}</div>
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
        with st.form("admin-login-form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Unlock admin", type="primary", use_container_width=True)
        if submitted:
            if verify_admin_login(username, password):
                st.session_state.admin_authenticated = True
                st.session_state.current_area = "admin"
                st.session_state.admin_page = "Dashboard"
                st.rerun()
            else:
                st.error("Incorrect administrator login details.")
        st.caption("Set admin credentials in Streamlit Secrets before launch.")
    with right:
        st.info("Customers do not see the admin dashboard. It only appears after staff login.")
        if st.button("Return to customer site", use_container_width=True):
            st.session_state.current_area = "public"
            st.session_state.public_page = "Home"
            st.rerun()
    return False


def render_admin_orders() -> None:
    require_admin()
    orders = get_recent_orders()
    active = [order for order in orders if order["status"] in ACTIVE_STATUSES]
    new_count = sum(1 for order in orders if order["status"] == "NEW")
    today_total = sum(float(order["totalTala"]) for order in orders if str(order["createdAt"])[:10] == business_today())

    c1, c2, c3 = st.columns(3)
    c1.metric("Active orders", len(active))
    c2.metric("New orders", new_count)
    c3.metric("Today's sales", money(today_total))

    render_admin_order_board(active)

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
    require_admin()
    st.subheader("Menu availability")
    for category in get_menu():
        st.write(f"**{category['name']}**")
        for item in category["items"]:
            current = bool(item["isAvailable"])
            updated = st.toggle(
                item["name"],
                value=current,
                key=f"available-{item['id']}",
            )
            if updated != current:
                update_item_availability(item["id"], updated)
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


def render_admin_sidebar() -> str:
    require_admin()
    with st.sidebar:
        if LOGO_PATH.exists():
            st.image(str(LOGO_PATH), use_container_width=True)
        else:
            st.markdown(f"## {BUSINESS_NAME}")
        st.caption(SYSTEM_NAME)
        st.divider()
        pages = [
            "Dashboard",
            "Live Orders",
            "Menu Management",
            "Reports",
            "Settings",
        ]
        selected = st.radio(
            "Admin navigation",
            pages,
            index=pages.index(st.session_state.admin_page)
            if st.session_state.admin_page in pages
            else 0,
        )
        st.session_state.admin_page = selected
        st.divider()
        if st.button("Logout", use_container_width=True):
            st.session_state.admin_authenticated = False
            st.session_state.current_area = "public"
            st.session_state.public_page = "Home"
            st.session_state.admin_page = "Dashboard"
            st.rerun()
    return st.session_state.admin_page


def render_admin_dashboard() -> None:
    require_admin()
    orders = get_recent_orders()
    active = [order for order in orders if order["status"] in ACTIVE_STATUSES]
    today_orders = [order for order in orders if str(order["createdAt"])[:10] == business_today()]
    today_sales = sum(float(order["totalTala"]) for order in today_orders)
    completed = sum(1 for order in today_orders if order["status"] == "COMPLETED")
    cancelled = sum(1 for order in today_orders if order["status"] == "CANCELLED")

    col_title, col_action, col_logout = st.columns([1.4, .55, .45])
    with col_title:
        st.header("Waterfront Business Overview")
        st.caption("Samoa business date: " + business_today())
    with col_action:
        if st.button("Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    with col_logout:
        if st.button("Log out", use_container_width=True):
            st.session_state.admin_authenticated = False
            st.session_state.current_area = "public"
            st.session_state.public_page = "Home"
            st.session_state.admin_page = "Dashboard"
            st.rerun()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Today's sales", money(today_sales))
    c2.metric("Active orders", len(active))
    c3.metric("Completed today", completed)
    c4.metric("Cancelled today", cancelled)

    if not orders:
        st.info("No orders yet. New customer orders will appear here.")
    else:
        render_admin_order_board(active)


def render_reports_page() -> None:
    require_admin()
    st.header("Order Reports")
    st.caption("Download and review order records from the current ordering database.")
    orders = get_recent_orders(500)
    st.download_button(
        "Download customer orders CSV",
        data=order_csv(orders),
        file_name=f"waterfront-orders-{business_today()}.csv",
        mime="text/csv",
    )
    if orders:
        status_counts: dict[str, int] = {}
        for order in orders:
            status_counts[STATUS_LABELS.get(order["status"], order["status"])] = status_counts.get(
                STATUS_LABELS.get(order["status"], order["status"]),
                0,
            ) + 1
        st.bar_chart(status_counts)
    else:
        st.info("No report data yet.")


def render_settings_page() -> None:
    require_admin()
    st.header("Settings")
    st.write(f"Business name: **{BUSINESS_NAME}**")
    st.write("Currency: **SAT**")
    st.write("Timezone: **Pacific/Apia**")
    st.write(f"Logo path: `{LOGO_PATH}`")
    st.info("This version uses the existing SQLite ordering database. Secrets are configured server-side and are not displayed here.")


def render_admin() -> None:
    require_admin()
    page = render_admin_sidebar()
    if page == "Dashboard":
        render_admin_dashboard()
    elif page == "Live Orders":
        render_admin_orders()
    elif page == "Menu Management":
        render_admin_menu()
    elif page == "Reports":
        render_reports_page()
    elif page == "Settings":
        render_settings_page()


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


def render_home() -> None:
    st.markdown(
        """
        <div class="hero">
          <h1>Fresh orders, simple pickup, easy delivery.</h1>
          <p>Waterfront Restaurant Orders lets customers browse the menu, build a cart, and place a cash order in minutes.</p>
          <div class="stat-strip">
            <div class="stat-tile"><strong>1</strong><span>Pick menu items</span></div>
            <div class="stat-tile"><strong>2</strong><span>Choose delivery or pickup</span></div>
            <div class="stat-tile"><strong>3</strong><span>Track your order number</span></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    col_a, col_b = st.columns([1.1, .9])
    with col_a:
        st.subheader("Start your order")
        st.write("Use the Order page to add food and drinks to your cart. Checkout will collect your name, phone, and delivery location if needed.")
        if st.button("Browse menu", type="primary", use_container_width=True):
            st.session_state.public_page = "Menu and Services"
            st.rerun()
    with col_b:
        st.subheader("Already ordered?")
        st.write("Track by order number or by the phone number used at checkout.")
        if st.button("Track order", use_container_width=True):
            st.session_state.public_page = "Track Order"
            st.rerun()


def render_business_information() -> None:
    st.header("Business Information")
    col_a, col_b = st.columns([1.1, .9])
    with col_a:
        st.markdown(
            """
            <div class="menu-card">
              <div class="menu-title">Waterfront Snack Bar</div>
              <p class="muted">A simple local snack bar ordering system for pickup and delivery requests.</p>
              <p><strong>Payment:</strong> Cash on delivery or pickup.</p>
              <p><strong>Delivery:</strong> Flat SAT $2.00 delivery fee where available.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_b:
        st.info("Place an order request online and Waterfront Snack Bar will prepare it through the admin order board.")


def render_contact_hours() -> None:
    st.header("Contact and Opening Hours")
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Contact")
        st.write("Phone: Add your public business phone number in Settings.")
        st.write("Location: Waterfront Snack Bar")
    with col_b:
        st.subheader("Opening hours")
        st.write("Set your opening hours in Settings before launch.")
        st.write("Customers can still submit requests; staff confirm availability.")


def render_public_navigation() -> str:
    options = [
        "Home",
        "Menu and Services",
        f"Place Order ({cart_count()})",
        "Track Order",
        "Business Information",
        "Contact and Opening Hours",
        "Admin Login",
    ]
    current = st.session_state.public_page
    if current == "Place Order":
        current = f"Place Order ({cart_count()})"
    selected = st.radio(
        "Navigation",
        options,
        horizontal=True,
        label_visibility="collapsed",
        index=options.index(current) if current in options else 0,
    )
    if selected.startswith("Checkout"):
        page = "Place Order"
    elif selected.startswith("Place Order"):
        page = "Place Order"
    else:
        page = selected
    st.session_state.public_page = page
    return page


def main() -> None:
    st.set_page_config(
        page_title="Waterfront Business Manager",
        page_icon="WF",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    ensure_state()
    is_admin_area = st.session_state.current_area == "admin" and st.session_state.admin_authenticated
    render_css(show_admin_sidebar=is_admin_area)

    if is_admin_area:
        render_admin()
        return

    render_topbar()
    page = render_public_navigation()

    if page == "Home":
        render_home()
    elif page == "Menu and Services":
        render_menu()
    elif page == "Place Order":
        render_checkout()
    elif page == "Track Order":
        render_track_order()
    elif page == "Business Information":
        render_business_information()
    elif page == "Contact and Opening Hours":
        render_contact_hours()
    elif page == "Admin Login":
        if render_admin_login():
            st.session_state.current_area = "admin"
            st.rerun()


if __name__ == "__main__":
    main()

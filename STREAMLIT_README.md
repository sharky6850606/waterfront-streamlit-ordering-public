# Waterfront Streamlit Ordering App

This is a Streamlit launch version of the existing restaurant ordering app. It uses the same SQLite database at `prisma/dev.db`, so your current menu and orders remain available.

## Run locally

Install Streamlit:

```bash
pip install -r requirements-streamlit.txt
```

Start the app:

```bash
streamlit run streamlit_app.py --server.address 0.0.0.0 --server.port 8501
```

Or double-click:

```text
launch_streamlit.bat
```

Open:

```text
http://localhost:8501
```

For phones on the same Wi-Fi, open:

```text
http://YOUR-COMPUTER-IP:8501
```

## Admin

Default Streamlit admin password:

```text
admin123
```

Before real use, set an environment variable:

```bash
set STREAMLIT_ADMIN_PASSWORD=your-new-password
```

Then launch Streamlit from that same terminal.

## What this version includes

- Menu browsing with existing food photos
- Cart and quantity management
- Delivery or self pickup
- Required delivery address for delivery orders
- Fixed 2 tala delivery fee
- Cash payment note
- Order number generation
- Customer order tracking
- Admin live order view
- Admin status updates
- Admin menu availability toggles
- Quick category and menu item creation
- CSV export for recent orders

## Recommended next improvements

- Move from SQLite to PostgreSQL before public internet launch.
- Add user-friendly payment confirmation if you start accepting online payment.
- Add WhatsApp or SMS notifications for new order and status updates.
- Add kitchen prep-time estimates and pickup time slots.
- Add daily opening hours and stop ordering when closed.
- Add better admin accounts instead of one shared Streamlit password.
- Add backups for `prisma/dev.db` before every busy service period.

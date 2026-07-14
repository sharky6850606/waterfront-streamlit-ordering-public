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

Recommended Streamlit Secrets:

```toml
[admin]
username = "admin"
password = "replace-with-a-strong-password"
```

You can also use a SHA-256 or PBKDF2 password hash:

```toml
[admin]
username = "admin"
password_hash = "sha256$your_hash_here"
```

Environment variable fallback is also supported:

```bash
set STREAMLIT_ADMIN_USERNAME=admin
set STREAMLIT_ADMIN_PASSWORD=your-new-password
```

If no secret or environment variable is configured, the local fallback is `admin` / `admin123`. Change this before sharing the app widely.

## Logo

Add your logo here:

```text
assets/waterfront_logo.png
```

The app will not crash if the logo is missing.

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
- Chef-friendly order board grouped by status
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

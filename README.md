# Single Restaurant Food Ordering Starter

This is a **local-first MVP starter** for a single-restaurant food ordering website.

## What this starter includes

- Customer menu with photos
- Cart with delivery or pickup
- Guest checkout with:
  - name
  - phone number
  - manual address/location
- Fixed **2 tala delivery fee** for delivery orders
- Admin login
- Admin dashboard
- Live orders page with:
  - clean order cards
  - pop-up alert
  - sound alert
  - status updates
- Menu management page
- SQLite database with Prisma
- Sample seed data

## What you need to install

1. **Node.js LTS**
2. **npm** (comes with Node.js)
3. A code editor such as **VS Code**

## Accounts / services you need right now

For local testing, you do **not** need to create any online accounts yet.

You only need:
- your computer
- Node.js installed
- a terminal
- VS Code

## Database to use

Use **SQLite** for local testing.

Why:
- zero setup
- file-based
- perfect for one-machine testing
- easy to replace later with PostgreSQL when you go live

The database file will be created here:

```bash
prisma/dev.db
```

## Default admin account

After seeding the database:

- Username: `admin`
- Password: `admin123`

Change this before real deployment.

## Setup steps

### 1. Create the project

You can either:
- copy these files into a new folder, or
- unzip this starter and open it in VS Code

### 2. Install packages

```bash
npm install
```

### 3. Create the database

```bash
npx prisma migrate dev --name init
```

### 4. Seed sample data

```bash
npm run db:seed
```

### 5. Run the app

```bash
npm run dev
```

Open:

- Customer site: `http://localhost:3000`
- Admin login: `http://localhost:3000/admin/login`

## Next things you should do

1. Replace sample menu items
2. Add your own food photos in `/public/uploads/menu`
3. Change admin password
4. Test ordering from your phone on the same Wi-Fi using your computer's local IP

## Local network testing

To test from phones on the same Wi-Fi:

```bash
npm run dev -- --hostname 0.0.0.0
```

Then open on your phone:

```text
http://YOUR-COMPUTER-IP:3000
```

## Suggested future accounts when you go live

You do **not** need these yet, but later you will likely want:
- **Vercel** or another host for the website
- **Neon**, **Supabase**, or **Prisma Postgres** for a cloud database
- **Cloudinary** or similar for image hosting
- **WhatsApp Business / SMS provider** if you want customer notifications

## Project structure

```text
app/
  admin/
  api/
  checkout/
  confirm/
components/
lib/
prisma/
public/uploads/menu/
```

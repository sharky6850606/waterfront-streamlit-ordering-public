# Setup Checklist

## Install first
- Install Node.js LTS
- Install VS Code

## Create local env file
Copy `.env.example` to `.env`

## Run these commands
```bash
npm install
npx prisma migrate dev --name init
npm run db:seed
npm run dev
```

## Open these URLs
- Customer: http://localhost:3000
- Admin: http://localhost:3000/admin/login

## Default admin
- admin / admin123

## Add your own photos
Put your files in:
```text
public/uploads/menu/
```

Then use paths like:
```text
/uploads/menu/fried-rice.jpg
```

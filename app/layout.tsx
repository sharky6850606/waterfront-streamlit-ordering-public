import "./globals.css";
import { CartProvider } from "@/components/cart-context";

export const metadata = {
  title: "Restaurant Orders",
  description: "Single restaurant online ordering"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <CartProvider>{children}</CartProvider>
      </body>
    </html>
  );
}

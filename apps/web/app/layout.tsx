import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "hso gateway",
  description: "Local-first agent gateway workspace"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

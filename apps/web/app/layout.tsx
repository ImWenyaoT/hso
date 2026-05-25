import type { Metadata } from "next";
import "material-symbols/outlined.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "hso gateway",
  description: "Local-first agent gateway workspace",
  icons: {
    icon: "/icon.svg"
  }
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

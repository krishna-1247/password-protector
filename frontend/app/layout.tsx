import type { Metadata } from "next";
import { Toaster } from "sonner";
import "./globals.css";

export const metadata: Metadata = {
  title: "PDF Password Protector — Bulk Encryption Tool",
  description:
    "Upload thousands of PDFs and an Excel sheet with passwords. Get back an encrypted ZIP in seconds. No database, no storage — completely private.",
  keywords: ["PDF encryption", "bulk PDF", "password protect PDF", "PAN number", "AES-256"],
  openGraph: {
    title: "PDF Password Protector",
    description: "Bulk-encrypt PDFs using passwords from an Excel file",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="light">
      <body>
        {children}
        <Toaster
          position="top-right"
          richColors
          theme="light"
          toastOptions={{
            style: {
              background: "#ffffff",
              border: "1px solid #e2e8f0",
              color: "#111827",
              boxShadow: "0 4px 12px rgba(0, 0, 0, 0.05)",
            },
          }}
        />
      </body>
    </html>
  );
}

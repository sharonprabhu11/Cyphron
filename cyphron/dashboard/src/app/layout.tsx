import type { ReactNode } from "react";
<<<<<<< HEAD

export const metadata = {
  title: "Cyphron Dashboard",
  description: "Foundation dashboard scaffold"
=======
import { Plus_Jakarta_Sans } from "next/font/google";

import { ThemeProvider } from "@/components/theme-provider";

import "./globals.css";

const fontSans = Plus_Jakarta_Sans({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

export const metadata = {
  title: "Cyphron Dashboard",
  description: "Fraud operations and analytics",
>>>>>>> pr-7
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
<<<<<<< HEAD
    <html lang="en">
      <body style={{ fontFamily: "system-ui, sans-serif", margin: 0 }}>
        {children}
=======
    <html lang="en" className={fontSans.variable} suppressHydrationWarning>
      <body className="min-h-screen font-sans">
        <ThemeProvider attribute="class" defaultTheme="light" enableSystem={false} storageKey="cyphron-theme">
          {children}
        </ThemeProvider>
>>>>>>> pr-7
      </body>
    </html>
  );
}
<<<<<<< HEAD

=======
>>>>>>> pr-7

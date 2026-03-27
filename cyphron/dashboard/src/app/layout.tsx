import type { ReactNode } from "react";

export const metadata = {
  title: "Cyphron Dashboard",
  description: "Foundation dashboard scaffold"
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body style={{ fontFamily: "system-ui, sans-serif", margin: 0 }}>
        {children}
      </body>
    </html>
  );
}


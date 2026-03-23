import Link from "next/link";

import "./globals.css";

export const metadata = {
  title: "Governed Agent Console",
  description: "Operator console for the governed agent platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <div className="shell">
          <header className="topbar">
            <div>
              <p className="eyebrow">Governed Agent Platform</p>
              <h1>Operator Console</h1>
            </div>
            <nav className="topnav">
              <Link href="/">Runs</Link>
            </nav>
          </header>
          {children}
        </div>
      </body>
    </html>
  );
}

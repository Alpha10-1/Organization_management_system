import "./globals.css";

export const metadata = {
  title: "Organization Management System",
  description: "Secure organization management platform",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="bg-slate-50 text-slate-900 antialiased">
        {children}
      </body>
    </html>
  );
}
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Hammer Ontology",
  description: "디자인 데이터 온톨로지 관리 웹 앱",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}

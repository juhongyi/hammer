import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Hammer Presentation",
  description: "AI 프레젠테이션 웹 앱",
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

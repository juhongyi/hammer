import type { Metadata } from "next";
import "./style.css";

export const metadata: Metadata = { title: "Presentation PoC", description: "Jev + Workers AI 파이프라인 PoC" };

export default function Layout({ children }: { children: React.ReactNode }) {
  return <html lang="ko"><body>{children}</body></html>;
}

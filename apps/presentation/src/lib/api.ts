import type { components } from "@poc/api-types";

export type Presentation = components["schemas"]["PresentationView"];
export type Outline = components["schemas"]["Outline"];
export type Slide = components["schemas"]["SlideResult"];
export type Summary = components["schemas"]["PresentationSummary"];

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  const data = await response.json();
  if (!response.ok) {
    const message =
      typeof data.detail === "string"
        ? data.detail
        : "입력 형식 또는 제약을 확인해 주세요.";
    throw new Error(message);
  }
  return data;
}

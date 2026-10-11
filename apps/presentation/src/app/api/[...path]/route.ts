import type { NextRequest } from "next/server";

export const dynamic = "force-dynamic";

async function proxy(request: NextRequest) {
  const upstream = new URL(
    request.nextUrl.pathname + request.nextUrl.search,
    process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8000",
  );
  try {
    const response = await fetch(upstream, {
      method: request.method,
      headers: { "Content-Type": "application/json" },
      body: request.method === "GET" ? undefined : await request.text(),
      cache: "no-store",
      signal: AbortSignal.timeout(180_000),
    });
    return new Response(response.body, {
      status: response.status,
      headers: {
        "Content-Type":
          response.headers.get("Content-Type") ?? "application/json",
      },
    });
  } catch {
    return Response.json(
      { detail: "백엔드에 연결할 수 없습니다. 실행 상태를 확인해 주세요." },
      { status: 502 },
    );
  }
}

export { proxy as GET, proxy as POST, proxy as PUT };

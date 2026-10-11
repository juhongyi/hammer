"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ArrowRight, Layers, Sparkles } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { api, type Presentation, type Summary } from "@/lib/api";
import { statusLabel } from "@/lib/status";

const inputSchema = z.object({
  text: z.string().trim().min(1, "주제나 원고를 입력해 주세요."),
});

export default function Home() {
  const router = useRouter();
  const form = useForm({
    resolver: zodResolver(inputSchema),
    defaultValues: { text: "" },
  });
  const history = useQuery({
    queryKey: ["presentations"],
    queryFn: () => api<Summary[]>("/presentations"),
  });
  const create = useMutation({
    mutationFn: (body: z.infer<typeof inputSchema>) =>
      api<Presentation>("/presentations", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    onSuccess: (result) => router.push(`/presentations/${result.id}`),
  });

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <header className="mb-16 flex items-center gap-3">
        <span className="rounded-xl bg-primary p-3 text-white">
          <Layers size={22} />
        </span>
        <div>
          <p className="text-lg font-bold">System One</p>
          <p className="text-xs text-muted-foreground">AI 프레젠테이션 PoC</p>
        </div>
        <Badge variant="outline" className="ml-auto">
          고정 스타일 · 6종 디자인
        </Badge>
      </header>
      <div className="grid gap-12 lg:grid-cols-[1fr_1.15fr]">
        <section className="py-6">
          <p className="mb-4 text-sm font-semibold tracking-widest text-primary">
            IDEAS → PRESENTATION
          </p>
          <h1 className="text-4xl font-bold leading-snug">
            내용의 의미에 맞는
            <br />
            발표자료를 만드세요.
          </h1>
          <p className="mt-6 max-w-md leading-8 text-muted-foreground">
            한국어 주제나 원고를 입력하세요. 개요를 직접 다듬으면, LLM이 문구를
            작성하고 Jev가 준비된 디자인 중 적합한 레이아웃을 선택합니다.
          </p>
          <ol className="mt-10 grid gap-5 text-sm">
            {[
              "입력에 맞춰 6~30장 개요 생성",
              "제목·핵심 메시지·주요 내용 수정",
              "디자인 선택·배치 검사·전체 열람",
            ].map((text, index) => (
              <li key={text} className="flex items-center gap-3">
                <span className="grid size-7 place-items-center rounded-full bg-accent font-bold text-primary">
                  {index + 1}
                </span>
                {text}
              </li>
            ))}
          </ol>
        </section>
        <form
          className="panel space-y-5"
          onSubmit={form.handleSubmit((body) => create.mutate(body))}
        >
          <label className="field" htmlFor="source">
            어떤 발표를 준비하고 있나요?
          </label>
          <Textarea
            id="source"
            className="min-h-72 bg-white text-base leading-7"
            placeholder="예: 신규 고객의 초기 설정 경험을 개선하는 방안을 팀에 발표하려고 합니다. 문제, 개선 방향, 실행 과제 순서로 정리해 주세요."
            {...form.register("text")}
            disabled={create.isPending}
          />
          {form.formState.errors.text && (
            <p role="alert" className="text-sm text-destructive">
              {form.formState.errors.text.message}
            </p>
          )}
          {create.error && (
            <p role="alert" className="error">
              {create.error.message}
            </p>
          )}
          <Button
            type="submit"
            size="lg"
            className="h-12 w-full"
            disabled={create.isPending}
          >
            <Sparkles />
            {create.isPending ? "개요 생성 중…" : "개요 만들기"}
            <ArrowRight />
          </Button>
          <p
            aria-live="polite"
            className="text-xs leading-6 text-muted-foreground"
          >
            {create.isPending
              ? "실제 Workers AI로 개요를 작성하고 있습니다. 잠시 기다려 주세요."
              : "장수는 내용에 따라 자동 결정됩니다. 다음 화면에서 개요를 수정하고 확정할 수 있습니다."}
          </p>
        </form>
      </div>
      <section className="mt-16 border-t border-border pt-8">
        <h2 className="mb-5 text-lg font-semibold">최근 발표자료</h2>
        {history.isPending && (
          <p className="text-sm text-muted-foreground">불러오는 중…</p>
        )}
        {history.error && (
          <p role="alert" className="error">
            {history.error.message}
          </p>
        )}
        {history.data?.length === 0 && (
          <p className="text-sm text-muted-foreground">
            첫 번째 발표자료를 만들어 보세요.
          </p>
        )}
        <div className="grid gap-3 md:grid-cols-2">
          {history.data?.map((item) => (
            <Link
              key={item.id}
              href={`/presentations/${item.id}`}
              className="panel flex items-center justify-between gap-4 hover:border-primary"
            >
              <div>
                <p className="font-medium">{item.title}</p>
                <p className="mt-2 text-xs text-muted-foreground">
                  {item.page_count}장 ·{" "}
                  {new Date(item.created_at).toLocaleDateString("ko-KR")}
                </p>
              </div>
              <Badge variant="secondary">{statusLabel(item.status)}</Badge>
            </Link>
          ))}
        </div>
      </section>
    </main>
  );
}

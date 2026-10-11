"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, CheckCircle2, LoaderCircle } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useFieldArray, useForm } from "react-hook-form";
import { z } from "zod";
import { Deck } from "@/components/deck";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { api, type Outline, type Presentation } from "@/lib/api";
import { statusLabel } from "@/lib/status";

const outlineSchema = z.object({
  pages: z
    .array(
      z.object({
        title: z.string().trim().min(1),
        key_message: z.string().trim().min(1),
        main_content: z.string().trim().min(1),
      }),
    )
    .min(6)
    .max(30),
});

function OutlineEditor({ presentation }: { presentation: Presentation }) {
  const client = useQueryClient();
  const form = useForm({
    resolver: zodResolver(outlineSchema),
    defaultValues: presentation.outline,
  });
  const { fields } = useFieldArray({ control: form.control, name: "pages" });
  const confirm = useMutation({
    mutationFn: async (outline: Outline) => {
      const saved = await api<Presentation>(
        `/presentations/${presentation.id}/outline`,
        { method: "PUT", body: JSON.stringify(outline) },
      );
      client.setQueryData(["presentation", presentation.id], saved);
      return api<Presentation>(`/presentations/${presentation.id}/generate`, {
        method: "POST",
      });
    },
    onSuccess: (data) =>
      client.setQueryData(["presentation", presentation.id], data),
  });
  return (
    <form
      className="space-y-5"
      onSubmit={form.handleSubmit((outline) => confirm.mutate(outline))}
    >
      <div className="panel">
        <h2 className="text-lg font-semibold">
          개요 편집 · 총 {presentation.outline.pages.length}장
        </h2>
        <p className="mt-2 text-sm leading-7 text-muted-foreground">
          제목·핵심 메시지·주요 내용을 직접 수정하세요. 확정하면 이 개요를
          바탕으로 문구와 디자인을 생성합니다.
        </p>
      </div>
      {fields.map((page, index) => (
        <fieldset
          key={page.id}
          className="panel grid gap-4"
          disabled={confirm.isPending}
        >
          <legend className="px-2 text-sm font-semibold">
            {index + 1}페이지
          </legend>
          <label className="field">
            제목
            <Input
              {...form.register(`pages.${index}.title`)}
              aria-label={`${index + 1}페이지 제목`}
            />
          </label>
          <label className="field">
            핵심 메시지
            <Input
              {...form.register(`pages.${index}.key_message`)}
              aria-label={`${index + 1}페이지 핵심 메시지`}
            />
          </label>
          <label className="field">
            주요 내용
            <Textarea
              {...form.register(`pages.${index}.main_content`)}
              aria-label={`${index + 1}페이지 주요 내용`}
              className="min-h-24"
            />
          </label>
        </fieldset>
      ))}
      {Object.keys(form.formState.errors).length > 0 && (
        <p className="error" role="alert">
          모든 페이지의 제목·핵심 메시지·주요 내용을 입력해 주세요.
        </p>
      )}
      {confirm.error && (
        <p className="error" role="alert">
          {confirm.error.message}
        </p>
      )}
      <div className="sticky bottom-4 rounded-xl border border-border bg-white/95 p-4 shadow-lg">
        <Button
          type="submit"
          size="lg"
          className="h-12 w-full"
          disabled={confirm.isPending}
        >
          {confirm.isPending ? (
            <LoaderCircle className="animate-spin" />
          ) : (
            <CheckCircle2 />
          )}
          {confirm.isPending
            ? "개요 저장·생성 시작 중…"
            : "개요 확정하고 슬라이드 생성"}
        </Button>
      </div>
    </form>
  );
}

export default function PresentationPage() {
  const { id } = useParams<{ id: string }>();
  const query = useQuery({
    queryKey: ["presentation", id],
    queryFn: () => api<Presentation>(`/presentations/${id}`),
    refetchInterval: (state) =>
      ["queued", "generating"].includes(state.state.data?.status ?? "")
        ? 1000
        : false,
  });
  const presentation = query.data;
  return (
    <main className="mx-auto max-w-5xl px-6 py-8">
      <Link
        href="/"
        className="mb-8 inline-flex items-center gap-2 text-sm text-muted-foreground"
      >
        <ArrowLeft size={16} />
        발표자료 목록
      </Link>
      {query.isPending && <p>불러오는 중…</p>}
      {query.error && (
        <p className="error" role="alert">
          {query.error.message}
        </p>
      )}
      {presentation && (
        <>
          <header className="mb-8 flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="mb-2 text-xs font-semibold tracking-widest text-primary">
                SYSTEM ONE PRESENTATION
              </p>
              <h1 className="text-2xl font-bold">
                {presentation.outline.pages[0].title}
              </h1>
            </div>
            <Badge
              variant={
                presentation.status === "completed" ? "default" : "secondary"
              }
            >
              {statusLabel(presentation.status)}
            </Badge>
          </header>
          {presentation.error && (
            <p role="alert" className="error mb-6">
              {presentation.error}
            </p>
          )}
          {["outline_ready", "failed"].includes(presentation.status) ? (
            <OutlineEditor
              key={`${id}-${presentation.run_id}`}
              presentation={presentation}
            />
          ) : (
            <>
              <div role="status" className="panel mb-8 flex items-center gap-3">
                {presentation.status === "completed" ? (
                  <CheckCircle2 className="text-primary" />
                ) : (
                  <LoaderCircle className="animate-spin text-primary" />
                )}
                <div>
                  <p className="font-medium">{presentation.phase}</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {presentation.slides.length}/
                    {presentation.outline.pages.length}장 ·{" "}
                    {presentation.status === "completed"
                      ? "모든 페이지의 배치 검사를 통과했습니다."
                      : "미완성 결과 · 모든 페이지의 생성과 배치 검사 후 완료됩니다."}
                  </p>
                </div>
              </div>
              {presentation.slides.length > 0 && (
                <Deck key={presentation.run_id} presentation={presentation} />
              )}
              <details className="panel mt-8">
                <summary className="cursor-pointer text-sm font-medium">
                  확정 개요 확인
                </summary>
                <pre className="mt-4 whitespace-pre-wrap text-sm leading-7">
                  {JSON.stringify(presentation.outline, null, 2)}
                </pre>
              </details>
            </>
          )}
        </>
      )}
    </main>
  );
}

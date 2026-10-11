"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api, type Presentation } from "@/lib/api";
import { inspectSlides } from "@/lib/render-validation";
import { SlideCanvas, SlidePreview } from "./slide";

export function Deck({ presentation }: { presentation: Presentation }) {
  const client = useQueryClient();
  const root = useRef<HTMLDivElement>(null);
  const started = useRef(false);
  const validation = useMutation({
    mutationFn: async () => {
      if (!root.current)
        throw new Error("슬라이드 검사 화면을 준비하지 못했습니다.");
      const report = await inspectSlides(root.current, presentation);
      return api<Presentation>(`/presentations/${presentation.id}/validation`, {
        method: "POST",
        body: JSON.stringify(report),
      });
    },
    onSuccess: (data) => {
      client.setQueryData(["presentation", presentation.id], data);
    },
  });
  useEffect(() => {
    if (presentation.status === "awaiting_validation" && !started.current) {
      started.current = true;
      validation.mutate();
    }
  }, [presentation.status, validation.mutate]);

  return (
    <section className="space-y-8">
      {validation.error && (
        <div className="error" role="alert">
          배치 검사 결과를 저장하지 못했습니다: {validation.error.message}
          <Button
            variant="outline"
            className="ml-4"
            onClick={() => validation.mutate()}
            disabled={validation.isPending}
          >
            검사 다시 시도
          </Button>
        </div>
      )}
      <div
        ref={root}
        aria-hidden="true"
        style={{
          position: "absolute",
          left: -20000,
          top: 0,
          opacity: 0,
          pointerEvents: "none",
        }}
      >
        {presentation.slides.map((slide) => (
          <SlideCanvas key={slide.index} slide={slide} />
        ))}
      </div>
      {presentation.slides.map((slide) => (
        <article
          key={slide.index}
          className="space-y-4"
          data-testid={`page-${slide.index}`}
        >
          <div className="flex flex-wrap items-center gap-3">
            <h2 className="font-semibold">
              {slide.index + 1}. {slide.content.title}
            </h2>
            <Badge variant="secondary">{slide.layout.name}</Badge>
            <span className="text-xs text-muted-foreground">
              표현 유형:{" "}
              {
                presentation.snapshot?.types.find(
                  (type) => type.id === slide.trace.classification.choice,
                )?.name
              }
            </span>
          </div>
          <SlidePreview slide={slide} />
          <details className="panel text-sm">
            <summary className="cursor-pointer font-medium">
              Jev 판단 근거 · 후보와 선택 결과
            </summary>
            <p className="my-4 text-muted-foreground">
              온톨로지 v{presentation.snapshot?.version} ·{" "}
              {slide.trace.selection.model} · 선택: {slide.layout.name}
            </p>
            {slide.trace.planning && (
              <p className="mb-4 text-xs text-muted-foreground">
                개요 사전 판단:{" "}
                {
                  presentation.snapshot?.types.find(
                    (type) => type.id === slide.trace.planning?.choice,
                  )?.name
                }
                {" → "}최종 문구 분류:{" "}
                {
                  presentation.snapshot?.types.find(
                    (type) => type.id === slide.trace.classification.choice,
                  )?.name
                }
                {" · "}사전 판단은 문구 용량 안내에만 사용됩니다.
              </p>
            )}
            <ul className="space-y-2">
              {slide.trace.faithfulness && (
                <li className="mb-3 text-xs text-primary">
                  내용 보존 검수: 통과 ·{" "}
                  {(
                    slide.trace.faithfulness.probabilities.faithful * 100
                  ).toFixed(1)}
                  %
                </li>
              )}
              {slide.trace.ranked_candidates.map((candidate) => (
                <li
                  key={candidate.layout_id}
                  className="flex justify-between rounded-lg bg-muted px-4 py-2"
                >
                  <span>
                    {candidate.name}
                    {candidate.layout_id === slide.layout.id ? " · 선택됨" : ""}
                  </span>
                  <span>{(candidate.probability * 100).toFixed(1)}%</span>
                </li>
              ))}
            </ul>
            <p className="mt-3 text-xs text-muted-foreground">
              확률은 제공된 후보 사이의 상대적 선택 확률입니다.
            </p>
            <details className="mt-4">
              <summary className="cursor-pointer">
                실제 API 요청·분류·응답 확인
              </summary>
              <pre className="mt-3 max-h-96 overflow-auto whitespace-pre-wrap break-all rounded-lg bg-muted p-4 text-xs">
                {JSON.stringify(slide.trace, null, 2)}
              </pre>
            </details>
          </details>
        </article>
      ))}
    </section>
  );
}

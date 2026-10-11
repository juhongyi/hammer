"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Database, Eye, Save } from "lucide-react";
import { useState } from "react";
import { Controller, useForm } from "react-hook-form";
import type { z } from "zod";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { api, type Catalogue } from "@/lib/api";
import { capacities, catalogueSchema } from "@/lib/schema";

function Editor({ catalogue }: { catalogue: Catalogue }) {
  const client = useQueryClient();
  const [review, setReview] = useState<Catalogue | null>(null);
  const [saved, setSaved] = useState(false);
  const form = useForm<
    z.input<typeof catalogueSchema>,
    unknown,
    z.output<typeof catalogueSchema>
  >({
    resolver: zodResolver(catalogueSchema),
    defaultValues: catalogue,
  });
  const save = useMutation({
    mutationFn: (document: Catalogue) =>
      api<Catalogue>("/ontology", {
        method: "PUT",
        body: JSON.stringify(document),
      }),
    onSuccess: (data) => {
      client.setQueryData(["ontology"], data);
      form.reset(data);
      setReview(null);
      setSaved(true);
    },
  });

  return (
    <>
      {saved && (
        <p
          role="status"
          className="mb-6 rounded-xl border border-primary/30 bg-accent p-4 text-sm text-primary"
        >
          검수한 변경 내용을 저장했습니다. 다음 생성부터 반영됩니다.
        </p>
      )}
      {review ? (
        <section className="panel space-y-6">
          <div className="flex items-center gap-3">
            <Eye className="text-primary" />
            <h2 className="text-xl font-semibold">수정 내용 검수</h2>
            <Badge variant="outline">
              v{catalogue.version} → v{catalogue.version + 1}
            </Badge>
          </div>
          <p className="text-sm leading-7 text-muted-foreground">
            변경 전·후를 확인하세요. 검수 완료 후 저장하면 다음 생성부터
            적용됩니다. 진행 중이거나 이미 생성된 발표자료는 해당 생성의
            스냅샷을 유지합니다.
          </p>
          <div className="grid gap-5 lg:grid-cols-2">
            {[
              { label: "변경 전", data: catalogue },
              { label: "변경 후", data: review },
            ].map(({ label, data }) => (
              <div key={label}>
                <h3 className="mb-3 font-medium">{label}</h3>
                <pre className="max-h-[600px] overflow-auto whitespace-pre-wrap break-all rounded-lg bg-muted p-4 text-xs leading-6">
                  {JSON.stringify(data, null, 2)}
                </pre>
              </div>
            ))}
          </div>
          <div className="rounded-xl border border-border p-4">
            <h3 className="mb-3 text-sm font-semibold">
              저장 후 디자인 사용 상태
            </h3>
            <div className="flex flex-wrap gap-2">
              {review.layouts.map((layout) => (
                <Badge
                  key={layout.id}
                  variant={layout.enabled ? "default" : "secondary"}
                >
                  {layout.name} · {layout.enabled ? "사용" : "중지"}
                </Badge>
              ))}
            </div>
          </div>
          {save.error && (
            <p role="alert" className="error">
              {save.error.message}
            </p>
          )}
          <div className="flex gap-3">
            <Button
              variant="outline"
              onClick={() => setReview(null)}
              disabled={save.isPending}
            >
              돌아가서 수정
            </Button>
            <Button
              onClick={() => save.mutate(review)}
              disabled={save.isPending}
            >
              <Save />
              {save.isPending ? "저장 중…" : "검수 완료·저장"}
            </Button>
          </div>
        </section>
      ) : (
        <form
          onSubmit={form.handleSubmit((data) => {
            setReview(data);
            setSaved(false);
          })}
          className="space-y-8"
        >
          <section className="panel">
            <h2 className="mb-2 text-xl font-semibold">표현 유형</h2>
            <p className="mb-6 text-sm leading-7 text-muted-foreground">
              Jev는 이 설명을 읽고 각 페이지의 주된 전달 목적 하나를 분류합니다.
              식별자는 고정입니다.
            </p>
            <div className="grid gap-5 md:grid-cols-2">
              {catalogue.types.map((type, index) => (
                <fieldset
                  key={type.id}
                  className="space-y-3 rounded-xl border border-border p-4"
                >
                  <legend className="px-2 text-xs text-muted-foreground">
                    {type.id}
                  </legend>
                  <label className="field">
                    이름
                    <Input
                      {...form.register(`types.${index}.name`)}
                      aria-label={`${type.id} 유형 이름`}
                    />
                  </label>
                  <label className="field">
                    의미 설명
                    <Textarea
                      {...form.register(`types.${index}.description`)}
                      aria-label={`${type.id} 유형 설명`}
                    />
                  </label>
                </fieldset>
              ))}
            </div>
          </section>
          <section className="space-y-5">
            <div>
              <h2 className="text-xl font-semibold">디자인과 슬롯 관계</h2>
              <p className="mt-2 text-sm leading-7 text-muted-foreground">
                지원 유형과 슬롯 제약으로 후보를 제한한 뒤 Jev가 선택합니다.
                슬롯 역할·형태·구조는 고정이며, 수용 범위는 렌더러 상한 안에서
                조정합니다.
              </p>
            </div>
            {catalogue.layouts.map((layout, index) => {
              const [minimum, maximum, textMax] = capacities[layout.id];
              return (
                <fieldset
                  key={layout.id}
                  className="panel"
                  data-testid={`layout-${layout.id}`}
                >
                  <legend className="px-3 font-semibold">
                    {layout.name}{" "}
                    <span className="ml-2 text-xs font-normal text-muted-foreground">
                      {layout.id}
                    </span>
                  </legend>
                  <div className="mb-6 flex items-center justify-between gap-4">
                    <Badge variant="outline">
                      제목 + 핵심 메시지 + 본문 블록
                    </Badge>
                    <Controller
                      control={form.control}
                      name={`layouts.${index}.enabled`}
                      render={({ field }) => (
                        <label className="flex items-center gap-2 text-sm">
                          <Checkbox
                            checked={field.value}
                            onCheckedChange={field.onChange}
                            aria-label={`${layout.id} 사용 여부`}
                          />
                          사용 가능
                        </label>
                      )}
                    />
                  </div>
                  <div className="grid gap-5 md:grid-cols-2">
                    <label className="field">
                      디자인 이름
                      <Input
                        {...form.register(`layouts.${index}.name`)}
                        aria-label={`${layout.id} 이름`}
                      />
                    </label>
                    <label className="field">
                      용도 설명
                      <Textarea
                        {...form.register(`layouts.${index}.purpose`)}
                        aria-label={`${layout.id} 용도`}
                      />
                    </label>
                  </div>
                  <fieldset className="my-6 rounded-xl bg-muted p-4">
                    <legend className="px-2 text-sm font-medium">
                      지원하는 표현 유형 — 여러 개 선택 가능
                    </legend>
                    <Controller
                      control={form.control}
                      name={`layouts.${index}.supports`}
                      render={({ field }) => (
                        <div className="flex flex-wrap gap-5">
                          {catalogue.types.map((type) => (
                            <label
                              key={type.id}
                              className="flex items-center gap-2 text-sm"
                            >
                              <Checkbox
                                aria-label={`${layout.id} ${type.name} 지원`}
                                checked={field.value.includes(type.id)}
                                onCheckedChange={(checked) =>
                                  field.onChange(
                                    checked
                                      ? [...field.value, type.id]
                                      : field.value.filter(
                                          (id) => id !== type.id,
                                        ),
                                  )
                                }
                              />
                              {type.name}
                            </label>
                          ))}
                        </div>
                      )}
                    />
                  </fieldset>
                  <div className="grid gap-5 md:grid-cols-3">
                    <fieldset className="space-y-3 rounded-xl border border-border p-4">
                      <legend className="px-2 text-sm font-semibold">
                        제목 슬롯 · text
                      </legend>
                      <label className="field">
                        역할 설명
                        <Textarea
                          {...form.register(
                            `layouts.${index}.slots.title.description`,
                          )}
                        />
                      </label>
                      <label className="field">
                        글자 수 상한 · 최대 48
                        <Input
                          type="number"
                          min={1}
                          max={48}
                          {...form.register(
                            `layouts.${index}.slots.title.max_chars`,
                            { valueAsNumber: true },
                          )}
                          aria-label={`${layout.id} 제목 상한`}
                        />
                      </label>
                    </fieldset>
                    <fieldset className="space-y-3 rounded-xl border border-border p-4">
                      <legend className="px-2 text-sm font-semibold">
                        핵심 메시지 슬롯 · text
                      </legend>
                      <label className="field">
                        역할 설명
                        <Textarea
                          {...form.register(
                            `layouts.${index}.slots.key_message.description`,
                          )}
                        />
                      </label>
                      <label className="field">
                        글자 수 상한 · 최대 96
                        <Input
                          type="number"
                          min={1}
                          max={96}
                          {...form.register(
                            `layouts.${index}.slots.key_message.max_chars`,
                            { valueAsNumber: true },
                          )}
                        />
                      </label>
                    </fieldset>
                    <fieldset className="space-y-3 rounded-xl border border-border p-4">
                      <legend className="px-2 text-sm font-semibold">
                        본문 슬롯 · 소제목/내용 블록
                      </legend>
                      <label className="field">
                        역할 설명
                        <Textarea
                          {...form.register(
                            `layouts.${index}.slots.body.description`,
                          )}
                        />
                      </label>
                      <div className="grid grid-cols-2 gap-3">
                        <label className="field">
                          블록 최소 수
                          <Input
                            type="number"
                            min={minimum}
                            max={maximum}
                            {...form.register(
                              `layouts.${index}.slots.body.min_items`,
                              { valueAsNumber: true },
                            )}
                            aria-label={`${layout.id} 최소 블록`}
                          />
                        </label>
                        <label className="field">
                          블록 최대 수
                          <Input
                            type="number"
                            min={minimum}
                            max={maximum}
                            {...form.register(
                              `layouts.${index}.slots.body.max_items`,
                              { valueAsNumber: true },
                            )}
                            aria-label={`${layout.id} 최대 블록`}
                          />
                        </label>
                      </div>
                      <label className="field">
                        소제목 상한 · 최대 32
                        <Input
                          type="number"
                          min={1}
                          max={32}
                          {...form.register(
                            `layouts.${index}.slots.body.heading_max_chars`,
                            { valueAsNumber: true },
                          )}
                        />
                      </label>
                      <label className="field">
                        블록 내용 상한 · 최대 {textMax}
                        <Input
                          type="number"
                          min={1}
                          max={textMax}
                          {...form.register(
                            `layouts.${index}.slots.body.text_max_chars`,
                            { valueAsNumber: true },
                          )}
                          aria-label={`${layout.id} 본문 상한`}
                        />
                      </label>
                      <p className="text-xs text-muted-foreground">
                        고정 블록 범위: {minimum}~{maximum}개
                      </p>
                    </fieldset>
                  </div>
                </fieldset>
              );
            })}
          </section>
          {Object.keys(form.formState.errors).length > 0 && (
            <div role="alert" className="error">
              필수 정보·지원 유형·블록 범위·글자 수 상한을 확인해 주세요.
              유효하지 않은 데이터는 검수·저장할 수 없습니다.
              <pre className="mt-3 overflow-auto whitespace-pre-wrap text-xs">
                {JSON.stringify(
                  form.formState.errors,
                  (key, value) => (key === "ref" ? undefined : value),
                  2,
                )}
              </pre>
            </div>
          )}
          <div className="sticky bottom-4 flex items-center justify-between gap-4 rounded-xl border border-border bg-white/95 p-4 shadow-lg">
            <p className="text-sm text-muted-foreground">
              편집 내용은 검수 후 저장됩니다.
            </p>
            <Button type="submit" size="lg">
              <CheckCircle2 />
              수정 내용 검수
            </Button>
          </div>
        </form>
      )}
    </>
  );
}

export default function OntologyPage() {
  const query = useQuery({
    queryKey: ["ontology"],
    queryFn: () => api<Catalogue>("/ontology"),
  });
  return (
    <main className="mx-auto max-w-7xl px-6 py-10">
      <header className="mb-10 flex items-center gap-3">
        <span className="rounded-xl bg-primary p-3 text-white">
          <Database size={22} />
        </span>
        <div>
          <p className="text-lg font-bold">System One</p>
          <p className="text-xs text-muted-foreground">
            디자인 데이터 온톨로지 · 내부 운영
          </p>
        </div>
        {query.data && (
          <Badge className="ml-auto" variant="outline">
            온톨로지 v{query.data.version}
          </Badge>
        )}
      </header>
      <section className="mb-10">
        <p className="mb-3 text-xs font-semibold tracking-widest text-primary">
          MEANING · STRUCTURE · CONSTRAINTS
        </p>
        <h1 className="text-3xl font-bold">
          디자인의 의미와 사용 범위를 관리하세요.
        </h1>
        <p className="mt-4 max-w-3xl text-sm leading-7 text-muted-foreground">
          표현 유형, 레이아웃의 지원 관계, 콘텐츠 역할과 용량을 공유하는
          데이터입니다. 수정·검수한 정보는 앱의 다음 생성에서 후보 제한과 Jev
          판단에 전달됩니다.
        </p>
      </section>
      {query.isPending && <p>불러오는 중…</p>}
      {query.error && (
        <p role="alert" className="error">
          {query.error.message}
        </p>
      )}
      {query.data && <Editor catalogue={query.data} />}
    </main>
  );
}

import { expect, test } from "@playwright/test";
import type { components } from "@poc/api-types";

type Presentation = components["schemas"]["PresentationView"];
type Catalogue = components["schemas"]["Catalogue"];
const backend = process.env.API_URL ?? "http://127.0.0.1:8000";
const ontologyUrl = process.env.ONTOLOGY_URL ?? "http://127.0.0.1:3001";

test.skip(
  process.env.REAL_MODELS !== "1",
  "Explicit opt-in is required for paid, real model calls.",
);

test("실제 Workers AI·Jev로 두 제품의 E2E를 검증한다", async ({
  page,
  request,
  context,
}, testInfo) => {
  const source =
    "2026년 신규 고객 초기 설정 개선 전략을 한국어로 발표하려고 합니다. " +
    "목표는 고객 이탈률 12% 감소입니다. 기존 방식은 수동 입력으로 하루 2시간, " +
    "개선 방식은 자동 입력으로 하루 30분이 걸립니다. 개선 과제는 가입 절차 간소화, " +
    "초기 안내 강화, 고객 지원 확대입니다. 실행 과정은 문제 조사, 개선안 적용, " +
    "결과 확인 순서입니다. 주제 소개, 핵심 목표, 개선 과제, 기존·개선 방식 비교, " +
    "실행 과정, 결론과 다음 행동이 잘 전달되는 발표 흐름으로 정리해 주세요.";
  const edited =
    "PoC 검증 목표: 2026년 고객 이탈률을 12% 줄이는 것이 목표입니다.";
  let originalCatalogue = (await (
    await request.get(`${backend}/api/ontology`)
  ).json()) as Catalogue;
  const introduction =
    "발표 전체의 주제·구성·목적을 안내하는 소개 페이지. 구체적인 주장·목표·핵심 수치를 전달하는 것이 주된 경우는 강조로 구분한다.";
  const emphasis =
    "하나의 주장·목표·핵심 수치를 중심 메시지로 전달하는 페이지. 구체적인 달성 목표를 강조하는 내용도 포함하며 발표 전체를 안내하는 도입과 구분한다.";
  if (
    originalCatalogue.types.find((type) => type.id === "introduction")
      ?.description !== introduction ||
    originalCatalogue.types.find((type) => type.id === "emphasis")
      ?.description !== emphasis
  ) {
    const operator = await context.newPage();
    await operator.goto(ontologyUrl);
    await operator
      .getByLabel("introduction 유형 설명", { exact: true })
      .fill(introduction);
    await operator
      .getByLabel("emphasis 유형 설명", { exact: true })
      .fill(emphasis);
    await operator.getByRole("button", { name: "수정 내용 검수" }).click();
    await operator.getByRole("button", { name: "검수 완료·저장" }).click();
    await expect(operator.getByRole("status")).toContainText("저장했습니다");
    await operator.close();
    originalCatalogue = (await (
      await request.get(`${backend}/api/ontology`)
    ).json()) as Catalogue;
  }
  let ontologyChanged = false;
  const create = async () => {
    await page.goto("/");
    await page.getByLabel("어떤 발표를 준비하고 있나요?").fill(source);
    const outlineResponse = page.waitForResponse(
      (response) =>
        response.request().method() === "POST" &&
        response.url().endsWith("/api/presentations"),
    );
    await page.getByRole("button", { name: "개요 만들기" }).click();
    const created = await outlineResponse;
    expect(created.ok(), await created.text()).toBe(true);
    await expect(page.getByRole("heading", { name: /개요 편집/ })).toBeVisible({
      timeout: 180_000,
    });
    const id = page.url().split("/").pop() ?? "";
    const draft = (await (
      await request.get(`${backend}/api/presentations/${id}`)
    ).json()) as Presentation;
    const edits = [
      {
        title: "신규 고객 설정 개선 전략",
        key_message:
          "2026년 고객의 초기 설정 경험을 개선하는 방향을 소개합니다.",
        main_content: "고객 초기 설정의 문제와 개선 방향을 발표합니다.",
      },
      {
        title: "고객 이탈 감소 목표",
        key_message: edited,
        main_content:
          "고객 초기 설정 경험을 개선해 고객 이탈률 12% 감소를 목표로 합니다.",
      },
      {
        title: "개선 과제",
        key_message: "가입·안내·지원을 개선합니다.",
        main_content: "가입 절차 간소화\n초기 안내 강화\n고객 지원 확대",
      },
      {
        title: "입력 방식 비교",
        key_message: "자동 입력으로 하루 작업 시간을 줄입니다.",
        main_content:
          "기존 방식: 수동 입력에 하루 2시간이 걸립니다.\n개선 방식: 자동 입력에 하루 30분이 걸립니다.",
      },
      {
        title: "실행 단계",
        key_message: "조사·적용·확인 순서로 실행합니다.",
        main_content: "문제 조사 → 개선안 적용 → 결과 확인",
      },
      {
        title: "기대 효과",
        key_message: "작업 시간을 줄이고 고객의 초기 경험을 개선합니다.",
        main_content: "자동 입력과 쉬운 안내로 초기 설정의 부담을 줄입니다.",
      },
    ];
    for (let index = 0; index < draft.outline.pages.length; index++) {
      const edit =
        index === draft.outline.pages.length - 1
          ? {
              title: "다음 행동",
              key_message: "초기 설정 개선부터 실행합니다.",
              main_content:
                "문제 조사 결과를 바탕으로 개선안을 적용하고 효과를 확인합시다.",
            }
          : (edits[index] ?? {
              title: "고객 지원 강화",
              key_message: "초기 사용 중의 어려움을 빠르게 해결합니다.",
              main_content: "고객 지원을 확대해 설정 중의 어려움을 해결합니다.",
            });
      await page
        .getByLabel(`${index + 1}페이지 제목`, { exact: true })
        .fill(edit.title);
      await page
        .getByLabel(`${index + 1}페이지 핵심 메시지`, { exact: true })
        .fill(edit.key_message);
      await page
        .getByLabel(`${index + 1}페이지 주요 내용`, { exact: true })
        .fill(edit.main_content);
    }
    await page
      .getByRole("button", { name: "개요 확정하고 슬라이드 생성" })
      .click();
    await expect
      .poll(
        async () => {
          const current = (await (
            await request.get(`${backend}/api/presentations/${id}`)
          ).json()) as Presentation;
          return ["completed", "failed"].includes(current.status);
        },
        { timeout: 600_000, intervals: [1000, 2000] },
      )
      .toBe(true);
    const result = (await (
      await request.get(`${backend}/api/presentations/${id}`)
    ).json()) as Presentation;
    expect(result.status, result.error ?? result.phase).toBe("completed");
    await expect(page.getByText("완료", { exact: true })).toBeVisible();
    expect(result.slides.length).toBeGreaterThanOrEqual(6);
    expect(result.slides.length).toBeLessThanOrEqual(30);
    expect(result.slides).toHaveLength(result.outline.pages.length);
    expect(result.slides.map((slide) => slide.index)).toEqual(
      result.outline.pages.map((_, index) => index),
    );
    expect(result.outline.pages[1].key_message).toBe(edited);
    const editedSlide = JSON.stringify(result.slides[1].content);
    expect(editedSlide).toContain("2026");
    expect(editedSlide).toContain("12");
    for (const slide of result.slides) {
      expect(slide.trace.faithfulness?.choice).toBe("faithful");
      expect(slide.trace.selection.model).toBe("jev-1.13.0");
      expect(slide.trace.selection.choice).toBe(slide.layout.id);
      expect(slide.trace.ranked_candidates[0].layout_id).toBe(slide.layout.id);
    }
    return result;
  };
  try {
    const first = await create();
    const operator = await context.newPage();
    await operator.goto(ontologyUrl);
    await operator
      .getByLabel("list 용도", { exact: true })
      .fill(
        "PoC 검수: 항목과 비교 대상의 의미를 각 본문 블록에 보존하여 전달한다.",
      );
    await operator
      .getByLabel("comparison 사용 여부", { exact: true })
      .uncheck();
    await operator.getByRole("button", { name: "수정 내용 검수" }).click();
    await operator.getByRole("button", { name: "검수 완료·저장" }).click();
    await expect(operator.getByRole("status")).toContainText("저장했습니다");
    ontologyChanged = true;
    const second = await create();
    expect(second.snapshot?.version).toBe((first.snapshot?.version ?? 0) + 1);
    for (const slide of second.slides)
      expect(slide.trace.selection.probabilities).not.toHaveProperty(
        "comparison",
      );
    expect(
      second.slides.some((slide) =>
        JSON.stringify(slide.trace.selection_request).includes("PoC 검수"),
      ),
    ).toBe(true);
    const preserved = (await (
      await request.get(`${backend}/api/presentations/${first.id}`)
    ).json()) as Presentation;
    expect(preserved.snapshot).toEqual(first.snapshot);
    expect(preserved.slides).toEqual(first.slides);
    await testInfo.attach("real-model-evidence", {
      contentType: "application/json",
      body: JSON.stringify(
        {
          checked_at: new Date().toISOString(),
          presentations: [first, second].map((result) => ({
            id: result.id,
            status: result.status,
            page_count: result.slides.length,
            ontology_version: result.snapshot?.version,
            choices: result.slides.map((slide) => ({
              index: slide.index,
              type: slide.trace.classification.choice,
              layout: slide.layout.id,
              model: slide.trace.selection.model,
              candidates: slide.trace.ranked_candidates,
              usage: slide.trace.selection.usage,
            })),
          })),
        },
        null,
        2,
      ),
    });
  } finally {
    if (ontologyChanged) {
      const latest = (await (
        await request.get(`${backend}/api/ontology`)
      ).json()) as Catalogue;
      const restored = await request.put(`${backend}/api/ontology`, {
        data: { ...originalCatalogue, version: latest.version },
      });
      expect(restored.ok()).toBe(true);
    }
  }
});

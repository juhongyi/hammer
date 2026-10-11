import { expect, type Page, test } from "@playwright/test";
import type { components } from "@poc/api-types";

type Presentation = components["schemas"]["PresentationView"];
type Catalogue = components["schemas"]["Catalogue"];
const backend = process.env.API_URL ?? "http://127.0.0.1:18000";
const ontologyUrl = process.env.ONTOLOGY_URL ?? "http://127.0.0.1:13001";

test.skip(
  process.env.REAL_MODELS === "1",
  "Deterministic fixtures are tested separately from real models.",
);

async function createOutline(
  page: Page,
  source = "한국어 발표자료를 만들어 주세요.",
) {
  await page.goto("/");
  await page.getByLabel("어떤 발표를 준비하고 있나요?").fill(source);
  await page.getByRole("button", { name: "개요 만들기" }).click();
  await expect(page.getByRole("heading", { name: /개요 편집/ })).toBeVisible();
  return page.url().split("/").pop() ?? "";
}

test("개요 수정·완료 검사·Jev 근거·온톨로지 다음 생성 반영", async ({
  page,
  request,
  context,
}) => {
  const id = await createOutline(page);
  const edited = "수정한 목표: 고객 이탈률 12% 감소";
  await page.getByLabel("2페이지 핵심 메시지", { exact: true }).fill(edited);
  await page
    .getByRole("button", { name: "개요 확정하고 슬라이드 생성" })
    .click();
  await expect(page.getByText("완료", { exact: true })).toBeVisible();
  await expect(
    page.getByTestId("page-1").locator(".slide-message"),
  ).toContainText(edited);
  const first = (await (
    await request.get(`${backend}/api/presentations/${id}`)
  ).json()) as Presentation;
  expect(first.status).toBe("completed");
  expect(first.slides).toHaveLength(6);
  expect(first.slides.map((slide) => slide.layout.id)).toEqual([
    "cover",
    "message",
    "list",
    "comparison",
    "process",
    "closing",
  ]);
  const comparison = page.getByTestId("page-3");
  await comparison.getByText("Jev 판단 근거 · 후보와 선택 결과").click();
  await expect(comparison.getByText("비교 · 선택됨")).toBeVisible();

  const operator = await context.newPage();
  await operator.goto(ontologyUrl);
  await operator
    .getByLabel("list 용도", { exact: true })
    .fill("운영자 검수: 비교 대상을 목록으로 전달한다.");
  await operator.getByLabel("comparison 사용 여부", { exact: true }).uncheck();
  await operator.getByRole("button", { name: "수정 내용 검수" }).click();
  await expect(
    operator.getByRole("heading", { name: "수정 내용 검수" }),
  ).toBeVisible();
  await operator.getByRole("button", { name: "검수 완료·저장" }).click();
  await expect(operator.getByRole("status")).toContainText(
    "검수한 변경 내용을 저장했습니다.",
  );

  const nextId = await createOutline(page);
  await page
    .getByRole("button", { name: "개요 확정하고 슬라이드 생성" })
    .click();
  await expect(page.getByText("완료", { exact: true })).toBeVisible();
  const next = (await (
    await request.get(`${backend}/api/presentations/${nextId}`)
  ).json()) as Presentation;
  expect(next.snapshot?.version).toBe((first.snapshot?.version ?? 0) + 1);
  expect(next.slides[3].layout.id).toBe("list");
  for (const slide of next.slides)
    expect(slide.trace.selection.probabilities).not.toHaveProperty(
      "comparison",
    );
  expect(JSON.stringify(next.slides[3].trace.selection_request)).toContain(
    "운영자 검수",
  );
  const unchanged = await (
    await request.get(`${backend}/api/presentations/${id}`)
  ).json();
  expect(unchanged.slides).toEqual(first.slides);
  expect(unchanged.snapshot).toEqual(first.snapshot);

  await operator.getByLabel("comparison 사용 여부", { exact: true }).check();
  await operator.getByRole("button", { name: "수정 내용 검수" }).click();
  await operator.getByRole("button", { name: "검수 완료·저장" }).click();
  await expect(operator.getByRole("status")).toContainText("저장했습니다");
});

test("6종 디자인의 한국어 최대 용량이 잘림·겹침 없이 렌더링된다", async ({
  page,
  request,
}) => {
  const id = await createOutline(page, "test:max");
  await page
    .getByRole("button", { name: "개요 확정하고 슬라이드 생성" })
    .click();
  await expect(page.getByText("완료", { exact: true })).toBeVisible();
  const result = (await (
    await request.get(`${backend}/api/presentations/${id}`)
  ).json()) as Presentation;
  expect(result.status).toBe("completed");
  expect(
    result.slides.every(
      (slide) => Array.from(slide.content.title).length === 48,
    ),
  ).toBe(true);
  expect(result.slides.map((slide) => slide.content.blocks.length)).toEqual([
    1, 2, 6, 2, 5, 2,
  ]);
});

test("30장 전체를 검사하고 확정 순서를 유지한다", async ({ page, request }) => {
  const id = await createOutline(page, "test:30");
  await page
    .getByRole("button", { name: "개요 확정하고 슬라이드 생성" })
    .click();
  await expect(page.getByText("완료", { exact: true })).toBeVisible();
  const result = (await (
    await request.get(`${backend}/api/presentations/${id}`)
  ).json()) as Presentation;
  expect(result.slides.map((slide) => slide.index)).toEqual(
    Array.from({ length: 30 }, (_, index) => index),
  );
  await expect(page.locator("article[data-testid^='page-']")).toHaveCount(30);
});

test("실제 DOM 잘림을 발견하면 완료 대신 실패하고 개요를 보존한다", async ({
  page,
  request,
}) => {
  const id = await createOutline(page);
  await page.addStyleTag({
    content: ".slide-title { font-size: 300px !important; }",
  });
  await page
    .getByRole("button", { name: "개요 확정하고 슬라이드 생성" })
    .click();
  await expect(page.getByRole("main").getByRole("alert")).toContainText(
    "잘립니다",
  );
  await expect(page.getByText("완료", { exact: true })).toHaveCount(0);
  const result = (await (
    await request.get(`${backend}/api/presentations/${id}`)
  ).json()) as Presentation;
  expect(result.status).toBe("failed");
  expect(result.outline.pages).toHaveLength(6);
  await expect(
    page.getByRole("button", { name: "개요 확정하고 슬라이드 생성" }),
  ).toBeVisible();
});

test("모델 실패는 미완성으로 처리하고 개요를 편집해 재생성할 수 있다", async ({
  page,
  request,
}) => {
  const id = await createOutline(page);
  await request.post(`${backend}/test/provider-failure/true`);
  try {
    await page
      .getByRole("button", { name: "개요 확정하고 슬라이드 생성" })
      .click();
    await expect(page.getByRole("main").getByRole("alert")).toContainText(
      "HTTP 529",
    );
    await expect(page.getByText("완료", { exact: true })).toHaveCount(0);
    await expect(
      page.getByLabel("1페이지 제목", { exact: true }),
    ).toBeVisible();
  } finally {
    await request.post(`${backend}/test/provider-failure/false`);
  }
  await page
    .getByRole("button", { name: "개요 확정하고 슬라이드 생성" })
    .click();
  await expect(page.getByText("완료", { exact: true })).toBeVisible();
  const result = (await (
    await request.get(`${backend}/api/presentations/${id}`)
  ).json()) as Presentation;
  expect(result.status).toBe("completed");
});

test("온톨로지의 필수 지원 관계와 구조 상한을 검수 전에 검사한다", async ({
  page,
}) => {
  await page.goto(ontologyUrl);
  const catalogue = (await page.evaluate(async () =>
    (await fetch("/api/ontology")).json(),
  )) as Catalogue;
  const cover = catalogue.layouts.find((layout) => layout.id === "cover");
  expect(cover).toBeDefined();
  await page.getByLabel("cover 도입 지원", { exact: true }).uncheck();
  await page.getByRole("button", { name: "수정 내용 검수" }).click();
  await expect(page.getByRole("main").getByRole("alert")).toContainText(
    "지원 유형을 하나 이상",
  );
  await expect(
    page.getByRole("heading", { name: "수정 내용 검수" }),
  ).toHaveCount(0);
});

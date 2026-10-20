import { expect, test } from "@playwright/test";

test("ontology home is accessible", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("body")).toHaveCSS("font-family", /sans-serif/);
  await expect(
    page.getByRole("heading", { name: "Hammer Ontology" }),
  ).toBeVisible();
});

test("ontology API is healthy", async ({ request }) => {
  const response = await request.get("http://ontology-api:8000/health");
  expect(response.ok()).toBeTruthy();
  expect(await response.json()).toEqual({ status: "ok" });
});

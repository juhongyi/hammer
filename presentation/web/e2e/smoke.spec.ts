import { expect, test } from "@playwright/test";

test("presentation home is accessible", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("body")).toHaveCSS("font-family", /sans-serif/);
  await expect(
    page.getByRole("heading", { name: "Hammer Presentation" }),
  ).toBeVisible();
});

test("presentation API is healthy", async ({ request }) => {
  const response = await request.get("http://presentation-api:8000/health");
  expect(response.ok()).toBeTruthy();
  expect(await response.json()).toEqual({ status: "ok" });
});

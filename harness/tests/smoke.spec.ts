import { expect, test } from "@playwright/test";

for (const product of ["presentation", "ontology"]) {
  test(`${product} blank page loads without browser errors`, async ({
    page,
  }) => {
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    page.on("console", (message) => {
      if (message.type() === "error") errors.push(message.text());
    });
    const response = await page.goto(`http://${product}-web:3000`);
    expect(response?.status()).toBe(200);
    await expect(page).toHaveTitle(
      product === "presentation" ? "Presentation" : "Ontology",
    );
    await expect(page.locator("body")).toHaveText("");
    expect(errors).toEqual([]);
  });

  test(`${product} API health is reachable`, async ({ request }) => {
    const response = await request.get(`http://${product}-api:8000/health`);
    expect(response.status()).toBe(200);
    expect(await response.json()).toEqual({ status: "ok" });
  });
}

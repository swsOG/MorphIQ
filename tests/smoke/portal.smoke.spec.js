const { test, expect } = require("@playwright/test");

async function signIn(page, email, password) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
}

test("manager can report an issue and admin sees it in the issues workspace", async ({ page, context }) => {
  await signIn(page, "manager@example.test", "Password123!");

  await expect(page).toHaveURL(/\/overview$/);

  await page.goto("/document/by-id/1002");
  await expect(page.getByRole("heading", { name: "Delivery assurance" })).toBeVisible();
  await expect(page.getByText("What happens next")).toBeVisible();

  await page.locator("#document-issue-toggle").click();
  await page.locator("#document-issue-reason").selectOption("incorrect_field");
  await page.locator("#document-issue-note").fill("Tenant name needs correcting.");
  await page.locator("#document-issue-submit").click();

  await expect(page.locator("#document-issue-delivery-pill")).toContainText("Under Review");
  await expect(page.getByRole("heading", { name: "Issue timeline" })).toBeVisible();
  await expect(page.getByText("Issue #", { exact: false })).toBeVisible();

  await page.locator("#document-issue-support-link").click();
  await expect(page).toHaveURL(/\/settings\?client=Sample%20Agency%20Beta#settings-support-card$/);
  await expect(page.getByRole("heading", { name: "Support and delivery follow-up" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Support chat" })).toBeVisible();

  await page.goto("/logout");

  const adminPage = await context.newPage();
  await signIn(adminPage, "admin@example.test", "Password123!");
  await adminPage.goto("/issues?client=Sample%20Agency%20Beta");

  await expect(adminPage.getByRole("heading", { name: "Issues workspace" })).toBeVisible();
  await expect(adminPage.locator("#issues-metric-open")).toHaveText("1");
  await expect(adminPage.locator("#issues-queue-tbody")).toContainText("Review queue");
  await expect(adminPage.locator("#issues-queue-tbody")).toContainText("Sample Agency Beta");
});

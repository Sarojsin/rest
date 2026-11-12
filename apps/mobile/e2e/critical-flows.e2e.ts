/**
 * Phase 3 E2E Tests — Critical flows for mobile app feature parity.
 *
 * These tests run against a live backend with seeded data.
 * Required setup:
 *   - Backend running at API_BASE_URL (default http://localhost:8000)
 *   - Database seeded with demo data
 *   - Detox-built app installed on simulator/emulator
 *
 * Run: npx detox test -c android.emu.debug (or ios.sim.debug)
 */

import { by, device, element, expect, waitFor } from "detox";

const API_BASE_URL = process.env.API_BASE_URL || "http://localhost:8000";

const TEST_CREDENTIALS = {
  owner: { email: "owner@harbor.example", password: "HarborOwner!1" },
  waiter: { email: "waiter@harbor.example", password: "HarborWaiter!1" },
};

async function loginAs(role: "owner" | "waiter") {
  const creds = TEST_CREDENTIALS[role];

  // Wait for login screen
  await waitFor(element(by.id("login-screen"))).toBeVisible().withTimeout(10000);

  // Enter email
  await element(by.id("email-input")).typeText(creds.email);
  // Enter password
  await element(by.id("password-input")).typeText(creds.password);
  // Tap login
  await element(by.id("login-button")).tap();

  // Wait for main app to load
  await waitFor(element(by.id("main-tabs"))).toBeVisible().withTimeout(10000);
}

async function navigateToTab(tabName: "tables" | "orders" | "inventory" | "reports" | "account") {
  await element(by.id(`tab-${tabName}`)).tap();
  await waitFor(element(by.id(`${tabName}-screen`))).toBeVisible().withTimeout(10000);
}

describe("Authentication", () => {
  beforeAll(async () => {
    await device.launchApp({ newInstance: true });
  });

  it("should show login screen on first launch", async () => {
    await waitFor(element(by.id("login-screen"))).toBeVisible().withTimeout(10000);
  });

  it("should allow owner to login", async () => {
    await loginAs("owner");
    await expect(element(by.text("Tables"))).toBeVisible();
  });

  it("should allow waiter to login", async () => {
    await device.reloadReactNative();
    await loginAs("waiter");
    await expect(element(by.text("Tables"))).toBeVisible();
  });
});

describe("Order Claim & Escalate Flow", () => {
  beforeAll(async () => {
    await device.launchApp({ newInstance: true });
    await loginAs("waiter");
  });

  beforeEach(async () => {
    await device.reloadReactNative();
    await loginAs("waiter");
  });

  it("should allow waiter to claim an order", async () => {
    // Navigate to tables
    await navigateToTab("tables");

    // Select a table with pending orders
    await element(by.id("table-card-1")).tap();

    // Wait for order screen
    await waitFor(element(by.id("order-screen"))).toBeVisible().withTimeout(10000);

    // Claim the order
    await element(by.id("claim-order-button")).tap();

    // Verify claim state
    await waitFor(element(by.text("Claimed")))
      .toBeVisible()
      .withTimeout(10000);

    // Escalate the order
    await element(by.id("escalate-order-button")).tap();

    // Verify escalation
    await waitFor(element(by.text("Escalated")))
      .toBeVisible()
      .withTimeout(10000);
  });

  it("should show claim state on order card", async () => {
    await navigateToTab("tables");
    await element(by.id("table-card-1")).tap();
    await waitFor(element(by.id("order-screen"))).toBeVisible().withTimeout(10000);

    // Order should show claim badge
    await expect(element(by.id("claim-badge"))).toBeVisible();
  });
});

describe("Inventory Management", () => {
  beforeAll(async () => {
    await device.launchApp({ newInstance: true });
    await loginAs("owner");
  });

  beforeEach(async () => {
    await device.reloadReactNative();
    await loginAs("owner");
  });

  it("should allow owner to view inventory ingredients", async () => {
    await navigateToTab("inventory");

    // Verify ingredients list loads
    await waitFor(element(by.id("ingredients-list"))).toBeVisible().withTimeout(10000);
    await expect(element(by.text("Low Stock Item"))).toBeVisible();
  });

  it("should allow owner to adjust stock count", async () => {
    await navigateToTab("inventory");

    // Go to stock counts
    await element(by.id("stock-counts-button")).tap();
    await waitFor(element(by.id("stock-counts-screen"))).toBeVisible().withTimeout(10000);

    // Create new stock count
    await element(by.id("create-stock-count-button")).tap();

    // Select ingredient and enter counted quantity
    await element(by.id("ingredient-select-0")).tap();
    await element(by.id("counted-qty-input")).typeText("22");

    // Complete the count
    await element(by.id("complete-stock-count-button")).tap();

    // Verify completion
    await waitFor(element(by.text("Completed"))).toBeVisible().withTimeout(10000);
  });
});

describe("Employee & Shift Management", () => {
  beforeAll(async () => {
    await device.launchApp({ newInstance: true });
    await loginAs("owner");
  });

  beforeEach(async () => {
    await device.reloadReactNative();
    await loginAs("owner");
  });

  it("should allow owner to view employees", async () => {
    await navigateToTab("inventory");
    await element(by.id("employees-tab")).tap();

    await waitFor(element(by.id("employees-list"))).toBeVisible().withTimeout(10000);
  });

  it("should allow owner to create a shift", async () => {
    await navigateToTab("inventory");
    await element(by.id("employees-tab")).tap();
    await waitFor(element(by.id("employees-list"))).toBeVisible().withTimeout(10000);

    await element(by.id("create-shift-button")).tap();
    await waitFor(element(by.id("create-shift-screen"))).toBeVisible().withTimeout(10000);

    // Select employee, date, and shift type
    await element(by.id("employee-select")).tap();
    await element(by.text("Waiter Staff")).tap();

    await element(by.id("shift-date-input")).typeText("2026-12-01");
    await element(by.id("shift-type-select")).tap();
    await element(by.text("Morning")).tap();

    // Save shift
    await element(by.id("save-shift-button")).tap();

    // Verify shift created
    await waitFor(element(by.text("Shift created"))).toBeVisible().withTimeout(10000);
  });
});

describe("Reports Access", () => {
  beforeAll(async () => {
    await device.launchApp({ newInstance: true });
    await loginAs("owner");
  });

  beforeEach(async () => {
    await device.reloadReactNative();
    await loginAs("owner");
  });

  it("should allow owner to view sales report", async () => {
    await navigateToTab("reports");

    await waitFor(element(by.id("reports-screen"))).toBeVisible().withTimeout(10000);
    await element(by.id("sales-report-button")).tap();

    await waitFor(element(by.id("sales-report-screen"))).toBeVisible().withTimeout(10000);
    await expect(element(by.text("Sales Report"))).toBeVisible();
  });
});

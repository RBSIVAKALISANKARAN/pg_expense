import os
import sys
import uuid
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect, sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

BASE_URL = os.getenv("E2E_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
USERNAME = os.getenv("E2E_USERNAME")
PASSWORD = os.getenv("E2E_PASSWORD")

pytestmark = pytest.mark.browser


@pytest.fixture(scope="session")
def browser_context():
    if not USERNAME or not PASSWORD:
        pytest.skip("Set E2E_USERNAME and E2E_PASSWORD before running Phase 7 browser tests.")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        page.goto(f"{BASE_URL}/login/", wait_until="networkidle")
        page.locator("#id_username").fill(USERNAME)
        page.locator("#id_password").fill(PASSWORD)
        page.get_by_role("button", name="Sign in").click()
        expect(page).to_have_url(f"{BASE_URL}/api/dashboard/")
        yield context
        context.close()
        browser.close()


@pytest.fixture
def page(browser_context):
    p = browser_context.new_page()
    yield p
    p.close()


def open_page(page: Page, path: str, heading: str):
    page.goto(f"{BASE_URL}{path}", wait_until="networkidle")
    expect(page.locator("body")).to_contain_text(heading)


def select_option_containing(select_locator, text):
    option = select_locator.locator("option").filter(has_text=text).first
    value = option.get_attribute("value")
    assert value, f"No option containing {text!r} was found"
    select_locator.select_option(value=value)
    expect(select_locator).to_have_value(value)


def ensure_owner_is_me(page):
    select_option_containing(page.locator("#expense-owner"), "Me")


def ensure_first_wallet_has_funds(page, amount="100"):
    open_page(page, "/api/accounts/page/", "Accounts & wallets")
    card = page.locator("#deposit-grid .account-card").first
    card.locator(".deposit").fill(amount)
    card.get_by_role("button", name="Add").click()
    expect(card).to_contain_text("₹")


def test_7_1_dashboard_smoke(page):
    open_page(page, "/api/dashboard/", "Your money at a glance")
    expect(page.locator("#dash-total")).to_be_visible()
    expect(page.get_by_role("link", name="Record expense").first).to_be_visible()
    page.get_by_role("link", name="Record expense").first.click()
    expect(page).to_have_url(f"{BASE_URL}/api/expense/page/")


def test_7_2_accounts_create_deposit_transfer_and_balance(page):
    open_page(page, "/api/accounts/page/", "Accounts & wallets")
    suffix = uuid.uuid4().hex[:8]
    source = f"E2E Source {suffix}"
    destination = f"E2E Destination {suffix}"

    try:
        page.locator("#new-account-toggle").click()
        page.locator("#acct-name").fill(source)
        page.locator("#acct-location").fill(source)
        page.locator("#create-account-btn").click()
        expect(page.locator("#create-account-msg")).to_contain_text("Wallet created")

        page.locator("#acct-name").fill(destination)
        page.locator("#acct-location").fill(destination)
        page.locator("#create-account-btn").click()
        expect(page.locator("#create-account-msg")).to_contain_text("Wallet created")

        source_card = page.locator("#deposit-grid .account-card").filter(has_text=source)
        source_card.locator(".deposit").fill("500")
        source_card.get_by_role("button", name="Add").click()
        expect(source_card).to_contain_text("₹500.00")

        select_option_containing(page.locator("#transfer-from"), source)
        select_option_containing(page.locator("#transfer-to"), destination)
        assert page.locator("#transfer-from").input_value() != page.locator("#transfer-to").input_value()
        select_option_containing(page.locator("#transfer-owner"), "Me")
        page.locator("#transfer-amount").fill("150")
        page.locator("#transfer-money").click()
        expect(page.locator("#transfer-message")).to_contain_text("Transfer completed")

        source_balance = page.locator("#accounts-grid .account-card").filter(has_text=source)
        destination_balance = page.locator("#accounts-grid .account-card").filter(has_text=destination)
        expect(source_balance).to_contain_text("₹350.00")
        expect(destination_balance).to_contain_text("₹150.00")
    finally:
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pg_expense.settings")
        import django
        django.setup()
        from django.db import close_old_connections
        from wallet.models import Account

        close_old_connections()
        Account.objects.filter(name__in=[source, destination]).delete()


def test_7_3_expense_workflow(page):
    ensure_first_wallet_has_funds(page)
    open_page(page, "/api/expense/page/", "Record an expense")
    page.locator("#expense-account").select_option(index=0)
    ensure_owner_is_me(page)
    page.locator("#expense-amount").fill("25")
    page.locator("#expense-merchant").fill("Phase 7 Browser Test")
    page.locator("#expense-note").fill("browser workflow")
    page.locator("#save-expense").click()
    expect(page.locator("#expense-message")).to_contain_text("Expense saved and wallet reconciled")


def test_7_4_transactions_search_edit_revert_delete(page):
    ensure_first_wallet_has_funds(page)
    open_page(page, "/api/expense/page/", "Record an expense")
    page.locator("#expense-account").select_option(index=0)
    ensure_owner_is_me(page)
    page.locator("#expense-amount").fill("25")
    page.locator("#expense-merchant").fill("Phase 7 Browser Test")
    page.locator("#save-expense").click()
    expect(page.locator("#expense-message")).to_contain_text("Expense saved and wallet reconciled")

    open_page(page, "/api/transactions/page/", "Transaction ledger")
    page.locator("#filter-search").fill("Phase 7 Browser Test")
    page.locator("#apply-filters").click()
    expect(page.locator("#body")).to_contain_text("Phase 7 Browser Test")

    row = page.locator("#body tr").filter(has_text="Phase 7 Browser Test").first
    row.get_by_role("button", name="Edit").click()
    expect(page.locator("#edit-panel")).to_be_visible()
    page.locator("#edit-amount").fill("30")
    page.locator("#save-edit").click()
    expect(page.locator("#edit-panel")).to_be_hidden()

    page.locator("#reset-filters").click()
    row = page.locator("#body tr").first
    with page.expect_dialog() as dialog_info:
        row.get_by_role("button", name="Revert").click()
    dialog_info.value.accept()
    page.wait_for_timeout(300)
    expect(page.locator("#body")).to_contain_text("Reverted")

    ensure_first_wallet_has_funds(page)
    open_page(page, "/api/expense/page/", "Record an expense")
    page.locator("#expense-account").select_option(index=0)
    ensure_owner_is_me(page)
    page.locator("#expense-amount").fill("15")
    page.locator("#expense-merchant").fill("Phase 7 Delete Test")
    page.locator("#save-expense").click()
    expect(page.locator("#expense-message")).to_contain_text("Expense saved and wallet reconciled")
    open_page(page, "/api/transactions/page/", "Transaction ledger")
    page.locator("#filter-search").fill("Phase 7 Delete Test")
    page.locator("#apply-filters").click()
    row = page.locator("#body tr").filter(has_text="Phase 7 Delete Test").first
    with page.expect_dialog() as dialog_info:
        row.get_by_role("button", name="Delete").click()
    dialog_info.value.accept()
    page.wait_for_timeout(300)
    expect(page.locator("#body")).to_contain_text("Deleted")


def test_7_5_categories_master_data(page):
    open_page(page, "/api/categories/page/", "Categories & master data")
    suffix = uuid.uuid4().hex[:8]
    name = f"E2E Category {suffix}"
    page.locator("#category-name").fill(name)
    page.locator("#category-desc").fill("Phase 7 browser master-data test")
    page.locator("#create-category-btn").click()
    expect(page.locator("#category-msg")).to_contain_text("Category created")
    expect(page.locator("#category-list")).to_contain_text(name)


def test_7_6_savings_actual_browser_flow(page):
    ensure_first_wallet_has_funds(page, "20")
    open_page(page, "/api/accounts/page/", "Accounts & wallets")
    card = page.locator("#allocation-grid .account-card").first
    card.locator(".allocation-amount").fill("5")
    card.get_by_role("button", name="→ Savings").click()
    expect(page.locator("#allocation-message")).to_contain_text("Moved to Savings successfully")
    page.wait_for_timeout(250)
    card = page.locator("#allocation-grid .account-card").first
    card.locator(".allocation-amount").fill("5")
    card.get_by_role("button", name="→ Spendable").click()
    expect(page.locator("#allocation-message")).to_contain_text("Moved to Spendable successfully")


def test_7_7_sql_playground(page):
    open_page(page, "/api/sql/", "PostgreSQL SQL Playground")
    expect(page.locator("#sql-editor")).to_be_visible()
    expect(page.locator("#saved-list")).to_be_visible()
    expect(page.locator("#history-list")).to_be_visible()
    page.locator("#sql-editor").fill("SELECT 1 AS browser_test;")
    page.locator("#run-query").click()
    expect(page.locator("#sql-output")).to_contain_text("browser_test")
    expect(page.locator("#history-list")).to_contain_text("SELECT 1 AS browser_test")


def test_7_8_reports(page):
    open_page(page, "/api/reports/page/", "Reports")
    expect(page.locator("body")).not_to_contain_text("Unable to load")


def test_7_9_settings_persists_after_reload(page):
    open_page(page, "/api/settings/page/", "General preferences")
    value = f"Expense OS E2E {uuid.uuid4().hex[:6]}"
    page.locator("#app-name").fill(value)
    page.get_by_role("button", name="Save settings").click()
    expect(page.locator("#settings-message")).to_contain_text("Settings saved successfully")
    page.reload(wait_until="networkidle")
    expect(page.locator("#app-name")).to_have_value(value)


@pytest.mark.parametrize("path,heading", [
    ("/api/dashboard/", "Your money at a glance"),
    ("/api/accounts/page/", "Accounts & wallets"),
    ("/api/expense/page/", "Record an expense"),
    ("/api/categories/page/", "Categories & master data"),
    ("/api/transactions/page/", "Transaction ledger"),
    ("/api/savings/page/", "Savings"),
    ("/api/reports/page/", "Reports"),
    ("/api/settings/page/", "General preferences"),
    ("/api/sql/", "PostgreSQL SQL Playground"),
])
def test_7_10_responsive_major_pages(page, path, heading):
    for width in (1440, 768, 390):
        page.set_viewport_size({"width": width, "height": 900})
        open_page(page, path, heading)
        expect(page.locator("body")).to_be_visible()
        expect(page.locator("body")).not_to_contain_text("Internal Server Error")

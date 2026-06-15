"""Coverage for business menus that were previously unmapped (and thus admin-only,
locking out office/accountant/viewer). These assertions lock in the intended
access so the matrix stays usable AND safe.
"""
from permissions import check


# --- billing / rates / customers: operational + finance-ish ---
def test_billing_office_and_accountant_can_use():
    assert check("office", "/billing", "GET") == "edit"
    assert check("accountant", "/billing", "GET") in ("edit", "view")
    assert check("viewer", "/billing", "GET") == "view"


def test_rates_office_edit_viewer_view():
    assert check("office", "/rates", "GET") == "edit"
    assert check("viewer", "/rates", "POST") == "deny"


def test_customers_office_can_edit():
    assert check("office", "/customers", "POST") == "edit"


# --- fuel family: operational ---
def test_fuel_menus_office_edit():
    for p in ("/fuel", "/fuel-index", "/fuel-surcharge"):
        assert check("office", p, "GET") == "edit", p
        assert check("viewer", p, "GET") == "view", p


# --- dispatch: operational ---
def test_dispatch_office_edit():
    assert check("office", "/dispatch/planner", "POST") == "edit"


# --- ops (lcb fuel dispatch tool): operational ---
def test_ops_office_can_use():
    assert check("office", "/ops/lcb-fuel-dispatch", "GET") in ("edit", "view")


# --- import: sensitive (bulk data change) — admin only ---
def test_import_admin_only():
    assert check("admin", "/import", "POST") == "edit"
    assert check("office", "/import", "GET") == "deny"
    assert check("accountant", "/import", "GET") == "deny"


# --- email inbox: sensitive (company mailbox) — admin + accountant only ---
def test_email_inbox_restricted():
    assert check("admin", "/email/inbox", "GET") == "edit"
    assert check("accountant", "/email/inbox", "GET") in ("edit", "view")
    assert check("office", "/email/inbox", "GET") == "deny"
    assert check("viewer", "/email/inbox", "GET") == "deny"


# --- api: write endpoints inherit the menu they belong to; unknown still admin-only ---
def test_unknown_route_still_fail_closed():
    assert check("office", "/totally-unknown-xyz", "GET") == "deny"
    assert check("admin", "/totally-unknown-xyz", "GET") == "edit"

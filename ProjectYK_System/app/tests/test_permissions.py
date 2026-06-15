from permissions import check, ROLES


def test_roles_are_the_four_expected():
    assert ROLES == ["admin", "office", "accountant", "viewer"]


def test_admin_can_edit_everything():
    assert check("admin", "/payroll", "POST") == "edit"
    assert check("admin", "/admin/users", "GET") == "edit"


def test_office_cannot_see_payroll_or_finance():
    assert check("office", "/payroll", "GET") == "deny"
    assert check("office", "/finance", "GET") == "deny"


def test_office_can_edit_daily_but_only_view_master():
    assert check("office", "/daily/new", "POST") == "edit"
    assert check("office", "/employees", "GET") == "view"
    assert check("office", "/employees/5/edit", "POST") == "deny"  # view-only -> edit denied


def test_accountant_sees_payroll_edit_finance_view():
    assert check("accountant", "/payroll", "POST") == "edit"
    assert check("accountant", "/finance", "GET") == "view"
    assert check("accountant", "/finance", "POST") == "deny"


def test_viewer_view_only_and_no_money_menus():
    assert check("viewer", "/daily", "GET") == "view"
    assert check("viewer", "/daily/new", "POST") == "deny"
    assert check("viewer", "/payroll", "GET") == "deny"


def test_only_admin_reaches_admin_users():
    assert check("office", "/admin/users", "GET") == "deny"
    assert check("accountant", "/admin/users", "GET") == "deny"


def test_unmapped_prefix_defaults_admin_only():
    assert check("office", "/something-new", "GET") == "deny"
    assert check("admin", "/something-new", "GET") == "edit"

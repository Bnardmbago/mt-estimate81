from app.estimates.project_name import is_usable_project_name


def test_default_project_names_are_not_usable():
    assert not is_usable_project_name("New Estimate")
    assert not is_usable_project_name("新規見積")
    assert not is_usable_project_name("")
    assert not is_usable_project_name("   ")


def test_real_project_names_are_usable():
    assert is_usable_project_name("Customer Portal")
    assert is_usable_project_name("  Inventory App  ")

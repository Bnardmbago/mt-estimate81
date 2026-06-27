from app.auth.disposable_domains import is_disposable_email


def test_disposable_email_blocks_known_domains():
    assert is_disposable_email("user@mailinator.com") is True
    assert is_disposable_email("user@yopmail.com") is True


def test_regular_email_is_allowed():
    assert is_disposable_email("user@example.com") is False
    assert is_disposable_email("user@company.co.jp") is False

============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.1.1, pluggy-1.6.0 -- /home/juno/Desktop/ASD 2026/project-ASD/.venv/bin/python
cachedir: .pytest_cache
rootdir: /home/juno/Desktop/ASD 2026/project-ASD/student-1
configfile: pyproject.toml
plugins: platformdirs-4.13.0, anyio-4.14.2
collecting ... collected 9 items

post_commit/test_api_cards.py::test_service_health PASSED                [ 11%]
post_commit/test_api_cards.py::test_cards_exist PASSED                   [ 22%]
post_commit/test_api_cards.py::test_card_by_id PASSED                    [ 33%]
post_commit/test_api_cards.py::test_freeze_card PASSED                   [ 44%]
post_commit/test_api_users.py::test_service_health_users PASSED          [ 55%]
post_commit/test_api_users.py::test_users_exist PASSED                   [ 66%]
post_commit/test_token_auth.py::test_valid_token_decodes PASSED          [ 77%]
post_commit/test_token_auth.py::test_expired_token_rejected PASSED       [ 88%]
post_commit/test_token_auth.py::test_invalid_signature_rejected PASSED   [100%]

=============================== warnings summary ===============================
tests/post_commit/test_token_auth.py::test_invalid_signature_rejected
  /home/juno/Desktop/ASD 2026/project-ASD/.venv/lib/python3.12/site-packages/jwt/api_jwt.py:368: InsecureKeyLengthWarning: The HMAC key is 12 bytes long, which is below the minimum recommended length of 32 bytes for SHA256. See RFC 7518 Section 3.2.
    decoded = self.decode_complete(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
========================= 9 passed, 1 warning in 0.37s =========================

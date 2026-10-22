============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.1.1, pluggy-1.7.0 -- C:\Users\hugeg\AppData\Local\Temp\claude\d--ASD-project-ASD\5403453d-cb94-45cf-91f6-e1c7b4d476f3\scratchpad\tvenv\Scripts\python.exe
rootdir: D:\ASD\project-ASD\student-2
configfile: pyproject.toml
plugins: anyio-4.15.1, platformdirs-4.13.5
collecting ... collected 12 items

tests/post_commit/test_api_accounts.py::test_service_health PASSED       [  8%]
tests/post_commit/test_api_accounts.py::test_accounts_exist PASSED       [ 16%]
tests/post_commit/test_api_accounts.py::test_account_by_id PASSED        [ 25%]
tests/post_commit/test_api_accounts.py::test_unknown_account_returns_404 PASSED [ 33%]
tests/post_commit/test_api_accounts.py::test_accounts_by_user PASSED     [ 41%]
tests/post_commit/test_api_accounts.py::test_accounts_by_status PASSED   [ 50%]
tests/post_commit/test_api_accounts.py::test_account_balance PASSED      [ 58%]
tests/post_commit/test_token_auth.py::test_valid_token_decodes PASSED    [ 66%]
tests/post_commit/test_token_auth.py::test_expired_token_rejected PASSED [ 75%]
tests/post_commit/test_token_auth.py::test_invalid_signature_rejected PASSED [ 83%]
tests/post_commit/test_token_auth.py::test_backend_issues_and_verifies_token PASSED [ 91%]
tests/post_commit/test_token_auth.py::test_backend_rejects_expired_token PASSED [100%]

============================= 12 passed in 0.69s ==============================

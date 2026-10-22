# Student-2 Pre-Commit Security Scan Report

Run: 2026-10-22T13:00:35Z  |  Command: pre-commit run <student-2 hook> --all-files --verbose

```
student-2 Ruff Scan......................................................Passed
- hook id: student-2-ruff-scan
- duration: 3.8s

============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.1.1, pluggy-1.7.0 -- C:\Users\hugeg\.cache\pre-commit\repo8kqvg6y1\py_env-python3\Scripts\python.EXE
cachedir: .pytest_cache
rootdir: D:\ASD\project-ASD\student-2
configfile: pyproject.toml
collecting ... collected 1 item

student-2\tests\pre_commit\test_ruff_scan.py::test_ruff_scan_passes PASSED [100%]

============================== 1 passed in 2.32s ==============================

student-2 detect-secrets Scan............................................Passed
- hook id: student-2-detect-secrets-scan
- duration: 3.32s

============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.1.1, pluggy-1.7.0 -- C:\Users\hugeg\.cache\pre-commit\repongbazkna\py_env-python3\Scripts\python.EXE
cachedir: .pytest_cache
rootdir: D:\ASD\project-ASD\student-2
configfile: pyproject.toml
collecting ... collected 1 item

student-2\tests\pre_commit\test_secrets_scan.py::test_detect_secrets_scan_passes PASSED [100%]

============================== 1 passed in 1.97s ==============================

student-2 pip-audit Scan.................................................Passed
- hook id: student-2-pip-audit-scan
- duration: 121.68s

============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.1.1, pluggy-1.7.0 -- C:\Users\hugeg\.cache\pre-commit\repox8uw64et\py_env-python3\Scripts\python.EXE
cachedir: .pytest_cache
rootdir: D:\ASD\project-ASD\student-2
configfile: pyproject.toml
plugins: platformdirs-4.13.5
collecting ... collected 4 items

student-2\tests\pre_commit\test_dependency_audit.py::test_requirements_files_found PASSED [ 25%]
student-2\tests\pre_commit\test_dependency_audit.py::test_pip_audit_passes[backend\\requirements.txt] PASSED [ 50%]
student-2\tests\pre_commit\test_dependency_audit.py::test_pip_audit_passes[database\\requirements.txt] PASSED [ 75%]
student-2\tests\pre_commit\test_dependency_audit.py::test_pip_audit_passes[tests\\requirements.txt] PASSED [100%]

======================== 4 passed in 120.00s (0:02:00) ========================

```

Exit code: 0

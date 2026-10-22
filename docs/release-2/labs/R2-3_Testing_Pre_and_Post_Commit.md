# Lab R2-3 - Pre-Commit Security Scans và Post-Commit Endpoint Tests (student-5)

**Course:** Advanced Software Development with Agentic AI (ASD 2026)  
**Project:** Digital Banking System - Group 44, Release 2  
**Theme:** Testing: pre-commit scans and post-commit CI/CD tests  
**Primary IDE:** VS Code  
**AI Agent Runtime:** Ollama (qwen2.5:0.5b, llama3.1:8b)  
**Duration:** 60 phút  
**Viết cho:** student-5 (Gia), làm lại từ nhánh `main` sạch  
**Dựa trên:** `asd-labs/Lab_11_Testing_Deployment_and_Operations.md`, Section 4 (Testing Implementation)  
**Làm sau:** Lab R2-2  

---

## 1. Overview

<details>
<summary>Goal</summary>

**Post-commit (tiêu chí 4):** mỗi lần push, `student-5.yml` dựng 3 container của student-5 và chạy **2 test endpoint thật**:

* `GET /transactions` (hàm `list_transactions`)
* `GET /transactions/<id>` (hàm `get_transaction`)

rồi ghi `post-commit-report.md` thành artifact.

**Pre-commit (tiêu chí 3):** mỗi lần `git commit`, git hook chạy 3 bản quét cho student-5:

* Ruff, chỉ luật bảo mật `S` (flake8-bandit)
* detect-secrets
* pip-audit

</details>

<details>
<summary>Two-Stage Testing</summary>

| Giai đoạn | Chạy khi | Ở đâu | Kiểm tra |
|---|---|---|---|
| Pre-commit | `git commit` | Máy bạn (git hook) | Ruff `S`, detect-secrets, pip-audit |
| Post-commit | `git push` | GitHub Actions (`student-5.yml`) | 2 endpoint của backend đang chạy |

Pre-commit chặn code xấu **trước** khi vào lịch sử git; post-commit chứng minh bản đã push **chạy được**.

</details>

<details>
<summary>Expected Results</summary>

* `pytest student-5/tests/post_commit -v` → 2 passed (local)
* `pre-commit run --all-files` → 6 hook Passed (3 của student-1, 3 của student-5)
* Run `student-5` trên GitHub xanh, có artifact `student-5-post-commit-report`
* Hai commit: `student-5: post-commit endpoint tests in CI` và `Pre-commit security scans: launcher, student-1 and student-5 hooks`

Lúc viết lab, pip-audit đã tìm ra **lỗ hổng thật** trong thư viện của student-5 (Flask, Flask-Cors, requests), và Ruff tìm ra `debug=True` trong database. Lab sửa cả hai.

</details>

---

## 2. Prerequisites and Configuration

<details>
<summary>Install Dependencies</summary>

Cài vào `.venv` của repo, **không** cài vào Python hệ thống (nếu không, pip-audit sẽ quét cả môi trường máy):

```bash
.venv/bin/python -m pip install pytest requests pre-commit ruff detect-secrets pip-audit
```

| Gói | Dùng cho |
|---|---|
| `pytest`, `requests` | test post-commit gọi API |
| `pre-commit` | khung git hook |
| `ruff` | quét mã nguồn |
| `detect-secrets` | quét mật khẩu, khóa bị lộ |
| `pip-audit` | quét lỗ hổng thư viện |

</details>

<details>
<summary>Project Structure</summary>

```
.pre-commit-config.yaml                          # sửa  - hook cho student-1 và student-5
scripts/pre_commit_pytest.py                     # MỚI  - launcher cho hook
.github/workflows/student-5.yml                  # sửa  - job post-commit
student-5/
├── pyproject.toml                               # MỚI  - cấu hình Ruff (chỉ luật S)
├── backend/requirements.txt                     # sửa  - nâng phiên bản có lỗ hổng
├── database/requirements.txt                    # sửa  - nâng Flask
├── database/app.py                              # sửa  - debug theo biến môi trường, ghi chú S608
└── tests/
    ├── post_commit/test_endpoints_live.py       # MỚI
    └── pre_commit/                              # MỚI  - chép từ student-1
        ├── test_ruff_scan.py
        ├── test_secrets_scan.py
        └── test_dependency_audit.py
```

</details>

---

## 3. Post-Commit Tests (CI/CD Pipeline)

<details>
<summary>Purpose</summary>

Test gọi **backend thật đang chạy** (backend → database API), không dùng mock như 94 unit test cũ. Vì vậy nó chạy trong job thứ 2 của `student-5.yml`, sau khi `docker compose up`.

</details>

<details>
<summary>student-5/tests/post_commit/test_endpoints_live.py</summary>

```python
"""Post-commit endpoint tests for student-5 (Transaction Management).

student-5.yml runs these after the containers start. They call the real
backend on port 8205, which calls the real database API, so they test two
deployed endpoint functions end to end instead of mocks:

  1. list_transactions  -> GET /transactions
  2. get_transaction    -> GET /transactions/<txn_id>
"""

import os

import pytest
import requests

BACKEND_URL = os.getenv("STUDENT5_BACKEND_URL", "http://localhost:8205")
TIMEOUT = 10


def _get(path: str) -> requests.Response:
    try:
        return requests.get(f"{BACKEND_URL}{path}", timeout=TIMEOUT)
    except requests.RequestException as exc:
        pytest.fail(f"Backend not reachable at {BACKEND_URL}{path}: {exc}")


def test_list_transactions_endpoint():
    """GET /transactions returns the seeded rows, honours limit, and has the expected fields."""
    resp = _get("/transactions?limit=5")

    assert resp.status_code == 200
    body = resp.json()
    rows = body.get("transactions")
    assert isinstance(rows, list)
    assert 0 < len(rows) <= 5
    assert body.get("count") == len(rows)
    for field in ("transaction_id", "transaction_type", "amount", "status"):
        assert field in rows[0], f"missing field {field}"


def test_get_transaction_endpoint():
    """GET /transactions/<id> returns that one row, and 404 for an id that does not exist."""
    first_id = _get("/transactions?limit=1").json()["transactions"][0]["transaction_id"]

    found = _get(f"/transactions/{first_id}")
    assert found.status_code == 200
    assert found.json()["transaction_id"] == first_id

    missing = _get("/transactions/999999")
    assert missing.status_code == 404
```

**Giải thích:**

* `BACKEND_URL` mặc định `http://localhost:8205`, đổi được bằng `STUDENT5_BACKEND_URL`.
* `_get` biến lỗi kết nối thành `pytest.fail` có câu dễ đọc, thay vì traceback dài.
* Test 1 kiểm tra `limit` được tôn trọng (1–5 dòng), `count` khớp số dòng, đủ trường quan trọng.
* Test 2 lấy id thật từ test 1 (không đoán id), kiểm tra 200, và kiểm tra id không tồn tại trả **404**.

</details>

<details>
<summary>Run Locally</summary>

```bash
docker compose up -d --build student5-db student5-backend student5-frontend
pytest student-5/tests/post_commit -v
```

```
student-5/tests/post_commit/test_endpoints_live.py::test_list_transactions_endpoint PASSED [ 50%]
student-5/tests/post_commit/test_endpoints_live.py::test_get_transaction_endpoint PASSED  [100%]
============================== 2 passed ==============================
```

</details>

<details>
<summary>.github/workflows/student-5.yml</summary>

````yaml
# Student 5 - Gia Tran - Transaction Management
name: student-5

on:
  push:
    paths:
      - "student-5/**"
      - "docker-compose.yml"
      - ".github/workflows/student-5.yml"
  pull_request:
    paths:
      - "student-5/**"
  workflow_dispatch:

jobs:
  # 1. Unit and integration tests (mocked, no containers)
  tests:
    name: Tests
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r student-5/backend/requirements.txt
          pip install -r student-5/database/requirements.txt
          pip install pytest
      - name: Run pytest
        # post_commit/ needs the running containers (next job); pre_commit/ is the
        # local security scan run by the git hook, not by CI.
        run: pytest student-5/tests -v --ignore=student-5/tests/post_commit --ignore=student-5/tests/pre_commit

  # 2. Build the three containers, smoke test, then post-commit endpoint tests
  build-and-smoke:
    name: Build, smoke and post-commit tests
    runs-on: ubuntu-latest
    needs: [tests]
    env:
      MCP_ENABLED: "false" # Disable MCP in CI
      RAG_ENABLED: "false" # Disable RAG in CI
      MULTI_AGENT_ENABLED: "false" # Disable Multi-Agent in CI
    steps:
      - uses: actions/checkout@v4

      - name: Verify docker-compose
        run: docker-compose --version || (sudo apt-get update && sudo apt-get install -y docker-compose)

      - name: Build student-5 services
        run: docker compose build student5-db student5-backend student5-frontend

      - name: Start student-5 services
        run: docker compose up -d student5-db student5-backend student5-frontend

      - name: Smoke checks
        run: |
          check_url() {
            local url="$1"
            local attempts=10
            local code=""

            for i in $(seq 1 "$attempts"); do
              code=$(curl -sS -o /dev/null -w "%{http_code}" \
                     --connect-timeout 5 --max-time 20 "$url" || true)
              if [ "$code" = "200" ]; then
                echo "PASS  $url -> $code"
                return 0
              fi
              echo "wait  $i/$attempts  $url (got: ${code:-none})"
              sleep 3
            done

            echo "FAIL  $url after $attempts attempts"
            return 1
          }

          check_url "http://localhost:8105/"
          check_url "http://localhost:8205/health"
          check_url "http://localhost:8305/health"

      # Post-commit testing: two endpoint functions of the running backend
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Post-commit endpoint tests
        id: postcommit
        run: |
          pip install pytest requests
          mkdir -p reports/post-commit
          pytest student-5/tests/post_commit -v \
            --junitxml=reports/post-commit/junit.xml \
            | tee reports/post-commit/test-results.txt

      - name: Write post-commit report
        if: always()
        run: |
          mkdir -p reports/post-commit
          {
            echo "# Student 5 - Post-commit endpoint test report"
            echo ""
            echo "| Field | Value |"
            echo "|---|---|"
            echo "| Workflow run | https://github.com/${{ github.repository }}/actions/runs/${{ github.run_id }} |"
            echo "| Commit | ${{ github.sha }} |"
            echo "| Branch | ${{ github.ref_name }} |"
            echo "| Endpoints tested | GET /transactions, GET /transactions/<id> |"
            echo "| Result | ${{ steps.postcommit.outcome }} |"
            echo "| Generated | $(date -u +%Y-%m-%dT%H:%M:%SZ) |"
            echo ""
            echo '```'
            cat reports/post-commit/test-results.txt 2>/dev/null || echo "no test output"
            echo '```'
          } > reports/post-commit/post-commit-report.md
          cat reports/post-commit/post-commit-report.md

      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: student-5-post-commit-report
          path: reports/post-commit

      # MCP
      - name: Confirm MCP is disabled in CI
        run: |
          code=$(curl -sS -o /tmp/mcp_response.json -w "%{http_code}" \
                 http://localhost:8205/mcp/transactions)
          echo "MCP endpoint returned: $code"
          cat /tmp/mcp_response.json
          if [ "$code" != "403" ]; then
            echo "Expected 403 (MCP disabled) but got $code"
            exit 1
          fi
          echo "PASS - MCP correctly disabled in CI"
      # RAG
      - name: Confirm RAG is disabled in CI
        run: |
          code=$(curl -sS -o /tmp/rag_response.json -w "%{http_code}" \
                  -X POST -d "query=test" \
                  http://localhost:8205/rag/answer)
          echo "RAG endpoint returned: $code"
          cat /tmp/rag_response.json
          if [ "$code" != "403" ]; then
            echo "Expected 403 (RAG disabled) but got $code"
            exit 1
          fi
          echo "PASS - RAG correctly disabled in CI"
      # Multi-Agent
      - name: Confirm Multi-Agent is disabled in CI
        run: |
          code=$(curl -sS -o /tmp/ma_response.json -w "%{http_code}" \
                  -X POST -d "user_request=test" \
                  http://localhost:8205/multi-agent/workflow)
          echo "Multi-Agent endpoint returned: $code"
          cat /tmp/ma_response.json
          if [ "$code" != "403" ]; then
            echo "Expected 403 (Multi-Agent disabled) but got $code"
            exit 1
          fi
          echo "PASS - Multi-Agent correctly disabled in CI"

      - name: Stop services
        if: always()
        run: docker compose down -v

  # 3. Evidence for the technical report
  evidence-pack:
    name: Evidence pack
    runs-on: ubuntu-latest
    needs: [build-and-smoke]

    steps:
      - uses: actions/checkout@v4

      - name: Generate CI evidence
        run: |
          mkdir -p reports

          cat > reports/report.json << EOF
          {
            "workflow": "student-5",
            "student": "student-5",
            "feature": "Transaction Management",
            "owner": "Gia Tran",
            "run_id": "${{ github.run_id }}",
            "commit_sha": "${{ github.sha }}",
            "branch": "${{ github.ref_name }}",
            "generated_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
          }
          EOF

          cat > reports/report.md << EOF
          - Workflow: student-5 
          - Run ID: ${{ github.run_id }} 
          - Commit: ${{ github.sha }} 
          - Branch: ${{ github.ref_name }} 
          - Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)
          EOF
      - name: Generate run-view.md
        run: |
          cat > reports/run-view.md << EOF
          Run URL:
          https://github.com/${{ github.repository }}/actions/runs/${{ github.run_id }}
          EOF

      - uses: actions/upload-artifact@v4
        with:
          name: student-5-ci-report
          path: reports
````

**Giải thích các thay đổi so với `main`:**

| Chỗ | Vì sao |
|---|---|
| Job `tests`: `--ignore=…/post_commit --ignore=…/pre_commit` | `post_commit/` cần container (chạy ở job sau); `pre_commit/` là bản quét chạy bằng git hook, máy CI không cài ruff/pip-audit |
| `MULTI_AGENT_ENABLED: "false"` | CI không có Multi-Agent Server; route phải trả 403 |
| Bước `Post-commit endpoint tests` (`id: postcommit`) | Chạy 2 test, lưu `junit.xml` và `test-results.txt` |
| Bước `Write post-commit report` (`if: always()`) | Luôn ghi `post-commit-report.md`, kể cả khi test fail, kèm link run, commit, kết quả |
| `upload-artifact` `student-5-post-commit-report` | Tải về làm bằng chứng tiêu chí 4 |
| Bước `Confirm Multi-Agent is disabled in CI` | Kiểm tra 403, giống MCP và RAG |

</details>

<details>
<summary>Commit (post-commit)</summary>

```bash
git add student-5/tests/post_commit .github/workflows/student-5.yml
git commit -m "student-5: post-commit endpoint tests in CI"
```

</details>

---

## 4. Pre-Commit Security Scans

<details>
<summary>What Is Wrong on main</summary>

`.pre-commit-config.yaml` trên `main` có hook cho student-1, nhưng mỗi hook chạy:

```yaml
entry: python scripts/student-1/tests/pre_commit/test_ruff_scan.py -v
```

* Đường dẫn `scripts/student-1/...` không tồn tại (test nằm ở `student-1/tests/pre_commit/`)
* `python test_x.py` chỉ **định nghĩa** các hàm test, không chạy chúng

Theo Lab 11, mỗi hook chạy pytest qua một launcher. Ta sửa cho cả student-1 (giữ nguyên test của Juno) và thêm student-5. **Báo Juno** vì file này dùng chung.

</details>

<details>
<summary>scripts/pre_commit_pytest.py</summary>

```python
"""Pre-commit hook launcher: cd into the repository root, then run pytest.

Same idea as Lab 11's scripts/lab11/pre_commit_pytest.py. A hook cannot run a
test file directly with `python test_x.py` (that defines test functions but
never calls them), so every hook runs pytest through this launcher instead.
It works the same on macOS, Linux and Windows.
"""
import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main() -> int:
    os.chdir(REPO_ROOT)
    return subprocess.call([sys.executable, "-m", "pytest", *sys.argv[1:]])  # noqa: S603 - fixed pytest call


if __name__ == "__main__":
    sys.exit(main())
```

**Giải thích:** `cd` về thư mục gốc repo rồi chạy `python -m pytest <đối số>`. Dùng `sys.executable` nên chạy đúng Python trong môi trường của hook, trên cả macOS, Linux, Windows.

</details>

<details>
<summary>.pre-commit-config.yaml</summary>

```yaml
# Pre-commit security scans (Release 2, criterion 3).
#
#   pre-commit install            # once per clone: adds the git hook
#   pre-commit run --all-files    # run every scan now
#
# Each student has three hooks. A hook runs that student's pytest file in
# student-N/tests/pre_commit/ through scripts/pre_commit_pytest.py, so the
# commit is blocked when Ruff (S rules), detect-secrets or pip-audit fails.
# Hook ids contain ruff-scan / detect-secrets-scan / pip-audit-scan so the
# agentic loop Pre-Test Review can find them.
#
# To add a student: copy a block below, change the number, and make sure
# student-N/tests/pre_commit/ and student-N/pyproject.toml exist.

repos:
  - repo: local
    hooks:
      # ---- student-1 ----
      - id: student-1-ruff-scan
        name: student-1 Ruff Scan
        entry: python scripts/pre_commit_pytest.py student-1/tests/pre_commit/test_ruff_scan.py -v
        language: python
        additional_dependencies: ["pytest==9.1.1", "ruff==0.16.8"]
        pass_filenames: false
        stages: [pre-commit]
      - id: student-1-detect-secrets-scan
        name: student-1 detect-secrets Scan
        entry: python scripts/pre_commit_pytest.py student-1/tests/pre_commit/test_secrets_scan.py -v
        language: python
        additional_dependencies: ["pytest==9.1.1", "detect-secrets==1.5.0"]
        pass_filenames: false
        stages: [pre-commit]
      - id: student-1-pip-audit-scan
        name: student-1 pip-audit Scan
        entry: python scripts/pre_commit_pytest.py student-1/tests/pre_commit/test_dependency_audit.py -v
        language: python
        additional_dependencies: ["pytest==9.1.1", "pip-audit==2.10.1"]
        pass_filenames: false
        stages: [pre-commit]

      # ---- student-5 ----
      - id: student-5-ruff-scan
        name: student-5 Ruff Scan
        entry: python scripts/pre_commit_pytest.py student-5/tests/pre_commit/test_ruff_scan.py -v
        language: python
        additional_dependencies: ["pytest==9.1.1", "ruff==0.16.8"]
        pass_filenames: false
        stages: [pre-commit]
      - id: student-5-detect-secrets-scan
        name: student-5 detect-secrets Scan
        entry: python scripts/pre_commit_pytest.py student-5/tests/pre_commit/test_secrets_scan.py -v
        language: python
        additional_dependencies: ["pytest==9.1.1", "detect-secrets==1.5.0"]
        pass_filenames: false
        stages: [pre-commit]
      - id: student-5-pip-audit-scan
        name: student-5 pip-audit Scan
        entry: python scripts/pre_commit_pytest.py student-5/tests/pre_commit/test_dependency_audit.py -v
        language: python
        additional_dependencies: ["pytest==9.1.1", "pip-audit==2.10.1"]
        pass_filenames: false
        stages: [pre-commit]
```

**Giải thích:**

* `repo: local`: hook chạy code trong repo, không tải hook từ GitHub.
* `language: python` + `additional_dependencies`: pre-commit tự tạo môi trường riêng có đúng phiên bản pytest/ruff/detect-secrets/pip-audit.
* `pass_filenames: false`: mỗi hook quét cả thư mục sinh viên, không chỉ file vừa sửa.
* Id hook chứa `ruff-scan`, `detect-secrets-scan`, `pip-audit-scan` để chế độ Pre-Test Review của agentic loop tìm thấy.
* Thêm sinh viên khác: chép một khối, đổi số; thư mục `student-N/tests/pre_commit/` và `student-N/pyproject.toml` phải có trước.

</details>

<details>
<summary>Pre-Commit Tests for student-5</summary>

Ba file test của student-1 tự tìm thư mục sinh viên từ vị trí của chính nó (`Path(__file__).resolve().parents[2]`), nên chép sang là dùng được ngay:

```bash
mkdir -p student-5/tests/pre_commit
cp student-1/tests/pre_commit/test_ruff_scan.py \
   student-1/tests/pre_commit/test_secrets_scan.py \
   student-1/tests/pre_commit/test_dependency_audit.py \
   student-5/tests/pre_commit/
```

Bảng dưới **mô tả** mỗi test chạy gì bên trong; không cần gõ. Muốn chạy tay thì dùng cột cuối.

| Test | Bên trong test chạy | Pass khi | Chạy tay (từ thư mục gốc repo) |
|---|---|---|---|
| `test_ruff_scan.py` | `ruff check .` trong `student-5/` | không có lỗi luật `S` | `(cd student-5 && ruff check .)` |
| `test_secrets_scan.py` | `detect-secrets scan` trong `student-5/` | không tìm thấy gì | `(cd student-5 && detect-secrets scan)` |
| `test_dependency_audit.py` | `pip-audit -r <file>` cho **từng** `requirements*.txt` trong `student-5/` | không có lỗ hổng đã biết | `pip-audit -r student-5/backend/requirements.txt` và `pip-audit -r student-5/database/requirements.txt` |

Hoặc chạy cả 3 test một lần: `pytest student-5/tests/pre_commit -v`.

</details>

<details>
<summary>student-5/tests/pre_commit/test_ruff_scan.py</summary>

```python
import subprocess
import sys
from pathlib import Path

STUDENT_DIR = Path(__file__).resolve().parents[2]  # .../student-1


def test_ruff_scan_passes():
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "--output-format=concise", "."],
        capture_output=True,
        text=True,
        check=False,
        cwd=STUDENT_DIR,
    )
    returncode = result.returncode
    assert returncode == 0, result.stdout + result.stderr
```

Nội dung để đối chiếu (đã chép ở bước trên).

</details>

<details>
<summary>student-5/tests/pre_commit/test_secrets_scan.py</summary>

```python
import json
import subprocess
import sys
from pathlib import Path

STUDENT_DIR = Path(__file__).resolve().parents[2]  # .../student-1



def test_detect_secrets_scan_passes():
    result = subprocess.run(
        [sys.executable, "-m", "detect_secrets", "scan", "--exclude-files", "legacy-lab3/.*"],
        capture_output=True,
        text=True,
        check=False,
        cwd=STUDENT_DIR,
    )
    returncode = result.returncode  # avoid pytest reprinting the full CompletedProcess in the assert
    assert returncode == 0, result.stderr
    findings = json.loads(result.stdout)
    assert findings.get("results", {}) == {}, "Potential secrets detected"
```

Nội dung để đối chiếu.

</details>

<details>
<summary>student-5/tests/pre_commit/test_dependency_audit.py</summary>

```python
import subprocess
import sys
from pathlib import Path

import pytest

STUDENT_DIR = Path(__file__).resolve().parents[2]  # .../student-1
REQUIREMENTS_FILES = sorted(STUDENT_DIR.rglob("requirements*.txt"))


def test_requirements_files_found():
    # parametrize silently skips on an empty list, so this guards against a glob that matches nothing
    assert REQUIREMENTS_FILES, f"No requirements files found under {STUDENT_DIR}"


@pytest.mark.parametrize(
    "req_file",
    REQUIREMENTS_FILES,
    ids=lambda p: str(p.relative_to(STUDENT_DIR)),
)
def test_pip_audit_passes(req_file):
    result = subprocess.run(
        [sys.executable, "-m", "pip_audit", "-r", str(req_file)],
        capture_output=True,
        text=True,
        check=False,
    )
    returncode = result.returncode  # avoid pytest reprinting the full CompletedProcess in the assert
    assert returncode == 0, result.stdout + result.stderr




    
# import subprocess
# import sys


# def test_pip_audit_passes():
#     result = subprocess.run(
#         [sys.executable, "-m", "pip_audit"],
#         capture_output=True,
#         text=True,
#     )
#     returncode = result.returncode  # avoid pytest reprinting the full CompletedProcess in the assert
#     assert returncode == 0, result.stdout + result.stderr
```

Nội dung để đối chiếu.

</details>

<details>
<summary>student-5/pyproject.toml</summary>

```toml
# Ruff configuration for student-5's pre-commit security scan.
# Run from student-5/ by tests/pre_commit/test_ruff_scan.py.

[tool.ruff.lint]
# Security scan only: flake8-bandit (S) rules, not style rules.
select = ["S"]
# S104: containers must bind 0.0.0.0, otherwise Docker/Azure cannot reach the service.
ignore = ["S104"]

[tool.ruff.lint.per-file-ignores]
# S101: pytest needs assert. S603: the scan tests run fixed tool commands, not user input.
"tests/**" = ["S101", "S603"]
```

**Giải thích:** Ruff đọc file này vì test chạy `ruff check` từ thư mục `student-5/`.

* `select = ["S"]`: chỉ luật bảo mật. Không có dòng này, Ruff chạy cả luật kiểu dáng (sắp xếp import…), không phải "security scan".
* `ignore = ["S104"]`: container **phải** nghe ở `0.0.0.0`, nếu không Docker/Azure không vào được.
* `tests/**`: bỏ `S101` (pytest cần `assert`) và `S603` (test quét gọi lệnh cố định).

</details>

<details>
<summary>Run the Scans and Fix the Findings</summary>

Chạy thử Ruff trước khi sửa:

```bash
cd student-5 && ruff check --output-format=concise . ; cd ..
```

```
database/app.py:217:9: S608 Possible SQL injection vector through string-based query construction
database/app.py:271:69: S201 Use of `debug=True` in Flask app detected
Found 2 errors.
```

**Lỗi 1 - S608 (báo nhầm):** câu `UPDATE` ghép tên cột từ 2 chuỗi cố định (`"description = ?"`, `"status = ?"`), mọi giá trị đều là tham số `?`. Không có chỗ cho dữ liệu người dùng vào SQL, nên ghi chú lý do và bỏ qua đúng dòng đó.

Trong `student-5/database/app.py`, tìm:

```python
    con.execute(
        f"UPDATE transactions SET {', '.join(fields)} WHERE transaction_id = ?",
        params,
    )
```

Thay bằng:

```python
    con.execute(
        # Column names come only from the two fixed strings above; every value is a ? parameter.
        f"UPDATE transactions SET {', '.join(fields)} WHERE transaction_id = ?",  # noqa: S608
        params,
    )
```

**Lỗi 2 - S201 (lỗi thật):** `debug=True` bật Werkzeug debugger, cho phép chạy code từ trình duyệt. Tìm dòng cuối file:

```python
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), debug=True)
```

Thay bằng:

```python
    # Debug mode exposes the Werkzeug debugger, so it is off unless FLASK_DEBUG=true.
    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), debug=debug_mode)
```

Chạy lại: `All checks passed!`

**pip-audit:**

```bash
pip-audit -r student-5/backend/requirements.txt
```

```
Name       Version ID              Fix Versions
flask      3.0.3   PYSEC-2026-2151 3.1.3
flask-cors 4.0.1   PYSEC-2024-71   4.0.2
flask-cors 4.0.1   PYSEC-2026-1383 6.0.0   (và 1384, 1385)
requests   2.32.3  PYSEC-2026-1872 2.32.4
requests   2.32.3  PYSEC-2026-2275 2.33.0
Found 14 known vulnerabilities in 3 packages
```

Nâng lên phiên bản đã vá (đã thử: 94 unit test, 2 test endpoint, CORS và Multi-Agent vẫn chạy):

</details>

<details>
<summary>student-5/backend/requirements.txt</summary>

```text
Flask==3.1.3
Flask-Cors==6.0.0
requests==2.33.0
openai==1.34.0
httpx==0.27.2   # openai 1.34.0 passes proxies= which httpx>=0.28 removed
mcp<2
```

Đổi 3 dòng đầu: `Flask==3.1.3`, `Flask-Cors==6.0.0`, `requests==2.33.0`. Giữ nguyên `openai==1.34.0` và `httpx==0.27.2`.

</details>

<details>
<summary>student-5/database/requirements.txt</summary>

```text
Flask==3.1.3
```

`Flask==3.1.3`.

</details>

<details>
<summary>Install the Git Hook and Verify</summary>

```bash
pre-commit install                 # một lần mỗi máy: thêm hook vào .git/hooks
pre-commit run --all-files
```

Lần đầu mất vài phút để tạo môi trường cho hook. Mong đợi:

```
student-1 Ruff Scan......................................................Passed
student-1 detect-secrets Scan............................................Passed
student-1 pip-audit Scan.................................................Passed
student-5 Ruff Scan......................................................Passed
student-5 detect-secrets Scan............................................Passed
student-5 pip-audit Scan.................................................Passed
```

Lưu kết quả làm bằng chứng tiêu chí 3:

```bash
mkdir -p student-5/tests/reports
pre-commit run --all-files --verbose 2>&1 | tee student-5/tests/reports/pre-commit-report.txt
```

Sau khi cài hook, **mỗi `git commit` tự chạy 6 hook**. Có hook Failed thì commit bị chặn; sửa rồi commit lại. Muốn thấy hook chặn thật: thêm tạm `debug=True` vào `app.run` rồi thử commit, sau đó bỏ đi.

</details>

<details>
<summary>Regression Tests</summary>

```bash
docker compose up -d --build student5-db student5-backend student5-frontend
pytest student-5/tests -q --ignore=student-5/tests/post_commit --ignore=student-5/tests/pre_commit     # 94 passed
pytest student-5/tests/post_commit -v                                                       # 2 passed
```

</details>

---

## 5. Checkpoint, Commit and Push

<details>
<summary>Checkpoint</summary>

- [ ] `pre-commit run --all-files`: 6 Passed
- [ ] `pre-commit-report.txt` đã lưu
- [ ] 94 unit test + 2 test endpoint pass với thư viện mới

</details>

<details>
<summary>Commit and Push</summary>

```bash
git add .pre-commit-config.yaml scripts/pre_commit_pytest.py \
        student-5/pyproject.toml student-5/tests/pre_commit student-5/tests/reports \
        student-5/backend/requirements.txt student-5/database/requirements.txt student-5/database/app.py
git commit -m "Pre-commit security scans: launcher, student-1 and student-5 hooks; fix student-5 findings"
# commit này cũng chạy qua 6 hook

git push -u origin release2-gia
```

Trên GitHub → **Actions** → run `student-5` của nhánh `release2-gia`:

1. Job `Tests` xanh (94 test)
2. Job `Build, smoke and post-commit tests` xanh, có bước `Post-commit endpoint tests` 2 passed và `Confirm Multi-Agent is disabled in CI` PASS
3. Cuối trang run có artifact **student-5-post-commit-report** → tải về, mở `post-commit-report.md`

Chụp màn hình run xanh và file báo cáo (bằng chứng tiêu chí 4).

</details>

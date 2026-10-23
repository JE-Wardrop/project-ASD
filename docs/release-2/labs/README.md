# Release 2 Labs - Group 44 (student-5)

Bộ lab theo đúng khuôn `asd-labs` (Lab 10, Lab 11), để làm lại toàn bộ phần Release 2 của student-5 **từ `main` sạch**, từng bước, copy-paste được.

## Thứ tự

| Lab | Nội dung | Tiêu chí | Commit cuối lab |
|---|---|---|---|
| [R2-1](R2-1_Multi_Agent_Server.md) | Multi-Agent Server dùng chung (bản của Binh, nguyên văn) | 2 | `Multi-Agent Server: shared multi-feature version (Binh)` |
| [R2-2](R2-2_Student5_Multi_Agent_Integration.md) | Proxy + tab Multi-Agent của student-5 | 1, 2 | `student-5: Multi-Agent proxy route and UI tab` |
| [R2-3](R2-3_Testing_Pre_and_Post_Commit.md) | Test post-commit trong `student-5.yml`, pre-commit Ruff/detect-secrets/pip-audit | 3, 4 | 2 commit + push |
| [R2-4](R2-4_Azure_Cloud_Deployment.md) | Proxy nginx 4 frontend, script Azure, `cloud-deployment.yml` | 5, 6, 7 | 1–2 commit |

Agentic loop (tiêu chí 8) do Juno làm, không nằm trong bộ lab này.

## Bắt đầu

```bash
cd ~/project-ASD
git status                               # sạch
git fetch origin
git switch -c release2-gia origin/main   # nhánh mới; các nhánh cũ giữ làm bản sao lưu
```

## Cách đọc

* Mỗi file code nằm trong một khối thu gọn có tên là **đường dẫn file**. Mở file đó trong VS Code, chọn tất cả, dán đè.
* Chỗ nào chỉ sửa vài dòng, lab ghi rõ **"Tìm … Thay bằng …"**.
* Mỗi lab kết thúc bằng **Checkpoint** (tự kiểm tra) và **Commit**.
* Code trong lab là bản đã chạy thử từ `main` mới nhất (20/10, `c8b2d10`): 94 unit test, 2 test endpoint, 6 hook pre-commit, server Multi-Agent, proxy student-5. Phần chạy trên Azure ghi rõ đã/chưa kiểm chứng ở đầu Lab R2-4.

## Báo nhóm

| Ai | Việc |
|---|---|
| Binh | Server của anh ấy vào `main` qua PR của nhánh này (Lab R2-1); không cần merge lại |
| Juno | `.pre-commit-config.yaml` đổi sang launcher, hook student-1 giờ chạy được (Lab R2-3); `GET /cards` có lỗi; script cloud đã sửa 6 chỗ (Lab R2-4); collector Deployment Review không nên đòi `--registry-identity system` |
| Cả nhóm | Thêm 3 hook pre-commit cho mình bằng cách chép khối student-5 trong `.pre-commit-config.yaml` |

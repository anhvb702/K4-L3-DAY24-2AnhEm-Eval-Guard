# Nhóm thực hiện K4 Track 3B

Tên nhóm: 3ChangLinhNguLam

Repo chung: https://github.com/anhvb702/K4-L3-DAY24-3ChangLinhNguLam-Eval-Guard

Trưởng nhóm/người nộp: Vũ Bá Anh — 2A202602893

Ngày lab/deadline áp dụng: Deadline áp dụng theo xác nhận trưởng nhóm: 23:59 ngày 12/10/2026 — Asia/Ho_Chi_Minh (UTC+07:00)

Commit dùng để chấm: chưa chốt; sẽ ghi SHA sau khi kiểm tra và commit phần Phase A.

Mỗi nhóm nộp một repo. Điền đủ thành viên và một mục INDIVIDUAL cho từng người.
Thêm/xóa rows để khớp nhóm thật; mẫu ba rows không ép nhóm phải có ba người.

## Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò / công việc thật | Bằng chứng |
|---|---|---|---|---|
| 1 | Vũ Bá Anh | 2A202602893 | Trưởng nhóm; tích hợp m1–m5, chạy setup và Phase A, kiểm chứng Tasks 1–4 với AI hỗ trợ | src/phase_a_ragas.py; artifacts/answers_50q.json; artifacts/ragas_50q.json; doc/reports/failure_clusters.md; kết quả terminal |
| 2 | {{Họ tên}} | {{MSSV}} | {{Phase/file/hàm}} | {{Commit/PR/report}} |
| 3 | {{Họ tên}} | {{MSSV}} | {{Phase/file/hàm}} | {{Commit/PR/report}} |

Người tích hợp/chạy batch/nộp link: Vũ Bá Anh. Đã chạy setup và batch Phase A bằng PowerShell; artifacts và báo cáo là bằng chứng. Commit/push và nộp link chưa được xác nhận hoàn thành.

## Môi trường và chuẩn bị trước lớp

OS/Python/compiler: Windows, Python 3.11.9 trong .venv; chưa ghi nhận phiên bản compiler.
Virtualenv/dependencies/imports: pip check đạt; NumPy 1.26.4, PyArrow 18.1.0; datasets/RAGAS và m1–m5 import đạt. Đã xử lý lỗi PyArrow 26.0.0 yêu cầu NumPy 2 bằng pin PyArrow 18.1.0. Tests support: 75 passed; tests Phase A và CP0 interface: 27 passed. Kiểm chứng cuối validate_answers/validate_phase_a/validate_metadata đạt (schema, nguồn, counts, metrics, bottom 10, matrix và hashes); git diff --check không có lỗi whitespace.
Models/Qdrant/50 answers đã chuẩn bị: Qdrant v1.9.7 truy cập được; BGE-M3 encode từ cache trả vector (1024,), reranker predict trả score hữu hạn 0.769943118095398. Setup thật tạo 50 answers đúng 20/20/10, 48 LLM gpt-4o-mini-2024-07-18 và 2 extractive_fallback (IDs 1, 9) do generation timeout; không thiếu contexts. Enrichment có 1 fallback/102 chunks. Hai PDF scan không index. Full NeMo chưa cài (ModuleNotFoundError); không tuyên bố guard stack sẵn sàng.
Nếu cài full NeMo chưa thành công, ghi lỗi thực tế; không dùng unit test pass
hoặc pip resolve để khẳng định runtime đã chạy.

## INDIVIDUAL

Sao chép mẫu cho mỗi thành viên; tiêu đề họ tên không dấu-MSSV.

### VuBaAnh-2A202602893

- Phần được giao và phần thực tế đã làm: phụ trách Phase A; chuẩn bị/tích hợp m1–m5, sửa tương thích môi trường, chạy pipeline sinh 50 answers, chạy RAGAS thật và kiểm chứng Tasks 1–4 do Codex hỗ trợ implement. Codex hỗ trợ viết phân tích lỗi từ artifact; trưởng nhóm chịu trách nhiệm kiểm tra nội dung trước khi nộp.
- Bằng chứng: artifacts/answers_50q.json, artifacts/ragas_50q.json (created_at 2026-10-12T09:52:02.327394+00:00), src/phase_a_ragas.py, tests/test_phase_a.py, tests/test_cp0_interface.py, doc/reports/failure_clusters.md và output terminal. Commit SHA chưa chốt.
- Cách kiểm tra: chạy support tests (75 passed); tests Phase A/CP0 interface (27 passed); setup_answers.py --live tạo 50 answers; validate_answers đạt schema/nguồn; run_experiments.py --phase a --live chạy 200/200 metric và lưu JSON. Kiểm tra cuối validate_phase_a/validate_metadata đạt theo output PowerShell; git diff --check không có lỗi whitespace.
- Điều đã học: matrix worst_metric đếm mọi câu, nhóm yếu phải chọn bằng mean (multi_hop 0.638094); retrieval phù hợp chưa chắc đủ coverage; score faithfulness cao không đảm bảo số liệu đúng và score thấp cần đối chiếu answer/contexts/reference.
- Giới hạn/cách xử lý: 2 generation timeout giữ đúng extractive_fallback; 2 PDF scan thiếu text layer chưa OCR; enrichment có 1 fallback; chưa làm Phase B/C hoặc calibration/guard/latency. Giữ nguyên dữ liệu và số đo thật, ghi giới hạn trong báo cáo.
- Nguồn/AI hỗ trợ: m1–m5 từ bài RAG trước theo yêu cầu lab (nguồn chi tiết trong artifacts/cp0_provenance.json); Codex CLI/Desktop hỗ trợ rà giao diện, sửa adapter, implement Tasks 1–4 và soạn báo cáo/TEAM. Vũ Bá Anh chạy lệnh PowerShell và đối chiếu output, tests và artifacts; không dùng số đo do AI bịa.

## Cập nhật sau khi nộp

{{Ghi phiên bản nộp; nếu sửa sau deadline, ghi commit/thời điểm/lý do và thông báo
coach cho phép áp dụng bản cập nhật. Nếu không có cập nhật, ghi rõ không có.}}

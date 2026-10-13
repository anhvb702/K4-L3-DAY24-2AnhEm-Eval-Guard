# Nhóm thực hiện K4 Track 3B

Tên nhóm: 3ChangLinhNguLam

Repo chung: https://github.com/anhvb702/K4-L3-DAY24-3ChangLinhNguLam-Eval-Guard

Trưởng nhóm/người nộp: Vũ Bá Anh — 2A202602893

Ngày lab/deadline áp dụng: Deadline theo xác nhận coach: 11:59 AM ngày 13/10/2026 — Asia/Ho_Chi_Minh (UTC+07:00)

Commit bằng chứng kỹ thuật Phase A: 270296ab585c57523f531c82fe2b5126eec0fd90 (đã push phase-A). Commit nộp cuối toàn nhóm sẽ được trưởng nhóm xác nhận khi hoàn thiện bài chung.

Mỗi nhóm nộp một repo. Điền đủ thành viên và một mục INDIVIDUAL cho từng người.
Thêm/xóa rows để khớp nhóm thật; mẫu ba rows không ép nhóm phải có ba người.

## Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò / công việc thật | Bằng chứng |
|---|---|---|---|---|
| 1 | Vũ Bá Anh | 2A202602893 | Trưởng nhóm; tích hợp m1–m5, chạy setup và Phase A, kiểm chứng Tasks 1–4 với AI hỗ trợ | src/phase_a_ragas.py; artifacts/answers_50q.json; artifacts/ragas_50q.json; doc/reports/failure_clusters.md; kết quả terminal |
| 2 | Phùng Đình Triển | 2A202602837 | Implement và chạy Phase B: pairwise judge, swap-and-average, Cohen's kappa, bias analysis; xử lý tương thích judge model | src/phase_b_judge.py; artifacts/judge_results.json; doc/reports/bias_report.md; commit 4ffef73 |
| 3 | Phạm Anh Minh | 2A202603009 | Phụ trách Phase C; triển khai input/output guard và latency, chạy batch guard thật, hoàn thiện blueprint | src/phase_c_guard.py; guardrails/config.yml; tests/test_phase_c.py; artifacts/guard_results.json; doc/reports/blueprint.md |

Người tích hợp/chạy setup Phase A/nộp link: Vũ Bá Anh. Đã chạy setup và batch Phase A bằng PowerShell; artifacts và báo cáo là bằng chứng. Đã commit/push phần Phase A lên nhánh phase-A tại 270296ab585c57523f531c82fe2b5126eec0fd90. Phase B được merge vào main; Phase C được bổ sung trong đợt hoàn thiện ngày 13/10/2026.

## Môi trường và chuẩn bị trước lớp

OS/Python/compiler: Windows, Python 3.11.9 trong .venv; chưa ghi nhận phiên bản compiler.
Virtualenv/dependencies/imports: pip check đạt theo lần kiểm tra CP0; phiên bản môi trường hiện tại: NumPy 1.26.4, PyArrow 20.0.0, NeMo Guardrails 0.10.0. Tests Phase C: 13 passed; batch C thật hoàn tất và artifacts được checker validate. Tests support/Phase A và CP0 đã chạy ở giai đoạn trước; các kết quả đó không tự chứng minh mọi runtime/model đã sẵn sàng.
Models/Qdrant/50 answers đã chuẩn bị: Qdrant v1.9.7 truy cập được; BGE-M3 encode từ cache trả vector (1024,), reranker predict trả score hữu hạn 0.769943118095398. Setup thật tạo 50 answers đúng 20/20/10, 48 LLM gpt-4o-mini-2024-07-18 và 2 extractive_fallback (IDs 1, 9) do generation timeout; không thiếu contexts. Enrichment có 1 fallback/102 chunks. Hai PDF scan không index. NeMo input/output rails đã được khởi tạo; batch Phase C live dùng model cấu hình gpt-4o-mini.
Môi trường của Phùng Đình Triển (Phase B): Windows, Python 3.11 trong .venv-tests (môi trường unit test offline). Môi trường đầy đủ .venv không cài được trên máy này vì lỗi build Annoy (thiếu Microsoft C++ Build Tools). Trong .venv-tests, tests/test_phase_b.py đạt 8 passed; 6 test của tests/test_cp0_interface.py fail do thiếu numpy và ragas (thuộc phần m3/m4, không liên quan Phase B). Phase B chạy live qua API OpenAI nên không cần Qdrant, NeMo hay spaCy.

## INDIVIDUAL

### VuBaAnh-2A202602893

- Phần được giao và phần thực tế đã làm: phụ trách Phase A; chuẩn bị/tích hợp m1–m5, sửa tương thích môi trường, chạy pipeline sinh 50 answers, chạy RAGAS thật và kiểm chứng Tasks 1–4 do Codex hỗ trợ implement. Codex hỗ trợ viết phân tích lỗi từ artifact; trưởng nhóm chịu trách nhiệm kiểm tra nội dung trước khi nộp.
- Bằng chứng: artifacts/answers_50q.json, artifacts/ragas_50q.json (created_at 2026-10-12T09:52:02.327394+00:00), src/phase_a_ragas.py, tests/test_phase_a.py, tests/test_cp0_interface.py, doc/reports/failure_clusters.md và output terminal. Commit bằng chứng Phase A: 270296ab585c57523f531c82fe2b5126eec0fd90 (đã push phase-A).
- Cách kiểm tra: chạy support tests (75 passed); tests Phase A/CP0 interface (27 passed); setup_answers.py --live tạo 50 answers; validate_answers đạt schema/nguồn; run_experiments.py --phase a --live chạy 200/200 metric và lưu JSON. Kiểm tra cuối validate_phase_a/validate_metadata đạt theo output PowerShell; git diff --check không có lỗi whitespace.
- Điều đã học: matrix worst_metric đếm mọi câu, nhóm yếu phải chọn bằng mean (multi_hop 0.638094); retrieval phù hợp chưa chắc đủ coverage; score faithfulness cao không đảm bảo số liệu đúng và score thấp cần đối chiếu answer/contexts/reference.
- Giới hạn/cách xử lý: 2 generation timeout giữ đúng extractive_fallback; 2 PDF scan thiếu text layer chưa OCR; enrichment có 1 fallback. Trực tiếp phụ trách Phase A; Phase B do Phùng Đình Triển và Phase C do Phạm Anh Minh phụ trách. Giữ nguyên dữ liệu và số đo thật, ghi giới hạn trong báo cáo.
- Nguồn/AI hỗ trợ: m1–m5 từ bài RAG trước theo yêu cầu lab (nguồn chi tiết trong artifacts/cp0_provenance.json); Codex CLI/Desktop hỗ trợ rà giao diện, sửa adapter, implement Tasks 1–4 và soạn báo cáo/TEAM. Vũ Bá Anh chạy lệnh PowerShell và đối chiếu output, tests và artifacts; không dùng số đo do AI bịa.

### PhungDinhTrien-2A202602837

- Phần được giao và phần thực tế đã làm: phụ trách Phase B (35 điểm). Implement Task 5 pairwise_judge, Task 6 swap_and_average, Task 7 cohen_kappa và Task 8 bias_report trong src/phase_b_judge.py; chạy Phase B live; xử lý tương thích judge model; điền doc/reports/bias_report.md.
- Bằng chứng: src/phase_b_judge.py, artifacts/judge_results.json (created_at 2026-10-12T10:44:24 UTC), doc/reports/bias_report.md, tests/test_phase_b.py; commit Phase B 4ffef73.
- Cách kiểm tra: tests/test_phase_b.py đạt 8 passed (mock SDK, không gọi API); không còn "# TODO" trong src/phase_b_judge.py; scripts/run_experiments.py --phase b --live tạo 5 cặp/10 lượt pairwise và 10 nhãn nhị phân đúng model_answer gốc. Kết quả: position bias 1/5 (id 41), verbosity 1/4 case decisive, Cohen's κ = 0.8 (p_o = 0.9, p_e = 0.5); đã tự tính lại bằng tay và khớp với JSON.
- Điều đã học: pairwise A/B và nhãn 0/1 trả lời hai câu hỏi khác nhau nên không đổi máy móc từ winner sang nhãn; swap-and-average quy lượt 2 về A/B gốc và chỉ giữ winner khi hai lượt đồng thuận; κ điều chỉnh agreement theo p_e; position inconsistency ở id 41 là cặp hai câu cùng sai nên chưa chứng minh bias vị trí; verbosity chỉ là dấu hiệu cần đọc nội dung (winner dài ở id 12 vì có thêm điều kiện đúng).
- Giới hạn/cách xử lý: key được cấp chỉ truy cập được model gpt-6-luna và model này không nhận temperature=0, nên đã đổi JUDGE_MODEL trong config.py và bỏ temperature=0 ở pairwise_judge và judge_binary (src/experiment_support.py). Judge chạy ở temperature mặc định nên kết quả có thể dao động giữa các lần chạy (điểm hai lượt cho cùng nội dung chênh nhau). Mẫu nhỏ (5 cặp, 10 nhãn). Judge lệch human ở id 12 do quá khắt khe; đã đối chiếu question, reference và human_note trong báo cáo.
- Nguồn/AI hỗ trợ: Claude (Anthropic) hỗ trợ giải thích đề, viết code Tasks 5–8 và soạn nháp bias_report.md. Phùng Đình Triển tự chạy lệnh, chạy test và live experiment, đối chiếu số liệu trong judge_results.json và tự tính lại κ, position/verbosity rate bằng tay; không dùng số đo do AI bịa.

### PhamAnhMinh-2A202603009

- Phần được giao và phần thực tế đã làm: phụ trách Phase C; hoàn thiện guard input/output, Presidio PII handling, NeMo policy, latency measurement và blueprint; kiểm tra logic offline và chạy batch Phase C thật.
- Bằng chứng: `src/phase_c_guard.py`, `guardrails/config.yml`, `tests/test_phase_c.py`, `artifacts/guard_results.json`, `doc/reports/blueprint.md`.
- Kết quả/giới hạn: 20/20 attacks, 8/8 clean inputs allowed, 4/4 output cases đúng. Đo 20 samples sau 2 warm-up; input-layer P95 = 924.013130 ms, trên mục tiêu 500 ms. RAG, output rail và full-request latency chưa đo.
- Hỗ trợ công cụ: AI hỗ trợ triển khai/kiểm tra code; batch live chạy qua runner, artifacts lưu provenance, và blueprint phân biệt số đo với đề xuất.

## Cập nhật sau khi nộp

Phase C và artifacts được hoàn thiện trước deadline coach xác nhận là 11:59 AM
ngày 13/10/2026. Commit chứa bộ source/evidence Phase C:
`fe12754e84e79aa8b2e6d3df302b47016099b4e6`; commit tiếp theo cập nhật deadline
đã xác nhận trong TEAM.md.

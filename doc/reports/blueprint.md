# Blueprint CI/CD cho RAG và guardrails

Nhóm: 3ChangLinhNguLam

Người phụ trách Phase C: Phạm Anh Minh — 2A202603009.
Môi trường chạy: Windows, Python 3.11.

Đây là **đề xuất CI/CD**, không phải workflow đã được triển khai/chạy.
Nguồn kết quả: `artifacts/ragas_50q.json`, `artifacts/judge_results.json` và
`artifacts/guard_results.json`. Phase C live run: `2026-10-12T18:35:14.027685+00:00`
(UTC). Metadata khai báo guard model `gpt-4o-mini`. Metadata là provenance do
runner ghi lại; không chứng minh riêng rằng API đã chạy hay provider đã phân giải
alias tới một snapshot cụ thể. Model generation/evaluator/judge theo artifacts A/B:
`gpt-4o-mini-2024-07-18`; `gpt-4o-mini`, `text-embedding-3-small`; `gpt-6-luna`.

## Kiến trúc và failure action

Input → Presidio → NeMo input → RAG → NeMo output → response. Request thật dừng
sớm khi bị chặn; phép đo latency Task 12 riêng biệt luôn chạy đủ Presidio rồi
NeMo input và không bao gồm RAG/output.

Presidio nhận diện CCCD/CMND, số điện thoại và email bằng các recognizer đã cấu
hình. Chỉ các entity `VN_CCCD`, `VN_PHONE`, `EMAIL_ADDRESS` và `PHONE_NUMBER`
được dùng để block; các loại như `PERSON` và `US_DRIVER_LICENSE` bị bỏ qua vì
đã gây false positive trên tiếng Việt và chuỗi phiên bản chính sách. Input có
PII bị dừng trước RAG; không ghi nội dung PII thô vào log. NeMo input đánh giá
jailbreak, nội dung ngoài phạm vi và yêu cầu dữ liệu/credential bí mật; câu hỏi
chính sách HR, VPN, password requirements và MFA được phép. Quyết định lấy từ
activated rails, không suy ra từ từ ngữ refusal.

Nếu một rail block, trả thông báo từ chối phù hợp và không tiếp tục xử lý tầng
sau. NeMo output giữ nguyên answer an toàn; khi bị chặn, thay answer bằng thông
báo từ chối. Lỗi cấu hình/service không được biến thành quyết định “allowed”;
đề xuất vận hành là fail closed, báo lỗi có mã tương quan và không ghi secret
hay raw PII. API keys chỉ lưu trong `.env` không commit. Hiện chưa có hệ thống
log/alert production hay workflow CI thực tế được triển khai.

## Phạm vi và số đo latency

Task 12 đo **`input_layers_sequential`**: Presidio rồi NeMo input, không
short-circuit. Engines được tạo trước phép đo; có hai lượt warm-up thật trong
cùng event loop, không tính vào mẫu. Thu 20 mẫu timed qua tám clean inputs theo
vòng lặp, dùng `perf_counter`; đơn vị milliseconds. Percentile nội suy tuyến
tính tại `(n-1)*q`, `q = .50/.95/.99`. `input_guard_ms` mỗi mẫu là tổng hai tầng
của chính mẫu đó; P95 tổng được tính từ các tổng này, không cộng P95 của từng
tầng.

Số mẫu timed: 20; warm-up: 2; phương pháp: `linear`. Nguồn: Phase C artifact
live run ở trên.

| Layer / scope | P50 ms | P95 ms | P99 ms | Tình trạng |
|---|---:|---:|---:|---|
| Presidio | 10.563400 | 12.241770 | 12.315794 | Đã đo |
| NeMo input | 711.214050 | 912.328660 | 968.782372 | Đã đo |
| Input guard sequential | 722.516200 | 924.013130 | 978.972226 | Đã đo |
| RAG | chưa đo | chưa đo | chưa đo | Ngoài phạm vi Task 12 |
| NeMo output | chưa đo | chưa đo | chưa đo | Ngoài phạm vi Task 12 |
| Full guard / short-circuit request | chưa đo | chưa đo | chưa đo | Không suy ra từ input latency |

Budget input-layer target là 500 ms P95; kết quả `924.013130 ms`,
`latency_budget_ok=false`. NeMo input là phần chi phối trong mẫu này; con số
không được giảm hay trình bày thành đạt budget. Muốn đánh giá production cần
đo thêm nhiều lượt theo tải/độ dài input, lưu raw samples và timestamp; đo riêng
RAG, output rail và request short-circuit với cùng quy tắc warm-up trước khi đặt
ngưỡng end-to-end.

## Kết quả guard và CI gates đề xuất

Live Phase C: attacks **20/20** (100%); clean controls **8/8 allowed**,
false-positive rate **0/8 = 0**; output cases **4/4** đúng expected. Mốc lab bắt
buộc là attacks ≥15/20 cùng clean 8/8 và output đúng; Phase C đạt các điều kiện
này. Mốc bonus là attacks ≥18/20 cùng clean controls đạt, cũng đạt trong batch
này. Kết quả chỉ phản ánh fixtures 20/8/4 của một lần chạy, không đảm bảo mọi
biến thể input hoặc model run khác.

Các ngưỡng sau là **đề xuất CI**, chưa được workflow thực thi:

- Chạy offline unit tests và `python scripts/check_lab.py` trên artifacts đã
  lưu; job thất bại nếu tests/checker trả mã khác 0.
- Đề xuất quality gate: RAGAS faithfulness ≥0.75 và avg_score ≥0.65 trên 50
  câu; attacks ≥18/20, clean 8/8 allowed và 4 output cases đúng.
- Đề xuất latency gate chỉ áp dụng cho input layers khi đã xác nhận nhiều batch
  đại diện; mẫu hiện tại vượt 500 ms nên chưa đạt mục tiêu này.
- Ngưỡng full-guard P95 <500 ms chỉ đặt sau khi có phép đo full guard riêng;
  không dùng `input_guard_ms` làm đại diện.

Checker hiện enforce mốc lab Phase C (15/20 và clean controls), không tự enforce
ngưỡng RAGAS hoặc bonus 18/20 như quality gates CI. Workflow tương lai cần thêm
bước kiểm tra ngưỡng tường minh và lưu kết quả; blueprint này không khẳng định
workflow đã tồn tại.

## Monitoring và cải tiến

Phase A cho thấy avg_score factual **0.825003**, multi-hop **0.638094** và
adversarial **0.678026**; multi-hop có mean thấp nhất, answer relevancy là metric
chi phối failure matrix. Phase B có Cohen’s κ **0.8** trên 10 nhãn; mẫu nhỏ nên
không đại diện độ tin cậy dài hạn. Phase C clean false-positive rate bằng 0 và
attack pass rate 100% trên fixtures, nhưng chưa đo drift hoặc tỷ lệ ngoài bộ
test. Presidio từng đánh nhầm các cụm PERSON tiếng Việt/chuỗi phiên bản; lọc
entity theo loại PII được yêu cầu giúp batch cuối đạt clean 8/8. Thay đổi prompt
NeMo để nêu rõ password/MFA policy và ví dụ off-topic trước batch cuối; không
nên suy rộng tính ổn định từ một lần chạy.

Đề xuất theo dõi theo release: attack pass rate, clean false-positive rate,
output cases, P50/P95/P99 theo từng layer, timeout/error rate, model/config
version và số lần từ chối do từng rail. Log chỉ nên giữ request ID, quyết định,
layer và latency; redact nội dung nhạy cảm, giới hạn quyền truy cập và thời hạn
lưu. Người trực vận hành xem xét false positives trước khi nới policy; thay đổi
recognizer/prompt phải chạy lại bộ test và được người phụ trách guard duyệt.

Các bước cải tiến có thể kiểm chứng:

1. Mở rộng clean/adversarial fixtures tiếng Việt và chạy lặp nhiều lần để đo
   biến thiên quyết định của NeMo, không chỉ một batch 20/8.
2. Phân tích các cụm multi-hop có answer relevancy thấp, cải thiện coverage
   retrieval và đánh giá lại trên cùng 50 câu cùng nguồn dữ liệu.
3. Điều tra NeMo input P95 912.328660 ms; thử tối ưu riêng model/transport sau
   khi giữ baseline raw samples, rồi so sánh cùng input và môi trường.
4. Mở rộng calibration judge vượt 10 câu và theo dõi bất đồng với human labels;
   κ hiện tại không đủ để kết luận hiệu năng tổng quát.
5. Bổ sung phép đo RAG, output rail và full request với warm-up, raw samples,
   percentile và failure action riêng trước khi đề xuất ngưỡng end-to-end.

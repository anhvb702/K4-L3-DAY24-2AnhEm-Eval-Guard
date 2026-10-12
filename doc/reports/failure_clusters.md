# Phân tích lỗi Phase A

Nhóm: 3ChangLinhNguLam.

Người phụ trách: Vũ Bá Anh — 2A202602893.

Nguồn: `artifacts/ragas_50q.json`; run timestamp: 2026-10-12T09:52:02.327394+00:00 (UTC).

Batch thật đánh giá 50 answers, 200 lượt metric. Python 3.11.9; Qdrant 1.9.7; embedding BGE-M3 và reranker đã load từ cache. Answers có 48 LLM, 2 extractive_fallback (IDs 1, 9) sau APITimeoutError; không câu nào thiếu contexts. Enrichment có 1 fallback trong 102 chunks. Không sinh lại answers giữa các bước đánh giá.

Models generation: gpt-4o-mini-2024-07-18. Evaluator do m4 báo: gpt-4o-mini, text-embedding-3-small. Judge/guard không tham gia Phase A.

## Điểm theo distribution

| Metric | factual (20) | multi_hop (20) | adversarial (10) |
|---|---:|---:|---:|
| faithfulness | 1.000000 | 0.442500 | 0.666667 |
| answer_relevancy | 0.458344 | 0.389042 | 0.428771 |
| context_precision | 0.941667 | 0.908333 | 0.933333 |
| context_recall | 0.900000 | 0.812500 | 0.683333 |
| avg_score | 0.825003 | 0.638094 | 0.678026 |

## Bottom 10 và nguyên nhân

Bảng giữ nguyên diagnosis/suggested_fix do Task 3 xuất. Chúng là giả thuyết theo metric; phân tích nội dung bên dưới kiểm tra và điều chỉnh cách diễn giải, không ghi đè JSON.

| Rank | ID | Question | Distribution | Avg score | Worst metric | Diagnosis | Suggested fix |
|---:|---:|---|---|---:|---|---|---|
| 1 | 39 | So sánh yêu cầu mật khẩu giữa policy v1.0 và v2.0 về độ dài tối thiểu, thời hạn đổi và MFA. | multi_hop | 0.25000000 | faithfulness | Giả thuyết cần đối chiếu answer/contexts/reference: LLM hallucinating; faithfulness=0.0000. | Tighten system prompt, lower temperature; kiểm tra bằng chứng câu 39 trước khi sửa và đánh giá lại. |
| 2 | 44 | Bao lâu phải đổi mật khẩu một lần? | adversarial | 0.37500000 | faithfulness | Giả thuyết cần đối chiếu answer/contexts/reference: LLM hallucinating; faithfulness=0.0000. | Tighten system prompt, lower temperature; kiểm tra bằng chứng câu 44 trước khi sửa và đánh giá lại. |
| 3 | 33 | Nhân viên Manager có thâm niên 12 năm: tổng phụ cấp hàng tháng và số ngày phép năm theo v2024 là bao nhiêu? | multi_hop | 0.37500000 | faithfulness | Giả thuyết cần đối chiếu answer/contexts/reference: LLM hallucinating; faithfulness=0.0000. | Tighten system prompt, lower temperature; kiểm tra bằng chứng câu 33 trước khi sửa và đánh giá lại. |
| 4 | 50 | Nhân viên Manager có thể dùng VPN cá nhân (như NordVPN) khi WFH để tăng bảo mật thêm không? | adversarial | 0.41666667 | faithfulness | Giả thuyết cần đối chiếu answer/contexts/reference: LLM hallucinating; faithfulness=0.0000. | Tighten system prompt, lower temperature; kiểm tra bằng chứng câu 50 trước khi sửa và đánh giá lại. |
| 5 | 40 | Nhân viên cấp Manager có thời hạn thử việc 90 ngày, đang trong tháng thứ 3, phát hiện vi phạm bảo mật. Họ nên và không nên làm gì theo chính sách? | multi_hop | 0.45459631 | context_precision | Giả thuyết cần đối chiếu answer/contexts/reference: Too many irrelevant chunks; context_precision=0.3333. | Add reranking or metadata filter; kiểm tra bằng chứng câu 40 trước khi sửa và đánh giá lại. |
| 6 | 29 | Nhân viên tạm ứng 8 triệu, chưa thanh toán sau 30 ngày (quá hạn 15 ngày). Ai phê duyệt khoản này và phí phạt là bao nhiêu? | multi_hop | 0.50000000 | faithfulness | Giả thuyết cần đối chiếu answer/contexts/reference: LLM hallucinating; faithfulness=0.0000. | Tighten system prompt, lower temperature; kiểm tra bằng chứng câu 29 trước khi sửa và đánh giá lại. |
| 7 | 32 | Nhân viên mới cấp Manager có thời hạn thử việc 90 ngày, đang trong tháng thứ 3, có BẮT BUỘC tham dự buổi đào tạo nội bộ của phòng ban không? Tại sao? | multi_hop | 0.50000000 | faithfulness | Giả thuyết cần đối chiếu answer/contexts/reference: LLM hallucinating; faithfulness=0.0000. | Tighten system prompt, lower temperature; kiểm tra bằng chứng câu 32 trước khi sửa và đánh giá lại. |
| 8 | 24 | Nhân viên tạm ứng 15 triệu, sau 20 ngày mới thanh toán. Bị phạt bao nhiêu? | multi_hop | 0.57107746 | faithfulness | Giả thuyết cần đối chiếu answer/contexts/reference: LLM hallucinating; faithfulness=0.0000. | Tighten system prompt, lower temperature; kiểm tra bằng chứng câu 24 trước khi sửa và đánh giá lại. |
| 9 | 21 | Một nhân viên Senior có 9 năm thâm niên được nghỉ bao nhiêu ngày phép năm và lương trong khoảng nào? | multi_hop | 0.58333333 | answer_relevancy | Giả thuyết cần đối chiếu answer/contexts/reference: Answer doesn't match question; answer_relevancy=0.0000. | Improve prompt template; kiểm tra bằng chứng câu 21 trước khi sửa và đánh giá lại. |
| 10 | 31 | Nhân viên đi công tác trong nước, ở khách sạn 2 đêm với giá 1.500.000 VNĐ/đêm. Công ty thanh toán tối đa bao nhiêu cho tiền khách sạn? | multi_hop | 0.60463712 | faithfulness | Giả thuyết cần đối chiếu answer/contexts/reference: LLM hallucinating; faithfulness=0.2500. | Tighten system prompt, lower temperature; kiểm tra bằng chứng câu 31 trước khi sửa và đánh giá lại. |

### Đối chiếu answer, contexts và reference

- **ID 39 (so sánh mật khẩu v1.0/v2.0):** answer “Không tìm thấy.”; contexts có 8 ký tự ở v1.0 đã thay thế và 12 ký tự ở v2.0 nhưng thiếu phần chu kỳ/MFA cần so sánh. Reference yêu cầu cả 8/12 ký tự, 90/120 ngày và MFA. Retrieval thiếu các đoạn hỗ trợ đầy đủ; generation bỏ cả phần đã có. Không thể kết luận chỉ là hallucination từ faithfulness=0.
- **ID 44 (chu kỳ đổi mật khẩu):** contexts có cả 120 và 90 ngày cùng đoạn thông báo thay thế, answer lại “Không tìm thấy.”. Reference chọn 120 ngày theo v2.0. Cần giữ source/version/effective date gắn với mỗi chunk và sinh câu trả lời phân biệt cũ/mới; chưa có bằng chứng pipeline giải quyết được xung đột phiên bản.
- **ID 50 (VPN cá nhân):** context đầu cấm NordVPN/ExpressVPN; context khác yêu cầu VPN công ty. Answer “Không tìm thấy.” không trả lời phủ định cần thiết theo reference. Đây là lỗi sử dụng bằng chứng/phủ định, không phải bằng chứng guard đã chặn yêu cầu.
- **ID 21 và 33 (nhiều chính sách):** ID 21 trả đúng 18 ngày phép nhưng thiếu lương Senior 20–35 triệu vì cả 3 contexts chỉ nói nghỉ phép. ID 33 có bằng chứng tính 19 ngày phép nhưng thiếu phụ cấp 1,5 triệu; answer bỏ toàn bộ. Retrieval top 3 chưa phủ đủ các vế câu hỏi, generation cần trả phần có căn cứ và nêu cụ thể phần thiếu.
- **ID 29 (tạm ứng):** contexts có công thức phí 2% × tiền × ngày quá hạn/30 nên hỗ trợ 80.000 VNĐ cho 15 ngày quá hạn; đoạn phê duyệt bị cắt tại “Từ 5.000.000 VNĐ trở l”, thiếu người duyệt. Answer “Không tìm thấy.” làm mất phần có thể tính. Cần phục hồi câu/parent context và thu đủ điều kiện phê duyệt.
- **ID 32 (đào tạo trong tháng 3):** quy tắc “nhân viên mới trong 6 tháng đầu” và “bắt buộc tham gia” bị chia qua hai chunks. Đọc nối chúng hỗ trợ kết luận bắt buộc; answer “Không tìm thấy.” cho thấy generation chưa nối điều kiện. Nên chunk theo câu/section hoặc bổ sung parent context.
- **ID 40 (sự cố bảo mật):** 2/3 contexts nói thử việc/lương, chỉ 1 context có quy trình báo cáo và bị cắt ở email/hotline. Answer có báo trong 1 giờ nhưng thiếu ext.9999, cấm xóa dấu vết/chia sẻ rộng rãi và hậu quả. Context precision=0,3333 phù hợp retrieval bị kéo về chi tiết Manager/thử việc thay vì hành động bảo mật.
- **ID 24 và 31 (tính toán):** ID 24 trả đúng 50.000 VNĐ, công thức pro-rata có trong context và reference, nhưng faithfulness=0. ID 31 trả đúng mức tối đa 2,4 triệu, context hỗ trợ 1,2 triệu/đêm × 2, nhưng faithfulness=0,25; answer chưa giải thích phần vượt tự trả. Đây là dấu hiệu cần kiểm chứng evaluator với phép tính, không tự gán lỗi hallucination cho mọi điểm thấp.
- **ID 2 ngoài bottom 10:** answer ghi 200.000 VNĐ/năm thay vì reference 200.000.000. Số bị tách giữa context thứ nhất (“200.000.”) và thứ ba (“000 VNĐ/năm”), nhưng faithfulness=1. Trường hợp này cho thấy metric cao không bảo đảm đúng số; cần chunk giữ nguyên số tiền và kiểm tra thủ công các dữ kiện quan trọng.
- **Fallback ID 1:** answer dùng context đầu về tang lễ/sinh con/con kết hôn, trong khi context thứ hai có đúng nghỉ kết hôn 3 ngày. Extractive fallback lấy đoạn đầu không đảm bảo trả lời đúng câu hỏi dù context recall=1. Fallback ID 9 cũng phải giữ trong thống kê, không giả khai là generation LLM.

## Matrix và nhóm yếu nhất

| Worst metric | factual | multi_hop | adversarial |
|---|---:|---:|---:|
| faithfulness | 0 | 12 | 3 |
| answer_relevancy | 18 | 7 | 5 |
| context_precision | 0 | 1 | 0 |
| context_recall | 2 | 0 | 2 |

Tổng cột = 20/20/10, đếm mọi câu theo metric thấp nhất, không phải số failures. Khi metrics bằng nhau, worst_metric dùng thứ tự faithfulness, answer_relevancy, context_precision, context_recall.

Nhóm yếu nhất là **multi_hop**, mean **0,638094**; không chọn bằng kích thước nhóm. Answer relevancy là metric thấp nhất của **30/50** câu. Multi_hop có nhiều câu thiếu một vế retrieval hoặc từ chối trả lời dù có bằng chứng một phần. Context precision cao (0,908333) vẫn không bảo đảm contexts phủ đủ các chính sách cần nối.

## Bẫy adversarial và giới hạn

Adversarial mean **0,678026 < factual 0,825003**, chênh lệch khoảng **0,146977**. Cùng phân tích version conflict ID 44 và policy contradiction/negation ID 50, kết quả đáp ứng điều kiện bonus Phase A trong rubric; điểm cuối do người chấm quyết định. Adversarial khó hơn không tự chứng minh pipeline nhận ra bẫy.

Chỉ có 50 câu (20/20/10), một batch và một cấu hình evaluator; không suy rộng sang mọi câu hỏi hoặc coi judge là đáp án tuyệt đối. Hai PDF scan BCTC.pdf và Nghi_dinh_so_13-2023_ve_bao_ve_du_lieu_ca_nhan_508ee.pdf không có text layer, bị bỏ qua, nên corpus index chưa bao phủ chúng. M4 metric/provenance và hash là bằng chứng nguồn; kết hợp terminal run để xác nhận thực nghiệm, không coi hash tự chứng minh API execution. NeMo chưa cài và Phase B/C chưa thực hiện, không có kết luận judge calibration/guard/latency.

## Hướng sửa và cách kiểm chứng

1. Chunk theo câu/section, giữ số tiền và đoạn điều kiện hoàn chỉnh; dùng parent context khi câu bị cắt. Kiểm tra IDs 2, 29, 32 trước khi chạy lại.
2. Với multi-hop, tách nhu cầu retrieval theo từng vế và kiểm tra coverage; giữ policy cũ/mới để so sánh lịch sử, gắn version/effective date/source vào contexts. Kiểm tra IDs 21, 33, 39, 44.
3. Generation trả phần có bằng chứng, giải thích phần thiếu và xử lý phủ định; tránh “Không tìm thấy.” khi contexts đã có quy tắc. Kiểm tra IDs 29, 32, 50 và fallback IDs 1, 9.
4. Kiểm tra thủ công các câu số học/định lượng với answer, context và reference; phân tích statement-level faithfulness trước khi kết luận ID 24/31 sai. Không sửa điểm đo hoặc reference.
5. Các mục trên là đề xuất, chưa được triển khai/chạy lại. Khi triển khai, tạo batch answers/evaluation mới có nguồn và timestamp riêng, so cả bốn metric cùng coverage/case correctness; không chỉ tối ưu một mean hoặc hạ chất lượng factual để đạt bonus.

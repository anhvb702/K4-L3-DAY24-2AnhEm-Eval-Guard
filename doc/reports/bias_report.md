# Đánh giá LLM Judge Phase B

Nhóm: 3ChangLinhNguLam

Người phụ trách: Phùng Đình Triển - 2A202602837

Nguồn: `artifacts/judge_results.json`; run timestamp: 2026-10-12T10:44:24 UTC (17:44 giờ Việt Nam).
Models generation/judge: generation = `gpt-4o-mini-2024-07-18`, judge = `gpt-6-luna`.
Hai vai trò evaluator và guard là `[]` vì không chạy trong Phase B.

## Năm cặp A/B và hai lượt

Nguồn cố định: A từ artifacts/answers_50q.json:answer; B từ
fixtures/human_labels_10q.json:model_answer; reference từ fixtures/test_set_50q.json:ground_truth.
Ids: 1, 5, 12, 21, 41. Không đổi nguồn sau khi xem kết quả judge.

| id | A (pipeline) | B (model_answer) | Lượt 1 | Lượt 2 (đã quy về A/B gốc) | Final | Nhất quán | Scores lượt 1 (A/B) | Scores lượt 2 (A/B) |
|---|---|---|---|---|---|---|---|---|
| 1 | Chunk context bị cắt, không nêu số ngày kết hôn (`extractive_fallback`) | 3 ngày làm việc có lương khi kết hôn | B | B | B | Có | 0.10 / 0.85 | 0.10 / 0.85 |
| 5 | CEO phê duyệt (đúng) | Giám đốc phòng ban phê duyệt (sai) | A | A | A | Có | 1.00 / 0.00 | 1.00 / 0.00 |
| 12 | 1 tháng lương, nêu đủ điều kiện chính thức từ 6 tháng | 1 tháng lương, không nêu điều kiện | A | A | A | Có | 1.00 / 0.70 | 1.00 / 0.85 |
| 21 | 18 ngày phép, nói không xác định được lương | 18 ngày phép và lương Senior 20-35 triệu | B | B | B | Có | 0.65 / 1.00 | 0.50 / 1.00 |
| 41 | 12 ngày phép năm có lương (v2023) | 12 ngày phép năm (v2023) | tie | B | tie | Không | 0.10 / 0.10 | 0.15 / 0.20 |

Lý do chính của judge (reasoning của lượt 2 được viết theo vị trí đã hoán đổi, nên nhãn A/B trong
lời giải thích đảo so với bảng trên): id 1, A không trả lời trường hợp nhân viên kết hôn; id 5, B nêu sai
người phê duyệt vì 55 triệu vượt ngưỡng 50 triệu; id 12, B thiếu điều kiện áp dụng; id 21, A thiếu
khoảng lương; id 41, cả hai cùng dùng mức 12 ngày của chính sách v2023 đã bị thay thế.

Position bias count/rate: 1/5 = 0.2.
Verbosity win rate: 0.25 (1/4); decisive cases: 4 (a_wins_a_longer = 1, b_wins_b_longer = 0).

Chỉ id 41 không nhất quán. Cả hai candidate đều sai như nhau (đều là 12 ngày của v2023), lượt 1 cho
tie với điểm 0.10/0.10, lượt 2 hơi nghiêng về câu ngắn hơn với điểm chênh nhỏ (0.20 so với 0.15).
Đây là cặp gần như ngang nhau nên chênh lệch giữa hai lượt có thể chỉ là nhiễu, và 1/5 case chưa đủ
để kết luận judge thiên vị vị trí. Về độ dài, ở 3/4 case có winner rõ ràng (id 1, 5, 21) winner là
câu ngắn hơn. Chỉ id 12 winner dài hơn, và phần dài thêm là điều kiện "chính thức từ 6 tháng" mà
reference có nêu, nên đó là khác biệt về nội dung chứ không phải về độ dài. Vì vậy chưa thấy dấu hiệu
verbosity bias; judge bám theo tính đúng sai so với reference (nhận ra id 5 B sai, id 41 dùng
chính sách cũ).

## Calibration đúng model_answer

Helper đánh giá đúng question/model_answer đang có trong fixtures/human_labels_10q.json;
không lấy answer mới của pipeline. Prompt chỉ nhận question, answer, reference.
Không gửi human_label, human_note hoặc phân bố nhãn human vào prompt.

| id | model_answer gốc | Judge | Human | Khớp | Lý do của judge |
|---|---|---|---|---|---|
| 1 | Nhân viên được nghỉ 3 ngày làm việc có lương khi kết hôn. | 1 | 1 | Có | Đúng 3 ngày có lương; không trừ phép năm là thông tin bổ sung |
| 5 | Cần Giám đốc phòng ban phê duyệt. | 0 | 0 | Có | 55 triệu vượt 50 triệu nên cần CEO |
| 12 | Nhân viên được thưởng Tết tối thiểu 1 tháng lương. | 0 | 1 | Không | Mức đúng nhưng bỏ qua điều kiện chính thức từ 6 tháng |
| 21 | Được nghỉ 18 ngày phép (15 cơ bản + 3 thâm niên). Lương Senior từ 20 đến 35 triệu. | 1 | 1 | Có | Đúng 18 ngày và khoảng lương |
| 23 | Hoàn trả 25 triệu vì chưa đủ 1 năm cam kết. | 1 | 1 | Có | Nghỉ sau 8 tháng phải hoàn trả 100% |
| 29 | Trưởng phòng phê duyệt. Phạt 2% tháng trên 8 triệu. | 0 | 0 | Có | Thiếu Kế toán trưởng; phí đúng là 80.000 VNĐ |
| 33 | Phép: 19 ngày. Phụ cấp: 1.500.000 VNĐ/tháng. | 1 | 1 | Có | Khớp reference |
| 41 | Nhân viên được nghỉ 12 ngày phép năm. | 0 | 0 | Có | Dùng chính sách v2023 đã bị thay thế |
| 46 | Nhân viên thử việc không được nghỉ phép năm và phải xin nghỉ không lương nếu cần. | 1 | 1 | Có | Đúng phủ định, phù hợp reference |
| 50 | Được, miễn là đảm bảo kết nối an toàn. | 0 | 0 | Có | Reference cấm VPN cá nhân |

Cohen's κ: 0.8.
Observed agreement p_o = 9/10 = 0.9. Judge gán nhãn 1 cho 5/10 và human gán nhãn 1 cho 6/10, nên
chance agreement p_e = 0.5 x 0.6 + 0.5 x 0.4 = 0.5. Do đó κ = (0.9 - 0.5) / (1 - 0.5) = 0.8,
nằm ở ranh giới giữa "substantial" và "almost perfect" theo thang Landis-Koch, cao hơn ngưỡng bonus 0.6.

Judge và human chỉ lệch ở id 12. Câu hỏi đã nêu sẵn điều kiện "nhân viên chính thức có từ 6 tháng
trở lên", nên câu trả lời "tối thiểu 1 tháng lương" vẫn đủ ý thiết yếu và judge đã quá khắt khe khi
trừ điểm vì không nhắc lại điều kiện. Điều này khớp với ghi chú của human (`human_note`: "Đúng và súc tích."),
tức là human coi câu trả lời ngắn vẫn đủ ý.
Judge cũng không nhất quán về mức khắt khe: ở id 1 nó chấp nhận câu trả lời thiếu chi tiết "không trừ vào phép năm"
vì coi là thông tin bổ sung.

## Giới hạn và cách dùng judge

- Mẫu rất nhỏ: 5 cặp pairwise và 10 nhãn. Đổi một nhãn làm p_o thay đổi 0.1 nên κ thay đổi đáng kể;
  tỉ lệ position bias 0.2 chỉ là một case trên năm.
- Ở id 1, A là chunk context do `extractive_fallback` tạo ra chứ không phải câu trả lời của LLM, nên
  việc judge chọn B ở case này phản ánh ít về bias của judge.
- Judge chạy bằng `gpt-6-luna`. Model này không nhận `temperature=0` (chỉ nhận mặc định), nên nhóm
  đã bỏ tham số này ở `pairwise_judge` và ở `judge_binary` (`src/experiment_support.py`), và đổi
  `JUDGE_MODEL` trong `config.py`. Vì chạy ở temperature mặc định, kết quả có thể dao động giữa các lần
  chạy: điểm của cùng nội dung chênh nhau giữa hai lượt (id 12: B 0.70 và 0.85; id 21: A 0.65 và 0.50).
  Do đó một phần position inconsistency có thể là nhiễu ngẫu nhiên chứ không chỉ là bias vị trí.
- Cách kiểm chứng: đọc lại question, reference và hai answer của các case lệch (id 12, id 41) rồi so với
  reasoning của judge; không xem judge là đáp án tuyệt đối. Khi dùng thật nên giữ swap-and-average,
  calibrate định kỳ với nhãn người và để người duyệt các case judge và human lệch nhau.
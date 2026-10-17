# Nguồn của bộ ca kiểm tra đơn

Các file trong thư mục này và các bộ ca `eval/golden/rx_golden_set.*`, `pair_set_alashwal.jsonl`, `pair_set_onc.jsonl`
do `eval/golden/build_rx_golden.py` sinh ra. Đáp án **không** lấy từ CSDL DDInter mà hệ thống tra cứu.

| File | Nguồn | Giấy phép, điều kiện dùng |
|---|---|---|
| `alashwal2023_pairs.csv`, `../pair_set_alashwal.jsonl` | Al-Ashwal FY, Zawiah M, Gharaibeh L, Abu-Farha R, Bitar AN. *Evaluating the Sensitivity, Specificity, and Accuracy of ChatGPT-3.5, ChatGPT-4, Bing AI, and Bard Against Conventional Drug-Drug Interactions Clinical Tools.* Drug Healthc Patient Saf. 2023;15:137-147. doi:10.2147/DHPS.S425858. Phụ lục S1 (tải tại `https://www.dovepress.com/get_supplementary_file.php?f=425858.xlsx`) | CC BY-NC 3.0: ghi nguồn, chỉ dùng phi thương mại |
| `onc_high_priority_2012.json`, `../pair_set_onc.jsonl` | Phansalkar S, Desai AA, Bell D, et al. *High-priority drug-drug interactions for use in electronic health records.* J Am Med Inform Assoc. 2012;19(5):735-743. doi:10.1136/amiajnl-2011-000612. Bảng 2 | Danh sách là dữ kiện, dùng kèm trích dẫn. Thành viên nhóm thuốc ba vòng lấy từ ATC N06AA qua RxClass |
| `rxnav_cache.json` | RxNav / RxNorm, U.S. National Library of Medicine (`https://rxnav.nlm.nih.gov`) | Dữ liệu công của chính phủ Mỹ |
| `../rx_golden_set.*` (đơn `MI-*`) | Johnson A, Bulgarelli L, Pollard T, et al. *MIMIC-IV Clinical Database Demo* (v2.2). PhysioNet. doi:10.13026/dp1f-ex47. Bảng `prescriptions`, `admissions` | Open Data Commons ODbL 1.0: ghi nguồn; CSDL dẫn xuất phải giữ cùng giấy phép. Bản demo là truy cập mở, không cần chứng chỉ (bản đầy đủ MIMIC-IV mới cần) |
| `../rx_golden_set.*` (đơn `VN-*`) | 3 đơn thật và 1 phiếu tư vấn nhóm thu thập, có đồng ý, đã che (`docs/demo/anh_don_that/`) | Chỉ dùng cho đánh giá và demo của nhóm |
| `fda_labels_used.json`, `fda_label_evidence_alashwal.jsonl` | Nhãn thuốc kê đơn (Structured Product Labeling) của U.S. FDA, lấy qua openFDA (`https://api.fda.gov/drug/label.json`). Mỗi thuốc một nhãn, ghi `set_id` và ngày hiệu lực. Câu trích là nguyên văn nhãn | Dữ liệu công của chính phủ Mỹ |
| `kegg_ids_alashwal.json`, `kegg_ddi_alashwal.jsonl` | KEGG DRUG và KEGG DDI (Kanehisa Laboratories, `https://rest.kegg.jp`), tổng hợp tương tác từ tờ hướng dẫn sử dụng thuốc được PMDA Nhật Bản duyệt. `CI` chống chỉ định phối hợp, `P` thận trọng khi phối hợp | KEGG API chỉ dùng cho học thuật, phi thương mại; ghi nguồn. Dùng thương mại phải mua giấy phép |
| `../pair_ref_authoritative.jsonl` | Chuẩn tổng hợp do `build_authoritative_ref.py` dựng từ 3 nguồn trên + Micromedex | Theo giấy phép của từng nguồn |

## Chuẩn tổng hợp (`build_authoritative_ref.py`)

Một cặp là **có tương tác cần cảnh báo** khi ít nhất một nguồn có thẩm quyền ghi nhận kèm giải thích: Micromedex mức
trung bình trở lên; nhãn FDA của một trong hai thuốc có khuyến cáo khi dùng chung (gọi tên thuốc kia hoặc nhóm chứa
nó: chống chỉ định, tránh, chỉnh liều, theo dõi, thận trọng); nhãn Nhật Bản ghi CI hoặc P. Drugs.com không nằm trong
chuẩn vì mức độ của DDInter gần như chép Drugs.com.

Nhãn FDA do DeepSeek (nhiệt độ 0) đọc: mô hình chỉ thấy nhãn và tên thuốc kia, không thấy kết quả của hệ thống; câu
trả lời phải kèm một câu trích nguyên văn và chỉ được tính khi câu trích có trong nhãn (so chuỗi sau khi chuẩn hóa khoảng
trắng, gạch nối, chữ hoa). Kết quả đọc lưu ở `data/raw/eval_refs/fda_judge_cache.json` (ngoài git) và chép vào
`fda_label_evidence_alashwal.jsonl` để người khác kiểm lại. Đây không phải dữ liệu MIMIC nên được gửi lên API.

```bash
python eval/golden/build_authoritative_ref.py            # tải nhãn FDA, KEGG rồi đọc nhãn (dùng cache nếu có)
python eval/golden/build_authoritative_ref.py --offline  # chỉ dựng lại từ cache
```

## Tải lại dữ liệu thô (để dựng lại bộ ca)

Dữ liệu thô nằm trong `data/raw/` (ngoài git):

```bash
mkdir -p data/raw/mimic_iv_demo data/raw/eval_refs
for t in prescriptions admissions; do
  curl -L -o data/raw/mimic_iv_demo/$t.csv.gz https://physionet.org/files/mimic-iv-demo/2.2/hosp/$t.csv.gz
done
curl -L -o data/raw/eval_refs/alashwal2023_S1.xlsx "https://www.dovepress.com/get_supplementary_file.php?f=425858.xlsx"
```

`alashwal2023_raw.csv` là trang tính đầu tiên của file xlsx ("Sens & speci b4 coding") lưu thành CSV, đổi tên cột
thành `pair,micromedex,chatgpt35,chatgpt4,bingai,bard,drugscom`. Mã: 1 không tương tác, 2 nhẹ, 3 trung bình, 4 nặng
hoặc chống chỉ định, 5 (chỉ có ở Micromedex, Bard) chống chỉ định, 7 không phân loại được.

**Không gửi dữ liệu MIMIC lên API LLM bên ngoài** (điều khoản PhysioNet). `eval/run_rx_eval.py` không gọi LLM.

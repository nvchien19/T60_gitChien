# Đánh giá chức năng kiểm tra đơn (nội bộ)

Sinh lúc 2026-10-17 10:06 bởi `eval/run_rx_eval.py`. Báo cáo này có danh sách ca sai, **không** hiện trên giao diện.

## 1. Al-Ashwal 2023 (255 cặp, bộ công bố độc lập)

| So với | Độ nhạy | Độ đặc hiệu | PPV | NPV | F1 | Kappa mức độ |
|---|---|---|---|---|---|---|
| drugscom | 0.924 [0.844, 0.965] | 1.0 [0.979, 1.0] | 1.0 | 0.967 | 0.96 | 0.945 |
| micromedex | 0.936 [0.828, 0.978] | 0.861 [0.807, 0.901] | 0.603 | 0.984 | 0.733 | 0.614 |

### Chuẩn tổng hợp từ nguồn có thẩm quyền

Số cặp mỗi nguồn ghi nhận: {'micromedex': 47, 'fda_label': 54, 'japan_label': 18, 'fda_no_label': 0}; số nguồn mỗi cặp: {0: 183, 1: 35, 2: 27, 3: 10}. Cảnh báo thừa so với Micromedex có nhãn thuốc làm cơ sở: 13/29.

**any** (Ít nhất 1 nguồn có thẩm quyền: Micromedex, nhãn thuốc FDA hoặc nhãn thuốc Nhật Bản (PMDA, qua KEGG); 72 cặp dương tính)

| Công cụ | Độ nhạy | Độ đặc hiệu | PPV | F1 | TP/FP/FN/TN |
|---|---|---|---|---|---|
| Rà Thuốc | 0.792 | 0.913 | 0.781 | 0.786 | 57/16/15/167 |
| Micromedex * | 0.653 | 1.0 | 1.0 | 0.79 | 47/0/25/183 |
| Drugs.com | 0.806 | 0.885 | 0.734 | 0.768 | 58/21/14/162 |
| ChatGPT-4 | 0.847 | 0.552 | 0.427 | 0.568 | 61/82/11/101 |
| ChatGPT-3.5 | 0.847 | 0.393 | 0.355 | 0.5 | 61/111/11/72 |
| Bing AI | 0.75 | 0.809 | 0.607 | 0.671 | 54/35/18/148 |
| Bard | 0.75 | 0.579 | 0.412 | 0.532 | 54/77/18/106 |

**two** (Ít nhất 2 trong 3 nguồn trên; 37 cặp dương tính)

| Công cụ | Độ nhạy | Độ đặc hiệu | PPV | F1 | TP/FP/FN/TN |
|---|---|---|---|---|---|
| Rà Thuốc | 0.973 | 0.83 | 0.493 | 0.654 | 36/37/1/181 |
| Micromedex * | 0.973 | 0.95 | 0.766 | 0.857 | 36/11/1/207 |
| Drugs.com | 0.973 | 0.803 | 0.456 | 0.621 | 36/43/1/175 |
| ChatGPT-4 | 0.946 | 0.505 | 0.245 | 0.389 | 35/108/2/110 |
| ChatGPT-3.5 | 0.919 | 0.367 | 0.198 | 0.326 | 34/138/3/80 |
| Bing AI | 0.892 | 0.743 | 0.371 | 0.524 | 33/56/4/162 |
| Bard | 0.811 | 0.537 | 0.229 | 0.357 | 30/101/7/117 |

**labels** (Chỉ nhãn thuốc được cơ quan quản lý duyệt (FDA hoặc Nhật Bản), không dùng Micromedex; 61 cặp dương tính)

| Công cụ | Độ nhạy | Độ đặc hiệu | PPV | F1 | TP/FP/FN/TN |
|---|---|---|---|---|---|
| Rà Thuốc | 0.803 | 0.876 | 0.671 | 0.731 | 49/24/12/170 |
| Micromedex | 0.59 | 0.943 | 0.766 | 0.667 | 36/11/25/183 |
| Drugs.com | 0.82 | 0.851 | 0.633 | 0.714 | 50/29/11/165 |
| ChatGPT-4 | 0.852 | 0.531 | 0.364 | 0.51 | 52/91/9/103 |
| ChatGPT-3.5 | 0.852 | 0.381 | 0.302 | 0.446 | 52/120/9/74 |
| Bing AI | 0.754 | 0.778 | 0.517 | 0.613 | 46/43/15/151 |
| Bard | 0.738 | 0.557 | 0.344 | 0.469 | 45/86/16/108 |

\* nằm trong chuẩn nên được lợi.

### Cảnh báo thừa so với Micromedex và bằng chứng nhãn thuốc

- AA-002 empagliflozin + Levothyroxine: nhãn levothyroxine (monitor): "Antidiabetic Agents - Biguanides - Meglitinides - Sulfonylureas - Thiazolidediones - Insulin Addition of levothyroxine to antidiabetic or insulin therapy may re"
- AA-005 empagliflozin + Amlodipine: không
- AA-009 empagliflozin + Losartan: không
- AA-025 empagliflozin + Tamsulosin: không
- AA-031 empagliflozin + Prednisone: nhãn prednisone (monitor): "Antidiabetics Because corticosteroids may increase blood glucose concentrations, dosage adjustments of antidiabetic agents may be required."
- AA-046 empagliflozin + Ethinyl Estradiol: không
- AA-053 dapagliflozin + Levothyroxine: nhãn levothyroxine (monitor): "Addition of levothyroxine to antidiabetic or insulin therapy may result in increased antidiabetic agent or insulin requirements. Careful monitoring of diabetic "
- AA-056 dapagliflozin + Amlodipine: không
- AA-060 dapagliflozin + Losartan: không
- AA-076 dapagliflozin + Tamsulosin: không
- AA-082 dapagliflozin + Prednisone: nhãn prednisone (monitor): "Antidiabetics Because corticosteroids may increase blood glucose concentrations, dosage adjustments of antidiabetic agents may be required."
- AA-097 dapagliflozin + Ethinyl Estradiol: không
- AA-102 dapagliflozin + Glipizide: nhãn dapagliflozin (adjust_dose): "Insulin and insulin secretagogues (e.g., sulfonylureas) are known to cause hypoglycemia. FARXIGA may increase the risk of hypoglycemia when combined with insuli"; nhãn glipizide (monitor): "Concomitant use of GLUCOTROL XL with other anti-diabetic medication can increase the risk of hypoglycemia. A lower dose of GLUCOTROL XL may be required to minim"
- AA-104 canagliflozin + Levothyroxine: nhãn levothyroxine (monitor): "Addition of levothyroxine to antidiabetic or insulin therapy may result in increased antidiabetic agent or insulin requirements. Careful monitoring of diabetic "
- AA-107 canagliflozin + Amlodipine: không
- AA-111 canagliflozin + Losartan: không
- AA-127 canagliflozin + Tamsulosin: không
- AA-133 canagliflozin + Prednisone: nhãn prednisone (monitor): "Antidiabetics Because corticosteroids may increase blood glucose concentrations, dosage adjustments of antidiabetic agents may be required."
- AA-148 canagliflozin + Ethinyl Estradiol: không
- AA-153 canagliflozin + Glipizide: nhãn canagliflozin (adjust_dose): "Insulin or Insulin Secretagogues Clinical Impact: The risk of hypoglycemia is increased when INVOKANA is used concomitantly with insulin secretagogues (e.g., su"; nhãn glipizide (monitor): "Concomitant use of GLUCOTROL XL with other anti-diabetic medication can increase the risk of hypoglycemia. A lower dose of GLUCOTROL XL may be required to minim"
- AA-156 clarithromycin + Metformin: nhãn clarithromycin (monitor): "The concomitant use of clarithromycin and oral hypoglycemic agents and/or insulin can result in significant hypoglycemia."
- AA-170 clarithromycin + Hydrocodone: nhãn hydrocodone (adjust_dose): "The concomitant use of HYSINGLA ER and CYP3A4 inhibitors can increase the plasma concentration of hydrocodone, resulting in increased or prolonged opioid effect"
- AA-183 clarithromycin + Clopidogrel: không
- AA-186 clarithromycin + Insulin Glargine: nhãn clarithromycin (monitor): "The concomitant use of clarithromycin and oral hypoglycemic agents and/or insulin can result in significant hypoglycemia."
- AA-199 clarithromycin + Ethinyl Estradiol: nhãn ethinyl estradiol (caution): "CYP3A inhibitors such as itraconazole, voriconazole, fluconazole, grapefruit juice The effect of grapefruit juice on CYP3A4 enzymes (e.g., strong vs. moderate i"
- AA-203 clarithromycin + Apixaban: không
- AA-240 azithromycin + Tramadol: không
- AA-248 azithromycin + Venlafaxine: không
- AA-250 azithromycin + Ethinyl Estradiol: không

Các công cụ khác trên cùng 255 cặp (so với Drugs.com):

| Công cụ | Độ nhạy | Độ đặc hiệu | PPV | F1 |
|---|---|---|---|---|
| Micromedex | 0.557 | 0.983 | 0.936 | 0.698 |
| ChatGPT-4 | 0.747 | 0.523 | 0.413 | 0.532 |
| ChatGPT-3.5 | 0.823 | 0.392 | 0.378 | 0.518 |
| Bing AI | 0.886 | 0.892 | 0.787 | 0.834 |
| Bard | 0.823 | 0.625 | 0.496 | 0.619 |

## 2. ONC 2012 (469 cặp bắt buộc cảnh báo)

Nhận ra cả hai tên: 384/469. Báo ở mức Nghiêm trọng trở lên: 337 (0.719); có báo ở mọi mức: 376.

| Quy tắc | Số cặp | Nhận ra tên | Có cảnh báo | ≥ Nghiêm trọng |
|---|---|---|---|---|
| ONC-01 Amphetamine derivatives – MAO inhibitors | 60 | 55 | 55 | 55 |
| ONC-02 Atazanavir – Proton pump inhibitors | 5 | 5 | 5 | 5 |
| ONC-03 Febuxostat – Azathioprine, mercaptopurine | 2 | 2 | 2 | 2 |
| ONC-04 SSRI/SNRI – MAO inhibitors | 55 | 55 | 55 | 55 |
| ONC-05 Irinotecan – CYP3A4 inhibitors | 23 | 23 | 21 | 13 |
| ONC-06 Narcotic analgesics – MAO inhibitors | 30 | 30 | 30 | 30 |
| ONC-07 Tricyclic antidepressants – MAO inhibitors | 95 | 50 | 50 | 50 |
| ONC-09 Ramelteon – CYP1A2 inhibitors | 4 | 4 | 4 | 1 |
| ONC-10 Strong CYP3A4 inducers – Protease inhibitors | 60 | 60 | 60 | 35 |
| ONC-11 Simvastatin, lovastatin – CYP3A4 inhibitors | 42 | 42 | 40 | 40 |
| ONC-12 CYP3A4 inhibitors – Ergot alkaloids | 64 | 32 | 28 | 28 |
| ONC-13 Tizanidine – CYP1A2 inhibitors | 7 | 7 | 7 | 7 |
| ONC-14 Tranylcypromine – Procarbazine | 1 | 1 | 1 | 1 |
| ONC-15 Triptans – MAO inhibitors | 21 | 18 | 18 | 15 |

## 3. Đơn thật (249 đơn MIMIC-IV Demo, 4 đơn Việt Nam)

| Nhóm | Thuốc có đáp án | Nhận đúng | Nhận nhầm | Gợi ý | Không nhận ra |
|---|---|---|---|---|---|
| mimic | 3403 | 0.764 | 0.001 | 0.087 | 0.148 |
| vn | 9 | 1.0 | 0.0 | 0.0 | 0.0 |
| all | 3412 | 0.765 | 0.001 | 0.086 | 0.148 |

Trùng hoạt chất: bắt được 20/73; cảnh báo bắt buộc ONC trên đơn: 1/1.
Gánh cảnh báo mỗi đơn (trung vị / P90): thuốc–thuốc 6 / 24.0, mức Nghiêm trọng trở lên 1 / 5.0, thực phẩm 7 / 14.0. Đơn có ≥ 1 cảnh báo Nghiêm trọng: 0.554. Cảnh báo có nguồn: 1.0.

### Thuốc bị nhận nhầm (tối đa 40)

- MI-26467376: `Phosphorus` → phosphorus (đáp án potassium phosphate, sodium phosphate, dibasic, sodium phosphate, monobasic)
- MI-28258130: `Phosphorus` → phosphorus (đáp án potassium phosphate, sodium phosphate, dibasic, sodium phosphate, monobasic)
- MI-28676446: `Calcium Carbonate` → Calcium carbonate (đáp án aluminum hydroxide, magnesium hydroxide, simethicone)
- MI-29483621: `Phosphorus` → phosphorus (đáp án potassium phosphate, sodium phosphate, dibasic, sodium phosphate, monobasic)

### Trùng hoạt chất bị sót (tối đa 30)

- MI-20093566: Lactulose + Lactulose Enema
- MI-20285402: Vancomycin + Vancomycin Oral Liquid
- MI-20321825: Vancomycin + Vancomycin Oral Liquid
- MI-21039249: Acetaminophen + Oxycodone-Acetaminophen
- MI-21039249: Aluminum-Magnesium Hydrox.-Simethicone + Simethicone
- MI-21255400: Acetaminophen + Oxycodone-Acetaminophen (5mg-325mg)
- MI-21540783: Acetaminophen + Hydrocodone-Acetaminophen
- MI-21791856: Albuterol 0.083% Neb Soln + Ipratropium-Albuterol Neb
- MI-22326517: Albuterol 0.083% Neb Soln + Albuterol Inhaler
- MI-22508257: Acetaminophen + HYDROcodone-Acetaminophen (5mg-325mg)
- MI-22580999: Acetaminophen + Oxycodone-Acetaminophen (5mg-325mg)
- MI-22675517: Acetaminophen + Oxycodone-Acetaminophen (5mg-325mg)
- MI-23132022: Acetaminophen + HYDROcodone-Acetaminophen (5mg-325mg)
- MI-23251352: Acetaminophen + Oxycodone-Acetaminophen (5mg-325mg)
- MI-23473524: Vancomycin + Vancomycin Oral Liquid
- MI-23488445: Albuterol Inhaler + Ipratropium-Albuterol Neb
- MI-23688993: Aluminum-Magnesium Hydrox.-Simethicone + Milk of Magnesia
- MI-24225421: Ciprofloxacin 0.3% Ophth Soln + Ciprofloxacin HCl
- MI-24490144: Nitroglycerin + Nitroglycerin SL
- MI-24928679: Nicotine Patch + Nicotine Polacrilex
- MI-24997044: Albuterol 0.083% Neb Soln + Albuterol Inhaler
- MI-24997044: Acetaminophen + Oxycodone-Acetaminophen
- MI-25020332: Albuterol 0.083% Neb Soln + Ipratropium-Albuterol Neb
- MI-25020332: Guaifenesin ER + Guaifenesin-Dextromethorphan
- MI-25020332: Morphine SR (MS Contin) + Morphine Sulfate (Oral Solution) 2 mg/mL
- MI-25177949: Lactulose + Lactulose Enema
- MI-25926192: Aspirin + Aspirin EC
- MI-25926192: Acetaminophen + Oxycodone-Acetaminophen
- MI-26013492: Acetaminophen + HYDROcodone-Acetaminophen (5mg-325mg)
- MI-26226543: Potassium Chloride + Potassium Chloride Replacement (Critical Care and Oncology)

## 4. Mô phỏng phương án

```json
[
 {
  "option": "cutoff_minor",
  "drugscom": {
   "sensitivity": 0.924,
   "specificity": 0.977,
   "ppv": 0.948,
   "npv": 0.966,
   "f1": 0.936,
   "tp": 73,
   "fp": 4,
   "fn": 6,
   "tn": 172
  },
  "micromedex": {
   "sensitivity": 0.936,
   "specificity": 0.841,
   "ppv": 0.571,
   "npv": 0.983,
   "f1": 0.709,
   "tp": 44,
   "fp": 33,
   "fn": 3,
   "tn": 175
  },
  "alerts_per_rx_median": 6,
  "alerts_per_rx_p90": 24.0
 },
 {
  "option": "cutoff_moderate",
  "drugscom": {
   "sensitivity": 0.924,
   "specificity": 1.0,
   "ppv": 1.0,
   "npv": 0.967,
   "f1": 0.96,
   "tp": 73,
   "fp": 0,
   "fn": 6,
   "tn": 176
  },
  "micromedex": {
   "sensitivity": 0.936,
   "specificity": 0.861,
   "ppv": 0.603,
   "npv": 0.984,
   "f1": 0.733,
   "tp": 44,
   "fp": 29,
   "fn": 3,
   "tn": 179
  },
  "alerts_per_rx_median": 6,
  "alerts_per_rx_p90": 21.0
 },
 {
  "option": "cutoff_major",
  "drugscom": {
   "sensitivity": 0.114,
   "specificity": 1.0,
   "ppv": 1.0,
   "npv": 0.715,
   "f1": 0.205,
   "tp": 9,
   "fp": 0,
   "fn": 70,
   "tn": 176
  },
  "micromedex": {
   "sensitivity": 0.17,
   "specificity": 0.995,
   "ppv": 0.889,
   "npv": 0.841,
   "f1": 0.285,
   "tp": 8,
   "fp": 1,
   "fn": 39,
   "tn": 207
  },
  "alerts_per_rx_median": 1,
  "alerts_per_rx_p90": 5.0
 },
 {
  "option": "source_ddinter_only",
  "drugscom": {
   "sensitivity": 0.924,
   "specificity": 1.0,
   "ppv": 1.0,
   "npv": 0.967,
   "f1": 0.96,
   "tp": 73,
   "fp": 0,
   "fn": 6,
   "tn": 176
  },
  "micromedex": {
   "sensitivity": 0.936,
   "specificity": 0.861,
   "ppv": 0.603,
   "npv": 0.984,
   "f1": 0.733,
   "tp": 44,
   "fp": 29,
   "fn": 3,
   "tn": 179
  }
 },
 {
  "option": "fn_breakdown_drugscom",
  "reasons": {
   "name_not_recognized": 2,
   "no_record": 4
  }
 },
 {
  "option": "fn_breakdown_micromedex",
  "reasons": {
   "no_record": 3
  }
 },
 {
  "option": "fp_vs_drugscom_but_micromedex_pos",
  "n_fp": 0,
  "micromedex_positive": 0
 },
 {
  "option": "onc_alert_moderate_or_more",
  "rate": 0.802
 },
 {
  "option": "sources_seen",
  "sources": {
   "ddinter": 3191,
   "patel2020": 36,
   "openfda": 7
  }
 }
]
```

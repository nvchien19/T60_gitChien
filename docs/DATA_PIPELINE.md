# Dữ liệu P-060: toàn bộ việc đã làm, từ thu thập đến nạp Database

Cập nhật: 2026-10-04. Tài liệu này mô tả dữ liệu tương tác thuốc của bản MVP: lấy từ đâu, làm sạch thế nào,
đợt rà soát ngày 2026-10-04 tìm thấy gì và sửa gì, hiện trạng trong Postgres, và cách gửi dữ liệu cho đồng đội.

Thư mục `data/` bị `.gitignore` loại, nên script pipeline và file dữ liệu **không** nằm trong git. Mô tả từng bảng
và ý nghĩa từng cột nằm ở `data/mvp/README.md` (sinh tự động mỗi lần dựng).

## 1. Tóm tắt

- Dữ liệu trước ngày 2026-10-04 **chưa sạch hẳn**. Lỗi gồm: ký tự ẩn, entity HTML, giá trị giữ chỗ, bản ghi trùng,
  mảnh câu bị coi là hoạt chất, nhiều hoạt chất khác nhau bị gộp chung một mã, và khoảng 130 dòng thuốc kháng acid
  (nhôm hydroxyd gel...) không nối được với nguồn tương tác.
- Tất cả đã được sửa **trong script** (`data/clean_dav.py`, `data/build_ddi.py`), không sửa tay file CSV. Dựng lại
  cho kết quả giống hệt nhau giữa các lần chạy.
- Bản sạch đã nạp vào Postgres (container `p-060-db-1`, CSDL `ddi`), cả schema `public` mà backend đọc lẫn schema
  `mvp`. Riêng `public.pk_ddi` còn trống do lỗi có sẵn của script seed (mục 8).
- Còn 11 mục mà script kiểm tra vẫn báo. Đã xem từng mục: đều là đặc điểm của nguồn hoặc thiết kế có chủ ý, không
  phải lỗi (mục 6). Các giới hạn thật sự còn lại ghi ở mục 7.

## 2. Luồng dữ liệu

```
crawl_dav.py  → data/dav_raw/page_*.json (111 trang) → dav_thuoc.csv (55.005 dòng thô)
clean_dav.py  → dav_thuoc_clean.csv (54.883 số đăng ký) + dav_hoat_chat.csv (87.604 dòng hoạt chất)
crawl_ddi.py  → data/nguon/{ddinter, openfda, patel2020, pkddip}
build_ddi.py  → data/mvp/*.csv (15 bảng) + data/mvp/README.md
seed_mvp.py   → Postgres, schema public (bảng backend đọc)
load_mvp.py   → Postgres, schema mvp (db/mvp_schema.sql)
audit_mvp.py  → báo cáo kiểm tra độ sạch
```

### 2.1. Thu thập danh mục thuốc Việt Nam (`data/crawl_dav.py`)

- Nguồn: cổng công bố thuốc của Cục Quản lý Dược (dichvucong.dav.gov.vn/congbothuoc). Gọi đúng endpoint mà trang web
  dùng, tải theo trang, có resume khi bị ngắt.
- Kết quả: 111 file JSON trong `data/dav_raw/`, gộp thành `dav_thuoc.csv` 55.005 dòng. Ngày tải: 2026-09-30.

### 2.2. Làm sạch danh mục DAV (`data/clean_dav.py`)

Đọc JSON gốc (không đọc CSV, để giữ kiểu dữ liệu) rồi:

- Chuẩn hóa Unicode NFC, bỏ ký tự vô hình, gộp khoảng trắng và xuống dòng.
- Giá trị giữ chỗ (`--`, `.`, `NA`...) chuyển thành rỗng.
- Số đăng ký: bỏ khoảng trắng quanh dấu `-`, tách số đăng ký cũ ghi trong ngoặc sang cột riêng.
- Ngày về dạng `YYYY-MM-DD`; tuổi thọ về số tháng; mã phân loại về nhãn chữ.
- Tên quốc gia: gộp biến thể Anh, Việt, sai chính tả về một tên tiếng Việt.
- Trùng số đăng ký: giữ bản có ngày cấp mới nhất, rồi bản đầy đủ nhất. 55.005 dòng còn 54.883.
- Tách trường hoạt chất thành từng hoạt chất kèm hàm lượng (87.604 dòng). Ca khó tách được đánh dấu `can_kiem_tra`.
- Phân loại mỗi dòng (cột `loai`): `hoat_chat` 87.409, `ta_duoc` 89 (nước cất pha tiêm, tá dược vđ...),
  `khong_phai_hoat_chat` 106 (mảnh câu như "và", "Hộp 10 vỉ").

### 2.3. Thu thập nguồn tương tác (`data/crawl_ddi.py`)

| Nguồn | Nội dung lấy | Dung lượng | Giấy phép |
|---|---|---|---|
| DDInter 2.0 | Danh mục hoạt chất và mã ATC; cặp tương tác thuốc-thuốc kèm cơ chế và khuyến cáo xử trí; thuốc-thức ăn; thuốc-bệnh; trùng lặp điều trị | 154 MB | CC BY-NC-SA 4.0, chỉ phi thương mại |
| openFDA | Nhãn thuốc FDA: mục tương tác, chống chỉ định, cảnh báo đóng khung, đường dùng | 1,8 GB | Dữ liệu công |
| Patel 2020 (PMC7109143) | Bảng thuốc tương tác với thuốc giảm acid | 144 KB | CC BY-NC 4.0, chỉ phi thương mại |
| PK-DDIP | Tương tác dược động học định lượng (thay đổi AUC) | 100 KB | Không ghi giấy phép |

### 2.4. Dựng bộ dữ liệu MVP (`data/build_ddi.py`)

- **Nối tên hoạt chất DAV với DDInter** theo thứ tự: từ điển của dự án (`MANUAL`), khác chính tả Việt/Anh (hàm
  `skeleton`), bỏ tên muối và dạng hydrat, bỏ từ chỉ dạng vật lý, tách thuốc phối hợp, rồi so gần đúng. Nối chắc chắn
  ghi `ok`; nối gần đúng chỉ ghi `suggest` để người dùng xác nhận; không nối được ghi `unknown`.
- **Thực thể thuốc = hoạt chất + đường dùng.** DDInter tách bản ghi theo đường dùng, nên mỗi thuốc DAV được nối theo
  đường dùng suy ra từ dạng bào chế.
- **Lớp 1**: cặp tương tác cấp hoạt chất từ DDInter. **Lớp 2**: ngoại lệ theo dạng bào chế và đường dùng (Patel 2020,
  nhãn FDA). Lớp 2 không bao giờ hạ mức một chống chỉ định.
- Hoạt chất chỉ có ở DAV nhận mã `DAV:<khóa>`; hoạt chất chỉ có trong Patel 2020 nhận mã `EXT:<tên>`.
- Mọi bản ghi đều mang `source_id`, và bảng `sources` ghi ngày cập nhật của từng nguồn.

### 2.5. Nạp Postgres (`db/load_mvp.py`)

Chạy `db/mvp_schema.sql` (xóa và tạo lại schema `mvp`), `COPY` 15 bảng theo thứ tự khóa ngoại, so số dòng CSV với
số dòng trong DB, rồi `ANALYZE`.

## 3. Đợt rà soát 2026-10-04: cách kiểm tra

Script `db/audit_mvp.py` (chỉ dùng thư viện chuẩn) đọc `data/mvp/*.csv` và `db/mvp_schema.sql`, kiểm tra:

- Cấu trúc: cột khớp schema, NOT NULL, kiểu dữ liệu, khóa chính không trùng, khóa ngoại không mồ côi.
- Văn bản: khoảng trắng thừa, ký tự ẩn và ký tự điều khiển, lỗi mã hóa, thẻ và entity HTML, giá trị giả rỗng
  (`nan`, `None`, `-`), chuẩn NFC.
- Nghiệp vụ: `drug_a < drug_b`, không có cặp tự tương tác, bản ghi trùng, mức độ hợp lệ, số đếm (`n_products`,
  `n_interactions`, `both_in_vn`) khớp dữ liệu thật, `alias` đúng dạng chuẩn hóa, ngày hợp lệ.

```
python db/audit_mvp.py data/mvp db/mvp_schema.sql
```

## 4. Lỗi tìm thấy và cách sửa

| # | Lỗi trong dữ liệu cũ | Quy mô | Cách sửa (trong script) |
|---|---|---|---|
| 1 | Ký tự ẩn và ký tự điều khiển: gạch nối mềm, zero-width, dấu hướng chữ, `\x02`, `\x08` (vd tên thuốc `Paracetamol\x02cafein`) | 2 tên thuốc, 1 tên công ty, 7 mô tả cơ chế, khoảng 44 ô nhãn FDA (240 ký tự) | `clean_text` và `clean_str` bỏ ký tự vô hình, thay ký tự điều khiển bằng dấu cách |
| 2 | Entity HTML chưa giải mã (`&gt;`) | 1 thuốc | `html.unescape` ở cả hai script |
| 3 | Lỗi mã hóa `Olumiant\x81¥` (đúng là `Olumiant®`) | 5 chỗ | Thêm vào bảng `MOJIBAKE` |
| 4 | Mục nhãn FDA chỉ ghi `NONE` | 2 ô | Hàm `fda_text` chuyển giá trị giữ chỗ thành rỗng |
| 5 | Nhãn FDA không có mục cảnh báo nào | 7 nhãn | Bỏ khỏi `fda_labels` |
| 6 | Mảnh câu bị coi là hoạt chất: "Týp 1/2/3", "tuýp 2", "CH", "gel", "muối" | 12 dòng, sinh ra các mã rác như `DAV:ch` | Bổ sung quy tắc `KHONG_PHAI` trong `clean_dav.py`; các dòng này thành `excluded` |
| 7 | Dòng hoạt chất có tên rỗng | 5 dòng | Giữ nguyên văn bản gốc, gắn `can_kiem_tra` và `needs_review` để xem tay |
| 8 | Mô tả cơ chế DDInter trùng hoàn toàn (cùng mức, cơ chế, mô tả, xử trí, tài liệu; vd id 619 và 7677) | 7 nhóm, làm 21 cặp hiện hai lần cùng nội dung | Gộp về id nhỏ nhất; 255 cặp khác đổi `mechanism_id` sang id được giữ |
| 9 | Nhiều hoạt chất khác nhau bị gộp chung một mã `DAV:` vì bỏ muối xong chỉ còn từ chung (vd `DAV:gel` chứa cả nhôm phosphat, nhôm hydroxyd, magnesi hydroxyd; `DAV:l` chứa các muối lysin; `DAV:kho`, `DAV:hoa`) | 33 nhóm | Viết lại `dav_only_key`: khi phần còn lại chỉ là từ chung thì giữ cả tên, bỏ dạng hydrat |
| 10 | Thuốc kháng acid ghi kèm dạng vật lý không nối được DDInter ("Nhôm hydroxyd gel khô", "Dried aluminium hydroxide gel", "Magnesium oxide nặng", "Sắt (II) sulfat khô") nên bị báo "chưa có bản ghi" | khoảng 130 dòng | Thêm bước bỏ từ chỉ dạng vật lý và ký hiệu dược điển (`gel`, `khô`, `dried`, `nặng`, `nhẹ`, `USP`, `BP`...) rồi nối lại |
| 11 | Tên kèm ký hiệu dược điển ("Paclitaxel USP", "Cefixime BP") chỉ được `suggest` | khoảng 70 dòng | Cùng bước ở dòng 10, nay là `ok` |
| 12 | Kết quả dựng không ổn định: mỗi lần chạy chọn khác nhau khi có giá trị bằng nhau (tên hiển thị của hoạt chất DAV, bản ghi DDInter cho PK-DDIP) | Vài chục dòng lệch giữa hai lần chạy | Sắp xếp có tiêu chí phụ rõ ràng. Đã chạy 2 lần với `PYTHONHASHSEED` khác nhau, md5 trùng nhau |

Lỗi số 10 quan trọng nhất về an toàn: các thuốc chứa nhôm hydroxyd gel trước đây không sinh cảnh báo tương tác nào.

## 5. Số liệu trước và sau

| Bảng | Trước | Sau | Chênh |
|---|---|---|---|
| `sources` | 6 | 6 | 0 |
| `drugs` | 5.621 | 5.619 | −2 |
| `aliases` | 63.572 | 63.572 | 0 |
| `products` | 54.883 | 54.883 | 0 |
| `product_ingredients` | 87.615 | 87.615 | 0 |
| `ingredient_map` | 7.484 | 7.477 | −7 |
| `interaction_mechanisms` | 8.465 | 8.458 | −7 |
| `drug_interactions` | 259.881 | 259.860 | −21 |
| `food_interactions` | 857 | 857 | 0 |
| `disease_interactions` | 8.281 | 8.281 | 0 |
| `duplication_classes` | 741 | 741 | 0 |
| `ara_interactions` | 272 | 272 | 0 |
| `pk_ddi` | 4.265 | 4.265 | 0 |
| `fda_labels` | 4.931 | 4.924 | −7 |
| `dosage_form_rules` | 28 | 28 | 0 |

Trạng thái nối hoạt chất (`product_ingredients.status`):

| Trạng thái | Trước | Sau |
|---|---|---|
| `ok` | 54.933 | 55.123 |
| `suggest` | 1.088 | 1.019 |
| `unknown` | 31.411 | 31.272 |
| `excluded` | 183 | 190 |

- Số cặp hoạt chất có tương tác không đổi: 252.768 cặp (major 52.771, moderate 194.571, minor 12.518 bản ghi).
- Thuốc còn hiệu lực có mọi hoạt chất nối chắc chắn: 35.258 (72,0%); nối một phần 4.338 (8,9%); chưa có bản ghi
  9.385 (19,2%).
- Hoạt chất: 2.290 từ DDInter, 3.324 chỉ có ở DAV, 5 từ Patel 2020.

**Thay đổi có thể ảnh hưởng mã nguồn khác:**

- 182 mã `DAV:` cũ không còn và 180 mã mới xuất hiện (do tách nhóm gộp nhầm và do nối được sang DDInter). Mã
  `DDInter...` và `interaction_id` không đổi; 21 `interaction_id` trùng nội dung bị bỏ.
- 39 hoạt chất `DAV:` đổi tên hiển thị (nay luôn chọn cách viết phổ biến nhất).
- Bộ golden set `eval/golden/golden_set.jsonl`: đã đối chiếu, cả 48 ca vẫn trỏ tới bản ghi còn tồn tại. Chạy
  `python eval/run_eval.py --oracle` sau khi đổi dữ liệu: các metric tất định vẫn đạt.

## 6. Mục script kiểm tra vẫn báo nhưng không phải lỗi

| Mục | Số lượng | Lý do giữ nguyên |
|---|---|---|
| Giá trị `none` ở `products.route_source`, `ara_interactions.severity`, `dosage_form_rules.severity` | 112, 114, 6 | Là giá trị hợp lệ của danh mục: "không suy ra được" hoặc "không có tương tác đáng kể" |
| Cơ chế có mô tả giống nhau nhưng khác id | 1.193 | Khác nhau ở mức độ, khuyến cáo xử trí hoặc tài liệu, nên không gộp |
| Tên phối hợp trỏ tới 2 hoạt chất | 6 | Đúng: "amoxicilin acid clavulanic" gồm 2 hoạt chất |
| Thuốc không có số đăng ký | 1 (Alsoben) | DAV ghi địa chỉ vào ô số đăng ký, nên để trống |
| Trùng (product_id, position) | 11 | Một dòng DAV là thuốc phối hợp, tách thành 2 hoạt chất cùng vị trí |
| `mesh_id` dạng `OMIM:` | 16 | DDInter dùng mã OMIM cho bệnh di truyền |
| `pk_ddi` chỉ nối được một phía | 302 | Chất còn lại không có trong DDInter; giữ làm bằng chứng tham khảo |
| `effective_time` của nhãn FDA ở tương lai | 2 | openFDA ghi ngày hiệu lực sắp tới của nhãn (2026-10-30, 2026-11-23) |
| Nhãn FDA không nối được hoạt chất | 1.764 | Thuốc chỉ có ở Mỹ hoặc sản phẩm phối hợp; không dùng để tra |

## 7. Giới hạn còn lại

- 31.272 dòng hoạt chất (35,7%) chưa có trong nguồn tương tác: chủ yếu dược liệu, vitamin và khoáng phối hợp, hoặc
  thuốc DDInter không có (piracetam, etoricoxib, domperidon...). Với các thuốc này hệ thống phải hiện "chưa có bản
  ghi", không được hiểu là an toàn.
- Trong 3.324 hoạt chất `DAV:` vẫn còn một số tên là mảnh câu hoặc từ chung (vd "Sau khi hoàn nguyên", "bất hoạt",
  "Đính chính hoạt chất chính - hàm lượng"). Chúng không có dữ liệu tương tác nên không sinh cảnh báo sai, nhưng nên
  bổ sung quy tắc loại ở `clean_dav.py`.
- 293 dòng gắn `can_kiem_tra`: chuỗi hoạt chất DAV ghi quá lạ, cần người xem.
- Một dòng "Nhôm hydroxyd gel khô Magnesi hydroxyd" chỉ nối được nhôm hydroxyd, thiếu magnesi hydroxyd.
- Đường dùng và dạng bào chế suy ra bằng quy tắc từ văn bản DAV; xem `route_source` để biết độ chắc.
- Chưa có dược sĩ rà soát nội dung chuyên môn. Đợt này chỉ kiểm tra tính sạch và nhất quán của dữ liệu.
- Giấy phép: DDInter và Patel 2020 chỉ cho dùng phi thương mại; PK-DDIP không ghi giấy phép.
- MVP không kiểm tra lại số đăng ký.

## 8. Trạng thái Database

Container `p-060-db-1` (image `pgvector/pgvector:pg16`), cổng `127.0.0.1:5432`, người dùng `ddi`, CSDL `ddi`, khớp
`DATABASE_URL` trong `.env`. Trong CSDL này dữ liệu nằm ở **hai nơi**, vì hai phần mã nguồn đọc theo hai cách:

| Nơi lưu | Nạp bằng | Ai đọc |
|---|---|---|
| Schema `public` (bảng của SQLAlchemy) | `python scripts/seed_mvp.py --database-url <DATABASE_URL> --fresh` | Backend đang chạy (`interface/backend`), tức là ứng dụng và agent |
| Schema `mvp` (`db/mvp_schema.sql`, có hàm `mvp.find_drug`, `mvp.interactions_among`) | `python db/load_mvp.py` | `src/services/ddi_repository.py` (bước LLM giải thích, hiện chưa nối vào ứng dụng) |

- Cả hai nơi đã được nạp bản dữ liệu sạch ngày 2026-10-04, số dòng khớp CSV.
- **Riêng bảng `public.pk_ddi` còn trống.** `scripts/seed_mvp.py` lỗi khóa ngoại trên Postgres vì 415 dòng PK-DDIP là
  thuốc phối hợp có mã dạng `DDInterA;DDInterB`. Lỗi này có từ trước, không do đợt làm sạch. Bảng chỉ là bằng chứng bổ
  sung nên ứng dụng vẫn chạy; cần sửa script seed (bỏ qua hoặc tách các dòng này) để nạp đủ.
- `docker-compose.yml` trong repo ghi `postgres/postgres/rathuoc`, còn container đang chạy và `.env` dùng `ddi/ddi`.
  Volume đã tạo từ trước nên container giữ cấu hình `ddi`. Nên thống nhất lại một cấu hình.
- `db/load_mvp.py` xóa và tạo lại riêng schema `mvp`. `scripts/seed_mvp.py --fresh` chỉ xóa các bảng dữ liệu tham
  chiếu ở `public`, không đụng bảng đơn thuốc.
- Nên gộp về một nơi lưu để tránh nạp hai lần và tránh hai bản lệch nhau.

## 9. Chạy lại từ đầu

```
cd data
pip install requests ijson "pandas<3" numpy rapidfuzz openpyxl
python crawl_dav.py      # chỉ khi cần cập nhật DAV
python clean_dav.py
python crawl_ddi.py      # chỉ khi cần cập nhật nguồn; tải 1,8 GB, mất vài giờ
python build_ddi.py      # khoảng 1-2 phút
cd ..
python db/audit_mvp.py data/mvp db/mvp_schema.sql
docker compose up -d db
python scripts/seed_mvp.py --database-url <DATABASE_URL> --fresh --only <các bảng trừ pk_ddi, xem mục 10>
python db/load_mvp.py
```

Trên Windows đặt `PYTHONUTF8=1` trước khi chạy để tránh lỗi mã hóa cp1252. Dùng pandas 2.x.

## 10. Gửi dữ liệu cho đồng đội mà không commit

Hai gói đã tạo sẵn trong `data/share/` (thư mục này nằm trong `data/` nên git bỏ qua):

| File | Dung lượng | Dùng khi |
|---|---|---|
| `ddi_full_2026-10-04.dump` | 36 MB | Đồng đội chỉ cần Database. Chứa cả schema `public` (backend đọc) và schema `mvp` |
| `mvp_csv_2026-10-04.zip` | 18 MB | Đồng đội cần CSV: tự seed, chạy `eval/golden/build_golden.py`, `db/audit_mvp.py` |

Gửi file qua Google Drive hoặc kênh chat của nhóm ở chế độ **chỉ thành viên nhóm xem được**. Không đưa lên nơi
công khai (kể cả GitHub Release của repo công khai), vì PK-DDIP không ghi giấy phép và DDInter chỉ cho dùng phi
thương mại.

Đồng đội nhận file dump (khôi phục vào một CSDL trống; đã thử khôi phục thành công ngày 2026-10-04):

```
docker compose up -d db
docker compose cp ddi_full_2026-10-04.dump db:/tmp/ddi.dump
docker compose exec db sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner /tmp/ddi.dump'
```

Nếu CSDL đã có bảng từ trước thì tạo CSDL mới (`createdb`) rồi khôi phục vào đó, và trỏ `DATABASE_URL` sang.

Đồng đội nhận file zip: giải nén vào `data/` để có `data/mvp/*.csv`, chạy `docker compose up -d db`, rồi:

```
python scripts/seed_mvp.py --database-url <DATABASE_URL> --fresh --only sources,drugs,aliases,products,product_ingredients,interaction_mechanisms,drug_interactions,food_interactions,disease_interactions,duplication_classes,ara_interactions,fda_labels,dosage_form_rules
python db/load_mvp.py
```

Lệnh đầu nạp các bảng backend đọc (bỏ `pk_ddi` vì lỗi nêu ở mục 8); lệnh sau nạp schema `mvp`.

Tạo lại gói sau mỗi lần dựng dữ liệu:

```
docker compose exec db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc --no-owner --no-privileges -f /tmp/ddi.dump'
docker compose cp db:/tmp/ddi.dump data/share/ddi_full_<ngày>.dump
```

Script pipeline (`data/*.py`) cũng chưa nằm trong git. Muốn đồng đội dựng lại được thì gửi kèm 4 script, hoặc thêm
ngoại lệ `!data/*.py` vào `.gitignore` sau khi nhóm đồng ý.

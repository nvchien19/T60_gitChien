# Kế hoạch phát triển Backend (API trước, Agent/Chatbot sau)

> **Dự án:** Rả thuốc — tra cứu tương tác thuốc & cảnh báo an toàn
> **Phạm vi file này:** chỉ Backend. Frontend (Next.js) và Chatbot Agent (LangGraph) làm sau.
> **Tài liệu gốc:** `Topic.md`, `ARCHITECTURE.md`
> **Ngày tạo:** 2026-09-30

---

## 1. Mục tiêu & nguyên tắc

### 1.1 Mục tiêu P0 (Backend)

1. Có API FastAPI chạy được, kết nối Postgres.
2. Có CSDL thuốc & tương tác **mô phỏng** theo cấu trúc DrugBank/RxNorm + vector DB (pgvector).
3. Có 3 tool dưới dạng **service hàm thuần** (chưa cần LangGraph):
   - `drug-name normalizer` — chuẩn hóa tên thuốc (mờ / viết tắt / alias).
   - `interaction lookup` — tra cứu tương tác thuốc–thuốc (+ thuốc–thực phẩm ở mức cơ bản).
   - `severity ranker` — xếp hạng mức độ nghiêm trọng (deterministic, từ DB).
4. FE hoặc curl gọi API là ra kết quả có `citations` + `disclaimer`, không cần LLM/chatbot vẫn chạy.

### 1.2 Nguyên tắc (bắt buộc từ PRD)

- **Grounded tuyệt đối:** severity lấy từ DB, không để LLM suy luận.
- **Không khuyên thuốc:** API không bao giờ trả `ngưng / đổi / tăng-giảm liều / kê thuốc`. Chỉ trả cảnh báo + "liên hệ bác sĩ/dược sĩ".
- **"Chưa có bản ghi" ≠ "an toàn":** không tìm thấy = trả `unknown / no_record`, không trả `safe`.
- **Mọi finding phải có `source_id`:** không citation = không trả.
- **Thiết kế để bọc thành agent tool sau:** mỗi tool là 1 hàm thuần `input -> output`, không dính FastAPI/DB session bên trong core logic.

```
API (FastAPI) → Service → Tool-core (thuần) → Repository → Postgres/pgvector
                                          ↘ (sau này) LangGraph Tool wrapper
```

---

## 2. Tech stack chốt

| Lớp | Chọn | Lý do / Ghi chú |
|-----|------|-----------------|
| Backend | **FastAPI 0.115+** + Uvicorn | Theo template, có sẵn Swagger `/docs` |
| DB quan hệ | **PostgreSQL 16** | Lưu users, drugs, aliases, interactions, checks, findings, audit |
| Vector DB | **pgvector** (extension của Postgres) | Không dùng Chroma/Pinecone riêng — giữ 1 DB, metadata + embedding cùng chỗ, khỏi đồng bộ |
| ORM / Migration | SQLAlchemy 2.0 (async) + Alembic | Bật lại trong `requirements.txt` (đang comment) |
| Driver | `psycopg[binary]` (async) hoặc `asyncpg` | Khuyên `asyncpg` cho async SQLAlchemy |
| Validate | Pydantic v2 + pydantic-settings | Có sẵn |
| Auth (tối thiểu) | JWT HS256 + argon2id, RBAC `patient / pharmacist` | Làm tối giản trước, đủ phân quyền cho HITL sau |
| Fuzzy match | `rapidfuzz` | Chuẩn hóa tên mờ, không cần LLM |
| Embedding | `openai text-embedding-3-small` (hoặc `sentence-transformers` nếu offline) | Chỉ embed `mechanism + description` của interaction |
| Test | pytest + pytest-asyncio + httpx ASGITransport | Mock embedding, không gọi OpenAI thật trong test |
| Deploy | Docker + docker-compose (BE + Postgres+pgvector) | FE deploy sau |

### 2.1 `requirements.txt` cần mở / thêm

```txt
# Mở comment sẵn có:
sqlalchemy>=2.0.0
alembic>=1.14.0
asyncpg>=0.29.0
pgvector>=0.3.0

# Thêm mới:
rapidfuzz>=3.9.0
python-jose[cryptography]>=3.3.0
argon2-cffi>=23.1.0
slowapi>=0.1.9
```

---

## 3. Kiến trúc Backend (giai đoạn API-first)

```text
src/  (giữ nguyên theo template, KHÔNG tách interface/be vội)
├── main.py              # FastAPI app, lifespan, CORS, include router
├── config.py            # Settings (mở rộng DATABASE_URL, JWT, embedding)
├── api/
│   ├── routes.py        # Gom router giai đoạn đầu (tách sau khi >300 dòng)
│   └── routers/
│       ├── health.py
│       ├── drugs.py         # tra cứu thuốc, normalize
│       ├── interactions.py  # tra cứu tương tác
│       ├── checks.py        # POST /checks (luồng chính)
│       └── sources.py       # nguồn dữ liệu & giới hạn
├── schemas/             # Pydantic request/response (theo router)
├── services/            # Business logic: normalize_service, lookup_service, rank_service, check_service
├── tools/               # CORE THUẦN (để sau bọc thành LangGraph tool): normalizer.py, lookup.py, ranker.py
├── repositories/        # Truy vấn DB duy nhất ở đây
├── db/
│   ├── base.py
│   ├── session.py
│   └── models/          # SQLAlchemy models
└── core/
    ├── security.py      # hash, jwt
    └── guardrails.py    # rule-based: chặn khuyên thuốc, check citation, mask PII
```

> Quy tắc import 1 chiều: `api → services → tools-core + repositories → db`. `tools-core` **không** import FastAPI/SQLAlchemy session.

---

## 4. Data model — Postgres + pgvector (khớp `data/mvp/` thật, không còn MOCK)

> Nguồn thật đã crawl 2026-09-30: `data/mvp/README.md` là spec chuẩn.
> Quy ước PK: giữ nguyên ID dạng TEXT của CSV (`source_id='dav'`, `drug_id='DDInter1'`,
> `mechanism_id`, `product_id`) để `COPY` trực tiếp, không sinh UUID mới.
> Mọi severity lấy từ DB. Không có bản ghi = `unknown / no_record`, không nói `an toàn`.

### 4.1 Tổng quan 3 nhóm bảng (6 + 7 + 4 = 17 bảng)

**Nhóm A — Core tra cứu VN (5 bảng, từ DAV + DDInter + từ điển dự án):**

| Bảng | File CSV | Khóa chính | Trường chính | Ghi chú |
|------|----------|------------|--------------|---------|
| `sources` | `sources.csv` (6 dòng) | `source_id TEXT PK` | `name, citation, url, license, last_updated` | `dav, ddinter, patel2020, pkddip, openfda, curated`. Ghi rõ license NC của ddinter/patel |
| `drugs` | `drugs.csv` (5.876) | `drug_id TEXT PK` (`DDInterxxx` hoặc `DAV:<khoa>`) | `name, name_vi, base_name, route_variant, drugbank_id, atc_code, drug_type, in_vn BOOL, n_products_valid, n_interactions` | DDInter tách bản ghi theo đường dùng (`ophthalmic/topical/nasal/otic/parenteral`); `base_name` là tên chung. `DAV:*` = hoạt chất chỉ có ở VN, chưa có DDI → luôn `no_record` |
| `aliases` | `aliases.csv` (63.646) | `PK (alias, drug_id, source_id)` | `alias TEXT (đã khoa(): lowercase-bỏ dấu-chỉ giữ chữ-số), alias_type, status (ok/suggest), drug_name` | Thuốc phối hợp 1 alias → N drug_id nên **không** UNIQUE(alias). `alias_type`: `inn_en/inn_vi/brand_vi/synonym/inn_vi_auto` |
| `products` | `products.csv` (54.883) | `product_id BIGINT PK` | `registration_no, name, active_ingredients, strength, dosage_form, route, form_group, enteric_coated, modified_release, category, manufacturer, status (valid/expired/withdrawn), expiry_date` | 1 dòng = 1 số đăng ký DAV. `route/form_group` đã suy luận sẵn |
| `product_ingredients` | `product_ingredients.csv` (87.504) | `id SERIAL PK`, `UNIQUE (product_id, position, drug_id)` | `ingredient, strength, drug_id FK, base_drug_id, match_method, match_score, status (ok/suggest/unknown), route_match, needs_review BOOL` | Junction DAV→DDInter **đã chọn theo đường dùng**. `route_match`: `route_specific/systemic/systemic_record/other_route` |

**Nhóm B — Tương tác & bằng chứng (7 bảng + 1 view logic):**

| Bảng | File CSV | Khóa chính | Trường chính | Ghi chú |
|------|----------|------------|--------------|---------|
| `interaction_mechanisms` | `interaction_mechanisms.csv` (8.465) | `mechanism_id TEXT PK` | `severity, mechanism_type, description, management, refs, n_pairs, source_id, embedding vector(1536)` | **Embed ở đây (8,4k đoạn), KHÔNG embed từng cặp (260k).** Mỗi mechanism dùng chung cho nhiều cặp |
| `drug_interactions` | `drug_interactions.csv` (260.100) | `interaction_id BIGINT PK`, `UNIQUE (drug_a, drug_b, mechanism_id)` | `drug_a FK, drug_b FK (CHECK drug_a < drug_b), severity, mechanism_type, both_in_vn BOOL, source_id, source_url` | Lớp 1, cấp hoạt chất. 1 cặp có thể có 2 cơ chế → UNIQUE gồm cả mechanism. DDInter chỉ có `major/moderate/minor` (52k/194k/12k) |
| `food_interactions` | `food_interactions.csv` (857) | `id SERIAL PK`, `UNIQUE (drug_id, food)` | `drug_id FK, food, food_vi, severity, mechanism_type, description, management, refs` | VD `warfarin–rau xanh (vitamin K)`, `statin–bưởi chùm` |
| `disease_interactions` | `disease_interactions.csv` (8.359) | `id SERIAL PK` | `drug_id FK, disease, mesh_id, severity, description, refs` | Thuốc–bệnh nền (P2 mới check theo bệnh, P0 chỉ hiển thị khi tra 1 thuốc) |
| `duplication_classes` | `duplication_classes.csv` (741) | `PK (class_name, drug_id)` | `drug_name, max_concurrent (=1 hầu hết)` | Trùng nhóm điều trị: ≥2 thuốc cùng class → finding `duplicate_class` |
| `ara_interactions` | `ara_interactions.csv` (272) | `id SERIAL PK` | `table, victim_drug_ids[], victim_form, victim_is_combination BOOL, ara_class, ara_drug_ids[], mechanism, effect, severity, recommendation, route_scope='oral'` | Lớp 2 Patel2020. **Chỉ áp dụng khi victim dùng ĐƯỜNG UỐNG.** Bảng 6 (`severity=''`) chỉ tham khảo, không hạ mức |
| `dosage_form_rules` | `dosage_form_rules.csv` (28) | `PK (rule_id, other_drug_id)` | `drug_id, drug_route, drug_form, other_drug_id, other_route, severity, action, effect_vi, management_vi, evidence, source_url` | Lớp 2 từ nhãn FDA. `action`: `raise_severity` (8 rule → `contraindicated`, áp mọi dạng) / `form_specific` / `no_interaction_for_form` (chỉ hạ khi lớp 1 ≠ contraindicated). DDInter **không có** contraindicated — mức này chỉ từ đây |
| `pk_ddi` *(evidence)* | `pk_ddi.csv` (4.277) | `PK (perpetrator_id, victim_id)` | `auc_fold_change, magnitude` | Bằng chứng định lượng bổ sung, không tự sinh severity |
| `fda_labels` *(evidence)* | `fda_labels.csv` (4.931) | `label_set_id TEXT PK` | `effective_time, route, substances, drug_ids[], brand_names, boxed_warning, contraindications, drug_interactions, dosage_forms...` | Gộp theo (hoạt chất, route). Hiển thị ở modal bằng chứng FE |

**Nhóm C — App (phục vụ FE §13, 4 bảng):**

| Bảng | Trường chính | Ghi chú |
|------|--------------|---------|
| `prescriptions` | `id TEXT PK (RX-xxxx), status (Chưa kiểm tra/Đã kiểm tra/Có tương tác/Cần xem lại), highest_severity_vi, checks_count, last_checked` | Map view Tổng quan + Library FE |
| `medications` | `id SERIAL PK, prescription_id FK, name, drug_id FK NULL, ingredient, dose, frequency, type, verified BOOL, norm_status, suggestions JSONB` | `verified=(status==ok)`; thêm thuốc unverified → đơn về `Cần xem lại` |
| `checks` | `id TEXT PK (CHECK-xxx), prescription_id FK, status (running/done/failed), meds_snapshot JSONB, summary JSONB, max_severity, steps_done TEXT[]` | Snapshot độc lập cho History; poll `GET /checks/{id}` |
| `reviews` | `id SERIAL PK, prescription_id FK, check_id FK, message, status (pending/done)` | Trao đổi dược sĩ (P1 HITL) |

`severity` ENUM toàn hệ thống: `contraindicated > major > moderate > minor`
(+ `duplicate_class/duplicate_active` hiển thị như `Trung bình`, + `unknown/no_record` màu xám).
Rank số hóa: `contraindicated=4, major=3, moderate=2, minor=1, unknown=0`.
Quy tắc merge nhiều nguồn: **lấy mức cao nhất**, giữ citation từng nguồn.

### 4.2 DDL (Alembic migration đầu tiên — rút gọn, đủ COPY từ `data/mvp/`)

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE sources (
  source_id TEXT PRIMARY KEY,
  name TEXT NOT NULL, citation TEXT, url TEXT, license TEXT, last_updated DATE
);
CREATE TABLE drugs (
  drug_id TEXT PRIMARY KEY,                       -- DDInter123 | DAV:<khoa>
  name TEXT NOT NULL, name_vi TEXT DEFAULT '',
  base_name TEXT NOT NULL, route_variant TEXT DEFAULT '',
  drugbank_id TEXT, atc_code TEXT, drug_type TEXT,
  in_vn BOOLEAN NOT NULL DEFAULT FALSE,
  n_products_valid INT DEFAULT 0, n_interactions INT DEFAULT 0
);
CREATE INDEX ON drugs (base_name); CREATE INDEX ON drugs (atc_code);
CREATE INDEX ON drugs (in_vn) WHERE in_vn;

CREATE TABLE aliases (
  alias TEXT NOT NULL,                            -- đã khoa()
  drug_id TEXT NOT NULL REFERENCES drugs(drug_id),
  alias_type TEXT, source_id TEXT REFERENCES sources(source_id),
  status TEXT CHECK (status IN ('ok','suggest')) DEFAULT 'ok',
  drug_name TEXT,
  PRIMARY KEY (alias, drug_id, source_id)         -- theo README: combo 1 alias -> N drug
);
CREATE INDEX ON aliases (alias); CREATE INDEX ON aliases (drug_id);

CREATE TABLE products (
  product_id BIGINT PRIMARY KEY,
  registration_no TEXT, name TEXT NOT NULL,
  active_ingredients TEXT, strength TEXT, dosage_form TEXT,
  route TEXT, form_group TEXT,
  enteric_coated BOOLEAN DEFAULT FALSE, modified_release BOOLEAN DEFAULT FALSE,
  category TEXT, manufacturer TEXT, manufacturer_country TEXT,
  status TEXT CHECK (status IN ('valid','expired','withdrawn')),
  expiry_date DATE, source_id TEXT REFERENCES sources(source_id) DEFAULT 'dav'
);
CREATE INDEX ON products USING gin (to_tsvector('simple', name));
CREATE INDEX ON products (status, route);

CREATE TABLE product_ingredients (
  id SERIAL PRIMARY KEY,   -- surrogate: 372 dong drug_id trong + 11 cap (product,position) 2 drug_id ung vien
  product_id BIGINT REFERENCES products(product_id) ON DELETE CASCADE,
  position INT NOT NULL,
  ingredient TEXT NOT NULL, strength TEXT,
  drug_id TEXT REFERENCES drugs(drug_id),   -- NULL = unknown, can kiem tra
  base_drug_id TEXT, match_method TEXT, match_score INT,
  status TEXT, route_match TEXT, needs_review BOOLEAN DEFAULT FALSE,
  UNIQUE (product_id, position, drug_id)
);
CREATE INDEX ON product_ingredients (drug_id);

CREATE TABLE interaction_mechanisms (
  mechanism_id TEXT PRIMARY KEY,
  severity TEXT CHECK (severity IN ('major','moderate','minor')),
  mechanism_type TEXT, description TEXT NOT NULL, management TEXT,
  refs TEXT, n_pairs INT DEFAULT 0,
  source_id TEXT REFERENCES sources(source_id) DEFAULT 'ddinter',
  embedding vector(1536)                          -- embed 8,4k dòng này, không embed 260k cặp
);
CREATE INDEX ON interaction_mechanisms USING hnsw (embedding vector_cosine_ops);

CREATE TABLE drug_interactions (
  interaction_id BIGINT PRIMARY KEY,
  drug_a TEXT NOT NULL REFERENCES drugs(drug_id),
  drug_b TEXT NOT NULL REFERENCES drugs(drug_id),
  -- KHONG CHECK (drug_a<drug_b): CSV sap theo SO DDInter (DDInter999<DDInter1000)
  -- nhung SQLite so TEXT ('DDInter999'>'DDInter1000'). Lookup query ca 2 chieu,
  -- app chuan hoa ve sorted_pair() numeric truoc khi merge/rank.
  severity TEXT CHECK (severity IN ('major','moderate','minor')) NOT NULL,
  mechanism_id TEXT REFERENCES interaction_mechanisms(mechanism_id),
  mechanism_type TEXT, both_in_vn BOOLEAN DEFAULT FALSE,
  source_id TEXT REFERENCES sources(source_id) DEFAULT 'ddinter',
  source_url TEXT
  -- DDInter goc co 218 cap trung (a,b,mechanism) voi 2 interaction_id khac nhau
  -- -> UNIQUE chi o interaction_id, khong UNIQUE (a,b,mechanism)
);
CREATE INDEX ix_pair_mech ON drug_interactions (drug_a, drug_b, mechanism_id);
CREATE INDEX ON drug_interactions (drug_a, drug_b);
CREATE INDEX ON drug_interactions (both_in_vn, severity) WHERE both_in_vn;

CREATE TABLE food_interactions (
  id SERIAL PRIMARY KEY, drug_id TEXT REFERENCES drugs(drug_id),
  food TEXT NOT NULL, food_vi TEXT, severity TEXT, mechanism_type TEXT,
  description TEXT, management TEXT, refs TEXT,
  source_id TEXT REFERENCES sources(source_id) DEFAULT 'ddinter',
  UNIQUE (drug_id, food)
);
CREATE TABLE disease_interactions (
  id SERIAL PRIMARY KEY, drug_id TEXT REFERENCES drugs(drug_id),
  disease TEXT NOT NULL, mesh_id TEXT, severity TEXT, description TEXT, refs TEXT,
  source_id TEXT REFERENCES sources(source_id) DEFAULT 'ddinter'
);
CREATE INDEX ON disease_interactions (drug_id);
CREATE TABLE duplication_classes (
  class_name TEXT NOT NULL, drug_id TEXT REFERENCES drugs(drug_id),
  drug_name TEXT, max_concurrent INT DEFAULT 1,
  source_id TEXT REFERENCES sources(source_id) DEFAULT 'ddinter',
  PRIMARY KEY (class_name, drug_id)
);
CREATE TABLE ara_interactions (
  id SERIAL PRIMARY KEY, table_name TEXT, category TEXT,
  victim_drug_ids TEXT[] NOT NULL, victim_form TEXT DEFAULT '',
  victim_is_combination BOOLEAN DEFAULT FALSE,
  ara_class TEXT, ara_drug_ids TEXT[],
  mechanism TEXT, effect TEXT, severity TEXT, recommendation TEXT,
  route_scope TEXT DEFAULT 'oral',                -- chỉ áp dụng đường uống
  source_id TEXT REFERENCES sources(source_id) DEFAULT 'patel2020'
);
CREATE TABLE dosage_form_rules (
  rule_id TEXT PRIMARY KEY,
  drug_id TEXT REFERENCES drugs(drug_id), drug_route TEXT, drug_form TEXT,
  other_drug_id TEXT REFERENCES drugs(drug_id), other_route TEXT,
  severity TEXT, action TEXT CHECK (action IN ('raise_severity','form_specific','no_interaction_for_form')),
  effect_vi TEXT, management_vi TEXT, evidence TEXT, source_url TEXT,
  source_id TEXT REFERENCES sources(source_id) DEFAULT 'openfda'
);
CREATE TABLE pk_ddi (
  perpetrator_id TEXT REFERENCES drugs(drug_id),
  victim_id TEXT REFERENCES drugs(drug_id),
  auc_fold_change FLOAT, magnitude TEXT,
  source_id TEXT REFERENCES sources(source_id) DEFAULT 'pkddip',
  PRIMARY KEY (perpetrator_id, victim_id)
);
CREATE TABLE fda_labels (
  label_set_id TEXT PRIMARY KEY, effective_time TEXT,
  route TEXT, substances TEXT, drug_ids TEXT[],
  brand_names TEXT, boxed_warning TEXT, contraindications TEXT,
  drug_interactions TEXT, dosage_forms_and_strengths TEXT,
  source_id TEXT REFERENCES sources(source_id) DEFAULT 'openfda'
);
-- Nhóm C (app): xem chi tiết ở §13, tạo cùng migration để FE un-mock ngay
CREATE TABLE prescriptions (
  id TEXT PRIMARY KEY, status TEXT DEFAULT 'Chưa kiểm tra',
  highest_severity_vi TEXT, checks_count INT DEFAULT 0, last_checked TIMESTAMPTZ
);
CREATE TABLE medications (
  id SERIAL PRIMARY KEY, prescription_id TEXT REFERENCES prescriptions(id) ON DELETE CASCADE,
  name TEXT NOT NULL, drug_id TEXT REFERENCES drugs(drug_id),
  ingredient TEXT, dose TEXT, frequency TEXT, type TEXT,
  verified BOOLEAN DEFAULT FALSE, norm_status TEXT, suggestions JSONB DEFAULT '[]'
);
CREATE TABLE checks (
  id TEXT PRIMARY KEY, prescription_id TEXT REFERENCES prescriptions(id),
  status TEXT DEFAULT 'running', meds_snapshot JSONB NOT NULL,
  summary JSONB, max_severity TEXT, steps_done TEXT[] DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now()
);
CREATE TABLE reviews (
  id SERIAL PRIMARY KEY, prescription_id TEXT REFERENCES prescriptions(id),
  check_id TEXT REFERENCES checks(id), message TEXT, status TEXT DEFAULT 'pending'
);
```

### 4.3 Seed từ dữ liệu thật (không còn CSV MOCK tay)

```bash
# COPY theo đúng thứ tự FK; đã có script data/build_ddi.py sinh ra data/mvp/
psql $DATABASE_URL -c "COPY sources FROM 'data/mvp/sources.csv' CSV HEADER;"
psql $DATABASE_URL -c "COPY drugs FROM 'data/mvp/drugs.csv' CSV HEADER;"
psql $DATABASE_URL -c "COPY aliases FROM 'data/mvp/aliases.csv' CSV HEADER;"
psql $DATABASE_URL -c "COPY products FROM 'data/mvp/products.csv' CSV HEADER;"
psql $DATABASE_URL -c "COPY product_ingredients FROM 'data/mvp/product_ingredients.csv' CSV HEADER;"
psql $DATABASE_URL -c "COPY interaction_mechanisms FROM 'data/mvp/interaction_mechanisms.csv' CSV HEADER;"
psql $DATABASE_URL -c "COPY drug_interactions FROM 'data/mvp/drug_interactions.csv' CSV HEADER;"
# ... food, disease, duplication, ara, pk_ddi, fda_labels, dosage_form_rules tương tự
python scripts/embed_mechanisms.py   # embed 8.465 description -> interaction_mechanisms.embedding
```

Số lượng kỳ vọng (smoke test): `drugs 5.876 | aliases 63.646 | products 54.883 |`
`drug_interactions 260.100 | mechanisms 8.465 | food 857 | disease 8.359 |`
`duplication 741 | ara 272 | pk 4.277 | fda_labels 4.931 | dosage_rules 28`.
`SELECT count(*) FROM drug_interactions WHERE both_in_vn` để biết độ phủ VN.
Script seed: `scripts/seed_mvp.py --mvp-dir data/mvp [--no-embed]` (thay `seed_mock_drugs.py`
cũ; giữ flag `--no-embed` để chạy offline — exact-match vẫn chạy).

---

## 5. Vector DB (RAG) — làm tối giản trước

**P0 không cần RAG phức tạp.** Dùng pgvector cho 2 việc (embed ở `interaction_mechanisms`, 8.465 dòng):

1. **Fallback khi lookup chính xác rỗng:** tìm mechanism có `description` gần nhất bằng cosine similarity (ngưỡng `>= 0.75` mới trả, kèm `match_type: vector_fallback` + cảnh báo độ tin cậy thấp).
2. **Chuẩn bị cho agent sau:** embedding sẵn để node `explain` truy xuất ngữ cảnh.

Luồng `interaction_lookup`:

```
1. Chuẩn hóa tên -> drug_id qua aliases (ok) hoặc product_ingredients (khi chọn thuốc DAV cụ thể theo đường dùng)
2. Sinh mọi cặp C(n,2), sort drug_a < drug_b, SELECT chính xác trong drug_interactions
   -> JOIN interaction_mechanisms qua mechanism_id lấy description/management (match_type=exact)
3. Lớp 2: xét dosage_form_rules (raise/form_specific/no_interaction_for_form)
   + ara_interactions (chỉ khi victim đường uống) -> có thể nâng lên contraindicated
4. Nếu cặp vẫn trống: vector search trên interaction_mechanisms.embedding top3
   -> chỉ giữ similarity >= 0.75, gắn flag vector_fallback
5. Vẫn rỗng / drug DAV:* / status unknown -> no_record (KHÔNG nói "an toàn")
```

Embedding input = `f"{mechanism_type}: {description} {management}"` (cột `interaction_mechanisms`). Model: `text-embedding-3-small` (1536 dim).

---

## 6. Ba tool — đặc tả (viết dạng hàm thuần trước)

### Tool 1 — `drug_name_normalizer`

- **File:** `src/tools/normalizer.py`
- **Input:** `str` (VD: `"Panadol extra"`, `"asca"`, `"para"`)
- **Output:**

```json
{
  "input": "asca",
  "canonical_name": "aspirin",
  "ingredient": "acetylsalicylic acid",
  "drug_id": "uuid",
  "status": "ok | suggest | unknown",
  "suggestions": [{"canonical_name": "aspirin", "score": 0.92}],
  "source": "aliases:DAV"
}
```

- **Logic (không LLM):** `khoa(tên)` (lowercase-bỏ dấu-chỉ giữ chữ-số, theo `data/build_ddi.py`) → tra `aliases` exact (`status=ok` dùng luôn, `suggest` hỏi xác nhận) → thử so gần đúng trên cột alias → dưới ngưỡng → `unknown`. Nếu user chọn thuốc DAV cụ thể thì lấy `drug_id` từ `product_ingredients` (đã chọn theo đường dùng + `route_match`).
- **Rule:** `suggest` không auto-accept. API trả về để FE hỏi user xác nhận.

### Tool 2 — `interaction_lookup`

- **File:** `src/tools/lookup.py`
- **Input:** `list[drug_id]` (2–50 thuốc)
- **Output:** `list[InteractionRecord]` — mỗi record gồm `pair, severity, mechanism, clinical_effect, management, source_id, source_name, match_type (exact|vector_fallback|no_record)`.
- **Logic:** sinh mọi cặp `C(n,2)` (n≤50 → ≤1225 cặp, OK) → batch SELECT → vector fallback nếu cần → cặp không có bản ghi → `no_record`.

### Tool 3 — `severity_ranker`

- **File:** `src/tools/ranker.py`
- **Input:** `list[InteractionRecord]` + danh sách ingredients (để bắt trùng hoạt chất)
- **Output:** `list[Finding]` đã sort `contraindicated → major → moderate → minor → duplicate_active → unknown`, kèm `max_severity` tổng.
- **Logic thuần rule:** trùng `ingredient` (VD: 2 thuốc cùng `paracetamol`) → thêm finding `duplicate_active`. Không gọi LLM, không suy luận thêm.

---

## 7. API contract (P0 — 6 endpoint)

Base: `/api/v1`. Lỗi theo RFC 9457 (`application/problem+json`).

| # | Method & Path | Mô tả | Auth |
|---|---------------|-------|------|
| 1 | `GET /health` | Sống/chết + version (giữ ở root `/health` như template) | không |
| 2 | `POST /api/v1/normalize` | Chuẩn hóa 1..50 tên thuốc | không (rate limit) |
| 3 | `GET /api/v1/drugs/search?q=` | Autocomplete / tìm thuốc (phục vụ FE nhập) | không |
| 4 | `POST /api/v1/interactions/check` | **Luồng chính:** nhận list tên thuốc → normalize → lookup → rank → trả findings + citations + disclaimer | không (rate limit 20/phút) |
| 5 | `GET /api/v1/sources` | Liệt kê nguồn + độ phủ + giới hạn dữ liệu (nêu rõ MOCK) | không |
| 6 | `GET /api/v1/interactions/pair?a=&b=` | Tra 1 cặp (debug, demo) | không |

Auth users/HITL (`/auth/*`, `/cases/*`) **để sang P1**, không làm trong P0 để khỏi tắc.

### 7.1 Ví dụ request/response (luồng chính)

Request:

```http
POST /api/v1/interactions/check
Content-Type: application/json

{
  "drugs": ["warfarin", "asca", "Panadol extra"],
  "include_food": true,
  "foods": ["rau xanh", "bưởi chùm"]
}
```

Response `200`:

```json
{
  "normalized": [
    {"input": "warfarin", "canonical_name": "warfarin", "status": "ok"},
    {"input": "asca", "canonical_name": "aspirin", "status": "suggest",
     "suggestions": [{"canonical_name": "aspirin", "score": 0.92}],
     "note": "Cần xác nhận, không tự áp dụng"}
  ],
  "unknown": [{"input": "Panadol extra", "status": "unknown",
               "note": "Chưa có bản ghi trong CSDL"}],
  "max_severity": "major",
  "findings": [
    {
      "pair": ["warfarin", "aspirin"],
      "severity": "major",
      "symbol": "!",
      "summary": "Tăng nguy cơ chảy máu khi dùng chung.",
      "mechanism": "Aspirin ức chế kết tập tiểu cầu, cộng hưởng với tác dụng chống đông của warfarin.",
      "management": "Liên hệ bác sĩ/dược sĩ để được đánh giá.",
      "citations": [{"source_id": "ddinter", "source_name": "DDInter 2.0", "source_url": "https://ddinter2.scbdd.com/server/interact/288140/"}],
      "match_type": "exact"
    }
  ],
  "no_record_pairs": [["warfarin", "paracetamol"]],
  "disclaimer": "Kết quả là cảnh báo tham khảo, không phải chẩn đoán hay chỉ định điều trị. Không tự ngưng/đổi/giảm liều. Liên hệ bác sĩ/dược sĩ. Mức nghiêm trọng → liên hệ y tế ngay.",
  "data_coverage": "CSDL thật: 5.876 hoạt chất / 260.100 cặp DDInter + 28 rule dạng bào chế + 272 rule Patel2020. Hoạt chất DAV:* ngoài danh sách sẽ trả 'chưa có bản ghi'."
}
```

### 7.2 Guardrail ở tầng API (rule-based, `src/core/guardrails.py`)

- Chặn response chứa `ngưng|dừng|bỏ thuốc|đổi sang|tăng liều|giảm liều|nên dùng|kê cho` → thay bằng câu handoff.
- Chặn từ `an toàn|không sao|không nguy hiểm` khi `match_type=no_record` → thay bằng `chưa có bản ghi trong CSDL`.
- Mọi finding thiếu `source_id` → 500 + log (không trả ra ngoài).
- Validate Pydantic: 1–50 thuốc, mỗi tên ≤ 200 ký tự.

---

## 8. Lộ trình triển khai (7 bước, làm theo thứ tự)

- [ ] **B0 — Dựng nền (0.5 ngày)**
  - Un-comment DB deps trong `requirements.txt`, `pip install -r requirements.txt`.
  - Mở rộng `src/config.py`: `database_url, jwt_secret, embedding_model, similarity_threshold=0.75`.
  - `docker-compose.yml`: thêm service `db` (image `pgvector/pgvector:pg16`), volume `pgdata`. BE `depends_on: db`.
  - Chạy tay: `docker compose up db`, `uvicorn src.main:app --reload`. Tiêu chí: `/health` + `/docs` mở được.

- [ ] **B1 — DB + migration (1 ngày)**
  - Tạo `src/db/base.py`, `session.py`, `models/*.py` (6 bảng mục 4).
  - `alembic init alembic`, viết migration đầu tiên (DDL mục 4.2).
  - `alembic upgrade head` trên Postgres local/Docker. Tiêu chí: `\d interactions` thấy cột `embedding vector(1536)`.

- [ ] **B2 — Seed thật (0.5 ngày)**
  - Không tạo `data/mock/*.csv` tay nữa — dùng sẵn `data/mvp/*.csv` (do `data/build_ddi.py` sinh ra).
  - Viết `scripts/seed_mvp.py` (+ flag `--no-embed`): COPY theo thứ tự §4.3.
  - Tiêu chí: `SELECT count(*) FROM drugs` = 5.876, `FROM drug_interactions` = 260.100, `FROM interaction_mechanisms` = 8.465.

- [ ] **B3 — Tools-core thuần (1–1.5 ngày)** ⭐ trọng tâm
  - `src/tools/normalizer.py` (rapidfuzz) + test `tests/test_tools/test_normalizer.py`.
  - `src/tools/lookup.py` (exact + vector fallback) + test với DB thật (testcontainer hoặc Postgres Docker).
  - `src/tools/ranker.py` (sort + trùng hoạt chất) + test sort + duplicate.
  - Tiêu chí: pytest 3 file xanh, ranker deterministic (cùng input → cùng output).

- [ ] **B4 — Services + API (1.5 ngày)** ⭐ trọng tâm
  - `src/services/*` bọc tools-core, `src/schemas/*.py` (Pydantic I/O đúng mục 7.1).
  - Router `drugs.py, interactions.py, sources.py` + `GET /health`.
  - `src/core/guardrails.py` + middleware gắn disclaimer.
  - Tiêu chí: mở `/docs`, gọi `POST /interactions/check` với cặp warfarin+aspirin ra `major` + citation.

- [ ] **B5 — RAG tối giản (0.5–1 ngày)**
  - Script `scripts/embed_mechanisms.py` embed `interaction_mechanisms.description` (8.465 dòng) → cột `embedding`.
  - Ngưỡng cosine `0.75` trong `lookup.py`, gắn `match_type=vector_fallback`.
  - Test: cặp chưa seed nhưng gần nghĩa vẫn trả fallback kèm flag; cặp xa nghĩa trả `no_record`.
  - Cho phép chạy offline: nếu thiếu `OPENAI_API_KEY` thì bỏ qua embed, exact-match vẫn chạy.

- [ ] **B6 — Test + Docker + docs (0.5–1 ngày)**
  - Bộ câu hỏi bẫy guardrail (5 câu: ngưng/thay/giảm liều/kê thêm/có tử vong không) → assert đều bị chặn/handoff.
  - `pytest` toàn bộ xanh, `ruff check`.
  - `Dockerfile` build được, `docker compose up --build` chạy BE+DB.
  - Cập nhật `eval/results/report.md` (số thuốc, số cặp, recall trên tập seed).

**Tổng ước lượng:** ~5–7 ngày / 1 người.

### Thứ tự file nên tạo

```
1. requirements.txt (sửa) → config.py (sửa) → docker-compose.yml (sửa)
2. src/db/ + alembic/
3. data/mock/*.csv + scripts/seed_mock_drugs.py
4. src/tools/*.py + tests/test_tools/
5. src/schemas/ + src/services/ + src/api/routers/ + src/core/guardrails.py
6. scripts/embed_interactions.py
7. tests/test_api/ + Dockerfile
```

---

## 9. Cấu hình môi trường (`.env`)

```bash
# DB — local Docker
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/rathuoc
# DB — khi chạy trong compose (service tên db)
# DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/rathuoc

OPENAI_API_KEY=sk-...            # chỉ cần cho embed; thiếu vẫn chạy exact-match
EMBEDDING_MODEL=text-embedding-3-small
SIMILARITY_THRESHOLD=0.75
APP_ENV=development
CORS_ORIGINS=http://localhost:3000
```

`docker-compose.yml` thêm:

```yaml
services:
  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: rathuoc
    ports: ["5432:5432"]
    volumes: ["pgdata:/var/lib/postgresql/data"]
volumes:
  pgdata:
```

---

## 10. Definition of Done (P0 Backend)

1. `docker compose up` → BE + DB chạy, `/health` trả `ok`.
2. `POST /api/v1/interactions/check` với `[warfarin, aspirin]` → `max_severity=major` + citation `ddinter` (kèm `source_url` DDInter) + `management` từ `interaction_mechanisms`.
3. `POST` với hoạt chất `DAV:*` (chỉ có ở VN, chưa có DDI) → `unknown` + câu `chưa có bản ghi`, **không** có chữ `an toàn`.
4. 5 câu hỏi bẫy guardrail đều bị chặn/handoff.
5. `pytest` xanh, `ruff` sạch, `/docs` hiển thị đủ 6 endpoint.
6. `GET /api/v1/sources` liệt kê đủ 6 nguồn từ `sources.csv`, nêu rõ `ddinter/patel2020 chỉ phi thương mại`.

---

## 11. Để sau (không làm trong P0)

| Việc | Khi nào |
|------|---------|
| LangGraph agent (`normalize → lookup → rank → explain → guardrail`), node `clarify`/`explain` dùng LLM | P-Agent (sau khi API ổn định). Lúc đó bọc `src/tools/*.py` bằng `@tool` — không viết lại logic |
| Chatbot endpoint (`POST /chat`, SSE stream) | P-Agent |
| Auth đầy đủ, roles, HITL dược sĩ (`/auth/*`, `/cases/*`, `reviews`, `audit_log`) | P1 |
| OCR đơn thuốc, thuốc–bệnh nền, memory hồ sơ | P2 (nâng cao) |
| Tách `src/` → `interface/be/` theo ARCHITECTURE.md §3 | Khi BE > 2000 dòng hoặc bắt đầu làm FE |

## 12. Workflow backend (chi tiết)

> Quy ước: `Client → API → Service → Tools-core → Repository → DB`. Tools-core không gọi HTTP/DB trực tiếp.

### W0 — Request lifecycle (mọi endpoint)

```mermaid
sequenceDiagram
    autonumber
    participant C as Client (curl/FE)
    participant M as Middleware (RequestID, CORS, RateLimit, Audit)
    participant R as Router (Pydantic validate)
    participant S as Service
    participant T as Tools-core
    participant Repo as Repository
    participant DB as Postgres+pgvector

    C->>M: HTTP request + RequestID
    M->>M: rate limit (SlowAPI 20/phút cho /check)
    M->>R: forward
    R->>R: validate (1-50 thuốc, mỗi tên ≤200 ký tự)
    R->>S: gọi service tương ứng
    S->>T: gọi hàm thuần (normalizer/lookup/ranker)
    T->>Repo: truy vấn qua repository
    Repo->>DB: SQL / vector search
    DB-->>Repo: rows + similarity
    Repo-->>T: records
    T-->>S: kết quả thuần
    S->>S: gắn disclaimer + data_coverage
    S-->>R: response schema
    R->>R: guardrail re-check (mục 7.2)
    R-->>C: 200 JSON (hoặc problem+json khi lỗi)
```

### W1 — Luồng chính `POST /api/v1/interactions/check`

```mermaid
flowchart TB
    A[Nhận drugs[] + foods[]] --> B{Pydantic hợp lệ?}
    B -- không --> E400[400 problem+json]
    B -- có --> C[normalize từng tên]
    C --> D{có suggest/unknown?}
    D -- có --> D1[Gắn note cần xác nhận / chưa có bản ghi, vẫn tiếp tục với nhóm ok]
    D -- toàn bộ ok --> E[]
    D1 --> E[Sinh mọi cặp C-n-2]
    E --> F[lookup exact trong interactions]
    F --> G{Cặp nào trống?}
    G -- có & có embedding --> H[vector fallback, ngưỡng 0.75]
    G -- không --> I[]
    H --> I[rank + bắt trùng hoạt chất]
    I --> J[guardrail check]
    J -- FAIL thiếu citation / chứa câu khuyên thuốc --> K[500 + log, không trả ra ngoài]
    J -- PASS --> L[200 findings + citations + disclaimer + coverage]
```

Pseudocode service (`src/services/check_service.py`):

```python
async def run_check(payload: CheckRequest) -> CheckResponse:
    normalized = [normalize_name(n) for n in payload.drugs]   # W2
    ok_ids = [x.drug_id for x in normalized if x.status == "ok"]
    records = lookup_interactions(ok_ids, foods=payload.foods) # W3
    findings, max_sev = rank_findings(records, normalized)     # W4
    guardrail_assert(findings)                                  # W5
    return CheckResponse(..., disclaimer=DISCLAIMER, coverage=COVERAGE)
```

> P0 **stateless**: không INSERT `checks/findings` vào DB. Sang P1 (HITL) mới thêm bước `INSERT checks status=done` sau guardrail PASS.

### W2 — Normalizer (per tên thuốc)

```mermaid
flowchart LR
    IN[input thô] --> P1[lowercase + strip + chuẩn hóa unicode]
    P1 --> Q1{khớp aliases exact?}
    Q1 -- có --> OK[status=ok]
    Q1 -- không --> Q2{khớp canonical_name exact?}
    Q2 -- có --> OK
    Q2 -- không --> Q3[rapidfuzz WRatio vs aliases+canonical]
    Q3 --> Q4{best score >= 85?}
    Q4 -- có --> SG[status=suggest + top3]
    Q4 -- không --> UN[status=unknown]
```

- `suggest` không auto-accept: API trả `suggestions[]`, FE hỏi user. Nếu user xác nhận → gọi lại `/check` với tên canonical.
- `unknown` vẫn trả `note: "Chưa có bản ghi trong CSDL"` và tiếp tục check các thuốc còn lại.

### W3 — Lookup (per cặp thuốc)

```mermaid
flowchart TB
    P[pair đã sort min-max] --> E1{SELECT exact?}
    E1 -- có --> EX[match_type=exact]
    E1 -- không --> V1{có OPENAI_API_KEY / embedding?}
    V1 -- không --> NR[match_type=no_record]
    V1 -- có --> V2[pgvector cosine top3]
    V2 --> V3{best similarity >= 0.75?}
    V3 -- có --> VF[match_type=vector_fallback + flag độ tin cậy thấp]
    V3 -- không --> NR
```

SQL fallback minh họa:

```sql
SELECT *, 1 - (embedding <=> :q) AS sim
FROM interactions
ORDER BY embedding <=> :q LIMIT 3;
-- service giữ lại sim >= 0.75
```

### W4 — Ranker (deterministic, không LLM)

1. Gom `records` loại `exact/vector_fallback` + phát hiện trùng `ingredient` → thêm finding `duplicate_active` (ký hiệu `=`, màu tím).
2. Sort: `contraindicated(4) > major(3) > moderate(2) > minor(1) > duplicate_active > unknown(0)`.
3. `max_severity` = severity cao nhất (để FE sort queue, P1 dùng cho HITL).
4. Cặp `no_record` không sort chung — trả riêng ở `no_record_pairs` + câu `chưa có bản ghi`.

### W5 — Guardrail pipeline (2 chốt)

```mermaid
flowchart LR
    F[findings từ ranker] --> G1[Chốt 1: guardrail_assert trong service]
    G1 -- thiếu source_id --> B1[Bỏ finding + log grounding + 500]
    G1 -- chứa mẫu khuyên thuốc --> B2[Thay bằng câu handoff bác sĩ/dược sĩ]
    G1 -- chứa an-toàn khi no_record --> B3[Thay bằng chưa có bản ghi]
    G1 -- pass --> G2[Chốt 2: response middleware re-check]
    G2 -- fail --> B4[Trả generic + alert log]
    G2 -- pass --> OUT[200 + disclaimer không tắt được]
```

Regex chặn (tiếng Việt, case-insensitive): `ngưng|dừng|bỏ thuốc|đổi sang|tăng liều|giảm liều|nên dùng|kê cho|an toàn|không sao|không nguy hiểm`.

### W6 — `GET /drugs/search?q=` (autocomplete)

```
q (≥2 ký tự) → ILIKE %q% trên aliases + canonical (LIMIT 10)
→ sắp xếp: exact-prefix trước, fuzzy sau → trả [{canonical_name, ingredient, matched_alias}]
```

Không cần embedding ở đây — SQL ILIKE đủ nhanh với <10k bản ghi MOCK.

### W7 — Seed & embed (offline-first)

```mermaid
flowchart TB
    CSV[data/mock/*.csv] --> S[seed_mock_drugs.py --no-embed]
    S --> DB[(Postgres)]
    DB --> E2{có OPENAI_API_KEY?}
    E2 -- có --> EM[embed_interactions.py → UPDATE embedding]
    E2 -- không --> SKIP[bỏ qua, exact-match vẫn chạy]
    EM --> IV[CREATE INDEX ivfflat nếu >10k rows]
```

Thứ tự chạy: `alembic upgrade head → seed --no-embed → (optional) embed → smoke test curl`.

### W8 — Lỗi & mã trạng thái

| Tình huống | HTTP | Body | Retry |
|------------|------|------|-------|
| Validate sai (0 thuốc, >50, tên >200 ký tự) | 400 | `problem+json {title, detail}` | không, sửa input |
| Rate limit vượt 20/phút | 429 | `Retry-After` header | client backoff |
| DB down / embedding timeout | 503 | `title: Service Unavailable` | retry 1 lần, sau đó fail-open trả exact-match |
| Finding thiếu citation (lỗi nội bộ) | 500 + log | generic, không lộ chi tiết | không retry, fix data |
| Cặp không bản ghi | 200 (không phải lỗi) | `no_record_pairs[]` + `chưa có bản ghi` | — |

### Traceability: workflow → file code

| Workflow | File chính | Test tương ứng |
|----------|-----------|----------------|
| W0 lifecycle | `src/main.py`, `src/api/middleware/*` | `tests/test_api/test_health.py` |
| W1 check | `src/services/check_service.py`, `src/api/routers/interactions.py` | `tests/test_api/test_check.py` |
| W2 normalize | `src/tools/normalizer.py` | `tests/test_tools/test_normalizer.py` |
| W3 lookup | `src/tools/lookup.py`, `src/repositories/interaction_repo.py` | `tests/test_tools/test_lookup.py` |
| W4 rank | `src/tools/ranker.py` | `tests/test_tools/test_ranker.py` |
| W5 guardrail | `src/core/guardrails.py` | `tests/test_guardrails.py` |
| W6 search | `src/api/routers/drugs.py` | `tests/test_api/test_drugs.py` |
| W7 seed/embed | `scripts/seed_mvp.py`, `scripts/embed_mechanisms.py` | smoke `SELECT count(*)` = số dòng §4.3 |

## 13. Luồng BE chính — bám FE đã làm (`app/page.tsx`)

> FE hiện tại: 5 view trong 1 page (`Tổng quan / Đơn thuốc / Kiểm tra an toàn / Lịch sử / Trao đổi dược sĩ`)
> + `MedicationAssistantWidget` + modal thêm thuốc + modal chi tiết phát hiện.
> Hiện tất cả đang mock (`demoPrescriptions`, `setTimeout 1700ms`, `interactions` cứng).
> Mục này định nghĩa BE tối thiểu để thay từng mock bằng API thật, **không đổi UI**.

### 13.1 Mapping FE → BE (làm theo bảng này là đủ chạy)

| FE view / hàm hiện tại | Dữ liệu mock cần thay | Endpoint BE chính | Ghi chú |
|---|---|---|---|
| `Tổng quan` (4 thẻ đếm) | `prescriptions.length`, filter status | `GET /api/v1/prescriptions/summary` | Trả `{total, checked, with_interaction, unverified_meds}` — đếm ở SQL, FE khỏi filter client |
| `Library` tìm kiếm + filter | `visiblePrescriptions` (filter client theo query + status) | `GET /api/v1/prescriptions?q=&status=` | `status ∈ Tất cả/Chưa kiểm tra/Có tương tác/Cần xem lại`. BE phân trang `limit/offset` |
| `openPrescription(id)` | `find(id)` trong mảng | `GET /api/v1/prescriptions/{id}` | Trả 1 đơn + `medications[]` (kèm `verified`, `ingredient`) |
| Modal `addMedication()` | push `{ingredient: 'Chưa xác minh', verified: false}` | `POST /api/v1/prescriptions/{id}/medications` | BE chạy normalize ngay (W2): trả `ok/suggest/unknown`; `verified = (status==ok)` |
| `runCheck(id)` + `Analysis` 8 bước | `setTimeout 1700ms` → `status: 'Có tương tác'` | `POST /api/v1/prescriptions/{id}/checks` → `GET /api/v1/checks/{check_id}` | Luồng chính §13.2. 8 bước FE ánh xạ 1-1 pipeline BE §13.3 |
| `Results` (4 thẻ + list phát hiện) | `interactions` cứng 3 dòng | `GET /api/v1/checks/{check_id}` | Trả `summary{meds_count, findings_count, max_severity, sources_count}` + `findings[]` sort sẵn (W4) |
| `InteractionModal` chi tiết | `text`, `evidence`, `sources` cứng | cùng response trên, object `finding` | `finding = {pair, severity_vi, kind, what, todo_handoff, evidence{label, sources, updated}}` |
| `HistoryView` | `filter(p.checks>0).slice(0,12)` | `GET /api/v1/prescriptions/{id}/checks` hoặc `GET /api/v1/checks?rx={id}` | Mỗi check là **snapshot độc lập** (copy meds tại thời điểm chạy — FE đã ghi "bản chụp độc lập") |
| `ReviewView` gửi review | `reviewSent` boolean local | `POST /api/v1/reviews` `{prescription_id, check_id, message}` | Trả `{review_id, status: 'Đang chờ dược sĩ xem xét'}` |
| `MedicationAssistantWidget.sendMessage` | `setTimeout 900ms` + câu handoff cứng | `POST /api/v1/assistant/chat` `{prescription_id, check_id?, message}` | P0: rule-based trên findings đã có (không LLM). P-Agent mới dùng LLM |

### 13.2 Luồng chính F2 — `runCheck` (thay `setTimeout`)

```mermaid
sequenceDiagram
    autonumber
    participant FE as FE SafetyView
    participant BE as FastAPI
    participant S as check_service
    participant DB as Postgres

    FE->>BE: POST /prescriptions/RX-0001/checks
    BE->>DB: SELECT medications WHERE rx_id (snapshot)
    BE->>S: run_check(snapshot) — 8 bước §13.3
    S-->>BE: {check_id, max_severity, findings_count}
    BE-->>FE: 201 {check_id, status: running}
    FE->>FE: hiện Analysis (8 bước, poll từng bước)
    FE->>BE: GET /checks/{id} (poll 500ms hoặc SSE sau này)
    BE-->>FE: 200 {status: done, summary, findings[]}
    FE->>FE: render Results + cập nhật status đơn → Có tương tác
```

- P0 dùng **polling** `GET /checks/{id}` (FE hiện không có SSE thật). Giữ nguyên `Analysis` UI, chỉ thay `setTimeout` bằng poll.
- `POST` trả ngay `201 + check_id` để UI chuyển sang màn Analysis trong <300ms; pipeline nặng chạy background (`BackgroundTasks` hoặc đơn giản là chạy sync nếu <3s với data MOCK).
- Snapshot: `checks` lưu `meds_snapshot JSONB` (copy nguyên `medications[]` lúc bấm kiểm tra) → History mở lại vẫn đúng dù sau đó thêm/xóa thuốc.

### 13.3 8 bước `Analysis` FE ↔ pipeline BE (1-1, không được rào)

FE `Analysis` render 8 dòng (`steps` trong `page.tsx:96`):

| # | Bước FE hiển thị | Việc BE làm | Tool / bảng |
|---|---|---|---|
| 1 | Chuẩn hóa tên thuốc | W2 normalizer từng med trong snapshot | `tools/normalizer.py` → `aliases/drugs` |
| 2 | Xác định hoạt chất | Map `canonical_name → ingredient` | `drugs.ingredient` |
| 3 | Kiểm tra hoạt chất trùng | Gom theo `ingredient`, sinh finding `duplicate_active` | `tools/ranker.py` |
| 4 | Kiểm tra tương tác thuốc–thuốc | Sinh `C(n,2)` cặp, lookup exact → vector fallback | `tools/lookup.py` → `interactions` |
| 5 | Kiểm tra thuốc–thực phẩm | Lookup `food_interactions` (mặc định check `rau xanh/vitamin K, bưởi chùm` nếu đơn có warfarin/statin; mở rộng khi FE có ô nhập thực phẩm) | `food_interactions` |
| 6 | Đánh giá mức độ | Sort + `max_severity` | `tools/ranker.py` (deterministic) |
| 7 | Truy xuất bằng chứng | Gắn `citations[]` + đếm `sources_count` | `sources` (FE hiện ghi `FDA Drug Labels · n nguồn · 2026` → BE trả thật từ bảng) |
| 8 | Tạo giải thích | P0: template cứng theo severity (không LLM). P-Agent: LLM `explain` | `services/explain_template.py` → sau này `agents/nodes/explain.py` |

Tiến trình poll trả về để FE tick từng dòng:

```json
// GET /api/v1/checks/{id} khi đang chạy
{"check_id": "CHECK-00031", "status": "running", "steps_done": ["normalize","ingredient","duplicate"],
 "steps_total": 8, "current_step": "drug_interaction"}
// khi xong
{"check_id": "CHECK-00031", "status": "done",
 "summary": {"meds_count": 3, "findings_count": 3, "max_severity": "Trung bình", "sources_count": 4},
 "findings": [...], "disclaimer": "...", "snapshot_at": "2026-09-30T10:00:00Z"}
```

### 13.4 Contract tối thiểu khớp type FE (Pydantic ↔ TypeScript)

```python
# POST /prescriptions/{rx_id}/medications
class AddMedicationRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)  # FE: newMedication
class MedicationOut(BaseModel):
    id: int; name: str; ingredient: str              # FE: 'Chưa xác minh' khi unknown
    dose: str; frequency: str
    type: Literal["Kê đơn","OTC","Bổ sung"]
    verified: bool                                    # = (normalize.status == ok)
    norm_status: Literal["ok","suggest","unknown"]
    suggestions: list[str] = []
```

```python
# GET /checks/{id} — khớp Results + InteractionModal
class FindingOut(BaseModel):
    id: int; a: str; b: str                           # FE: item.a / item.b
    severity: Literal["Nghiêm trọng","Trung bình","Nhẹ"]
    kind: str                                         # 'Thuốc - thuốc' / 'Thuốc - bổ sung'
    what: str                                         # FE: item.text ('Phát hiện gì?')
    todo_handoff: str = "Hãy trao đổi với bác sĩ hoặc dược sĩ trước khi bắt đầu, ngừng hoặc thay đổi bất kỳ thuốc nào."
    evidence_label: str = "FDA Drug Labels"           # thay bằng sources.name thật khi có
    evidence_level: str                               # Mạnh/Vừa/Hạn chế (từ severity)
    sources_count: int; citations: list[Citation]
```

FE `Severity` hiện chỉ có 3 mức (`Nghiêm trọng/Trung bình/Nhẹ`) — BE map:
`contraindicated+major → Nghiêm trọng`, `moderate → Trung bình`, `minor → Nhẹ`,
`duplicate_active → Trung bình + kind='Trùng hoạt chất'`, `unknown → không tạo finding` (vào `unverified` + `NotFoundNotice`).

### 13.5 State machine (khớp `Status` FE)

```
Prescription.status: Chưa kiểm tra → (POST checks → done, findings rỗng) → Đã kiểm tra
                                  → (done, có findings) → Có tương tác
                                  → (dược sĩ reject / có med unverified) → Cần xem lại
Check.status: running → done | failed
Review.status: Đang chờ dược sĩ xem xét → Đã xem (P1 HITL)
```

- `runCheck` xong: `UPDATE prescriptions SET status, highest=max_severity_vi, last_checked=now(), checks=checks+1`.
- Thêm thuốc mới (`verified=false`) → kéo đơn về `Cần xem lại` để FE nhắc kiểm tra lại (khớp badge `Cần xác minh` ở Tổng quan).

### 13.6 Thứ tự un-mock (làm F2 trước, widget sau)

1. `GET prescriptions + summary` (Tổng quan + Library có data thật).
2. `POST checks + GET checks` (thay `setTimeout 1700ms` — giá trị lớn nhất).
3. `POST prescriptions/{id}/medications` (thay push local).
4. `GET checks history + POST reviews` (Lịch sử + Trao đổi dược sĩ).
5. `POST assistant/chat` rule-based (widget: chỉ đọc findings của check hiện tại + 3 gợi ý cứng FE đã có; chặn mọi câu khuyên thuốc).

---

## Phụ lục — lệnh nhanh

```bash
# 1. Cài & chạy DB
pip install -r requirements.txt
docker compose up db -d

# 2. Migrate + seed
alembic upgrade head
python scripts/seed_mock_drugs.py --no-embed   # chạy offline trước

# 3. Chạy API
uvicorn src.main:app --reload --port 8000
# Mở http://localhost:8000/docs

# 4. Test nhanh
curl -X POST http://localhost:8000/api/v1/interactions/check ^
  -H "Content-Type: application/json" ^
  -d "{\"drugs\": [\"warfarin\", \"aspirin\"]}"

# 5. Test + lint
pytest -q
ruff check src tests
```

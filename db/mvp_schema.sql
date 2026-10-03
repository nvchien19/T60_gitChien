-- Schema cho dữ liệu MVP (data/mvp/*.csv). Thứ tự cột khớp thứ tự cột trong CSV.
-- Nạp bằng: python db/load_mvp.py

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;   -- so khớp gần đúng tên thuốc (bước normalize)
CREATE EXTENSION IF NOT EXISTS unaccent;  -- mvp.khoa(): bỏ dấu tiếng Việt như hàm khoa() của pipeline

DROP SCHEMA IF EXISTS mvp CASCADE;
CREATE SCHEMA mvp;
SET search_path = mvp, public;

CREATE TABLE sources (
    source_id    text PRIMARY KEY,
    name         text NOT NULL,
    citation     text NOT NULL,
    url          text,
    license      text NOT NULL,
    last_updated text NOT NULL
);

-- Thứ tự mức độ: dùng để lấy "mức cao nhất" khi nhiều nguồn/cơ chế lệch nhau
CREATE TABLE severity_levels (
    severity text PRIMARY KEY,
    rank     integer NOT NULL UNIQUE,
    label_vi text NOT NULL
);
INSERT INTO severity_levels VALUES
    ('contraindicated', 4, 'Chống chỉ định'),
    ('major',           3, 'Nghiêm trọng'),
    ('moderate',        2, 'Trung bình'),
    ('minor',           1, 'Nhẹ'),
    ('none',            0, 'Không có tương tác đáng kể');

CREATE TABLE drugs (
    drug_id          text PRIMARY KEY,           -- DDInterNNN, DAV:<khóa> hoặc EXT:<tên> (chỉ có trong Patel 2020)
    name             text NOT NULL,
    name_vi          text,
    base_name        text NOT NULL,
    route_variant    text,
    drugbank_id      text,
    atc_code         text,
    drug_type        text,
    source_id        text NOT NULL REFERENCES sources,
    n_products       integer NOT NULL,
    n_products_valid integer NOT NULL,
    in_vn            boolean NOT NULL,
    n_interactions   integer NOT NULL
);

-- Khóa duy nhất là (alias, drug_id, source_id): thuốc phối hợp trỏ tới nhiều drug_id.
CREATE TABLE aliases (
    alias      text NOT NULL,                   -- đã chuẩn hóa theo khoa()
    drug_id    text NOT NULL REFERENCES drugs,
    alias_type text NOT NULL,
    source_id  text NOT NULL REFERENCES sources,
    status     text NOT NULL CHECK (status IN ('ok', 'suggest')),
    drug_name  text NOT NULL,
    PRIMARY KEY (alias, drug_id, source_id)
);

CREATE TABLE products (
    product_id          integer PRIMARY KEY,
    registration_no     text,
    name                text NOT NULL,
    active_ingredients  text,
    strength            text,
    dosage_form         text,
    packaging           text,
    route               text NOT NULL,
    route_source        text NOT NULL,           -- dosage_form | packaging | name | category | none
    form_group          text NOT NULL,
    enteric_coated      boolean NOT NULL,
    modified_release    boolean NOT NULL,
    category            text,
    manufacturer        text,
    manufacturer_country text NOT NULL,
    registrant          text,
    status              text NOT NULL,           -- valid | expired | withdrawn
    expiry_date         date,
    source_id           text NOT NULL REFERENCES sources
);

CREATE TABLE product_ingredients (
    product_id    integer NOT NULL REFERENCES products,
    position      integer NOT NULL,
    ingredient    text,
    strength      text,
    drug_id       text REFERENCES drugs,
    base_drug_id  text REFERENCES drugs,
    match_method  text NOT NULL,
    match_score   integer NOT NULL,
    status        text NOT NULL CHECK (status IN ('ok', 'suggest', 'unknown', 'excluded')),
    route_match   text,
    needs_review  boolean NOT NULL
);

CREATE TABLE interaction_mechanisms (
    mechanism_id   integer PRIMARY KEY,
    severity       text NOT NULL REFERENCES severity_levels,
    mechanism_type text NOT NULL,
    description    text NOT NULL,
    management     text,
    "references"   text NOT NULL,
    n_pairs        integer NOT NULL,
    source_id      text NOT NULL REFERENCES sources
    -- embedding vector(N): thêm khi chọn model embedding
);

CREATE TABLE drug_interactions (
    interaction_id integer PRIMARY KEY,
    drug_a         text NOT NULL REFERENCES drugs,
    drug_b         text NOT NULL REFERENCES drugs,
    severity       text NOT NULL REFERENCES severity_levels,
    mechanism_id   integer NOT NULL REFERENCES interaction_mechanisms,
    mechanism_type text NOT NULL,
    source_id      text NOT NULL REFERENCES sources,
    source_url     text NOT NULL,
    both_in_vn     boolean NOT NULL,
    CHECK (drug_a <> drug_b),
    UNIQUE (drug_a, drug_b, mechanism_id)
);

CREATE TABLE food_interactions (
    drug_id        text NOT NULL REFERENCES drugs,
    drug_name      text NOT NULL,
    food           text NOT NULL,
    food_vi        text NOT NULL,
    severity       text NOT NULL REFERENCES severity_levels,
    mechanism_type text,
    description    text NOT NULL,
    management     text NOT NULL,
    "references"   text NOT NULL,
    source_id      text NOT NULL REFERENCES sources
);

CREATE TABLE disease_interactions (
    drug_id      text NOT NULL REFERENCES drugs,
    drug_name    text NOT NULL,
    disease      text NOT NULL,
    mesh_id      text,
    severity     text NOT NULL REFERENCES severity_levels,
    description  text NOT NULL,
    "references" text,
    source_id    text NOT NULL REFERENCES sources
);

CREATE TABLE duplication_classes (
    class_name     text NOT NULL,
    drug_id        text NOT NULL REFERENCES drugs,
    drug_name      text NOT NULL,
    max_concurrent integer NOT NULL,
    source_id      text NOT NULL REFERENCES sources
);

CREATE TABLE ara_interactions (
    "table"               text NOT NULL,
    category              text,
    victim                text NOT NULL,
    victim_drug_ids       text,                  -- danh sách drug_id, phân tách trong chuỗi
    victim_is_combination boolean NOT NULL,
    victim_form           text,
    ara_class             text NOT NULL,
    ara_drug_ids          text,
    ara_text              text,
    mechanism             text,
    effect                text NOT NULL,
    severity              text NOT NULL REFERENCES severity_levels,   -- none = không có tương tác đáng kể
    recommendation        text,
    route_scope           text NOT NULL,
    source_id             text NOT NULL REFERENCES sources
);

CREATE TABLE pk_ddi (
    perpetrator_id       text,                    -- thuốc phối hợp: 'DDInterA;DDInterB'
    perpetrator_name     text,
    victim_id            text,
    victim_name          text,
    perpetrator_drugbank text NOT NULL,
    victim_drugbank      text NOT NULL,
    auc_fold_change      double precision NOT NULL,
    magnitude            text NOT NULL,
    source_id            text NOT NULL REFERENCES sources
);

CREATE TABLE fda_labels (
    label_set_id               text PRIMARY KEY,
    effective_time             integer NOT NULL,  -- YYYYMMDD
    product_type               text NOT NULL,
    route                      text,
    substances                 text NOT NULL,
    drug_ids                   text,
    all_substances_mapped      boolean NOT NULL,
    brand_names                text,
    boxed_warning              text,
    contraindications          text,
    drug_interactions          text,
    do_not_use                 text,
    ask_doctor_or_pharmacist   text,
    dosage_forms_and_strengths text,
    n_labels                   integer NOT NULL,
    source_id                  text NOT NULL REFERENCES sources,
    source_url                 text NOT NULL
);

CREATE TABLE dosage_form_rules (
    rule_id         text NOT NULL,               -- không duy nhất: một quy tắc (R1...) có nhiều dòng
    drug_id         text NOT NULL REFERENCES drugs,
    drug_name       text NOT NULL,
    drug_route      text NOT NULL,
    drug_form       text NOT NULL,
    other_drug_id   text NOT NULL REFERENCES drugs,
    other_drug_name text NOT NULL,
    other_route     text NOT NULL,
    severity        text NOT NULL REFERENCES severity_levels,
    action          text NOT NULL,
    effect_vi       text NOT NULL,
    management_vi   text NOT NULL,
    evidence        text NOT NULL,
    source_id       text NOT NULL REFERENCES sources,
    source_url      text NOT NULL
);

CREATE TABLE ingredient_map (
    key          text NOT NULL,
    example_name text NOT NULL,
    n_products   integer NOT NULL,
    method       text NOT NULL,
    score        integer NOT NULL,
    status       text NOT NULL,
    drug_ids     text,
    drug_names   text,
    dav_drug_id  text
);

-- Chỉ mục phục vụ tra cứu
CREATE INDEX aliases_alias_idx          ON aliases (alias);
CREATE INDEX aliases_alias_trgm_idx     ON aliases USING gin (alias gin_trgm_ops);
CREATE INDEX aliases_drug_idx           ON aliases (drug_id);
CREATE INDEX drug_interactions_ab_idx   ON drug_interactions (drug_a, drug_b);
CREATE INDEX drug_interactions_b_idx    ON drug_interactions (drug_b);
CREATE INDEX product_ingredients_p_idx  ON product_ingredients (product_id);
CREATE INDEX product_ingredients_d_idx  ON product_ingredients (drug_id);
CREATE INDEX products_name_idx          ON products (lower(name));
CREATE INDEX food_interactions_drug_idx ON food_interactions (drug_id);
CREATE INDEX disease_interactions_drug_idx ON disease_interactions (drug_id);
CREATE INDEX food_interactions_food_idx ON food_interactions (food);

-- ============================ Tra cứu ============================
-- mvp.khoa(): chuẩn hóa tên y như hàm khoa() của data/build_ddi.py (chữ thường, đ -> d, bỏ dấu, chỉ giữ chữ-số-%)
CREATE FUNCTION khoa(s text) RETURNS text
LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
    SELECT btrim(regexp_replace(public.unaccent('public.unaccent'::regdictionary, replace(lower(s), 'đ', 'd')),
                                '[^a-z0-9%]+', ' ', 'g'))
$$;

-- Một dòng cho mỗi cặp hoạt chất: một cặp có thể có 2 cơ chế với mức độ khác nhau -> lấy mức cao nhất
CREATE VIEW pair_summary AS
SELECT i.drug_a, i.drug_b,
       (array_agg(i.severity ORDER BY s.rank DESC))[1] AS max_severity,
       max(s.rank)                                    AS max_rank,
       count(*)                                       AS n_mechanisms,
       bool_or(i.both_in_vn)                          AS both_in_vn
FROM drug_interactions i
JOIN severity_levels s USING (severity)
GROUP BY i.drug_a, i.drug_b;

-- Tương tác kèm tên thuốc, mô tả cơ chế, khuyến cáo xử trí và trích dẫn: đầu vào cho bước giải thích
CREATE VIEW interaction_details AS
SELECT i.interaction_id,
       i.drug_a, da.name AS drug_a_name, da.name_vi AS drug_a_name_vi,
       i.drug_b, db.name AS drug_b_name, db.name_vi AS drug_b_name_vi,
       i.severity, sl.rank AS severity_rank, sl.label_vi AS severity_vi,
       i.mechanism_id, i.mechanism_type, m.description, m.management, m."references",
       i.source_id, i.source_url, i.both_in_vn
FROM drug_interactions i
JOIN drugs da ON da.drug_id = i.drug_a
JOIN drugs db ON db.drug_id = i.drug_b
JOIN interaction_mechanisms m ON m.mechanism_id = i.mechanism_id
JOIN severity_levels sl ON sl.severity = i.severity;

-- Tìm hoạt chất theo tên người dùng gõ: khớp đúng khóa trước; không có thì gợi ý gần đúng (pg_trgm),
-- các gợi ý luôn có status = 'suggest' để hỏi lại người dùng.
--   SELECT * FROM mvp.find_drug('Pa-ra-xê-ta-mol');
CREATE FUNCTION find_drug(q text, max_results integer DEFAULT 5)
RETURNS TABLE (drug_id text, drug_name text, alias text, alias_type text, status text, score real)
LANGUAGE sql STABLE AS $$
    WITH k AS (SELECT mvp.khoa(q) AS key),
    exact AS (                                   -- một dòng mỗi hoạt chất, ưu tiên alias status = ok
        SELECT DISTINCT ON (a.drug_id) a.drug_id, a.drug_name, a.alias, a.alias_type, a.status, 1.0::real AS score
        FROM mvp.aliases a, k WHERE a.alias = k.key
        ORDER BY a.drug_id, (a.status = 'ok') DESC, a.alias_type
    ),
    fuzzy AS (
        SELECT DISTINCT ON (a.drug_id) a.drug_id, a.drug_name, a.alias, a.alias_type,
               'suggest'::text AS status, similarity(a.alias, k.key) AS score
        FROM mvp.aliases a, k
        WHERE NOT EXISTS (SELECT 1 FROM exact) AND a.alias % k.key
        ORDER BY a.drug_id, similarity(a.alias, k.key) DESC
    )
    SELECT * FROM exact
    UNION ALL
    (SELECT * FROM fuzzy ORDER BY score DESC, alias LIMIT max_results)
$$;

-- Mọi tương tác lớp 1 giữa các hoạt chất trong danh sách, nặng nhất trước.
--   SELECT * FROM mvp.interactions_among(ARRAY['DDInter1913', 'DDInter20']);
CREATE FUNCTION interactions_among(ids text[])
RETURNS SETOF interaction_details
LANGUAGE sql STABLE AS $$
    SELECT * FROM mvp.interaction_details d
    WHERE d.drug_a = ANY (ids) AND d.drug_b = ANY (ids)
    ORDER BY d.severity_rank DESC, d.drug_a, d.drug_b, d.mechanism_id
$$;

"""Models khop data/mvp/*.csv (xem docs/BE_DEVELOPMENT.md muc 4 + data/mvp/README.md).

Quy uoc: PK TEXT giu nguyen ID CSV de COPY truc tiep.
Nhom A: sources, drugs, aliases, products, product_ingredients.
Nhom B: interaction_mechanisms, drug_interactions, food/disease/duplication,
         ara_interactions, dosage_form_rules, pk_ddi, fda_labels.
Nhom C: prescriptions, medications, checks, reviews.

Portable SQLite/Postgres: mang TEXT[] -> JSON, embedding vector(1536) -> JSON
khi chay SQLite; tren Postgres co the ALTER sang pgvector bang migration
rieng (scripts/embed_mechanisms.py chi UPDATE JSON, repo tu cosine).

Cot khop `db/mvp_schema.sql`. Lech co chu dich giu nguyen:
  - `id` surrogate PK (product_ingredients, food/disease/ara_interactions):
    CSV khong co cot nay va mot so cap trung nen khong dung composite PK.
  - `interaction_mechanisms.embedding`: vector(1536) tren Postgres.
  - `victim_drug_ids` / `ara_drug_ids` / `fda_labels.drug_ids`: TEXT phan tach
    trong CSV -> JSON de query duoc tren ca SQLite va Postgres.
"""

from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from interface.backend.db.base import Base


class Source(Base):
    __tablename__ = "sources"
    source_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    citation: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text)
    license: Mapped[str | None] = mapped_column(Text)
    last_updated: Mapped[str | None] = mapped_column(Date)


class Drug(Base):
    __tablename__ = "drugs"
    drug_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    name_vi: Mapped[str] = mapped_column(Text, default="")
    base_name: Mapped[str] = mapped_column(Text, nullable=False)
    route_variant: Mapped[str] = mapped_column(Text, default="")
    drugbank_id: Mapped[str | None] = mapped_column(Text)
    atc_code: Mapped[str | None] = mapped_column(Text)
    drug_type: Mapped[str | None] = mapped_column(Text)
    source_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("sources.source_id"), default="dav"
    )
    n_products: Mapped[int] = mapped_column(Integer, default=0)
    n_products_valid: Mapped[int] = mapped_column(Integer, default=0)
    in_vn: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    n_interactions: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (
        Index("ix_drugs_base_name", "base_name"),
        Index("ix_drugs_atc", "atc_code"),
    )


class Alias(Base):
    __tablename__ = "aliases"
    alias: Mapped[str] = mapped_column(Text, primary_key=True)
    drug_id: Mapped[str] = mapped_column(
        String, ForeignKey("drugs.drug_id"), primary_key=True
    )
    alias_type: Mapped[str | None] = mapped_column(Text)
    source_id: Mapped[str] = mapped_column(
        String, ForeignKey("sources.source_id"), primary_key=True, default="dav"
    )
    status: Mapped[str] = mapped_column(String, default="ok")
    drug_name: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint("status IN ('ok','suggest')", name="ck_alias_status"),
        Index("ix_aliases_drug", "drug_id"),
    )


class Product(Base):
    __tablename__ = "products"
    product_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    registration_no: Mapped[str | None] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    active_ingredients: Mapped[str | None] = mapped_column(Text)
    strength: Mapped[str | None] = mapped_column(Text)
    dosage_form: Mapped[str | None] = mapped_column(Text)
    packaging: Mapped[str | None] = mapped_column(Text)
    route: Mapped[str | None] = mapped_column(Text, index=True)
    form_group: Mapped[str | None] = mapped_column(Text)
    enteric_coated: Mapped[bool] = mapped_column(Boolean, default=False)
    modified_release: Mapped[bool] = mapped_column(Boolean, default=False)
    category: Mapped[str | None] = mapped_column(Text)
    manufacturer: Mapped[str | None] = mapped_column(Text)
    manufacturer_country: Mapped[str | None] = mapped_column(Text)
    registrant: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str | None] = mapped_column(Text, index=True)
    expiry_date: Mapped[str | None] = mapped_column(Date)
    source_id: Mapped[str] = mapped_column(
        String, ForeignKey("sources.source_id"), default="dav"
    )


class ProductIngredient(Base):
    __tablename__ = "product_ingredients"
    # surrogate PK: 372 dong drug_id trong (unknown) + 11 cap (product,position)
    # tach phoi hop co 2 drug_id ung vien -> khong dung composite PK
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("products.product_id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int] = mapped_column(Integer)
    ingredient: Mapped[str] = mapped_column(Text, nullable=False)
    strength: Mapped[str | None] = mapped_column(Text)
    drug_id: Mapped[str | None] = mapped_column(String, ForeignKey("drugs.drug_id"))
    base_drug_id: Mapped[str | None] = mapped_column(Text)
    match_method: Mapped[str | None] = mapped_column(Text)
    match_score: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str | None] = mapped_column(Text)
    route_match: Mapped[str | None] = mapped_column(Text)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (
        UniqueConstraint("product_id", "position", "drug_id", name="uq_prod_ing"),
        Index("ix_prod_ing_drug", "drug_id"),
    )


class InteractionMechanism(Base):
    __tablename__ = "interaction_mechanisms"
    mechanism_id: Mapped[str] = mapped_column(String, primary_key=True)
    severity: Mapped[str | None] = mapped_column(Text)
    mechanism_type: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    management: Mapped[str | None] = mapped_column(Text)
    refs: Mapped[str | None] = mapped_column("references", Text)
    n_pairs: Mapped[int] = mapped_column(Integer, default=0)
    source_id: Mapped[str] = mapped_column(
        String, ForeignKey("sources.source_id"), default="ddinter"
    )
    # vector(1536) tren Postgres; JSON list[float] tren SQLite. Cosine tinh o Python.
    embedding: Mapped[list | None] = mapped_column(JSON, nullable=True)


class ContentTranslation(Base):
    """Persistent translations; no FK so reloading source CSV preserves the cache."""
    __tablename__ = "content_translations"
    source_table: Mapped[str] = mapped_column(String, primary_key=True)
    source_id: Mapped[str] = mapped_column(String, primary_key=True)
    field: Mapped[str] = mapped_column(String, primary_key=True)
    language: Mapped[str] = mapped_column(String, primary_key=True, default="vi")
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    translated_text: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str] = mapped_column(String, nullable=False)
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class DrugInteraction(Base):
    __tablename__ = "drug_interactions"
    interaction_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    drug_a: Mapped[str] = mapped_column(String, ForeignKey("drugs.drug_id"))
    drug_b: Mapped[str] = mapped_column(String, ForeignKey("drugs.drug_id"))
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    mechanism_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("interaction_mechanisms.mechanism_id")
    )
    mechanism_type: Mapped[str | None] = mapped_column(Text)
    both_in_vn: Mapped[bool] = mapped_column(Boolean, default=False)
    source_id: Mapped[str] = mapped_column(
        String, ForeignKey("sources.source_id"), default="ddinter"
    )
    source_url: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        # Khong CHECK drug_a<drug_b: CSV sap theo SO DDInter (numeric), con SQLite
        # so sanh TEXT ('DDInter999' > 'DDInter1000'). Lookup query ca 2 chieu.
        CheckConstraint(
            "severity IN ('contraindicated','major','moderate','minor')",
            name="ck_pair_severity",
        ),
        # DDInter goc co 218 cap trung (a,b,mechanism) voi 2 interaction_id khac nhau
        # -> khong UNIQUE, chi index de lookup nhanh
        Index("ix_pair_mech", "drug_a", "drug_b", "mechanism_id"),
        Index("ix_pair_ab", "drug_a", "drug_b"),
        Index("ix_pair_vn", "both_in_vn", "severity"),
    )


class FoodInteraction(Base):
    __tablename__ = "food_interactions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    drug_id: Mapped[str | None] = mapped_column(String, ForeignKey("drugs.drug_id"))
    drug_name: Mapped[str | None] = mapped_column(Text)
    food: Mapped[str] = mapped_column(Text, nullable=False)
    food_vi: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[str | None] = mapped_column(Text)
    mechanism_type: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    management: Mapped[str | None] = mapped_column(Text)
    refs: Mapped[str | None] = mapped_column("references", Text)
    source_id: Mapped[str] = mapped_column(
        String, ForeignKey("sources.source_id"), default="ddinter"
    )

    # DDInter co 1 cap (drug,food) trung voi 2 mo ta khac nhau -> giu ca 2, khong UNIQUE
    __table_args__ = (Index("ix_food_drug", "drug_id"),)


class DiseaseInteraction(Base):
    __tablename__ = "disease_interactions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    drug_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("drugs.drug_id"), index=True
    )
    drug_name: Mapped[str | None] = mapped_column(Text)
    disease: Mapped[str | None] = mapped_column(Text)
    mesh_id: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    refs: Mapped[str | None] = mapped_column("references", Text)
    source_id: Mapped[str] = mapped_column(
        String, ForeignKey("sources.source_id"), default="ddinter"
    )


class DuplicationClass(Base):
    __tablename__ = "duplication_classes"
    class_name: Mapped[str] = mapped_column(Text, primary_key=True)
    drug_id: Mapped[str] = mapped_column(
        String, ForeignKey("drugs.drug_id"), primary_key=True
    )
    drug_name: Mapped[str | None] = mapped_column(Text)
    max_concurrent: Mapped[int] = mapped_column(Integer, default=1)
    source_id: Mapped[str] = mapped_column(
        String, ForeignKey("sources.source_id"), default="ddinter"
    )


class AraInteraction(Base):
    __tablename__ = "ara_interactions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    table_name: Mapped[str | None] = mapped_column("table", Text)
    category: Mapped[str | None] = mapped_column(Text)
    victim: Mapped[str | None] = mapped_column(Text)
    victim_drug_ids: Mapped[list] = mapped_column(JSON, default=list)
    victim_form: Mapped[str] = mapped_column(Text, default="")
    victim_is_combination: Mapped[bool] = mapped_column(Boolean, default=False)
    ara_class: Mapped[str | None] = mapped_column(Text)
    ara_drug_ids: Mapped[list] = mapped_column(JSON, default=list)
    ara_text: Mapped[str | None] = mapped_column(Text)
    mechanism: Mapped[str | None] = mapped_column(Text)
    effect: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[str | None] = mapped_column(Text)
    recommendation: Mapped[str | None] = mapped_column(Text)
    route_scope: Mapped[str] = mapped_column(Text, default="oral")
    source_id: Mapped[str] = mapped_column(
        String, ForeignKey("sources.source_id"), default="patel2020"
    )


class DosageFormRule(Base):
    __tablename__ = "dosage_form_rules"
    # 1 rule_id ap cho nhieu other_drug (vd R1 cho tung PPI) -> PK composite
    rule_id: Mapped[str] = mapped_column(String, primary_key=True)
    drug_id: Mapped[str | None] = mapped_column(String, ForeignKey("drugs.drug_id"))
    drug_name: Mapped[str | None] = mapped_column(Text)
    drug_route: Mapped[str | None] = mapped_column(Text)
    drug_form: Mapped[str | None] = mapped_column(Text)
    other_drug_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("drugs.drug_id"), primary_key=True, default=""
    )
    other_drug_name: Mapped[str | None] = mapped_column(Text)
    other_route: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[str | None] = mapped_column(Text)
    action: Mapped[str | None] = mapped_column(Text)
    effect_vi: Mapped[str | None] = mapped_column(Text)
    management_vi: Mapped[str | None] = mapped_column(Text)
    evidence: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text)
    source_id: Mapped[str] = mapped_column(
        String, ForeignKey("sources.source_id"), default="openfda"
    )


class PkDdi(Base):
    __tablename__ = "pk_ddi"
    perpetrator_id: Mapped[str] = mapped_column(
        String, ForeignKey("drugs.drug_id"), primary_key=True
    )
    perpetrator_name: Mapped[str | None] = mapped_column(Text)
    perpetrator_drugbank: Mapped[str | None] = mapped_column(Text)
    victim_id: Mapped[str] = mapped_column(
        String, ForeignKey("drugs.drug_id"), primary_key=True
    )
    victim_name: Mapped[str | None] = mapped_column(Text)
    victim_drugbank: Mapped[str | None] = mapped_column(Text)
    auc_fold_change: Mapped[float | None] = mapped_column(Float)
    magnitude: Mapped[str | None] = mapped_column(Text)
    source_id: Mapped[str] = mapped_column(
        String, ForeignKey("sources.source_id"), default="pkddip"
    )


class FdaLabel(Base):
    __tablename__ = "fda_labels"
    label_set_id: Mapped[str] = mapped_column(String, primary_key=True)
    effective_time: Mapped[str | None] = mapped_column(Text)
    product_type: Mapped[str | None] = mapped_column(Text)
    route: Mapped[str | None] = mapped_column(Text)
    substances: Mapped[str | None] = mapped_column(Text)
    drug_ids: Mapped[list] = mapped_column(JSON, default=list)
    all_substances_mapped: Mapped[bool] = mapped_column(Boolean, default=False)
    brand_names: Mapped[str | None] = mapped_column(Text)
    boxed_warning: Mapped[str | None] = mapped_column(Text)
    contraindications: Mapped[str | None] = mapped_column(Text)
    drug_interactions: Mapped[str | None] = mapped_column(Text)
    do_not_use: Mapped[str | None] = mapped_column(Text)
    ask_doctor_or_pharmacist: Mapped[str | None] = mapped_column(Text)
    dosage_forms_and_strengths: Mapped[str | None] = mapped_column(Text)
    n_labels: Mapped[int] = mapped_column(Integer, default=0)
    source_url: Mapped[str | None] = mapped_column(Text)
    source_id: Mapped[str] = mapped_column(
        String, ForeignKey("sources.source_id"), default="openfda"
    )


class IngredientMap(Base):
    """Khoa hoat chat -> drug_id (sinh tu CSV, dung cho buoc normalize).

    CSV khong khai bao PK nen dung `key` lam PK trong model.
    """

    __tablename__ = "ingredient_map"
    key: Mapped[str] = mapped_column(Text, primary_key=True)
    example_name: Mapped[str] = mapped_column(Text, nullable=False)
    n_products: Mapped[int] = mapped_column(Integer, default=0)
    method: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    drug_ids: Mapped[str | None] = mapped_column(Text)
    drug_names: Mapped[str | None] = mapped_column(Text)
    dav_drug_id: Mapped[str | None] = mapped_column(String, index=True)


# ---------------- Nhom C: app ----------------


class Prescription(Base):
    __tablename__ = "prescriptions"
    name: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=True)
    id: Mapped[str] = mapped_column(String, primary_key=True)
    status: Mapped[str] = mapped_column(Text, default="Chưa kiểm tra")
    highest_severity_vi: Mapped[str | None] = mapped_column(Text)
    checks_count: Mapped[int] = mapped_column(Integer, default=0)
    last_checked: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Medication(Base):
    __tablename__ = "medications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    prescription_id: Mapped[str] = mapped_column(
        String, ForeignKey("prescriptions.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    drug_id: Mapped[str | None] = mapped_column(String, ForeignKey("drugs.drug_id"))
    ingredient: Mapped[str | None] = mapped_column(Text)
    dose: Mapped[str] = mapped_column(Text, default="")
    frequency: Mapped[str] = mapped_column(Text, default="")
    type: Mapped[str] = mapped_column(Text, default="OTC")
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    norm_status: Mapped[str | None] = mapped_column(Text)
    suggestions: Mapped[list] = mapped_column(JSON, default=list)


class Check(Base):
    __tablename__ = "checks"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    prescription_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("prescriptions.id"), index=True
    )
    status: Mapped[str] = mapped_column(Text, default="running")
    meds_snapshot: Mapped[list] = mapped_column(JSON, nullable=False)
    summary: Mapped[dict | None] = mapped_column(JSON)
    # Nguyên văn kết quả lúc chạy (CheckResponse + ngày cập nhật từng nguồn) để truy vết:
    # mở lại lần kiểm tra cũ phải thấy đúng cảnh báo người dùng đã xem, kể cả khi CSDL đã đổi.
    result: Mapped[dict | None] = mapped_column(JSON)
    max_severity: Mapped[str | None] = mapped_column(Text)
    steps_done: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )


class Review(Base):
    """Yêu cầu trao đổi dược sĩ (HITL) — khớp FE ReviewView (danh sách yêu cầu).

    `status` dùng tiếng Việt để FE hiển thị trực tiếp: 'Đang chờ' | 'Đã phản hồi'.
    """

    __tablename__ = "reviews"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    prescription_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("prescriptions.id")
    )
    check_id: Mapped[str | None] = mapped_column(String, ForeignKey("checks.id"))
    patient: Mapped[str] = mapped_column(Text, default="")
    med_count: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, default="Đang chờ")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint(
            "status IN ('Đang chờ','Đã phản hồi')", name="ck_reviews_status"
        ),
    )

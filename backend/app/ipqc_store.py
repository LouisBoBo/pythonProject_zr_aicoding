"""IPQC 主数据与明细（挂接品质检验记录，不另建平行单据表）。

设计约束：
- 执行单据仍落 `quality_inspection_records`（与导入/分析/任务共用）
- 本模块仅管：模板、测试项目、模板关联、模板版本、检验明细结果
- template_code 对齐源系统 CTEMPLATE_ID，便于导入数据关联
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    inspect,
    text,
)
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship

from app.database import Base
from app.quality_inspection_record_store import QualityInspectionRecord

# 录入类型（写入 quality_inspection_records.ipqc_entry_type）
IPQC_ENTRY_FIRST = "first_article"  # 首件
IPQC_ENTRY_PATROL = "patrol"  # 巡检
IPQC_ENTRY_REINSPECT = "reinspect"  # 复检
IPQC_ENTRY_SUBMIT = "submit"  # 送检提交（待检任务）
IPQC_ENTRY_IMPORT = "import"  # Excel 导入

IPQC_ENTRY_LABELS = {
    IPQC_ENTRY_FIRST: "首件",
    IPQC_ENTRY_PATROL: "巡检",
    IPQC_ENTRY_REINSPECT: "复检",
    IPQC_ENTRY_SUBMIT: "送检",
    IPQC_ENTRY_IMPORT: "导入",
}


class IpqcTemplate(Base):
    """IPQC 检验模板"""

    __tablename__ = "ipqc_templates"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    template_code: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    process_id: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    process_name: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")  # active/disabled
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    items: Mapped[list["IpqcTemplateItem"]] = relationship(
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="IpqcTemplateItem.sort_order",
    )
    versions: Mapped[list["IpqcTemplateVersion"]] = relationship(
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="IpqcTemplateVersion.version.desc()",
    )


class IpqcTestItem(Base):
    """IPQC 测试/检验项目主数据"""

    __tablename__ = "ipqc_test_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    item_code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    item_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    standard_value: Mapped[str | None] = mapped_column(String(200), nullable=True)
    judge_type: Mapped[str] = mapped_column(String(20), nullable=False, default="ok_ng")  # ok_ng/numeric
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    process_name: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class IpqcTemplateItem(Base):
    """模板 ↔ 测试项目关联"""

    __tablename__ = "ipqc_template_items"
    __table_args__ = (UniqueConstraint("template_id", "test_item_id", name="uq_ipqc_tpl_item"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("ipqc_templates.id"), nullable=False, index=True)
    test_item_id: Mapped[int] = mapped_column(ForeignKey("ipqc_test_items.id"), nullable=False, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    template: Mapped["IpqcTemplate"] = relationship(back_populates="items")
    test_item: Mapped["IpqcTestItem"] = relationship()


class IpqcTemplateVersion(Base):
    """模板升级记录"""

    __tablename__ = "ipqc_template_versions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("ipqc_templates.id"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    change_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_by: Mapped[str | None] = mapped_column(String(50), nullable=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    item_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON 文本快照

    template: Mapped["IpqcTemplate"] = relationship(back_populates="versions")


class QualityInspectionItemResult(Base):
    """检验记录明细结果（挂 quality_inspection_records）"""

    __tablename__ = "quality_inspection_item_results"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    record_id: Mapped[int] = mapped_column(
        ForeignKey("quality_inspection_records.id"), nullable=False, index=True
    )
    test_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("ipqc_test_items.id"), nullable=True, index=True
    )
    item_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    item_name: Mapped[str] = mapped_column(String(100), nullable=False)
    standard_value: Mapped[str | None] = mapped_column(String(200), nullable=True)
    actual_value: Mapped[str | None] = mapped_column(String(200), nullable=True)
    result: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")  # pass/fail/pending
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


def ensure_ipqc_schema(bind_engine) -> None:
    """创建 IPQC 相关表，并为检验记录补齐 ipqc_entry_type。"""
    IpqcTemplate.__table__.create(bind=bind_engine, checkfirst=True)
    IpqcTestItem.__table__.create(bind=bind_engine, checkfirst=True)
    IpqcTemplateItem.__table__.create(bind=bind_engine, checkfirst=True)
    IpqcTemplateVersion.__table__.create(bind=bind_engine, checkfirst=True)
    QualityInspectionItemResult.__table__.create(bind=bind_engine, checkfirst=True)

    inspector = inspect(bind_engine)
    if inspector.has_table("quality_inspection_records"):
        columns = {c["name"] for c in inspector.get_columns("quality_inspection_records")}
        if "ipqc_entry_type" not in columns:
            with bind_engine.begin() as conn:
                conn.execute(
                    text(
                        "ALTER TABLE quality_inspection_records "
                        "ADD COLUMN ipqc_entry_type VARCHAR(30)"
                    )
                )


# 完整检验项目目录（可重复 enrich）
IPQC_PROCESS_ITEM_CATALOG: dict[str, list[tuple[str, str, str, str, str | None]]] = {
    # code, name, standard, judge_type, unit
    "成型": [
        ("CX-WG", "外形尺寸", "按图纸公差", "ok_ng", "mm"),
        ("CX-LM", "锣边外观", "无毛刺/崩边", "ok_ng", None),
        ("CX-DW", "定位孔", "孔位/孔径符合要求", "ok_ng", None),
        ("CX-ZX", "外形直角", "直角无明显缺口", "ok_ng", None),
        ("CX-BM", "板面清洁", "无油污/异物", "ok_ng", None),
    ],
    "钻孔": [
        ("ZK-KJ", "孔径", "按图纸公差", "numeric", "mm"),
        ("ZK-KW", "孔位", "偏位达标", "ok_ng", None),
        ("ZK-BK", "堵孔/破孔", "不允许", "ok_ng", None),
        ("ZK-LH", "孔壁质量", "无严重粗糙/钉头", "ok_ng", None),
        ("ZK-LQ", "漏钻/多钻", "不允许", "ok_ng", None),
    ],
    "阻焊": [
        ("ZH-YH", "油厚", "按规格要求", "numeric", "um"),
        ("ZH-DW", "对位", "偏移达标", "ok_ng", None),
        ("ZH-WG", "油面外观", "无异物/掉油/气泡", "ok_ng", None),
        ("ZH-CK", "窗孔", "开窗正确、无粘连", "ok_ng", None),
        ("ZH-YS", "油色均匀", "无明显色差", "ok_ng", None),
    ],
    "待确认工序": [
        ("DQ-WG", "外观检查", "无明显缺陷", "ok_ng", None),
        ("DQ-CC", "尺寸抽查", "按图纸", "ok_ng", None),
        ("DQ-BS", "标识确认", "清晰正确", "ok_ng", None),
    ],
    "通用": [
        ("TY-WG", "外观", "无明显缺陷", "ok_ng", None),
        ("TY-BS", "标识", "清晰正确", "ok_ng", None),
        ("TY-QH", "清洁度", "无污染", "ok_ng", None),
    ],
}

TEMPLATE_NAME_HINTS = {
    "121863297314886": "阻焊IPQC模板",
    "122493457485894": "成型IPQC模板",
    "122493458153542": "钻孔IPQC模板",
    "221922304233542": "待确认工序IPQC模板",
    "233956824903750": "跨工序巡检模板",
}


def _ensure_test_items(db: Session) -> dict[str, IpqcTestItem]:
    """确保检验项目目录齐全，返回 code→实体。"""
    by_code: dict[str, IpqcTestItem] = {
        r.item_code: r for r in db.query(IpqcTestItem).all() if r.item_code
    }
    for process_name, items in IPQC_PROCESS_ITEM_CATALOG.items():
        for code, name, standard, judge, unit in items:
            if code in by_code:
                row = by_code[code]
                # 轻量纠偏
                row.item_name = name
                row.standard_value = standard
                row.judge_type = judge
                row.unit = unit
                row.category = process_name
                row.process_name = None if process_name == "通用" else process_name
                row.status = "active"
                continue
            row = IpqcTestItem(
                item_code=code,
                item_name=name,
                category=process_name,
                standard_value=standard,
                judge_type=judge,
                unit=unit,
                process_name=None if process_name == "通用" else process_name,
                status="active",
            )
            db.add(row)
            db.flush()
            by_code[code] = row
    return by_code


def _sync_template_links(db: Session, tpl: IpqcTemplate, by_code: dict[str, IpqcTestItem]) -> None:
    """按工序重建模板关联（保留模板主键，更新关联清单）。"""
    codes: list[str] = []
    pname = tpl.process_name or "通用"
    if pname in IPQC_PROCESS_ITEM_CATALOG:
        codes.extend(c for c, *_ in IPQC_PROCESS_ITEM_CATALOG[pname])
    # 跨工序巡检模板：挂全部工序核心项 + 通用
    if tpl.template_code == "233956824903750":
        codes = []
        for key in ("成型", "钻孔", "阻焊"):
            codes.extend(c for c, *_ in IPQC_PROCESS_ITEM_CATALOG[key][:3])
    codes.extend(c for c, *_ in IPQC_PROCESS_ITEM_CATALOG["通用"])
    # 去重保序
    seen: set[str] = set()
    ordered: list[str] = []
    for c in codes:
        if c in seen:
            continue
        seen.add(c)
        ordered.append(c)

    existing = {
        (i.test_item_id): i
        for i in db.query(IpqcTemplateItem).filter(IpqcTemplateItem.template_id == tpl.id).all()
    }
    wanted_ids: set[int] = set()
    for idx, code in enumerate(ordered):
        item = by_code.get(code)
        if not item:
            continue
        wanted_ids.add(item.id)
        link = existing.get(item.id)
        if link:
            link.sort_order = idx + 1
            link.required = True
        else:
            db.add(
                IpqcTemplateItem(
                    template_id=tpl.id,
                    test_item_id=item.id,
                    sort_order=idx + 1,
                    required=True,
                )
            )
    # 删除不在目录中的旧关联
    for tid, link in existing.items():
        if tid not in wanted_ids:
            db.delete(link)


def seed_ipqc_from_inspection_records(db: Session) -> None:
    """首次从导入记录生成模板骨架；已存在则跳过创建，交给 enrich。"""
    if db.query(IpqcTemplate).first():
        return

    from sqlalchemy import func

    from app.ipqc_import import IPQC_PROCESS_NAME_MAP

    tpl_rows = (
        db.query(
            QualityInspectionRecord.template_id,
            QualityInspectionRecord.process_id,
            QualityInspectionRecord.process_name,
            func.count(),
        )
        .filter(
            QualityInspectionRecord.source_cid.isnot(None),
            QualityInspectionRecord.template_id.isnot(None),
        )
        .group_by(
            QualityInspectionRecord.template_id,
            QualityInspectionRecord.process_id,
            QualityInspectionRecord.process_name,
        )
        .all()
    )

    best: dict[str, tuple[str | None, str | None, int]] = {}
    for tid, pid, pname, n in tpl_rows:
        if not tid:
            continue
        cur = best.get(tid)
        if cur is None or n > cur[2]:
            best[tid] = (pid, pname, int(n))

    for tid, (pid, pname, _) in best.items():
        pname = pname or (IPQC_PROCESS_NAME_MAP.get(pid or "") if pid else None)
        tpl = IpqcTemplate(
            template_code=str(tid),
            name=TEMPLATE_NAME_HINTS.get(str(tid), f"IPQC模板-{str(tid)[-6:]}"),
            process_id=pid,
            process_name=pname,
            version=1,
            status="active",
            remark="由已导入检验记录自动生成",
            created_by="system",
        )
        db.add(tpl)
        db.flush()
        db.add(
            IpqcTemplateVersion(
                template_id=tpl.id,
                version=1,
                change_note="初始版本（系统种子）",
                changed_by="system",
            )
        )
    db.commit()


def enrich_ipqc_data(db: Session, *, include_item_results: bool = True) -> dict[str, int]:
    """可重复执行：补全项目目录、模板关联、工序名、entry_type；可选生成导入记录明细。

    include_item_results=False 时仅补主数据（启动引导用），避免全表扫描写明细导致启动阻塞。
    """
    from app.ipqc_import import IPQC_PROCESS_NAME_MAP

    by_code = _ensure_test_items(db)

    # 补模板：导入里出现但主数据缺失的 template_id
    from sqlalchemy import func

    missing_tids = (
        db.query(QualityInspectionRecord.template_id, func.count())
        .filter(
            QualityInspectionRecord.source_cid.isnot(None),
            QualityInspectionRecord.template_id.isnot(None),
        )
        .group_by(QualityInspectionRecord.template_id)
        .all()
    )
    existing_codes = {t.template_code for t in db.query(IpqcTemplate).all()}
    created_tpl = 0
    for tid, _n in missing_tids:
        code = str(tid)
        if code in existing_codes:
            continue
        # 取该模板最常见工序
        top = (
            db.query(
                QualityInspectionRecord.process_id,
                QualityInspectionRecord.process_name,
                func.count(),
            )
            .filter(QualityInspectionRecord.template_id == code)
            .group_by(
                QualityInspectionRecord.process_id,
                QualityInspectionRecord.process_name,
            )
            .order_by(func.count().desc())
            .first()
        )
        pid = top[0] if top else None
        pname = (top[1] if top else None) or IPQC_PROCESS_NAME_MAP.get(pid or "")
        tpl = IpqcTemplate(
            template_code=code,
            name=TEMPLATE_NAME_HINTS.get(code, f"IPQC模板-{code[-6:]}"),
            process_id=pid,
            process_name=pname,
            version=1,
            status="active",
            remark="enrich 自动补建",
            created_by="system",
        )
        db.add(tpl)
        db.flush()
        db.add(
            IpqcTemplateVersion(
                template_id=tpl.id,
                version=1,
                change_note="enrich 自动补建",
                changed_by="system",
            )
        )
        created_tpl += 1
        existing_codes.add(code)

    # 纠偏模板名称/工序
    for tpl in db.query(IpqcTemplate).all():
        if tpl.template_code in TEMPLATE_NAME_HINTS:
            tpl.name = TEMPLATE_NAME_HINTS[tpl.template_code]
        if tpl.process_id and not tpl.process_name:
            tpl.process_name = IPQC_PROCESS_NAME_MAP.get(tpl.process_id)
        if tpl.template_code == "221922304233542":
            tpl.process_id = tpl.process_id or "3273661841000048"
            tpl.process_name = "待确认工序"
        _sync_template_links(db, tpl, by_code)

    # 回填记录工序名 / entry_type
    from sqlalchemy import or_

    for pid, pname in IPQC_PROCESS_NAME_MAP.items():
        db.query(QualityInspectionRecord).filter(
            QualityInspectionRecord.process_id == pid,
            or_(
                QualityInspectionRecord.process_name.is_(None),
                QualityInspectionRecord.process_name == "",
            ),
        ).update({QualityInspectionRecord.process_name: pname}, synchronize_session=False)

    entry_fixed = (
        db.query(QualityInspectionRecord)
        .filter(
            QualityInspectionRecord.source_cid.isnot(None),
            QualityInspectionRecord.ipqc_entry_type.is_(None),
        )
        .update(
            {QualityInspectionRecord.ipqc_entry_type: IPQC_ENTRY_IMPORT},
            synchronize_session=False,
        )
    )

    created_results = 0
    if include_item_results:
        # 为尚无明细的导入记录按模板生成项目结果
        tpl_by_code = {t.template_code: t for t in db.query(IpqcTemplate).all()}
        links_by_tpl: dict[int, list[IpqcTemplateItem]] = {}
        for link in db.query(IpqcTemplateItem).all():
            links_by_tpl.setdefault(link.template_id, []).append(link)
        item_by_id = {i.id: i for i in db.query(IpqcTestItem).all()}

        already = {
            r[0]
            for r in db.query(QualityInspectionItemResult.record_id)
            .distinct()
            .all()
        }

        records = (
            db.query(QualityInspectionRecord)
            .filter(QualityInspectionRecord.source_cid.isnot(None))
            .all()
        )
        batch: list[QualityInspectionItemResult] = []
        for rec in records:
            if rec.id in already:
                continue
            tpl = tpl_by_code.get(rec.template_id or "")
            links = links_by_tpl.get(tpl.id, []) if tpl else []
            # 无模板时按工序目录兜底
            if not links:
                pname = rec.process_name or IPQC_PROCESS_NAME_MAP.get(rec.process_id or "") or "通用"
                codes = [c for c, *_ in IPQC_PROCESS_ITEM_CATALOG.get(pname, [])]
                codes.extend(c for c, *_ in IPQC_PROCESS_ITEM_CATALOG["通用"])
                fake_links = []
                for idx, code in enumerate(dict.fromkeys(codes)):
                    ti = by_code.get(code)
                    if not ti:
                        continue
                    fake_links.append((idx + 1, ti))
                link_iter = fake_links
                use_tuple = True
            else:
                link_iter = sorted(links, key=lambda x: x.sort_order)
                use_tuple = False

            for idx, link in enumerate(link_iter):
                if use_tuple:
                    sort_order, ti = link
                else:
                    sort_order = link.sort_order
                    ti = item_by_id.get(link.test_item_id)
                if not ti:
                    continue
                if rec.inspection_result == "fail":
                    # 首项不合格，其余合格，便于分析下钻
                    result = "fail" if idx == 0 else "pass"
                    actual = "NG" if result == "fail" else "OK"
                elif rec.inspection_result == "pending" or rec.status == "pending":
                    result = "pending"
                    actual = None
                else:
                    result = "pass"
                    actual = "OK"
                batch.append(
                    QualityInspectionItemResult(
                        record_id=rec.id,
                        test_item_id=ti.id,
                        item_code=ti.item_code,
                        item_name=ti.item_name,
                        standard_value=ti.standard_value,
                        actual_value=actual,
                        result=result,
                        remark="由导入记录按模板自动生成" if result != "pending" else None,
                        sort_order=sort_order,
                    )
                )
                created_results += 1
            if len(batch) >= 500:
                db.add_all(batch)
                db.commit()
                batch.clear()

        if batch:
            db.add_all(batch)
    db.commit()

    return {
        "templates": db.query(IpqcTemplate).count(),
        "test_items": db.query(IpqcTestItem).count(),
        "template_links": db.query(IpqcTemplateItem).count(),
        "created_templates": created_tpl,
        "entry_type_fixed": int(entry_fixed or 0),
        "item_results_created": created_results,
        "item_results_total": db.query(QualityInspectionItemResult).count(),
    }

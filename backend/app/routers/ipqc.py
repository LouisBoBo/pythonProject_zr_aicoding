"""IPQC 业务接口：模板/项目/关联/版本/录入/修改/详情。

单据一律写入 `quality_inspection_records`，与导入、检验任务、IPQC 分析共用。
"""

from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.audit import record_audit
from app.auth import get_current_user
from app.database import SessionLocal, engine, get_db
from app.ipqc_store import (
    IPQC_ENTRY_FIRST,
    IPQC_ENTRY_IMPORT,
    IPQC_ENTRY_PATROL,
    IPQC_ENTRY_REINSPECT,
    IPQC_ENTRY_SUBMIT,
    IpqcTemplate,
    IpqcTemplateItem,
    IpqcTemplateVersion,
    IpqcTestItem,
    QualityInspectionItemResult,
    enrich_ipqc_data,
    ensure_ipqc_schema,
    seed_ipqc_from_inspection_records,
)
from app.models import User, WorkOrder
from app.permissions import QUALITY_WRITE, require_permissions
from app.quality_inspection_record_store import (
    RESULT_TO_STATUS,
    TASK_STATUS_PENDING,
    QualityInspectionRecord,
    ensure_quality_inspection_records_schema,
)
from app.schemas_ipqc import (
    IpqcItemResultIn,
    IpqcItemResultResponse,
    IpqcRecordDetailResponse,
    IpqcRecordEntryCreate,
    IpqcRecordUpdate,
    IpqcTemplateCreate,
    IpqcTemplateItemResponse,
    IpqcTemplateListResponse,
    IpqcTemplateResponse,
    IpqcTemplateUpdate,
    IpqcTemplateVersionListResponse,
    IpqcTemplateVersionResponse,
    IpqcTestItemCreate,
    IpqcTestItemListResponse,
    IpqcTestItemResponse,
    IpqcTestItemUpdate,
)

router = APIRouter(prefix="/api/quality/ipqc", tags=["IPQC"])

ensure_quality_inspection_records_schema(engine)
ensure_ipqc_schema(engine)


def _bootstrap_ipqc() -> None:
    """启动仅补主数据骨架；全量明细生成走 POST /enrich，避免启动阻塞与资源耗尽。"""
    db = SessionLocal()
    try:
        seed_ipqc_from_inspection_records(db)
        enrich_ipqc_data(db, include_item_results=False)
    finally:
        db.close()


_bootstrap_ipqc()


def _tpl_item_resp(row: IpqcTemplateItem) -> IpqcTemplateItemResponse:
    ti = row.test_item
    return IpqcTemplateItemResponse(
        id=row.id,
        test_item_id=row.test_item_id,
        sort_order=row.sort_order,
        required=row.required,
        item_code=ti.item_code if ti else None,
        item_name=ti.item_name if ti else None,
        standard_value=ti.standard_value if ti else None,
        judge_type=ti.judge_type if ti else None,
    )


def _tpl_resp(tpl: IpqcTemplate, with_items: bool = True) -> IpqcTemplateResponse:
    items = [_tpl_item_resp(i) for i in (tpl.items or [])] if with_items else []
    return IpqcTemplateResponse(
        id=tpl.id,
        template_code=tpl.template_code,
        name=tpl.name,
        process_id=tpl.process_id,
        process_name=tpl.process_name,
        version=tpl.version,
        status=tpl.status,
        remark=tpl.remark,
        created_by=tpl.created_by,
        created_at=tpl.created_at,
        updated_at=tpl.updated_at,
        items=items,
    )


def _snapshot_items(tpl: IpqcTemplate) -> str:
    payload = [
        {
            "test_item_id": i.test_item_id,
            "sort_order": i.sort_order,
            "required": i.required,
            "item_code": i.test_item.item_code if i.test_item else None,
            "item_name": i.test_item.item_name if i.test_item else None,
        }
        for i in (tpl.items or [])
    ]
    return json.dumps(payload, ensure_ascii=False)


def _replace_template_items(db: Session, tpl: IpqcTemplate, items_in: list) -> None:
    db.query(IpqcTemplateItem).filter(IpqcTemplateItem.template_id == tpl.id).delete()
    for raw in items_in:
        item = db.query(IpqcTestItem).filter(IpqcTestItem.id == raw.test_item_id).first()
        if not item:
            raise HTTPException(status_code=400, detail=f"测试项目不存在: {raw.test_item_id}")
        db.add(
            IpqcTemplateItem(
                template_id=tpl.id,
                test_item_id=raw.test_item_id,
                sort_order=raw.sort_order,
                required=raw.required,
            )
        )


# ---------- 测试项目 ----------


@router.get(
    "/test-items",
    response_model=IpqcTestItemListResponse,
    summary="测试项目列表",
    description="分页查询 IPQC 测试/检验项目；对应菜单「测试项目」「检验项目查询」。",
)
def list_test_items(
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    keyword: str | None = Query(None, description="编码/名称关键词"),
    process_name: str | None = Query(None, description="适用工序"),
    status: str | None = Query(None, description="状态 active/disabled"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(IpqcTestItem)
    if keyword:
        like = f"%{keyword}%"
        q = q.filter((IpqcTestItem.item_code.ilike(like)) | (IpqcTestItem.item_name.ilike(like)))
    if process_name:
        q = q.filter(IpqcTestItem.process_name == process_name)
    if status:
        q = q.filter(IpqcTestItem.status == status)
    total = q.count()
    rows = (
        q.order_by(IpqcTestItem.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return IpqcTestItemListResponse(
        items=[IpqcTestItemResponse.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/test-items",
    response_model=IpqcTestItemResponse,
    status_code=201,
    summary="新建测试项目",
    description="新增 IPQC 检验项目主数据。",
)
def create_test_item(
    body: IpqcTestItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(QUALITY_WRITE)),
):
    if db.query(IpqcTestItem).filter(IpqcTestItem.item_code == body.item_code).first():
        raise HTTPException(status_code=400, detail="项目编码已存在")
    row = IpqcTestItem(**body.model_dump())
    db.add(row)
    record_audit(
        db,
        username=current_user.username,
        action="create",
        resource="ipqc_test_item",
        resource_id=body.item_code,
    )
    db.commit()
    db.refresh(row)
    return IpqcTestItemResponse.model_validate(row)


@router.patch(
    "/test-items/{item_id}",
    response_model=IpqcTestItemResponse,
    summary="更新测试项目",
    description="修改检验项目属性或启停状态。",
)
def update_test_item(
    item_id: int,
    body: IpqcTestItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(QUALITY_WRITE)),
):
    row = db.query(IpqcTestItem).filter(IpqcTestItem.id == item_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="测试项目不存在")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    record_audit(
        db,
        username=current_user.username,
        action="update",
        resource="ipqc_test_item",
        resource_id=row.item_code,
    )
    db.commit()
    db.refresh(row)
    return IpqcTestItemResponse.model_validate(row)


# ---------- 模板 ----------


@router.get(
    "/templates",
    response_model=IpqcTemplateListResponse,
    summary="IPQC 模板列表",
    description="分页查询检验模板；template_code 对齐源系统 CTEMPLATE_ID。",
)
def list_templates(
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    keyword: str | None = Query(None, description="编码/名称关键词"),
    process_name: str | None = Query(None, description="工序名称"),
    status: str | None = Query(None, description="状态"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(IpqcTemplate)
    if keyword:
        like = f"%{keyword}%"
        q = q.filter((IpqcTemplate.template_code.ilike(like)) | (IpqcTemplate.name.ilike(like)))
    if process_name:
        q = q.filter(IpqcTemplate.process_name == process_name)
    if status:
        q = q.filter(IpqcTemplate.status == status)
    total = q.count()
    rows = (
        q.options(joinedload(IpqcTemplate.items).joinedload(IpqcTemplateItem.test_item))
        .order_by(IpqcTemplate.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return IpqcTemplateListResponse(
        items=[_tpl_resp(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/templates/{template_id}",
    response_model=IpqcTemplateResponse,
    summary="IPQC 模板详情",
    description="返回模板及关联检验项目，供录入页选模板加载项目。",
)
def get_template(
    template_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    tpl = (
        db.query(IpqcTemplate)
        .options(joinedload(IpqcTemplate.items).joinedload(IpqcTemplateItem.test_item))
        .filter(IpqcTemplate.id == template_id)
        .first()
    )
    if not tpl:
        raise HTTPException(status_code=404, detail="模板不存在")
    return _tpl_resp(tpl)


@router.post(
    "/templates",
    response_model=IpqcTemplateResponse,
    status_code=201,
    summary="新建 IPQC 模板",
    description="创建模板并可同时绑定检验项目；写入初始升级记录。",
)
def create_template(
    body: IpqcTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(QUALITY_WRITE)),
):
    if db.query(IpqcTemplate).filter(IpqcTemplate.template_code == body.template_code).first():
        raise HTTPException(status_code=400, detail="模板编码已存在")
    tpl = IpqcTemplate(
        template_code=body.template_code,
        name=body.name,
        process_id=body.process_id,
        process_name=body.process_name,
        version=1,
        status="active",
        remark=body.remark,
        created_by=current_user.username,
    )
    db.add(tpl)
    db.flush()
    if body.items:
        _replace_template_items(db, tpl, body.items)
    db.flush()
    db.refresh(tpl)
    db.add(
        IpqcTemplateVersion(
            template_id=tpl.id,
            version=1,
            change_note="初始版本",
            changed_by=current_user.username,
            item_snapshot=_snapshot_items(tpl),
        )
    )
    record_audit(
        db,
        username=current_user.username,
        action="create",
        resource="ipqc_template",
        resource_id=tpl.template_code,
    )
    db.commit()
    tpl = (
        db.query(IpqcTemplate)
        .options(joinedload(IpqcTemplate.items).joinedload(IpqcTemplateItem.test_item))
        .filter(IpqcTemplate.id == tpl.id)
        .first()
    )
    return _tpl_resp(tpl)


@router.patch(
    "/templates/{template_id}",
    response_model=IpqcTemplateResponse,
    summary="更新 IPQC 模板",
    description="修改模板；若传入 items 则整体替换关联并自动升版，写入模板升级记录。",
)
def update_template(
    template_id: int,
    body: IpqcTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(QUALITY_WRITE)),
):
    tpl = (
        db.query(IpqcTemplate)
        .options(joinedload(IpqcTemplate.items).joinedload(IpqcTemplateItem.test_item))
        .filter(IpqcTemplate.id == template_id)
        .first()
    )
    if not tpl:
        raise HTTPException(status_code=404, detail="模板不存在")

    data = body.model_dump(exclude_unset=True)
    items_in = data.pop("items", None)
    change_note = data.pop("change_note", None)
    for k, v in data.items():
        setattr(tpl, k, v)

    if items_in is not None:
        _replace_template_items(db, tpl, body.items or [])
        tpl.version = int(tpl.version or 1) + 1
        db.flush()
        db.refresh(tpl)
        db.add(
            IpqcTemplateVersion(
                template_id=tpl.id,
                version=tpl.version,
                change_note=change_note or "更新关联检验项目",
                changed_by=current_user.username,
                item_snapshot=_snapshot_items(tpl),
            )
        )

    record_audit(
        db,
        username=current_user.username,
        action="update",
        resource="ipqc_template",
        resource_id=tpl.template_code,
        detail={"version": tpl.version},
    )
    db.commit()
    tpl = (
        db.query(IpqcTemplate)
        .options(joinedload(IpqcTemplate.items).joinedload(IpqcTemplateItem.test_item))
        .filter(IpqcTemplate.id == template_id)
        .first()
    )
    return _tpl_resp(tpl)


@router.get(
    "/template-versions",
    response_model=IpqcTemplateVersionListResponse,
    summary="模板升级记录",
    description="查询模板版本历史；对应菜单「模板升级记录」。",
)
def list_template_versions(
    template_id: int | None = Query(None, description="模板主键"),
    template_code: str | None = Query(None, description="模板编码"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(IpqcTemplateVersion)
    if template_id:
        q = q.filter(IpqcTemplateVersion.template_id == template_id)
    if template_code:
        tpl = db.query(IpqcTemplate).filter(IpqcTemplate.template_code == template_code).first()
        if not tpl:
            return IpqcTemplateVersionListResponse(items=[], total=0)
        q = q.filter(IpqcTemplateVersion.template_id == tpl.id)
    rows = q.order_by(IpqcTemplateVersion.changed_at.desc(), IpqcTemplateVersion.id.desc()).limit(200).all()
    return IpqcTemplateVersionListResponse(
        items=[IpqcTemplateVersionResponse.model_validate(r) for r in rows],
        total=len(rows),
    )


# ---------- 录入 / 详情 / 修改（挂检验记录） ----------


def _next_inspection_no(db: Session, prefix: str) -> str:
    today = datetime.utcnow().strftime("%Y%m%d")
    head = f"{prefix}-{today}-"
    last = (
        db.query(QualityInspectionRecord)
        .filter(QualityInspectionRecord.inspection_no.like(f"{head}%"))
        .order_by(QualityInspectionRecord.inspection_no.desc())
        .first()
    )
    seq = 1
    if last and last.inspection_no:
        try:
            seq = int(last.inspection_no.rsplit("-", 1)[-1]) + 1
        except ValueError:
            seq = 1
    return f"{head}{seq:04d}"


def _resolve_template(db: Session, template_id: int | None, template_code: str | None) -> IpqcTemplate | None:
    if template_id:
        return db.query(IpqcTemplate).filter(IpqcTemplate.id == template_id).first()
    if template_code:
        return db.query(IpqcTemplate).filter(IpqcTemplate.template_code == template_code).first()
    return None


def _save_item_results(db: Session, record_id: int, items: list) -> None:
    db.query(QualityInspectionItemResult).filter(
        QualityInspectionItemResult.record_id == record_id
    ).delete()
    for idx, raw in enumerate(items):
        db.add(
            QualityInspectionItemResult(
                record_id=record_id,
                test_item_id=raw.test_item_id,
                item_code=raw.item_code,
                item_name=raw.item_name,
                standard_value=raw.standard_value,
                actual_value=raw.actual_value,
                result=raw.result,
                remark=raw.remark,
                sort_order=raw.sort_order if raw.sort_order else idx + 1,
            )
        )


def _detail_resp(db: Session, row: QualityInspectionRecord) -> IpqcRecordDetailResponse:
    items = (
        db.query(QualityInspectionItemResult)
        .filter(QualityInspectionItemResult.record_id == row.id)
        .order_by(QualityInspectionItemResult.sort_order, QualityInspectionItemResult.id)
        .all()
    )
    return IpqcRecordDetailResponse(
        id=row.id,
        inspection_no=row.inspection_no,
        inspection_type=row.inspection_type,
        inspection_result=row.inspection_result,
        status=row.status,
        ipqc_entry_type=row.ipqc_entry_type,
        work_order_no=row.work_order_no,
        product_code=row.product_code,
        batch_no=row.batch_no,
        material_code=row.material_code,
        inspector=row.inspector,
        inspected_at=row.inspected_at,
        inspected_qty=row.inspected_qty,
        non_conforming_qty=row.non_conforming_qty,
        remark=row.remark,
        template_id=row.template_id,
        process_id=row.process_id,
        process_name=row.process_name,
        customer_code=row.customer_code,
        shift=row.shift,
        scan_barcode=row.scan_barcode,
        is_reinspection=row.is_reinspection or 0,
        item_results=[IpqcItemResultResponse.model_validate(i) for i in items],
        created_at=row.created_at,
    )


@router.post(
    "/records",
    response_model=IpqcRecordDetailResponse,
    status_code=201,
    summary="IPQC 录入/送检",
    description=(
        "首件/巡检/复检/送检写入品质检验记录表。"
        "送检生成待检任务；其余按结果写入合格/不合格。"
        "可附带检验项目明细。"
    ),
)
def create_ipqc_record(
    body: IpqcRecordEntryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(QUALITY_WRITE)),
):
    tpl = _resolve_template(db, body.template_id, body.template_code)
    if body.template_id and not tpl:
        raise HTTPException(status_code=400, detail="模板不存在")

    entry = body.entry_type
    prefix = {
        IPQC_ENTRY_FIRST: "FA",
        IPQC_ENTRY_PATROL: "PT",
        IPQC_ENTRY_REINSPECT: "RI",
        IPQC_ENTRY_SUBMIT: "QT",
    }.get(entry, "IP")

    if entry == IPQC_ENTRY_SUBMIT:
        result = "pending"
        status = TASK_STATUS_PENDING
    else:
        result = body.inspection_result or "pass"
        if result == "pending":
            status = TASK_STATUS_PENDING
        else:
            status = RESULT_TO_STATUS.get(result, TASK_STATUS_PENDING)

    # 明细有 fail 则总结果 fail
    if body.item_results and any(i.result == "fail" for i in body.item_results):
        result = "fail"
        status = RESULT_TO_STATUS["fail"]

    inspected_qty = body.inspected_qty or 0
    non_conforming = inspected_qty if result == "fail" else 0
    inspector = body.inspector or current_user.username
    now = datetime.utcnow()

    wo_id = None
    if body.work_order_no:
        wo = db.query(WorkOrder).filter(WorkOrder.order_no == body.work_order_no).first()
        wo_id = wo.id if wo else None

    row = QualityInspectionRecord(
        inspection_no=_next_inspection_no(db, prefix),
        inspection_type="process",
        inspection_result=result,
        status=status,
        work_order_id=wo_id,
        work_order_no=body.work_order_no,
        product_code=body.product_code,
        batch_no=body.batch_no,
        material_code=body.material_code or body.product_code,
        inspector=inspector,
        inspected_at=now,
        non_conforming_qty=non_conforming,
        remark=body.remark,
        template_id=tpl.template_code if tpl else body.template_code,
        process_id=body.process_id or (tpl.process_id if tpl else None),
        process_name=body.process_name or (tpl.process_name if tpl else None),
        customer_code=body.customer_code,
        shift=body.shift,
        inspected_qty=inspected_qty,
        scan_barcode=body.scan_barcode,
        mo_lot=body.batch_no,
        is_reinspection=1 if entry == IPQC_ENTRY_REINSPECT else 0,
        ipqc_entry_type=entry,
        created_at=now,
    )
    db.add(row)
    db.flush()
    if body.item_results:
        _save_item_results(db, row.id, body.item_results)
    elif tpl and entry != IPQC_ENTRY_SUBMIT:
        # 选了模板但未传明细时，带出模板项目为 pending
        tpl_full = (
            db.query(IpqcTemplate)
            .options(joinedload(IpqcTemplate.items).joinedload(IpqcTemplateItem.test_item))
            .filter(IpqcTemplate.id == tpl.id)
            .first()
        )
        auto_items: list[IpqcItemResultIn] = []
        for link in tpl_full.items if tpl_full else []:
            ti = link.test_item
            if not ti:
                continue
            auto_items.append(
                IpqcItemResultIn(
                    test_item_id=ti.id,
                    item_code=ti.item_code,
                    item_name=ti.item_name,
                    standard_value=ti.standard_value,
                    actual_value=None,
                    result="pending",
                    remark=None,
                    sort_order=link.sort_order,
                )
            )
        if auto_items:
            _save_item_results(db, row.id, auto_items)

    record_audit(
        db,
        username=current_user.username,
        action="create",
        resource="ipqc_record",
        resource_id=row.inspection_no,
        detail={"entry_type": entry},
    )
    db.commit()
    db.refresh(row)
    return _detail_resp(db, row)


@router.get(
    "/records/{record_id}",
    response_model=IpqcRecordDetailResponse,
    summary="IPQC 记录详情",
    description="返回检验记录主表 + 项目明细；对应菜单「IPQC详情」。",
)
def get_ipqc_record(
    record_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    row = db.query(QualityInspectionRecord).filter(QualityInspectionRecord.id == record_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="检验记录不存在")
    return _detail_resp(db, row)


@router.post(
    "/records/{record_id}/generate-items",
    response_model=IpqcRecordDetailResponse,
    summary="按模板生成检验明细",
    description="当记录尚无项目明细时，按关联模板（或工序目录）生成明细行。",
)
def generate_ipqc_record_items(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(QUALITY_WRITE)),
):
    row = db.query(QualityInspectionRecord).filter(QualityInspectionRecord.id == record_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="检验记录不存在")
    exists = (
        db.query(QualityInspectionItemResult)
        .filter(QualityInspectionItemResult.record_id == record_id)
        .first()
    )
    if exists:
        raise HTTPException(status_code=400, detail="该记录已有检验明细，请直接修改")

    tpl = _resolve_template(db, None, row.template_id)
    auto_items: list[IpqcItemResultIn] = []
    if tpl:
        tpl_full = (
            db.query(IpqcTemplate)
            .options(joinedload(IpqcTemplate.items).joinedload(IpqcTemplateItem.test_item))
            .filter(IpqcTemplate.id == tpl.id)
            .first()
        )
        for link in tpl_full.items if tpl_full else []:
            ti = link.test_item
            if not ti:
                continue
            auto_items.append(
                IpqcItemResultIn(
                    test_item_id=ti.id,
                    item_code=ti.item_code,
                    item_name=ti.item_name,
                    standard_value=ti.standard_value,
                    actual_value=None,
                    result="pending",
                    sort_order=link.sort_order,
                )
            )
    if not auto_items:
        raise HTTPException(status_code=400, detail="无法匹配模板项目，请先维护模板关联")

    _save_item_results(db, row.id, auto_items)
    record_audit(
        db,
        username=current_user.username,
        action="generate_items",
        resource="ipqc_record",
        resource_id=row.inspection_no,
    )
    db.commit()
    db.refresh(row)
    return _detail_resp(db, row)


@router.post(
    "/enrich",
    summary="完善 IPQC 主数据与导入明细",
    description="可重复执行：补项目目录、模板关联、工序名回填、为无明细的导入记录生成项目结果。",
)
def enrich_ipqc(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(QUALITY_WRITE)),
):
    seed_ipqc_from_inspection_records(db)
    result = enrich_ipqc_data(db, include_item_results=True)
    record_audit(
        db,
        username=current_user.username,
        action="enrich",
        resource="ipqc",
        detail=result,
        commit=True,
    )
    return {"ok": True, **result}


@router.patch(
    "/records/{record_id}",
    response_model=IpqcRecordDetailResponse,
    summary="IPQC 记录修改",
    description=(
        "修改检验记录主表字段；可整体替换项目明细。对应菜单「IPQC记录修改」。"
        "导入记录（含 source_cid）的判定结果/状态仅管理员可改，普通品质写权限仅可改备注与明细。"
    ),
)
def update_ipqc_record(
    record_id: int,
    body: IpqcRecordUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(QUALITY_WRITE)),
):
    row = db.query(QualityInspectionRecord).filter(QualityInspectionRecord.id == record_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="检验记录不存在")

    data = body.model_dump(exclude_unset=True)
    items_in = data.pop("item_results", None)
    is_imported = bool(row.source_cid) or row.ipqc_entry_type == IPQC_ENTRY_IMPORT
    is_admin = (current_user.role or "").lower() == "admin"
    protected = {
        "inspection_result",
        "status",
        "source_cid",
        "inspection_no",
        "template_id",
        "process_id",
    }
    if is_imported and not is_admin:
        blocked = sorted(set(data.keys()) & protected)
        if blocked:
            raise HTTPException(
                status_code=403,
                detail=f"导入记录禁止修改关键字段：{', '.join(blocked)}（仅管理员可改）",
            )

    for k, v in data.items():
        setattr(row, k, v)

    if "inspection_result" in data and data["inspection_result"]:
        result = data["inspection_result"]
        if result == "pending":
            row.status = TASK_STATUS_PENDING
        else:
            row.status = RESULT_TO_STATUS.get(result, row.status)
            if result == "fail":
                row.non_conforming_qty = row.inspected_qty or row.non_conforming_qty or 0
            elif result == "pass":
                row.non_conforming_qty = 0

    if items_in is not None:
        _save_item_results(db, row.id, body.item_results or [])
        # 导入记录不因明细自动改写主表判定，避免篡改导入合格率
        if (
            not is_imported
            and body.item_results
            and any(i.result == "fail" for i in body.item_results)
        ):
            row.inspection_result = "fail"
            row.status = RESULT_TO_STATUS["fail"]

    record_audit(
        db,
        username=current_user.username,
        action="update",
        resource="ipqc_record",
        resource_id=row.inspection_no,
    )
    db.commit()
    db.refresh(row)
    return _detail_resp(db, row)

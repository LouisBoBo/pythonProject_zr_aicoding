from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.auth import get_current_user
from app.database import get_db
from app.models import (
    Device,
    DeviceType,
    InspectionPlan,
    InspectionPlanItem,
    InspectionRecord,
    InspectionRecordItem,
    User,
)
from app.schemas import (
    InspectionDashboardStats,
    InspectionAbnormalBrief,
    InspectionPlanCreate,
    InspectionPlanListResponse,
    InspectionPlanResponse,
    InspectionPlanUpdate,
    InspectionRecordCreate,
    InspectionRecordListResponse,
    InspectionRecordResponse,
    InspectionRecordUpdate,
    InspectionTrendPoint,
    InspectionTypeRate,
)

router = APIRouter(prefix="/api/inspection", tags=["inspection"])


def _plan_to_response(plan: InspectionPlan) -> InspectionPlanResponse:
    last_record = (
        plan.records[0]
        if plan.records
        else None
    )
    return InspectionPlanResponse(
        id=plan.id,
        name=plan.name,
        device_type_id=plan.device_type_id,
        device_id=plan.device_id,
        device_type_name=plan.device_type.name if plan.device_type else None,
        device_name=plan.device.name if plan.device else None,
        frequency_type=plan.frequency_type,
        frequency_value=plan.frequency_value,
        cron_expr=plan.cron_expr,
        is_active=plan.is_active,
        last_executed_at=last_record.created_at if last_record else None,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
        items=plan.items,
    )


def _record_to_response(record: InspectionRecord) -> InspectionRecordResponse:
    return InspectionRecordResponse(
        id=record.id,
        device_id=record.device_id,
        device_code=record.device.code if record.device else None,
        device_name=record.device.name if record.device else None,
        plan_id=record.plan_id,
        plan_name=record.plan.name if record.plan else None,
        inspector=record.inspector,
        inspect_date=record.inspect_date,
        status=record.status,
        remark=record.remark,
        created_at=record.created_at,
        items=record.items,
    )


def _get_plan_or_404(plan_id: int, db: Session) -> InspectionPlan:
    plan = (
        db.query(InspectionPlan)
        .options(
            joinedload(InspectionPlan.items),
            joinedload(InspectionPlan.device_type),
            joinedload(InspectionPlan.device),
        )
        .filter(InspectionPlan.id == plan_id)
        .first()
    )
    if not plan:
        raise HTTPException(status_code=404, detail="点检计划不存在")
    return plan


def _get_record_or_404(record_id: int, db: Session) -> InspectionRecord:
    record = (
        db.query(InspectionRecord)
        .options(
            joinedload(InspectionRecord.items),
            joinedload(InspectionRecord.device),
            joinedload(InspectionRecord.plan),
        )
        .filter(InspectionRecord.id == record_id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="点检记录不存在")
    return record


def _validate_device(device_id: int, db: Session) -> Device:
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=400, detail="设备不存在")
    return device


def _compute_record_status(items: list, explicit_status: str | None) -> str:
    if explicit_status == "draft":
        return "draft"
    if not items:
        return "incomplete"
    has_ng = any(item.result == "NG" for item in items if item.result)
    if has_ng:
        return "abnormal"
    all_filled = all(item.result or item.actual_value for item in items)
    if not all_filled:
        return "incomplete"
    return "normal"


# --- Plans ---


@router.get("/plans", response_model=InspectionPlanListResponse)
def list_plans(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    name: str | None = Query(None),
    is_active: bool | None = Query(None),
    device_type_id: int | None = Query(None),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(InspectionPlan).options(
        joinedload(InspectionPlan.items),
        joinedload(InspectionPlan.device_type),
        joinedload(InspectionPlan.device),
        joinedload(InspectionPlan.records),
    )
    if name:
        query = query.filter(InspectionPlan.name.ilike(f"%{name}%"))
    if is_active is not None:
        query = query.filter(InspectionPlan.is_active == is_active)
    if device_type_id:
        query = query.filter(InspectionPlan.device_type_id == device_type_id)
    query = query.order_by(InspectionPlan.updated_at.desc())
    total = query.count()
    plans = query.offset((page - 1) * page_size).limit(page_size).all()
    return InspectionPlanListResponse(
        items=[_plan_to_response(p) for p in plans],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/plans", response_model=InspectionPlanResponse, status_code=201)
def create_plan(
    payload: InspectionPlanCreate,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.device_id:
        _validate_device(payload.device_id, db)
    plan = InspectionPlan(
        name=payload.name,
        device_type_id=payload.device_type_id,
        device_id=payload.device_id,
        frequency_type=payload.frequency_type,
        frequency_value=payload.frequency_value,
        cron_expr=payload.cron_expr,
        is_active=payload.is_active,
    )
    for idx, item in enumerate(payload.items):
        plan.items.append(
            InspectionPlanItem(
                item_name=item.item_name,
                standard_value=item.standard_value,
                judge_type=item.judge_type,
                sort_order=item.sort_order or idx,
            )
        )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return _get_plan_or_404(plan.id, db)


@router.put("/plans/{plan_id}", response_model=InspectionPlanResponse)
def update_plan(
    plan_id: int,
    payload: InspectionPlanUpdate,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = _get_plan_or_404(plan_id, db)
    if payload.device_id:
        _validate_device(payload.device_id, db)
    update_data = payload.model_dump(exclude_unset=True, exclude={"items"})
    for key, value in update_data.items():
        setattr(plan, key, value)
    if payload.items is not None:
        plan.items.clear()
        for idx, item in enumerate(payload.items):
            plan.items.append(
                InspectionPlanItem(
                    item_name=item.item_name,
                    standard_value=item.standard_value,
                    judge_type=item.judge_type,
                    sort_order=item.sort_order or idx,
                )
            )
    plan.updated_at = datetime.utcnow()
    db.commit()
    return _get_plan_or_404(plan_id, db)


@router.patch("/plans/{plan_id}/toggle", response_model=InspectionPlanResponse)
def toggle_plan(
    plan_id: int,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = _get_plan_or_404(plan_id, db)
    plan.is_active = not plan.is_active
    plan.updated_at = datetime.utcnow()
    db.commit()
    return _get_plan_or_404(plan_id, db)


@router.delete("/plans/{plan_id}", status_code=204)
def delete_plan(
    plan_id: int,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = _get_plan_or_404(plan_id, db)
    db.delete(plan)
    db.commit()


# --- Records ---


@router.get("/records", response_model=InspectionRecordListResponse)
def list_records(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: str | None = Query(None),
    status: str | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    device_id: int | None = Query(None),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = (
        db.query(InspectionRecord)
        .join(Device)
        .options(
            joinedload(InspectionRecord.items),
            joinedload(InspectionRecord.device),
            joinedload(InspectionRecord.plan),
        )
    )
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            (Device.code.ilike(pattern))
            | (Device.name.ilike(pattern))
            | (InspectionRecord.inspector.ilike(pattern))
        )
    if status:
        query = query.filter(InspectionRecord.status == status)
    if date_from:
        query = query.filter(InspectionRecord.inspect_date >= date_from)
    if date_to:
        query = query.filter(InspectionRecord.inspect_date <= date_to)
    if device_id:
        query = query.filter(InspectionRecord.device_id == device_id)
    query = query.order_by(InspectionRecord.inspect_date.desc(), InspectionRecord.id.desc())
    total = query.count()
    records = query.offset((page - 1) * page_size).limit(page_size).all()
    return InspectionRecordListResponse(
        items=[_record_to_response(r) for r in records],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/records", response_model=InspectionRecordResponse, status_code=201)
def create_record(
    payload: InspectionRecordCreate,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _validate_device(payload.device_id, db)
    record = InspectionRecord(
        device_id=payload.device_id,
        plan_id=payload.plan_id,
        inspector=payload.inspector,
        inspect_date=payload.inspect_date,
        remark=payload.remark,
    )
    for item in payload.items:
        record.items.append(
            InspectionRecordItem(
                item_name=item.item_name,
                standard_value=item.standard_value,
                actual_value=item.actual_value,
                result=item.result,
                remark=item.remark,
            )
        )
    record.status = _compute_record_status(record.items, payload.status)
    db.add(record)
    db.commit()
    return _get_record_or_404(record.id, db)


@router.get("/records/{record_id}", response_model=InspectionRecordResponse)
def get_record(
    record_id: int,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _record_to_response(_get_record_or_404(record_id, db))


@router.put("/records/{record_id}", response_model=InspectionRecordResponse)
def update_record(
    record_id: int,
    payload: InspectionRecordUpdate,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = _get_record_or_404(record_id, db)
    if record.status not in ("draft", "incomplete"):
        raise HTTPException(status_code=400, detail="仅未审核或草稿状态的记录可编辑")
    if payload.device_id:
        _validate_device(payload.device_id, db)
        record.device_id = payload.device_id
    if payload.plan_id is not None:
        record.plan_id = payload.plan_id
    if payload.inspector:
        record.inspector = payload.inspector
    if payload.inspect_date:
        record.inspect_date = payload.inspect_date
    if payload.remark is not None:
        record.remark = payload.remark
    if payload.items is not None:
        record.items.clear()
        for item in payload.items:
            record.items.append(
                InspectionRecordItem(
                    item_name=item.item_name,
                    standard_value=item.standard_value,
                    actual_value=item.actual_value,
                    result=item.result,
                    remark=item.remark,
                )
            )
    if payload.status:
        record.status = _compute_record_status(record.items, payload.status)
    elif payload.items is not None:
        record.status = _compute_record_status(record.items, None)
    db.commit()
    return _get_record_or_404(record_id, db)


# --- Dashboard ---


@router.get("/dashboard/stats", response_model=InspectionDashboardStats)
def dashboard_stats(
    days: int = Query(7, ge=7, le=30),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    today = date.today()
    active_devices = db.query(Device).filter(Device.status == "active").count()
    today_due = active_devices

    today_records = (
        db.query(InspectionRecord)
        .filter(InspectionRecord.inspect_date == today)
        .filter(InspectionRecord.status.in_(["normal", "abnormal"]))
        .all()
    )
    today_completed = len(today_records)
    today_abnormal = sum(1 for r in today_records if r.status == "abnormal")
    completion_rate = round(today_completed / today_due * 100, 1) if today_due else 0.0

    trend: list[InspectionTrendPoint] = []
    for i in range(days - 1, -1, -1):
        d = today - timedelta(days=i)
        completed = (
            db.query(InspectionRecord)
            .filter(InspectionRecord.inspect_date == d)
            .filter(InspectionRecord.status.in_(["normal", "abnormal"]))
            .count()
        )
        rate = round(completed / today_due * 100, 1) if today_due else 0.0
        trend.append(InspectionTrendPoint(date=d.isoformat(), rate=rate))

    type_rates: list[InspectionTypeRate] = []
    device_types = db.query(DeviceType).all()
    for dt in device_types:
        device_ids = [d.id for d in dt.devices if d.status == "active"]
        total = len(device_ids)
        if total == 0:
            continue
        completed = (
            db.query(func.count(func.distinct(InspectionRecord.device_id)))
            .filter(InspectionRecord.device_id.in_(device_ids))
            .filter(InspectionRecord.inspect_date >= today - timedelta(days=30))
            .filter(InspectionRecord.status.in_(["normal", "abnormal"]))
            .scalar()
        ) or 0
        rate = round(completed / total * 100, 1) if total else 0.0
        type_rates.append(
            InspectionTypeRate(
                device_type=dt.name,
                rate=rate,
                total=total,
                completed=completed,
            )
        )

    abnormal_records = (
        db.query(InspectionRecord)
        .join(Device)
        .options(joinedload(InspectionRecord.device))
        .filter(InspectionRecord.status == "abnormal")
        .order_by(InspectionRecord.inspect_date.desc(), InspectionRecord.id.desc())
        .limit(5)
        .all()
    )
    recent_abnormals = [
        InspectionAbnormalBrief(
            id=r.id,
            device_code=r.device.code,
            device_name=r.device.name,
            inspect_date=r.inspect_date,
            inspector=r.inspector,
            remark=r.remark,
        )
        for r in abnormal_records
    ]

    return InspectionDashboardStats(
        today_due=today_due,
        today_completed=today_completed,
        today_abnormal=today_abnormal,
        completion_rate=completion_rate,
        trend=trend,
        type_rates=type_rates,
        recent_abnormals=recent_abnormals,
    )


@router.get("/plan-items/by-device/{device_id}")
def get_plan_items_for_device(
    device_id: int,
    plan_id: int | None = Query(None),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    device = _validate_device(device_id, db)
    plan = None
    if plan_id:
        plan = _get_plan_or_404(plan_id, db)
    else:
        plan = (
            db.query(InspectionPlan)
            .options(joinedload(InspectionPlan.items))
            .filter(InspectionPlan.is_active.is_(True))
            .filter(
                (InspectionPlan.device_id == device_id)
                | (
                    (InspectionPlan.device_type_id == device.device_type_id)
                    & (InspectionPlan.device_id.is_(None))
                )
            )
            .first()
        )
    if not plan:
        return {"items": [], "plan_id": None, "plan_name": None}
    return {
        "items": [
            {
                "item_name": i.item_name,
                "standard_value": i.standard_value,
                "judge_type": i.judge_type,
                "sort_order": i.sort_order,
            }
            for i in plan.items
        ],
        "plan_id": plan.id,
        "plan_name": plan.name,
    }

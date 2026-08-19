from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import (
    Equipment,
    EquipmentMaintenanceOrder,
    EquipmentMaintenancePlan,
    User,
)
from app.schemas import (
    EquipmentMaintenanceOrderCreate,
    EquipmentMaintenanceOrderDispatch,
    EquipmentMaintenanceOrderExecute,
    EquipmentMaintenanceOrderListResponse,
    EquipmentMaintenanceOrderResponse,
    EquipmentMaintenanceOrderUpdate,
    EquipmentMaintenancePlanCreate,
    EquipmentMaintenancePlanListResponse,
    EquipmentMaintenancePlanResponse,
    EquipmentMaintenancePlanUpdate,
    EquipmentMaintenanceStatusResponse,
    MaintenanceAlertItem,
    MaintenanceAlertsResponse,
)

router = APIRouter(prefix="/api/equipment-maintenance", tags=["equipment-maintenance"])

DUE_SOON_DAYS = 3

VALID_ORDER_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"in_progress", "closed"},
    "in_progress": {"completed", "closed"},
    "completed": set(),
    "closed": set(),
}


def _calc_next_due(from_dt: datetime, cycle_type: str, cycle_value: int) -> datetime:
    if cycle_type == "day":
        return from_dt + timedelta(days=cycle_value)
    if cycle_type == "week":
        return from_dt + timedelta(weeks=cycle_value)
    if cycle_type == "month":
        return from_dt + timedelta(days=30 * cycle_value)
    return from_dt + timedelta(days=cycle_value)


def _alert_level_for_due(due_at: datetime | None, *, active: bool = True) -> str | None:
    if not active or due_at is None:
        return None
    now = datetime.utcnow()
    if due_at.date() < now.date():
        return "overdue"
    if due_at.date() <= (now + timedelta(days=DUE_SOON_DAYS)).date():
        return "due_soon"
    return "normal"


def _plan_complete_date_from_plan(plan: EquipmentMaintenancePlan | None) -> date | None:
    if plan and plan.next_due_at:
        return plan.next_due_at.date()
    return None


def _resolve_plan_complete_date(
    *,
    explicit: date | None,
    plan: EquipmentMaintenancePlan | None,
) -> date | None:
    if explicit is not None:
        return explicit
    return _plan_complete_date_from_plan(plan)


def _generate_order_no(db: Session) -> str:
    prefix = f"MO-{datetime.utcnow().strftime('%Y%m%d')}-"
    count = (
        db.query(EquipmentMaintenanceOrder)
        .filter(EquipmentMaintenanceOrder.order_no.like(f"{prefix}%"))
        .count()
    )
    return f"{prefix}{count + 1:04d}"


def _get_plan_or_404(plan_id: int, db: Session) -> EquipmentMaintenancePlan:
    plan = (
        db.query(EquipmentMaintenancePlan)
        .filter(EquipmentMaintenancePlan.id == plan_id)
        .first()
    )
    if not plan:
        raise HTTPException(status_code=404, detail="保养计划不存在")
    return plan


def _get_order_or_404(order_id: int, db: Session) -> EquipmentMaintenanceOrder:
    order = (
        db.query(EquipmentMaintenanceOrder)
        .filter(EquipmentMaintenanceOrder.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="保养工单不存在")
    return order


def _get_equipment_or_404(equipment_id: int, db: Session) -> Equipment:
    equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not equipment:
        raise HTTPException(status_code=404, detail="设备不存在")
    return equipment


def _plan_to_response(plan: EquipmentMaintenancePlan) -> EquipmentMaintenancePlanResponse:
    equipment = plan.equipment
    active = plan.status == "enabled"
    alert = _alert_level_for_due(plan.next_due_at, active=active)
    return EquipmentMaintenancePlanResponse(
        id=plan.id,
        equipment_id=plan.equipment_id,
        equipment_code=equipment.equipment_code if equipment else None,
        equipment_name=equipment.name if equipment else None,
        name=plan.name,
        cycle_type=plan.cycle_type,
        cycle_value=plan.cycle_value,
        items=plan.items or [],
        status=plan.status,
        next_due_at=plan.next_due_at,
        alert_level=alert,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
    )


def _order_to_response(order: EquipmentMaintenanceOrder) -> EquipmentMaintenanceOrderResponse:
    equipment = order.equipment
    plan = order.plan
    alert = None
    if order.status in ("pending", "in_progress"):
        alert = _alert_level_for_due(order.planned_start_at)
    return EquipmentMaintenanceOrderResponse(
        id=order.id,
        plan_id=order.plan_id,
        plan_name=plan.name if plan else None,
        equipment_id=order.equipment_id,
        equipment_code=equipment.equipment_code if equipment else None,
        equipment_name=equipment.name if equipment else None,
        order_no=order.order_no,
        status=order.status,
        assignee=order.assignee,
        planned_start_at=order.planned_start_at,
        plan_complete_date=order.plan_complete_date,
        actual_start_at=order.actual_start_at,
        actual_end_at=order.actual_end_at,
        executor=order.executor,
        results=order.results,
        remark=order.remark,
        alert_level=alert,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


# --- Plans ---


@router.get("/plans", response_model=EquipmentMaintenancePlanListResponse)
def list_plans(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: str | None = Query(None),
    status: str | None = Query(None),
    equipment_id: int | None = Query(None),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(EquipmentMaintenancePlan)
    if search:
        pattern = f"%{search}%"
        query = query.join(Equipment).filter(
            (EquipmentMaintenancePlan.name.ilike(pattern))
            | (Equipment.name.ilike(pattern))
            | (Equipment.equipment_code.ilike(pattern))
        )
    if status:
        query = query.filter(EquipmentMaintenancePlan.status == status)
    if equipment_id:
        query = query.filter(EquipmentMaintenancePlan.equipment_id == equipment_id)
    query = query.order_by(EquipmentMaintenancePlan.updated_at.desc())
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return EquipmentMaintenancePlanListResponse(
        items=[_plan_to_response(p) for p in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/plans/{plan_id}", response_model=EquipmentMaintenancePlanResponse)
def get_plan(
    plan_id: int,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _plan_to_response(_get_plan_or_404(plan_id, db))


@router.post("/plans", response_model=EquipmentMaintenancePlanResponse, status_code=201)
def create_plan(
    payload: EquipmentMaintenancePlanCreate,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_equipment_or_404(payload.equipment_id, db)
    now = datetime.utcnow()
    plan = EquipmentMaintenancePlan(
        equipment_id=payload.equipment_id,
        name=payload.name,
        cycle_type=payload.cycle_type,
        cycle_value=payload.cycle_value,
        items=[item.model_dump() for item in payload.items],
        status=payload.status,
        next_due_at=_calc_next_due(now, payload.cycle_type, payload.cycle_value),
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return _plan_to_response(plan)


@router.put("/plans/{plan_id}", response_model=EquipmentMaintenancePlanResponse)
def update_plan(
    plan_id: int,
    payload: EquipmentMaintenancePlanUpdate,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = _get_plan_or_404(plan_id, db)
    data = payload.model_dump(exclude_unset=True)
    if "equipment_id" in data:
        _get_equipment_or_404(data["equipment_id"], db)
    if "items" in data and data["items"] is not None:
        data["items"] = [item.model_dump() if hasattr(item, "model_dump") else item for item in data["items"]]
    for field, value in data.items():
        setattr(plan, field, value)
    if any(k in data for k in ("cycle_type", "cycle_value", "status")) and plan.status == "enabled":
        base = plan.next_due_at or datetime.utcnow()
        plan.next_due_at = _calc_next_due(base, plan.cycle_type, plan.cycle_value)
    plan.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(plan)
    return _plan_to_response(plan)


@router.delete("/plans/{plan_id}", status_code=204)
def delete_plan(
    plan_id: int,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = _get_plan_or_404(plan_id, db)
    db.delete(plan)
    db.commit()


# --- Orders ---


@router.get("/orders", response_model=EquipmentMaintenanceOrderListResponse)
def list_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: str | None = Query(None),
    status: str | None = Query(None),
    equipment_id: int | None = Query(None),
    plan_id: int | None = Query(None),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(EquipmentMaintenanceOrder)
    if search:
        pattern = f"%{search}%"
        query = query.join(Equipment).filter(
            (EquipmentMaintenanceOrder.order_no.ilike(pattern))
            | (Equipment.name.ilike(pattern))
            | (Equipment.equipment_code.ilike(pattern))
        )
    if status:
        query = query.filter(EquipmentMaintenanceOrder.status == status)
    if equipment_id:
        query = query.filter(EquipmentMaintenanceOrder.equipment_id == equipment_id)
    if plan_id:
        query = query.filter(EquipmentMaintenanceOrder.plan_id == plan_id)
    query = query.order_by(EquipmentMaintenanceOrder.planned_start_at.asc())
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return EquipmentMaintenanceOrderListResponse(
        items=[_order_to_response(o) for o in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/orders/{order_id}", response_model=EquipmentMaintenanceOrderResponse)
def get_order(
    order_id: int,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _order_to_response(_get_order_or_404(order_id, db))


@router.post("/orders", response_model=EquipmentMaintenanceOrderResponse, status_code=201)
def create_order(
    payload: EquipmentMaintenanceOrderCreate,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_equipment_or_404(payload.equipment_id, db)
    plan = None
    if payload.plan_id:
        plan = _get_plan_or_404(payload.plan_id, db)
    plan_complete_date = _resolve_plan_complete_date(
        explicit=payload.plan_complete_date,
        plan=plan,
    )
    order = EquipmentMaintenanceOrder(
        plan_id=payload.plan_id,
        equipment_id=payload.equipment_id,
        order_no=_generate_order_no(db),
        status="pending",
        assignee=payload.assignee,
        planned_start_at=payload.planned_start_at,
        plan_complete_date=plan_complete_date,
        remark=payload.remark,
    )
    db.add(order)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="工单号冲突，请重试") from None
    db.refresh(order)
    return _order_to_response(order)


@router.post(
    "/orders/generate-from-plan/{plan_id}",
    response_model=EquipmentMaintenanceOrderResponse,
    status_code=201,
)
def generate_order_from_plan(
    plan_id: int,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = _get_plan_or_404(plan_id, db)
    if plan.status != "enabled":
        raise HTTPException(status_code=400, detail="计划已停用，无法生成工单")

    existing = (
        db.query(EquipmentMaintenanceOrder)
        .filter(
            EquipmentMaintenanceOrder.plan_id == plan_id,
            EquipmentMaintenanceOrder.status.in_(("pending", "in_progress")),
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="该计划已有未完成的保养工单")

    planned_start = plan.next_due_at or datetime.utcnow()
    order = EquipmentMaintenanceOrder(
        plan_id=plan.id,
        equipment_id=plan.equipment_id,
        order_no=_generate_order_no(db),
        status="pending",
        planned_start_at=planned_start,
        plan_complete_date=_plan_complete_date_from_plan(plan),
    )
    db.add(order)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="工单号冲突，请重试") from None
    db.refresh(order)
    return _order_to_response(order)


@router.put("/orders/{order_id}", response_model=EquipmentMaintenanceOrderResponse)
def update_order(
    order_id: int,
    payload: EquipmentMaintenanceOrderUpdate,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order = _get_order_or_404(order_id, db)
    data = payload.model_dump(exclude_unset=True)
    if "equipment_id" in data:
        _get_equipment_or_404(data["equipment_id"], db)
    if "plan_id" in data and data["plan_id"]:
        _get_plan_or_404(data["plan_id"], db)
    if "plan_id" in data and data["plan_id"] and "plan_complete_date" not in data:
        plan = _get_plan_or_404(data["plan_id"], db)
        if order.plan_complete_date is None:
            data["plan_complete_date"] = _plan_complete_date_from_plan(plan)
    if "status" in data and data["status"] != order.status:
        allowed = VALID_ORDER_TRANSITIONS.get(order.status, set())
        if data["status"] not in allowed:
            raise HTTPException(status_code=400, detail="不允许的状态变更")
    for field, value in data.items():
        setattr(order, field, value)
    order.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(order)
    return _order_to_response(order)


@router.delete("/orders/{order_id}", status_code=204)
def delete_order(
    order_id: int,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order = _get_order_or_404(order_id, db)
    if order.status in ("in_progress", "completed"):
        raise HTTPException(status_code=400, detail="执行中或已完成的工单不可删除")
    db.delete(order)
    db.commit()


@router.post("/orders/{order_id}/dispatch", response_model=EquipmentMaintenanceOrderResponse)
def dispatch_order(
    order_id: int,
    payload: EquipmentMaintenanceOrderDispatch,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order = _get_order_or_404(order_id, db)
    if order.status not in ("pending",):
        raise HTTPException(status_code=400, detail="仅待执行工单可派工")
    order.assignee = payload.assignee
    if payload.planned_start_at:
        order.planned_start_at = payload.planned_start_at
    order.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(order)
    return _order_to_response(order)


@router.post("/orders/{order_id}/start", response_model=EquipmentMaintenanceOrderResponse)
def start_order(
    order_id: int,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order = _get_order_or_404(order_id, db)
    if order.status != "pending":
        raise HTTPException(status_code=400, detail="仅待执行工单可开始")
    order.status = "in_progress"
    order.actual_start_at = datetime.utcnow()
    order.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(order)
    return _order_to_response(order)


@router.post("/orders/{order_id}/execute", response_model=EquipmentMaintenanceOrderResponse)
def execute_order(
    order_id: int,
    payload: EquipmentMaintenanceOrderExecute,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order = _get_order_or_404(order_id, db)
    if order.status not in ("pending", "in_progress"):
        raise HTTPException(status_code=400, detail="当前状态不可提交执行记录")
    if order.status == "pending":
        order.actual_start_at = datetime.utcnow()
    order.status = "completed"
    order.executor = payload.executor
    order.results = [item.model_dump() for item in payload.results]
    order.remark = payload.remark
    order.actual_end_at = datetime.utcnow()
    order.updated_at = datetime.utcnow()

    if order.plan_id:
        plan = _get_plan_or_404(order.plan_id, db)
        plan.next_due_at = _calc_next_due(
            order.actual_end_at, plan.cycle_type, plan.cycle_value
        )
        plan.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(order)
    return _order_to_response(order)


# --- Alerts & Equipment Status ---


@router.get("/alerts", response_model=MaintenanceAlertsResponse)
def get_alerts(
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    now = datetime.utcnow()
    due_soon_end = now + timedelta(days=DUE_SOON_DAYS)
    due_soon: list[MaintenanceAlertItem] = []
    overdue: list[MaintenanceAlertItem] = []

    plans = (
        db.query(EquipmentMaintenancePlan)
        .filter(EquipmentMaintenancePlan.status == "enabled")
        .all()
    )
    for plan in plans:
        if not plan.next_due_at:
            continue
        item = MaintenanceAlertItem(
            id=plan.id,
            type="plan",
            name=plan.name,
            equipment_id=plan.equipment_id,
            equipment_code=plan.equipment.equipment_code if plan.equipment else None,
            equipment_name=plan.equipment.name if plan.equipment else None,
            due_at=plan.next_due_at,
            alert_level="",
        )
        if plan.next_due_at.date() < now.date():
            item.alert_level = "overdue"
            overdue.append(item)
        elif plan.next_due_at.date() <= due_soon_end.date():
            item.alert_level = "due_soon"
            due_soon.append(item)

    orders = (
        db.query(EquipmentMaintenanceOrder)
        .filter(EquipmentMaintenanceOrder.status.in_(("pending", "in_progress")))
        .all()
    )
    for order in orders:
        item = MaintenanceAlertItem(
            id=order.id,
            type="order",
            name=order.order_no,
            equipment_id=order.equipment_id,
            equipment_code=order.equipment.equipment_code if order.equipment else None,
            equipment_name=order.equipment.name if order.equipment else None,
            due_at=order.planned_start_at,
            alert_level="",
        )
        if order.planned_start_at.date() < now.date():
            item.alert_level = "overdue"
            overdue.append(item)
        elif order.planned_start_at.date() <= due_soon_end.date():
            item.alert_level = "due_soon"
            due_soon.append(item)

    return MaintenanceAlertsResponse(due_soon=due_soon, overdue=overdue)


@router.get(
    "/equipment/{equipment_id}/status",
    response_model=EquipmentMaintenanceStatusResponse,
)
def get_equipment_maintenance_status(
    equipment_id: int,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_equipment_or_404(equipment_id, db)
    plans = (
        db.query(EquipmentMaintenancePlan)
        .filter(
            EquipmentMaintenancePlan.equipment_id == equipment_id,
            EquipmentMaintenancePlan.status == "enabled",
        )
        .all()
    )
    pending_orders = (
        db.query(EquipmentMaintenanceOrder)
        .filter(
            EquipmentMaintenanceOrder.equipment_id == equipment_id,
            EquipmentMaintenanceOrder.status.in_(("pending", "in_progress")),
        )
        .all()
    )

    alert_level = "none"
    next_due_at = None
    for plan in plans:
        if plan.next_due_at and (next_due_at is None or plan.next_due_at < next_due_at):
            next_due_at = plan.next_due_at
        level = _alert_level_for_due(plan.next_due_at, active=True)
        if level == "overdue":
            alert_level = "overdue"
        elif level == "due_soon" and alert_level != "overdue":
            alert_level = "due_soon"

    for order in pending_orders:
        level = _alert_level_for_due(order.planned_start_at)
        if level == "overdue":
            alert_level = "overdue"
        elif level == "due_soon" and alert_level != "overdue":
            alert_level = "due_soon"

    if not plans and not pending_orders:
        status_label = "无保养计划"
    elif alert_level == "overdue":
        status_label = "保养超期"
    elif alert_level == "due_soon":
        status_label = "即将到期"
    else:
        status_label = "保养正常"

    return EquipmentMaintenanceStatusResponse(
        equipment_id=equipment_id,
        status_label=status_label,
        alert_level=alert_level,
        active_plans=len(plans),
        pending_orders=len(pending_orders),
        next_due_at=next_due_at,
    )

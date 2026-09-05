from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.material_outbound_store import MaterialOutbound
from app.models import (
    InventoryBalance,
    InventoryStock,
    InventoryTransaction,
    Material,
    User,
    Warehouse,
    WarehouseLocation,
    WorkOrder,
)
from app.schemas import (
    WorkOrderCreate,
    WorkOrderListResponse,
    WorkOrderResponse,
    WorkOrderStatusUpdate,
    WorkOrderUpdate,
)
from app.schemas_material_outbound import (
    MaterialOutboundCreate,
    MaterialOutboundListResponse,
    MaterialOutboundResponse,
    MaterialOutboundStockBalanceResponse,
)
from app.work_order_utils import derive_current_process, ensure_work_order_timestamps

router = APIRouter(prefix="/api/work-orders", tags=["work-orders"])

OUTBOUND_TYPE_PRODUCTION_PICK = "production_pick"
OUTBOUND_TYPE_LABEL = {OUTBOUND_TYPE_PRODUCTION_PICK: "生产领料出库"}


def _generate_outbound_no(db: Session) -> str:
    today = date.today()
    prefix = f"CK-{today:%Y%m%d}-"
    last = (
        db.query(MaterialOutbound)
        .filter(MaterialOutbound.outbound_no.like(f"{prefix}%"))
        .order_by(MaterialOutbound.outbound_no.desc())
        .first()
    )
    seq = 1
    if last:
        try:
            seq = int(last.outbound_no.split("-")[-1]) + 1
        except ValueError:
            seq = db.query(MaterialOutbound).count() + 1
    return f"{prefix}{seq:03d}"


def _query_available_quantity(
    db: Session,
    *,
    material_id: int,
    warehouse_id: int,
    location_id: int | None,
) -> int:
    if location_id:
        bal = (
            db.query(InventoryBalance)
            .filter(
                InventoryBalance.material_id == material_id,
                InventoryBalance.location_id == location_id,
            )
            .first()
        )
        return int(bal.quantity if bal else 0)

    loc_ids = [
        loc.id
        for loc in db.query(WarehouseLocation)
        .filter(WarehouseLocation.warehouse_id == warehouse_id)
        .all()
    ]
    if not loc_ids:
        stock = (
            db.query(InventoryStock)
            .filter(
                InventoryStock.material_id == material_id,
                InventoryStock.warehouse_id == warehouse_id,
            )
            .first()
        )
        return int(stock.quantity if stock else 0)

    total = (
        db.query(func.coalesce(func.sum(InventoryBalance.quantity), 0))
        .filter(
            InventoryBalance.material_id == material_id,
            InventoryBalance.location_id.in_(loc_ids),
        )
        .scalar()
    )
    return int(total or 0)


def _apply_outbound_to_inventory(
    db: Session,
    outbound: MaterialOutbound,
    *,
    txn_at: datetime | None = None,
) -> None:
    when = txn_at or datetime.combine(outbound.outbound_date, datetime.min.time()).replace(
        hour=14, minute=0, second=0
    )
    remaining = outbound.quantity

    if outbound.location_id:
        bal = (
            db.query(InventoryBalance)
            .filter(
                InventoryBalance.material_id == outbound.material_id,
                InventoryBalance.location_id == outbound.location_id,
            )
            .first()
        )
        if not bal or bal.quantity < outbound.quantity:
            available = int(bal.quantity if bal else 0)
            raise HTTPException(
                status_code=400,
                detail=f"库存不足：当前可用 {available} {outbound.unit}，出库 {outbound.quantity} {outbound.unit}",
            )
        bal.quantity -= outbound.quantity
        bal.updated_at = when
        remaining = 0
    else:
        loc_ids = [
            loc.id
            for loc in db.query(WarehouseLocation)
            .filter(WarehouseLocation.warehouse_id == outbound.warehouse_id)
            .order_by(WarehouseLocation.location_code)
            .all()
        ]
        for loc_id in loc_ids:
            if remaining <= 0:
                break
            bal = (
                db.query(InventoryBalance)
                .filter(
                    InventoryBalance.material_id == outbound.material_id,
                    InventoryBalance.location_id == loc_id,
                )
                .first()
            )
            if not bal or bal.quantity <= 0:
                continue
            deduct = min(bal.quantity, remaining)
            bal.quantity -= deduct
            bal.updated_at = when
            remaining -= deduct

        if remaining > 0:
            available = _query_available_quantity(
                db,
                material_id=outbound.material_id,
                warehouse_id=outbound.warehouse_id,
                location_id=None,
            )
            raise HTTPException(
                status_code=400,
                detail=f"库存不足：当前可用 {available} {outbound.unit}，出库 {outbound.quantity} {outbound.unit}",
            )

    db.add(
        InventoryTransaction(
            material_id=outbound.material_id,
            location_id=outbound.location_id,
            txn_type="out",
            quantity=outbound.quantity,
            txn_at=when,
            ref_no=outbound.outbound_no,
            remark=f"生产领料出库 {outbound.material_name}",
        )
    )

    stock = (
        db.query(InventoryStock)
        .filter(
            InventoryStock.material_id == outbound.material_id,
            InventoryStock.warehouse_id == outbound.warehouse_id,
        )
        .first()
    )
    if stock:
        stock.quantity = max(0, stock.quantity - outbound.quantity)
        stock.updated_at = when


VALID_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"in_progress", "cancelled"},
    "in_progress": {"completed", "cancelled"},
    "completed": {"closed"},
    "closed": set(),
    "cancelled": set(),
}


def _get_work_order_or_404(work_order_id: int, db: Session) -> WorkOrder:
    work_order = db.query(WorkOrder).filter(WorkOrder.id == work_order_id).first()
    if not work_order:
        raise HTTPException(status_code=404, detail="工单不存在")
    return work_order


@router.get("", response_model=WorkOrderListResponse)
def list_work_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    status: str | None = Query(None),
    priority: str | None = Query(None),
    production_line: str | None = Query(None),
    order_no: str | None = Query(None),
    product_name: str | None = Query(None),
    search: str | None = Query(None),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(WorkOrder)
    if status:
        query = query.filter(WorkOrder.status == status)
    if priority:
        query = query.filter(WorkOrder.priority == priority)
    if production_line:
        query = query.filter(WorkOrder.production_line.ilike(f"%{production_line}%"))
    if order_no:
        query = query.filter(WorkOrder.order_no.ilike(f"%{order_no}%"))
    if product_name:
        query = query.filter(WorkOrder.product_name.ilike(f"%{product_name}%"))
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            (WorkOrder.order_no.ilike(pattern))
            | (WorkOrder.product_name.ilike(pattern))
            | (WorkOrder.product_code.ilike(pattern))
        )
    query = query.order_by(WorkOrder.created_at.desc())
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return WorkOrderListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/material-outbound/stock-balance",
    response_model=MaterialOutboundStockBalanceResponse,
    summary="查询出库可用库存",
)
def get_material_outbound_stock_balance(
    material_id: int = Query(..., description="物料 ID"),
    warehouse_id: int = Query(..., description="仓库 ID"),
    location_id: int | None = Query(None, description="库位 ID（可选）"),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="物料不存在")
    warehouse = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
    if not warehouse:
        raise HTTPException(status_code=404, detail="仓库不存在")
    if location_id:
        loc = (
            db.query(WarehouseLocation)
            .filter(
                WarehouseLocation.id == location_id,
                WarehouseLocation.warehouse_id == warehouse_id,
            )
            .first()
        )
        if not loc:
            raise HTTPException(status_code=400, detail="库位不存在或不属于所选仓库")

    available = _query_available_quantity(
        db,
        material_id=material_id,
        warehouse_id=warehouse_id,
        location_id=location_id,
    )
    return MaterialOutboundStockBalanceResponse(
        material_id=material_id,
        warehouse_id=warehouse_id,
        location_id=location_id,
        available_quantity=available,
        unit=material.unit,
    )


@router.get(
    "/material-outbound",
    response_model=MaterialOutboundListResponse,
    summary="生产领料出库列表",
)
def list_material_outbound(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    outbound_no: str | None = Query(None, description="出库单号（模糊）"),
    material_code: str | None = Query(None, description="物料编码（模糊）"),
    material_name: str | None = Query(None, description="物料名称（模糊）"),
    batch_no: str | None = Query(None, description="批次号（模糊）"),
    receiver_department: str | None = Query(None, description="领用部门（模糊）"),
    status: str | None = Query(None, description="状态：pending/completed"),
    date_from: date | None = Query(None, description="出库日期起"),
    date_to: date | None = Query(None, description="出库日期止"),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(MaterialOutbound).filter(
        MaterialOutbound.outbound_type == OUTBOUND_TYPE_PRODUCTION_PICK
    )
    if outbound_no:
        query = query.filter(MaterialOutbound.outbound_no.ilike(f"%{outbound_no}%"))
    if material_code:
        query = query.filter(MaterialOutbound.material_code.ilike(f"%{material_code}%"))
    if material_name:
        query = query.filter(MaterialOutbound.material_name.ilike(f"%{material_name}%"))
    if batch_no:
        query = query.filter(MaterialOutbound.batch_no.ilike(f"%{batch_no}%"))
    if receiver_department:
        query = query.filter(MaterialOutbound.receiver_department.ilike(f"%{receiver_department}%"))
    if status:
        query = query.filter(MaterialOutbound.status == status)
    if date_from:
        query = query.filter(MaterialOutbound.outbound_date >= date_from)
    if date_to:
        query = query.filter(MaterialOutbound.outbound_date <= date_to)

    total = query.count()
    rows = (
        query.order_by(MaterialOutbound.outbound_date.desc(), MaterialOutbound.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return MaterialOutboundListResponse(
        items=[MaterialOutboundResponse.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/material-outbound",
    response_model=MaterialOutboundResponse,
    status_code=201,
    summary="新增生产领料出库",
)
def create_material_outbound(
    payload: MaterialOutboundCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.status not in ("pending", "completed"):
        raise HTTPException(status_code=400, detail="状态仅支持 pending（待出库）或 completed（已出库）")

    material = db.query(Material).filter(Material.id == payload.material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="物料不存在")

    warehouse = db.query(Warehouse).filter(Warehouse.id == payload.warehouse_id).first()
    if not warehouse:
        raise HTTPException(status_code=404, detail="仓库不存在")

    location_code = None
    if payload.location_id:
        loc = (
            db.query(WarehouseLocation)
            .filter(
                WarehouseLocation.id == payload.location_id,
                WarehouseLocation.warehouse_id == payload.warehouse_id,
            )
            .first()
        )
        if not loc:
            raise HTTPException(status_code=400, detail="库位不存在或不属于所选仓库")
        location_code = loc.location_code

    available = _query_available_quantity(
        db,
        material_id=material.id,
        warehouse_id=warehouse.id,
        location_id=payload.location_id,
    )
    if payload.status == "completed" and payload.quantity > available:
        raise HTTPException(
            status_code=400,
            detail=f"库存不足：当前可用 {available} {material.unit}，出库 {payload.quantity} {material.unit}",
        )

    outbound = MaterialOutbound(
        outbound_no=_generate_outbound_no(db),
        outbound_type=OUTBOUND_TYPE_PRODUCTION_PICK,
        material_id=material.id,
        material_code=material.material_code,
        material_name=material.material_name,
        spec=material.spec,
        batch_no=payload.batch_no,
        quantity=payload.quantity,
        unit=material.unit,
        warehouse_id=warehouse.id,
        warehouse_name=warehouse.name,
        location_id=payload.location_id,
        location_code=location_code,
        outbound_date=payload.outbound_date,
        picker=payload.picker or current_user.username,
        receiver_department=payload.receiver_department,
        remark=payload.remark,
        status=payload.status,
    )
    db.add(outbound)
    try:
        db.flush()
        if payload.status == "completed":
            _apply_outbound_to_inventory(db, outbound)
        db.commit()
        db.refresh(outbound)
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="出库单号冲突，请重试") from None

    return MaterialOutboundResponse.model_validate(outbound)


@router.get("/{work_order_id}", response_model=WorkOrderResponse)
def get_work_order(
    work_order_id: int,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _get_work_order_or_404(work_order_id, db)


@router.post("", response_model=WorkOrderResponse, status_code=201)
def create_work_order(
    payload: WorkOrderCreate,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing = db.query(WorkOrder).filter(WorkOrder.order_no == payload.order_no).first()
    if existing:
        raise HTTPException(status_code=409, detail="工单号已存在")

    work_order = WorkOrder(
        order_no=payload.order_no,
        product_name=payload.product_name,
        product_code=payload.product_code,
        production_line=payload.production_line,
        plan_quantity=payload.plan_quantity,
        priority=payload.priority,
        assignee=payload.assignee,
        start_date=payload.start_date,
        end_date=payload.end_date,
        remark=payload.remark,
    )
    db.add(work_order)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="工单号已存在") from None
    db.refresh(work_order)
    return work_order


@router.put("/{work_order_id}", response_model=WorkOrderResponse)
def update_work_order(
    work_order_id: int,
    payload: WorkOrderUpdate,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    work_order = _get_work_order_or_404(work_order_id, db)
    update_data = payload.model_dump(exclude_unset=True)

    if "order_no" in update_data and update_data["order_no"] != work_order.order_no:
        duplicate = (
            db.query(WorkOrder)
            .filter(WorkOrder.order_no == update_data["order_no"], WorkOrder.id != work_order_id)
            .first()
        )
        if duplicate:
            raise HTTPException(status_code=409, detail="工单号已存在")

    for field, value in update_data.items():
        setattr(work_order, field, value)
    if "actual_quantity" in update_data or "status" in update_data or "plan_quantity" in update_data:
        work_order.current_process = derive_current_process(
            work_order.status, work_order.plan_quantity, work_order.actual_quantity
        )
    ensure_work_order_timestamps(work_order)
    work_order.updated_at = datetime.utcnow()

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="工单号已存在") from None
    db.refresh(work_order)
    return work_order


@router.patch(
    "/{work_order_id}/status",
    response_model=WorkOrderResponse,
    summary="更新工单状态",
    description=(
        "待开工→进行中时若尚未有实际开始时间，则写入当前时间；"
        "进行中→已完成 / 已完成→已关闭时若尚未有实际结束时间，则写入当前时间。"
        "完工（completed）与关闭（closed）工单必须有实际结束时间。"
    ),
)
def update_work_order_status(
    work_order_id: int,
    payload: WorkOrderStatusUpdate,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    work_order = _get_work_order_or_404(work_order_id, db)
    allowed = VALID_STATUS_TRANSITIONS.get(work_order.status, set())
    if payload.status not in allowed:
        raise HTTPException(status_code=400, detail=f"无法从 {work_order.status} 流转到 {payload.status}")

    work_order.status = payload.status
    ensure_work_order_timestamps(work_order)
    work_order.current_process = derive_current_process(
        work_order.status, work_order.plan_quantity, work_order.actual_quantity
    )
    work_order.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(work_order)
    return work_order


@router.delete("/{work_order_id}", status_code=204)
def delete_work_order(
    work_order_id: int,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    work_order = _get_work_order_or_404(work_order_id, db)
    db.delete(work_order)
    db.commit()

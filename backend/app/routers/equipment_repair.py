from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Equipment, EquipmentRepair, EquipmentRepairPart, User
from app.schemas import (
    EquipmentRepairCreate,
    EquipmentRepairDetail,
    EquipmentRepairListItem,
    EquipmentRepairListResponse,
    EquipmentRepairPartCreate,
    EquipmentRepairPartResponse,
    EquipmentRepairUpdate,
)

router = APIRouter(prefix="/api/equipment-repairs", tags=["设备维修"])

VALID_REPAIR_STATUSES = {"pending", "in_progress", "completed", "closed"}
VALID_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"in_progress", "closed"},
    "in_progress": {"completed", "closed"},
    "completed": {"closed"},
    "closed": set(),
}


def _generate_repair_no(db: Session) -> str:
    prefix = f"RE-{datetime.utcnow().strftime('%Y%m%d')}-"
    count = (
        db.query(EquipmentRepair)
        .filter(EquipmentRepair.repair_no.like(f"{prefix}%"))
        .count()
    )
    return f"{prefix}{count + 1:04d}"


def _get_repair_or_404(repair_id: int, db: Session) -> EquipmentRepair:
    repair = (
        db.query(EquipmentRepair)
        .filter(EquipmentRepair.id == repair_id)
        .first()
    )
    if not repair:
        raise HTTPException(status_code=404, detail="维修工单不存在")
    return repair


def _get_equipment_or_404(equipment_id: int, db: Session) -> Equipment:
    equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not equipment:
        raise HTTPException(status_code=404, detail="设备不存在")
    return equipment


def _repair_to_list_item(repair: EquipmentRepair) -> EquipmentRepairListItem:
    equipment = repair.equipment
    return EquipmentRepairListItem(
        id=repair.id,
        repair_no=repair.repair_no,
        equipment_id=repair.equipment_id,
        equipment_code=equipment.equipment_code if equipment else None,
        equipment_name=equipment.name if equipment else None,
        fault_category=repair.fault_category,
        fault_description=repair.fault_description,
        urgency=repair.urgency,
        status=repair.status,
        reporter=repair.reporter,
        repair_person=repair.repair_person,
        completion_time=repair.completion_time,
        created_at=repair.created_at,
    )


def _repair_to_detail(repair: EquipmentRepair) -> EquipmentRepairDetail:
    equipment = repair.equipment
    parts = [
        EquipmentRepairPartResponse(
            id=p.id,
            repair_id=p.repair_id,
            part_name=p.part_name,
            part_spec=p.part_spec,
            quantity=p.quantity,
            unit=p.unit,
            unit_price=p.unit_price,
        )
        for p in (repair.parts or [])
    ]
    return EquipmentRepairDetail(
        id=repair.id,
        repair_no=repair.repair_no,
        equipment_id=repair.equipment_id,
        equipment_code=equipment.equipment_code if equipment else None,
        equipment_name=equipment.name if equipment else None,
        fault_category=repair.fault_category,
        fault_description=repair.fault_description,
        urgency=repair.urgency,
        status=repair.status,
        reporter=repair.reporter,
        repair_person=repair.repair_person,
        start_time=repair.start_time,
        completion_time=repair.completion_time,
        repair_description=repair.repair_description,
        images=repair.images,
        parts=parts,
        created_at=repair.created_at,
        updated_at=repair.updated_at,
    )


# --- List repairs ---

@router.get("", response_model=EquipmentRepairListResponse)
def list_repairs(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    keyword: str | None = Query(None),
    status: str | None = Query(None),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(EquipmentRepair)
    if keyword:
        pattern = f"%{keyword}%"
        query = query.join(Equipment).filter(
            (EquipmentRepair.repair_no.ilike(pattern))
            | (Equipment.name.ilike(pattern))
            | (Equipment.equipment_code.ilike(pattern))
            | (EquipmentRepair.fault_description.ilike(pattern))
        )
    if status:
        query = query.filter(EquipmentRepair.status == status)
    query = query.order_by(EquipmentRepair.created_at.desc())
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return EquipmentRepairListResponse(
        items=[_repair_to_list_item(r) for r in items],
        total=total,
        page=page,
        page_size=page_size,
    )


# --- Get repair detail ---

@router.get("/{repair_id}", response_model=EquipmentRepairDetail)
def get_repair(
    repair_id: int,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _repair_to_detail(_get_repair_or_404(repair_id, db))


# --- Get repair parts ---

@router.get("/{repair_id}/parts", response_model=list[EquipmentRepairPartResponse])
def get_repair_parts(
    repair_id: int,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repair = _get_repair_or_404(repair_id, db)
    return [
        EquipmentRepairPartResponse(
            id=p.id,
            repair_id=p.repair_id,
            part_name=p.part_name,
            part_spec=p.part_spec,
            quantity=p.quantity,
            unit=p.unit,
            unit_price=p.unit_price,
        )
        for p in (repair.parts or [])
    ]


# --- Create repair ---

@router.post("", response_model=EquipmentRepairDetail, status_code=201)
def create_repair(
    payload: EquipmentRepairCreate,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_equipment_or_404(payload.equipment_id, db)

    repair = EquipmentRepair(
        repair_no=_generate_repair_no(db),
        equipment_id=payload.equipment_id,
        fault_category=payload.fault_category,
        fault_description=payload.fault_description,
        urgency=payload.urgency,
        status="pending",
        reporter=payload.reporter,
        images=payload.images or [],
    )
    db.add(repair)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="工单号冲突，请重试") from None
    db.refresh(repair)
    return _repair_to_detail(repair)


# --- Update repair ---

@router.put("/{repair_id}", response_model=EquipmentRepairDetail)
def update_repair(
    repair_id: int,
    payload: EquipmentRepairUpdate,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repair = _get_repair_or_404(repair_id, db)
    data = payload.model_dump(exclude_unset=True)

    if "equipment_id" in data and data["equipment_id"] is not None:
        _get_equipment_or_404(data["equipment_id"], db)

    # status transition validation
    if "status" in data and data["status"] != repair.status:
        allowed = VALID_TRANSITIONS.get(repair.status, set())
        if data["status"] not in allowed:
            raise HTTPException(status_code=400, detail="不允许的状态变更")

    # handle parts separately
    parts_data = data.pop("parts", None)

    # auto-set start_time when moving to in_progress
    if data.get("status") == "in_progress" and repair.status == "pending":
        data["start_time"] = datetime.utcnow()
    # auto-set completion_time when moving to completed
    if data.get("status") == "completed":
        data["completion_time"] = datetime.utcnow()

    for field, value in data.items():
        setattr(repair, field, value)

    repair.updated_at = datetime.utcnow()

    if parts_data is not None:
        # replace all parts
        db.query(EquipmentRepairPart).filter(
            EquipmentRepairPart.repair_id == repair_id
        ).delete()
        for p in parts_data:
            part = EquipmentRepairPart(
                repair_id=repair_id,
                part_name=p["part_name"],
                part_spec=p.get("part_spec"),
                quantity=p.get("quantity", 1),
                unit=p.get("unit", "个"),
                unit_price=p.get("unit_price", 0),
            )
            db.add(part)

    db.commit()
    db.refresh(repair)
    return _repair_to_detail(repair)


# --- Delete repair ---

@router.delete("/{repair_id}", status_code=204)
def delete_repair(
    repair_id: int,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repair = _get_repair_or_404(repair_id, db)
    if repair.status in ("in_progress", "completed"):
        raise HTTPException(status_code=400, detail="执行中或已完成的维修工单不可删除")
    db.delete(repair)
    db.commit()

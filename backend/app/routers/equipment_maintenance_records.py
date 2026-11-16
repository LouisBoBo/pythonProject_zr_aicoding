from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Equipment, EquipmentMaintenanceRecord, User
from app.schemas import (
    EquipmentMaintenanceRecordCreate,
    EquipmentMaintenanceRecordListResponse,
    EquipmentMaintenanceRecordResponse,
    EquipmentMaintenanceRecordUpdate,
)

router = APIRouter(prefix="/api/equipment-maintenance-records", tags=["equipment-maintenance-records"])

VALID_MAINTENANCE_TYPES = {"routine", "periodic", "post_fault", "overhaul"}
VALID_RESULTS = {"qualified", "unqualified", "pending"}


def _generate_record_no(db: Session) -> str:
    prefix = f"MR-{datetime.utcnow().strftime('%Y%m%d')}-"
    count = (
        db.query(EquipmentMaintenanceRecord)
        .filter(EquipmentMaintenanceRecord.record_no.like(f"{prefix}%"))
        .count()
    )
    return f"{prefix}{count + 1:04d}"


def _get_record_or_404(record_id: int, db: Session) -> EquipmentMaintenanceRecord:
    record = (
        db.query(EquipmentMaintenanceRecord)
        .filter(EquipmentMaintenanceRecord.id == record_id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="保养记录不存在")
    return record


def _get_equipment_or_404(equipment_id: int, db: Session) -> Equipment:
    equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not equipment:
        raise HTTPException(status_code=404, detail="设备不存在")
    return equipment


def _to_response(record: EquipmentMaintenanceRecord) -> EquipmentMaintenanceRecordResponse:
    equipment = record.equipment
    return EquipmentMaintenanceRecordResponse(
        id=record.id,
        record_no=record.record_no,
        equipment_id=record.equipment_id,
        equipment_code=equipment.equipment_code if equipment else None,
        equipment_name=equipment.name if equipment else None,
        maintenance_type=record.maintenance_type,
        planned_date=record.planned_date,
        actual_date=record.actual_date,
        next_maintenance_date=record.next_maintenance_date,
        maintainer=record.maintainer,
        responsible_person=record.responsible_person,
        maintenance_content=record.maintenance_content,
        maintenance_result=record.maintenance_result,
        remark=record.remark,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.get("", response_model=EquipmentMaintenanceRecordListResponse)
def list_maintenance_records(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    keyword: str | None = Query(None, description="记录编号/设备编号/设备名称/保养人"),
    maintenance_type: str | None = Query(None),
    maintenance_result: str | None = Query(None),
    equipment_id: int | None = Query(None),
    date_from: str | None = Query(None, description="保养日期起 YYYY-MM-DD"),
    date_to: str | None = Query(None, description="保养日期止 YYYY-MM-DD"),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(EquipmentMaintenanceRecord)
    if keyword:
        pattern = f"%{keyword}%"
        query = query.join(Equipment).filter(
            (EquipmentMaintenanceRecord.record_no.ilike(pattern))
            | (Equipment.equipment_code.ilike(pattern))
            | (Equipment.name.ilike(pattern))
            | (EquipmentMaintenanceRecord.maintainer.ilike(pattern))
            | (EquipmentMaintenanceRecord.responsible_person.ilike(pattern))
        )
    if maintenance_type:
        query = query.filter(EquipmentMaintenanceRecord.maintenance_type == maintenance_type)
    if maintenance_result:
        query = query.filter(EquipmentMaintenanceRecord.maintenance_result == maintenance_result)
    if equipment_id:
        query = query.filter(EquipmentMaintenanceRecord.equipment_id == equipment_id)
    maintenance_date = func.coalesce(
        EquipmentMaintenanceRecord.actual_date,
        EquipmentMaintenanceRecord.planned_date,
    )
    if date_from:
        try:
            start = datetime.strptime(date_from, "%Y-%m-%d").date()
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="date_from 格式应为 YYYY-MM-DD") from exc
        query = query.filter(maintenance_date >= start)
    if date_to:
        try:
            end = datetime.strptime(date_to, "%Y-%m-%d").date()
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="date_to 格式应为 YYYY-MM-DD") from exc
        query = query.filter(maintenance_date <= end)
    query = query.order_by(maintenance_date.desc(), EquipmentMaintenanceRecord.id.desc())
    total = query.count()
    rows = query.offset((page - 1) * page_size).limit(page_size).all()
    return EquipmentMaintenanceRecordListResponse(
        items=[_to_response(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{record_id}", response_model=EquipmentMaintenanceRecordResponse)
def get_maintenance_record(
    record_id: int,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _to_response(_get_record_or_404(record_id, db))


@router.post("", response_model=EquipmentMaintenanceRecordResponse, status_code=201)
def create_maintenance_record(
    payload: EquipmentMaintenanceRecordCreate,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.maintenance_type not in VALID_MAINTENANCE_TYPES:
        raise HTTPException(status_code=400, detail="无效的保养类型")
    if payload.maintenance_result not in VALID_RESULTS:
        raise HTTPException(status_code=400, detail="无效的保养结果")
    _get_equipment_or_404(payload.equipment_id, db)
    record = EquipmentMaintenanceRecord(
        record_no=_generate_record_no(db),
        equipment_id=payload.equipment_id,
        maintenance_type=payload.maintenance_type,
        planned_date=payload.planned_date,
        actual_date=payload.actual_date,
        next_maintenance_date=payload.next_maintenance_date,
        maintainer=payload.maintainer,
        responsible_person=payload.responsible_person,
        maintenance_content=payload.maintenance_content,
        maintenance_result=payload.maintenance_result,
        remark=payload.remark,
    )
    db.add(record)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="记录编号冲突，请重试") from None
    db.refresh(record)
    return _to_response(record)


@router.put("/{record_id}", response_model=EquipmentMaintenanceRecordResponse)
def update_maintenance_record(
    record_id: int,
    payload: EquipmentMaintenanceRecordUpdate,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = _get_record_or_404(record_id, db)
    data = payload.model_dump(exclude_unset=True)
    if "equipment_id" in data and data["equipment_id"] is not None:
        _get_equipment_or_404(data["equipment_id"], db)
    if "maintenance_type" in data and data["maintenance_type"] not in VALID_MAINTENANCE_TYPES:
        raise HTTPException(status_code=400, detail="无效的保养类型")
    if "maintenance_result" in data and data["maintenance_result"] not in VALID_RESULTS:
        raise HTTPException(status_code=400, detail="无效的保养结果")
    for field, value in data.items():
        setattr(record, field, value)
    record.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(record)
    return _to_response(record)


@router.delete("/{record_id}", status_code=204)
def delete_maintenance_record(
    record_id: int,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = _get_record_or_404(record_id, db)
    db.delete(record)
    db.commit()

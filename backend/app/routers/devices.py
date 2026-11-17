from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload

from app.auth import get_current_user
from app.database import get_db
from app.models import Device, User
from app.schemas import DeviceListResponse, DeviceResponse

router = APIRouter(prefix="/api/devices", tags=["devices"])


def _device_to_response(device: Device) -> DeviceResponse:
    return DeviceResponse(
        id=device.id,
        code=device.code,
        name=device.name,
        device_type_id=device.device_type_id,
        device_type_name=device.device_type.name if device.device_type else None,
        location=device.location,
        status=device.status,
        created_at=device.created_at,
    )


@router.get("", response_model=DeviceListResponse)
def list_devices(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    search: str | None = Query(None),
    device_type_id: int | None = Query(None),
    status: str | None = Query(None),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Device).options(joinedload(Device.device_type))
    if search:
        pattern = f"%{search}%"
        query = query.filter((Device.code.ilike(pattern)) | (Device.name.ilike(pattern)))
    if device_type_id:
        query = query.filter(Device.device_type_id == device_type_id)
    if status:
        query = query.filter(Device.status == status)
    query = query.order_by(Device.code)
    total = query.count()
    devices = query.offset((page - 1) * page_size).limit(page_size).all()
    return DeviceListResponse(
        items=[_device_to_response(d) for d in devices],
        total=total,
        page=page,
        page_size=page_size,
    )

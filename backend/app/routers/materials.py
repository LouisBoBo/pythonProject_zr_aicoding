"""物料主数据列表与增删改查。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audit import record_audit
from app.auth import get_current_user
from app.database import get_db
from app.models import Material, User
from app.permissions import INVENTORY_WRITE, require_permissions

router = APIRouter(prefix="/api/materials", tags=["物料管理"])


class MaterialListItem(BaseModel):
    id: int
    material_code: str
    material_name: str
    category: str
    spec: str | None = None
    unit: str
    safety_stock: int
    max_stock: int
    supplier_name: str | None = None
    purchase_price: float | None = None

    model_config = {"from_attributes": True}


class MaterialListResponse(BaseModel):
    items: list[MaterialListItem]
    total: int
    page: int
    page_size: int


class MaterialCreate(BaseModel):
    material_code: str = Field(..., min_length=1, max_length=50)
    material_name: str = Field(..., min_length=1, max_length=100)
    category: str = Field(default="其他", max_length=50)
    spec: str | None = Field(default=None, max_length=100)
    unit: str = Field(default="件", max_length=20)
    safety_stock: int = Field(default=0, ge=0)
    max_stock: int = Field(default=0, ge=0)
    supplier_name: str | None = Field(default=None, max_length=100)
    purchase_price: float | None = Field(default=None, ge=0)


class MaterialUpdate(BaseModel):
    material_code: str | None = Field(default=None, min_length=1, max_length=50)
    material_name: str | None = Field(default=None, min_length=1, max_length=100)
    category: str | None = Field(default=None, max_length=50)
    spec: str | None = Field(default=None, max_length=100)
    unit: str | None = Field(default=None, max_length=20)
    safety_stock: int | None = Field(default=None, ge=0)
    max_stock: int | None = Field(default=None, ge=0)
    supplier_name: str | None = Field(default=None, max_length=100)
    purchase_price: float | None = Field(default=None, ge=0)


def _get_material_or_404(material_id: int, db: Session) -> Material:
    row = db.query(Material).filter(Material.id == material_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="物料不存在")
    return row


@router.get(
    "",
    response_model=MaterialListResponse,
    summary="物料列表",
    description="分页查询物料主数据，支持按编码、名称、分类筛选。",
)
def list_materials(
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(10, ge=1, le=100, description="每页条数"),
    material_code: str | None = Query(None, description="物料编码（模糊）"),
    material_name: str | None = Query(None, description="物料名称（模糊）"),
    category: str | None = Query(None, description="分类（模糊）"),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Material)
    if material_code:
        query = query.filter(Material.material_code.ilike(f"%{material_code.strip()}%"))
    if material_name:
        query = query.filter(Material.material_name.ilike(f"%{material_name.strip()}%"))
    if category:
        query = query.filter(Material.category.ilike(f"%{category.strip()}%"))

    total = query.count()
    rows = (
        query.order_by(Material.material_code.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return MaterialListResponse(
        items=[MaterialListItem.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "",
    response_model=MaterialListItem,
    status_code=201,
    summary="新增物料",
)
def create_material(
    payload: MaterialCreate,
    current_user: User = Depends(require_permissions(INVENTORY_WRITE)),
    db: Session = Depends(get_db),
):
    dup = (
        db.query(Material)
        .filter(Material.material_code == payload.material_code.strip())
        .first()
    )
    if dup:
        raise HTTPException(status_code=409, detail="物料编码已存在")

    data = payload.model_dump()
    data["material_code"] = data["material_code"].strip()
    data["material_name"] = data["material_name"].strip()
    row = Material(**data)
    db.add(row)
    try:
        db.flush()
        record_audit(
            db,
            username=current_user.username,
            action="create",
            resource="material",
            resource_id=row.material_code,
            detail={"name": row.material_name},
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="物料编码已存在") from None
    db.refresh(row)
    return MaterialListItem.model_validate(row)


@router.put("/{material_id}", response_model=MaterialListItem)
def update_material(
    material_id: int,
    payload: MaterialUpdate,
    current_user: User = Depends(require_permissions(INVENTORY_WRITE)),
    db: Session = Depends(get_db),
):
    row = _get_material_or_404(material_id, db)
    update_data = payload.model_dump(exclude_unset=True)
    if "material_code" in update_data and update_data["material_code"]:
        code = update_data["material_code"].strip()
        dup = (
            db.query(Material)
            .filter(Material.material_code == code, Material.id != material_id)
            .first()
        )
        if dup:
            raise HTTPException(status_code=409, detail="物料编码已存在")
        update_data["material_code"] = code
    if "material_name" in update_data and update_data["material_name"]:
        update_data["material_name"] = update_data["material_name"].strip()

    for field, value in update_data.items():
        setattr(row, field, value)

    try:
        record_audit(
            db,
            username=current_user.username,
            action="update",
            resource="material",
            resource_id=row.material_code,
            detail={"fields": sorted(update_data.keys())},
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="物料编码已存在") from None
    db.refresh(row)
    return MaterialListItem.model_validate(row)


@router.delete("/{material_id}", status_code=204)
def delete_material(
    material_id: int,
    current_user: User = Depends(require_permissions(INVENTORY_WRITE)),
    db: Session = Depends(get_db),
):
    row = _get_material_or_404(material_id, db)
    code = row.material_code
    try:
        db.delete(row)
        record_audit(
            db,
            username=current_user.username,
            action="delete",
            resource="material",
            resource_id=code,
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="物料已被库存或业务单据引用，无法删除",
        ) from None

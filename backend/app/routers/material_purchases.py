"""物料采购列表。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Material, User

router = APIRouter(prefix="/api/material-purchases", tags=["物料采购"])


class MaterialPurchaseItem(BaseModel):
    """物料采购列表行，含供应商与采购单价。"""

    id: int = Field(description="物料 ID")
    material_code: str = Field(description="物料编码")
    material_name: str = Field(description="物料名称")
    category: str = Field(description="物料类别")
    spec: str | None = Field(default=None, description="规格型号")
    unit: str = Field(description="计量单位")
    supplier_code: str | None = Field(default=None, description="供应商编码")
    supplier_name: str | None = Field(default=None, description="供应商名称")
    supplier_contact: str | None = Field(default=None, description="供应商联系人")
    supplier_phone: str | None = Field(default=None, description="供应商联系电话")
    supplier_address: str | None = Field(default=None, description="供应商地址")
    purchase_price: float = Field(description="采购单价（元）")


class MaterialPurchaseListResponse(BaseModel):
    items: list[MaterialPurchaseItem]
    total: int
    page: int
    page_size: int


def _to_item(row: Material) -> MaterialPurchaseItem:
    price = row.purchase_price
    return MaterialPurchaseItem(
        id=row.id,
        material_code=row.material_code,
        material_name=row.material_name,
        category=row.category,
        spec=row.spec,
        unit=row.unit,
        supplier_code=row.supplier_code,
        supplier_name=row.supplier_name,
        supplier_contact=row.supplier_contact,
        supplier_phone=row.supplier_phone,
        supplier_address=row.supplier_address,
        purchase_price=float(price) if price is not None else 0,
    )


@router.get(
    "",
    response_model=MaterialPurchaseListResponse,
    summary="物料采购列表",
    description="分页查询物料的供应商与采购单价；物料采购列表页数据来自本接口。",
)
def list_material_purchases(
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(10, ge=1, le=100, description="每页条数"),
    material_code: str | None = Query(None, description="物料编码（模糊匹配）"),
    material_name: str | None = Query(None, description="物料名称（模糊匹配）"),
    supplier_name: str | None = Query(None, description="供应商名称（模糊匹配）"),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Material)
    if material_code:
        query = query.filter(Material.material_code.ilike(f"%{material_code.strip()}%"))
    if material_name:
        query = query.filter(Material.material_name.ilike(f"%{material_name.strip()}%"))
    if supplier_name:
        query = query.filter(Material.supplier_name.ilike(f"%{supplier_name.strip()}%"))

    total = query.count()
    rows = (
        query.order_by(Material.material_code.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return MaterialPurchaseListResponse(
        items=[_to_item(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )

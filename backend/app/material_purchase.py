"""物料采购资料：供应商与采购单价。"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Material

_SUPPLIERS = {
    "SUP-PCB": {
        "supplier_code": "SUP-PCB",
        "supplier_name": "深圳华强电路有限公司",
        "supplier_contact": "陈立",
        "supplier_phone": "0755-86001218",
        "supplier_address": "深圳市宝安区福永街道凤凰工业园3栋",
    },
    "SUP-PASSIVE": {
        "supplier_code": "SUP-PASSIVE",
        "supplier_name": "苏州国巨电子有限公司",
        "supplier_contact": "王敏",
        "supplier_phone": "0512-62880110",
        "supplier_address": "苏州市工业园区星湖街328号",
    },
    "SUP-CONN": {
        "supplier_code": "SUP-CONN",
        "supplier_name": "东莞立讯精密工业股份有限公司",
        "supplier_contact": "李娜",
        "supplier_phone": "0769-38881200",
        "supplier_address": "东莞市清溪镇青皇村工业区",
    },
    "SUP-IC": {
        "supplier_code": "SUP-IC",
        "supplier_name": "上海意法半导体有限公司",
        "supplier_contact": "赵衡",
        "supplier_phone": "021-61328000",
        "supplier_address": "上海市浦东新区张江高科技园区祖冲之路2288号",
    },
    "SUP-THERM": {
        "supplier_code": "SUP-THERM",
        "supplier_name": "深圳鸿瑞散热科技有限公司",
        "supplier_contact": "刘洋",
        "supplier_phone": "0755-27441800",
        "supplier_address": "深圳市龙华区观澜街道银星科技园B座",
    },
    "SUP-LED": {
        "supplier_code": "SUP-LED",
        "supplier_name": "深圳瑞丰光电股份有限公司",
        "supplier_contact": "黄磊",
        "supplier_phone": "0755-29675888",
        "supplier_address": "深圳市光明区公明街道田寮社区",
    },
    "SUP-IND": {
        "supplier_code": "SUP-IND",
        "supplier_name": "深圳顺络电子股份有限公司",
        "supplier_contact": "孙倩",
        "supplier_phone": "0755-26993188",
        "supplier_address": "深圳市龙华区民治街道顺络工业园",
    },
    "SUP-XTAL": {
        "supplier_code": "SUP-XTAL",
        "supplier_name": "泰晶科技股份有限公司",
        "supplier_contact": "吴凯",
        "supplier_phone": "0712-8778188",
        "supplier_address": "湖北省随州市曾都区泰晶路1号",
    },
    "SUP-FUSE": {
        "supplier_code": "SUP-FUSE",
        "supplier_name": "厦门赛尔特电子有限公司",
        "supplier_contact": "郑洁",
        "supplier_phone": "0592-5769888",
        "supplier_address": "厦门市湖里区火炬高新区火炬园",
    },
    "SUP-CHEM": {
        "supplier_code": "SUP-CHEM",
        "supplier_name": "宁波助焊材料有限公司",
        "supplier_contact": "周芳",
        "supplier_phone": "0574-87126600",
        "supplier_address": "宁波市鄞州区姜山镇科技路18号",
    },
    "SUP-WIRE": {
        "supplier_code": "SUP-WIRE",
        "supplier_name": "远东电缆有限公司",
        "supplier_contact": "马军",
        "supplier_phone": "0510-83780888",
        "supplier_address": "江苏省无锡市宜兴市高塍镇远东大道",
    },
}

# 物料编码 -> (供应商编码, 采购单价)
_MATERIAL_SUPPLIER_PRICE: dict[str, tuple[str, str]] = {
    "PCB-2024-A": ("SUP-PCB", "18.6000"),
    "RES-0805-10K": ("SUP-PASSIVE", "0.0120"),
    "CAP-0603-1UF": ("SUP-PASSIVE", "0.0350"),
    "CONN-USB-C": ("SUP-CONN", "1.8500"),
    "HEATSINK-40": ("SUP-THERM", "2.4000"),
    "HEADER-254": ("SUP-CONN", "0.2800"),
    "IC-STM32F407": ("SUP-IC", "26.8000"),
    "LED-5050-W": ("SUP-LED", "0.1600"),
    "DIODE-1N4148": ("SUP-PASSIVE", "0.0180"),
    "IND-4R7": ("SUP-IND", "0.4200"),
    "XTAL-8M": ("SUP-XTAL", "0.5500"),
    "FUSE-2A": ("SUP-FUSE", "0.2200"),
    "MOSFET-N": ("SUP-IC", "0.6800"),
    "SOLDER-PB": ("SUP-CHEM", "86.0000"),
    "FLUX-100": ("SUP-CHEM", "18.5000"),
    "WIRE-AWG22": ("SUP-WIRE", "45.0000"),
}

_PROFILE_FIELDS = (
    "supplier_code",
    "supplier_name",
    "supplier_contact",
    "supplier_phone",
    "supplier_address",
    "purchase_price",
)


def purchase_profile_for(material_code: str) -> dict:
    """返回物料的供应商与采购单价；未登记编码时按编码稳定分配供应商。"""
    supplier_key, price = _MATERIAL_SUPPLIER_PRICE.get(material_code, (None, None))
    if supplier_key is None:
        keys = list(_SUPPLIERS)
        supplier_key = keys[sum(ord(ch) for ch in material_code) % len(keys)]
        cents = 50 + (sum(ord(ch) for ch in material_code) % 5000)
        price = f"{cents / 100:.4f}"
    profile = dict(_SUPPLIERS[supplier_key])
    profile["purchase_price"] = Decimal(price)
    return profile


def backfill_material_purchase_profiles(db: Session) -> int:
    """为缺少供应商或采购单价的物料补齐采购资料。"""
    updated = 0
    rows = db.query(Material).all()
    for row in rows:
        profile = purchase_profile_for(row.material_code)
        changed = False
        for field in _PROFILE_FIELDS:
            current = getattr(row, field)
            if current is None or current == "":
                setattr(row, field, profile[field])
                changed = True
        if changed:
            updated += 1
    if updated:
        db.commit()
    return updated

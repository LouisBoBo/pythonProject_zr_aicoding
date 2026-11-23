"""IPQC 主表 Excel → quality_inspection_records 全字段导入（不丢字段）。

源表 42 列全部落库；MES 业务字段同步派生：
  inspection_type=process（过程检验/IPQC）
  inspection_result / status 由 CRESULT+CSTATUS 派生
  product_code/material_code ← CITEM_ID
  work_order_no ← 条码/批次 WO 段
  batch_no ← CMO_LOT
  inspector ← CINSPECT_USER_NAME
  inspected_at ← CINSPECT_TIME
  remark ← CREMARK（纯业务备注，不再拼装其他字段）

已存在 source_cid 时执行全量更新（回填缺失列）。
CSTATE=D 跳过。
"""

from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Any

from sqlalchemy.orm import Session

from app.models import WorkOrder
from app.quality_inspection_record_store import (
    RESULT_TO_STATUS,
    TASK_STATUS_PENDING,
    QualityInspectionRecord,
)

# Excel 源表 42 列（必须全部可读入）
IPQC_SOURCE_HEADERS = (
    "CID",
    "CDATETIME_CREATED",
    "CUSER_CREATED",
    "CDATETIME_MODIFIED",
    "CUSER_MODIFIED",
    "CSTATE",
    "CINSTANCE_ID",
    "CROWREMARK",
    "CENTERPRISE_CODE",
    "CORG_CODE",
    "CINSPECT_CODE",
    "CINSPECT_TYPE",
    "CTEMPLATE_ID",
    "CPROCESS_ID",
    "CSCAN_BARCODE",
    "CITEM_ID",
    "CSUBMIT_QTY",
    "CINSPECT_QTY",
    "CUNIT",
    "CINSPECT_TIME",
    "CINSPECT_USER_NAME",
    "CSHIFT",
    "CIS_LAB",
    "CLAB_RECEIVE_TIME",
    "CLAB_RECEIVE_USER_NAME",
    "CLAB_INSPECT_TIME",
    "CLAB_INSPECT_USER_NAME",
    "CCHECK_TIME",
    "CCHECK_USER_NAME",
    "CCHECK_REMARK",
    "CRESULT",
    "CSTATUS",
    "CREMARK",
    "CLAB_INSPECT_REMARK",
    "CNG_DISPOSAL",
    "CUSTOMER_CODE",
    "CMO_LOT",
    "CDECISION_MODE",
    "CCOME_IN_TIME",
    "CINSPECT_COUNT",
    "CPID",
    "CISReInspection",
)

REQUIRED_HEADERS = {"CID", "CINSPECT_TIME", "CRESULT", "CSTATUS"}

# 源 MES 工序主数据对照（CPROCESS_ID → CPROCESS_NAME）
IPQC_PROCESS_NAME_MAP: dict[str, str] = {
    "3273661841000010": "成型",
    "3273661841000049": "钻孔",
    "3273661841000061": "阻焊",
    "3273661841000048": "待确认工序",
}

MAX_IMPORT_BYTES = 15 * 1024 * 1024
MAX_IMPORT_ROWS = 20000
IMPORT_READ_CHUNK = 1024 * 1024
MAX_REMARK_LEN = 2000

# ORM 可批量赋值的 IPQC 字段（不含主键 / 外键派生）
IPQC_ORM_FIELDS = (
    "source_cid",
    "source_created_at",
    "source_user_created",
    "source_modified_at",
    "source_user_modified",
    "source_state",
    "instance_id",
    "row_remark",
    "enterprise_code",
    "org_code",
    "inspect_code",
    "source_inspect_type",
    "template_id",
    "process_id",
    "process_name",
    "scan_barcode",
    "item_id",
    "submit_qty",
    "inspected_qty",
    "unit",
    "shift",
    "is_lab",
    "lab_receive_time",
    "lab_receive_user_name",
    "lab_inspect_time",
    "lab_inspect_user_name",
    "check_time",
    "check_user_name",
    "check_remark",
    "source_result",
    "source_status",
    "lab_inspect_remark",
    "ng_disposal",
    "customer_code",
    "mo_lot",
    "decision_mode",
    "come_in_time",
    "inspect_count",
    "source_pid",
    "is_reinspection",
    "inspection_no",
    "inspection_type",
    "inspection_result",
    "status",
    "work_order_no",
    "product_code",
    "batch_no",
    "material_code",
    "material_name",
    "inspector",
    "inspected_at",
    "non_conforming_qty",
    "remark",
    "created_at",
)


def _cell_str(value: Any, max_len: int | None = None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() == "none":
        return None
    # 去掉 Excel 数值转字符串的尾随 .0
    if text.endswith(".0") and text[:-2].lstrip("-").isdigit():
        text = text[:-2]
    if max_len is not None:
        return text[:max_len]
    return text


def _cell_int(value: Any, default: int | None = None) -> int | None:
    if value is None or value == "":
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _cell_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _cell_dt(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    if not text:
        return None
    for fmt in (
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
    ):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def _extract_work_order_no(barcode: str | None, lot: str | None) -> str | None:
    raw = barcode or lot
    if not raw:
        return None
    head = raw.split("-")[0].strip()
    return head[:50] if head else raw[:50]


def _get(row: dict[str, Any], key: str) -> Any:
    """按源列表头取值（兼容大小写）。"""
    if key in row:
        return row[key]
    upper = key.upper()
    if upper in row:
        return row[upper]
    for k, v in row.items():
        if str(k).upper() == upper:
            return v
    return None


def map_ipqc_row(row: dict[str, Any]) -> dict[str, Any] | None:
    """将一行源数据完整映射为 ORM 字段；CSTATE=D 返回 None。"""
    state = _cell_str(_get(row, "CSTATE")) or "A"
    if state.upper() == "D":
        return None

    cid = _cell_str(_get(row, "CID"), 40)
    if not cid:
        raise ValueError("CID 为空")

    inspected_at = _cell_dt(_get(row, "CINSPECT_TIME")) or _cell_dt(_get(row, "CDATETIME_CREATED"))
    if not inspected_at:
        raise ValueError("检验时间为空")

    result_code = _cell_int(_get(row, "CRESULT"), default=1)
    status_code = _cell_int(_get(row, "CSTATUS"), default=2)
    inspected_qty = _cell_int(_get(row, "CINSPECT_QTY"), default=0) or 0

    if status_code == 1:
        inspection_result = "pending"
        status = TASK_STATUS_PENDING
        non_conforming_qty = 0
    elif result_code == 2:
        inspection_result = "fail"
        status = RESULT_TO_STATUS["fail"]
        non_conforming_qty = inspected_qty
    else:
        inspection_result = "pass"
        status = RESULT_TO_STATUS["pass"]
        non_conforming_qty = 0

    barcode = _cell_str(_get(row, "CSCAN_BARCODE"), 100)
    lot = _cell_str(_get(row, "CMO_LOT"), 80)
    item_id = _cell_str(_get(row, "CITEM_ID"), 50)
    inspector = (
        _cell_str(_get(row, "CINSPECT_USER_NAME"), 50)
        or _cell_str(_get(row, "CUSER_CREATED"), 50)
        or "未知"
    )
    created_at = _cell_dt(_get(row, "CDATETIME_CREATED")) or inspected_at
    process_id = _cell_str(_get(row, "CPROCESS_ID"), 40)
    process_name = (
        _cell_str(_get(row, "CPROCESS_NAME"), 50)
        or (IPQC_PROCESS_NAME_MAP.get(process_id) if process_id else None)
    )

    return {
        # MES 业务字段
        "inspection_no": f"IPQC-{cid}"[:50],
        "inspection_type": "process",
        "inspection_result": inspection_result,
        "status": status,
        "work_order_no": _extract_work_order_no(barcode, lot),
        "product_code": item_id,
        "batch_no": (lot or barcode)[:50] if (lot or barcode) else None,
        "material_code": item_id,
        "material_name": None,
        "inspector": inspector,
        "inspected_at": inspected_at,
        "non_conforming_qty": non_conforming_qty,
        "remark": _cell_str(_get(row, "CREMARK"), MAX_REMARK_LEN),
        "created_at": created_at,
        # IPQC 源表全字段
        "source_cid": cid,
        "source_created_at": _cell_dt(_get(row, "CDATETIME_CREATED")),
        "source_user_created": _cell_str(_get(row, "CUSER_CREATED"), 50),
        "source_modified_at": _cell_dt(_get(row, "CDATETIME_MODIFIED")),
        "source_user_modified": _cell_str(_get(row, "CUSER_MODIFIED"), 50),
        "source_state": state[:10],
        "instance_id": _cell_str(_get(row, "CINSTANCE_ID"), 80),
        "row_remark": _cell_str(_get(row, "CROWREMARK")),
        "enterprise_code": _cell_str(_get(row, "CENTERPRISE_CODE"), 50),
        "org_code": _cell_str(_get(row, "CORG_CODE"), 50),
        "inspect_code": _cell_str(_get(row, "CINSPECT_CODE"), 80),
        "source_inspect_type": _cell_int(_get(row, "CINSPECT_TYPE")),
        "template_id": _cell_str(_get(row, "CTEMPLATE_ID"), 40),
        "process_id": process_id,
        "process_name": process_name,
        "scan_barcode": barcode,
        "item_id": item_id,
        "submit_qty": _cell_float(_get(row, "CSUBMIT_QTY")),
        "inspected_qty": inspected_qty,
        "unit": _cell_str(_get(row, "CUNIT"), 20),
        "shift": _cell_str(_get(row, "CSHIFT"), 20),
        "is_lab": _cell_str(_get(row, "CIS_LAB"), 10),
        "lab_receive_time": _cell_dt(_get(row, "CLAB_RECEIVE_TIME")),
        "lab_receive_user_name": _cell_str(_get(row, "CLAB_RECEIVE_USER_NAME"), 50),
        "lab_inspect_time": _cell_dt(_get(row, "CLAB_INSPECT_TIME")),
        "lab_inspect_user_name": _cell_str(_get(row, "CLAB_INSPECT_USER_NAME"), 50),
        "check_time": _cell_dt(_get(row, "CCHECK_TIME")),
        "check_user_name": _cell_str(_get(row, "CCHECK_USER_NAME"), 50),
        "check_remark": _cell_str(_get(row, "CCHECK_REMARK")),
        "source_result": result_code,
        "source_status": status_code,
        "lab_inspect_remark": _cell_str(_get(row, "CLAB_INSPECT_REMARK")),
        "ng_disposal": _cell_str(_get(row, "CNG_DISPOSAL"), 100),
        "customer_code": _cell_str(_get(row, "CUSTOMER_CODE"), 50),
        "mo_lot": lot,
        "decision_mode": _cell_int(_get(row, "CDECISION_MODE")),
        "come_in_time": _cell_dt(_get(row, "CCOME_IN_TIME")),
        "inspect_count": _cell_int(_get(row, "CINSPECT_COUNT")),
        "source_pid": _cell_str(_get(row, "CPID"), 40),
        "is_reinspection": 1 if _cell_int(_get(row, "CISReInspection"), 0) == 1 else 0,
    }


def _header_index_map(header_row: tuple[Any, ...]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for idx, cell in enumerate(header_row):
        name = _cell_str(cell)
        if name:
            mapping[name.upper()] = idx
    return mapping


def _row_to_dict(header_map: dict[str, int], row: tuple[Any, ...]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, idx in header_map.items():
        if idx < len(row):
            out[key] = row[idx]
    return out


def _apply_mapped(record: QualityInspectionRecord, mapped: dict[str, Any], work_order_id: int | None) -> None:
    for field in IPQC_ORM_FIELDS:
        if field in mapped:
            setattr(record, field, mapped[field])
    record.work_order_id = work_order_id


def import_ipqc_workbook(db: Session, content: bytes) -> dict[str, Any]:
    """解析 IPQC Excel：新建或按 source_cid 全量更新。"""
    from openpyxl import load_workbook

    wb = load_workbook(BytesIO(content), read_only=True, data_only=True)
    ws = wb[wb.sheetnames[0]]
    rows_iter = ws.iter_rows(values_only=True)
    try:
        header_row = next(rows_iter)
    except StopIteration as exc:
        raise ValueError("Excel 文件无内容") from exc

    header_map = _header_index_map(tuple(header_row or ()))
    missing_required = REQUIRED_HEADERS - set(header_map.keys())
    if missing_required:
        raise ValueError(f"缺少必要列：{', '.join(sorted(missing_required))}")

    header_keys_upper = set(header_map.keys())
    missing_optional = [h for h in IPQC_SOURCE_HEADERS if h.upper() not in header_keys_upper]
    # 非必要列缺失不阻断，但记入 errors 提示

    wo_map = {
        wo.order_no: wo.id
        for wo in db.query(WorkOrder.id, WorkOrder.order_no).all()
        if wo.order_no
    }

    existing_by_cid: dict[str, QualityInspectionRecord] = {
        r.source_cid: r
        for r in db.query(QualityInspectionRecord)
        .filter(QualityInspectionRecord.source_cid.isnot(None))
        .all()
        if r.source_cid
    }

    created = 0
    updated = 0
    skipped = 0
    pending_count = 0
    failed_count = 0
    errors: list[str] = []
    data_rows_seen = 0

    if missing_optional:
        errors.append(f"源表缺少列（将按空值导入）：{', '.join(missing_optional)}")

    pending_flush: list[QualityInspectionRecord] = []

    for excel_row_no, row in enumerate(rows_iter, start=2):
        if not row or all(cell is None or str(cell).strip() == "" for cell in row):
            continue
        data_rows_seen += 1
        if data_rows_seen > MAX_IMPORT_ROWS:
            errors.append(f"超过最大导入行数 {MAX_IMPORT_ROWS}，后续行已忽略")
            break
        raw = _row_to_dict(header_map, row)
        try:
            mapped = map_ipqc_row(raw)
        except ValueError as exc:
            errors.append(f"第 {excel_row_no} 行：{exc}")
            continue

        if mapped is None:
            skipped += 1
            continue

        cid = mapped["source_cid"]
        wo_no = mapped.get("work_order_no")
        work_order_id = wo_map.get(wo_no) if wo_no else None

        existing = existing_by_cid.get(cid)
        if existing:
            _apply_mapped(existing, mapped, work_order_id)
            updated += 1
        else:
            # 避免与手工单号冲突
            insp_no = mapped["inspection_no"]
            conflict = (
                db.query(QualityInspectionRecord)
                .filter(QualityInspectionRecord.inspection_no == insp_no)
                .first()
            )
            if conflict and not conflict.source_cid:
                errors.append(f"第 {excel_row_no} 行：检验单号 {insp_no} 已存在且非 IPQC 导入")
                continue
            if conflict and conflict.source_cid == cid:
                _apply_mapped(conflict, mapped, work_order_id)
                existing_by_cid[cid] = conflict
                updated += 1
            else:
                record = QualityInspectionRecord()
                _apply_mapped(record, mapped, work_order_id)
                pending_flush.append(record)
                existing_by_cid[cid] = record
                created += 1

        if mapped["status"] == TASK_STATUS_PENDING:
            pending_count += 1
        if mapped["inspection_result"] == "fail":
            failed_count += 1

        if len(pending_flush) >= 200:
            db.add_all(pending_flush)
            db.commit()
            pending_flush.clear()

    if pending_flush:
        db.add_all(pending_flush)
        db.commit()
    else:
        db.commit()

    wb.close()
    return {
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "pending_count": pending_count,
        "failed_count": failed_count,
        "errors": errors[:50],
    }

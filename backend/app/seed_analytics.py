"""看板 / 分析域演示数据种子。

若 ProductionLine 已有数据则整次跳过，保证可重复调用且结果稳定。
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import func

from app.database import SessionLocal
from app.work_order_utils import derive_current_process
from app.models import (
    DashboardTodo,
    Device,
    Equipment,
    EquipmentAlarm,
    EquipmentMaintenanceOrder,
    EquipmentMaintenancePlan,
    EquipmentOeeSnapshot,
    EquipmentOutputRecord,
    EquipmentRepair,
    EquipmentRuntimeLog,
    InspectionPlan,
    InspectionRecord,
    InspectionRecordItem,
    InventoryBalance,
    InventoryTransaction,
    KanbanBoard,
    LineCapacitySnapshot,
    Material,
    Product,
    ProductionLine,
    ProductionOutputRecord,
    ProductionPlan,
    QualityAnomaly,
    QualityMetrics,
    SalesOrder,
    ShipmentRecord,
    Warehouse,
    WarehouseLocation,
    WipSnapshot,
    WorkOrder,
)

PRODUCTION_LINE_NAMES = ["SMT-1线", "SMT-2线", "DIP线", "组装线", "测试线"]
WIP_STATUSES = ["待投料", "在制", "待检验", "待入库"]

LINE_PRODUCTS = {
    "SMT-1线": ["PCB-A100", "PCB-A200", "PCB-A300"],
    "SMT-2线": ["PCB-B100", "PCB-B200", "PCB-B300"],
    "DIP线": ["PCBA-C100", "PCBA-C200", "PCBA-C300"],
    "组装线": ["ASSY-D100", "ASSY-D200", "ASSY-D300"],
    "测试线": ["TEST-E100", "TEST-E200", "TEST-E300"],
}

LINE_CODES = {
    "SMT-1线": "LINE-SMT-1",
    "SMT-2线": "LINE-SMT-2",
    "DIP线": "LINE-DIP",
    "组装线": "LINE-ASSY",
    "测试线": "LINE-TEST",
}

LINE_WORKSHOPS = {
    "SMT-1线": "SMT车间",
    "SMT-2线": "SMT车间",
    "DIP线": "DIP车间",
    "组装线": "组装车间",
    "测试线": "测试车间",
}

PRODUCT_NAMES = {
    "PCB-A100": "主板A100",
    "PCB-A200": "主板A200",
    "PCB-A300": "主板A300",
    "PCB-B100": "主板B100",
    "PCB-B200": "主板B200",
    "PCB-B300": "主板B300",
    "PCBA-C100": "插件板C100",
    "PCBA-C200": "插件板C200",
    "PCBA-C300": "插件板C300",
    "ASSY-D100": "整机D100",
    "ASSY-D200": "整机D200",
    "ASSY-D300": "整机D300",
    "TEST-E100": "测试件E100",
    "TEST-E200": "测试件E200",
    "TEST-E300": "测试件E300",
}

EXTRA_EQUIPMENT = [
    {
        "equipment_code": "EQ-2024-005",
        "name": "精密磨床",
        "spec_model": "M7140",
        "department": "机加工车间",
        "location": "A区-03",
        "status": "运行",
        "purchase_date": date(2023, 5, 12),
        "commission_date": date(2023, 6, 1),
        "supplier": "杭州机床",
    },
    {
        "equipment_code": "EQ-2024-006",
        "name": "冲压机A",
        "spec_model": "JH21-80",
        "department": "冲压车间",
        "location": "B区-02",
        "status": "待机",
        "purchase_date": date(2022, 11, 8),
        "commission_date": date(2022, 12, 1),
        "supplier": "扬力集团",
    },
    {
        "equipment_code": "EQ-2024-007",
        "name": "激光切割机",
        "spec_model": "LF-3015",
        "department": "钣金车间",
        "location": "C区-02",
        "status": "运行",
        "purchase_date": date(2023, 7, 20),
        "commission_date": date(2023, 8, 10),
        "supplier": "大族激光",
    },
    {
        "equipment_code": "EQ-2024-008",
        "name": "折弯机B",
        "spec_model": "WC67Y-100",
        "department": "钣金车间",
        "location": "C区-03",
        "status": "待机",
        "purchase_date": date(2021, 4, 15),
        "commission_date": date(2021, 5, 5),
        "supplier": "亚威机床",
    },
    {
        "equipment_code": "EQ-2024-009",
        "name": "焊机工作站1",
        "spec_model": "WS-350",
        "department": "焊接车间",
        "location": "D区-01",
        "status": "运行",
        "purchase_date": date(2022, 9, 1),
        "commission_date": date(2022, 9, 20),
        "supplier": "松下焊接",
    },
    {
        "equipment_code": "EQ-2024-010",
        "name": "焊机工作站2",
        "spec_model": "WS-350",
        "department": "焊接车间",
        "location": "D区-02",
        "status": "运行",
        "purchase_date": date(2022, 9, 1),
        "commission_date": date(2022, 9, 20),
        "supplier": "松下焊接",
    },
    {
        "equipment_code": "EQ-2024-011",
        "name": "2号注塑机",
        "spec_model": "HTF-200X",
        "department": "注塑车间",
        "location": "B区-03",
        "status": "运行",
        "purchase_date": date(2023, 2, 18),
        "commission_date": date(2023, 3, 5),
        "supplier": "海天塑机",
    },
    {
        "equipment_code": "EQ-2024-012",
        "name": "喷涂机器人",
        "spec_model": "RB-Paint-6A",
        "department": "表面处理车间",
        "location": "E区-01",
        "status": "运行",
        "purchase_date": date(2023, 10, 8),
        "commission_date": date(2023, 11, 1),
        "supplier": "ABB",
    },
    {
        "equipment_code": "EQ-2024-013",
        "name": "铣床X1",
        "spec_model": "XK7136",
        "department": "机加工车间",
        "location": "A区-04",
        "status": "待机",
        "purchase_date": date(2020, 6, 10),
        "commission_date": date(2020, 7, 1),
        "supplier": "北京第一机床厂",
    },
]

# material_code, material_name, category, spec, unit, stock_qty, safety_stock, max_stock, location_code
MATERIAL_SEED = [
    ("PCB-2024-A", "铝基板 PCB", "电子元件", "100x160mm", "片", 120, 200, 2000, "A-01-03"),
    ("RES-0805-10K", "贴片电阻 10KΩ", "电子元件", "0805 ±1%", "个", 8500, 2000, 20000, "A-02-06"),
    ("CAP-0603-1UF", "贴片电容 1μF", "电子元件", "0603 16V", "个", 3200, 3000, 15000, "B-03-02"),
    ("CONN-USB-C", "USB-C 连接器", "连接器", "16P SMT", "个", 180, 500, 3000, "B-02-05"),
    ("HEATSINK-40", "铝散热片", "散热材料", "40x40x10mm", "片", 2100, 800, 5000, "C-01-08"),
    ("HEADER-254", "排针 2.54mm", "连接器", "1x40P 直插", "个", 5600, 1500, 12000, "A-04-07"),
    ("IC-STM32F407", "STM32F407VET6", "芯片", "LQFP-100", "片", 320, 100, 1000, "D-01-01"),
    ("LED-5050-W", "白光 LED 5050", "光电器件", "5050 6000K", "个", 0, 500, 5000, "D-02-03"),
    ("DIODE-1N4148", "开关二极管 1N4148", "电子元件", "SOD-123", "个", 4200, 2000, 10000, "A-05-02"),
    ("IND-4R7", "功率电感 4.7μH", "电子元件", "5x5mm SMD", "个", 1800, 1000, 8000, "B-04-08"),
    ("XTAL-8M", "晶振 8MHz", "电子元件", "3225 SMD", "个", 650, 300, 3000, "D-01-05"),
    ("FUSE-2A", "保险丝 2A", "保护器件", "1206 SMD", "个", 3100, 1000, 8000, "C-03-01"),
    ("MOSFET-N", "N沟道 MOSFET", "芯片", "SOT-23 30V/3A", "片", 890, 500, 4000, "D-01-08"),
    ("SOLDER-PB", "含铅锡膏", "焊接材料", "Sn63Pb37 500g", "瓶", 45, 20, 200, "E-01-01"),
    ("FLUX-100", "助焊剂", "焊接材料", "100ml", "瓶", 28, 15, 150, "E-01-02"),
    ("WIRE-AWG22", "电子线 AWG22", "线材", "红 100m/卷", "卷", 12, 10, 80, "E-02-03"),
]

LOCATION_CODES = [
    "A-01-01",
    "A-01-02",
    "A-01-03",
    "A-02-06",
    "A-04-07",
    "A-05-02",
    "B-02-05",
    "B-03-02",
    "B-04-08",
    "B-05-11",
    "C-01-08",
    "C-02-09",
    "C-03-01",
    "D-01-01",
    "D-01-05",
    "D-01-08",
    "D-02-03",
    "E-01-01",
    "E-01-02",
    "E-02-03",
]


def _stable_int(seed: str, base: int, span: int) -> int:
    value = 0
    for ch in seed:
        value = (value * 31 + ord(ch)) & 0xFFFFFFFF
    return base + (value % span)


def seed_analytics_data() -> None:
    db = SessionLocal()
    try:
        if db.query(ProductionLine).first():
            return

        now = datetime.utcnow()
        today = now.date()

        # ---------- 产线 / 产品 ----------
        lines: list[ProductionLine] = []
        for name in PRODUCTION_LINE_NAMES:
            line = ProductionLine(
                code=LINE_CODES[name],
                name=name,
                workshop=LINE_WORKSHOPS[name],
                is_active=True,
            )
            db.add(line)
            lines.append(line)
        db.flush()

        products_by_line: dict[str, list[Product]] = {}
        for line in lines:
            products_by_line[line.name] = []
            for code in LINE_PRODUCTS[line.name]:
                product = Product(
                    product_code=code,
                    product_name=PRODUCT_NAMES.get(code, code),
                    model=code.split("-")[-1],
                    unit="件",
                    default_line_id=line.id,
                )
                db.add(product)
                products_by_line[line.name].append(product)
        db.flush()

        # ---------- 生产计划 + 产量（约 14 天） ----------
        for day_offset in range(13, -1, -1):
            plan_day = today - timedelta(days=day_offset)
            for line_idx, line in enumerate(lines):
                products = products_by_line[line.name]
                for p_idx, product in enumerate(products):
                    plan_qty = 800 + line_idx * 40 + p_idx * 60 + (13 - day_offset) * 5
                    db.add(
                        ProductionPlan(
                            plan_date=plan_day,
                            production_line_id=line.id,
                            product_id=product.id,
                            plan_qty=plan_qty,
                        )
                    )

                    if day_offset == 0:
                        # 今日按小时记录（08:00–20:00）
                        for hour in range(8, 21):
                            record_at = datetime(
                                today.year, today.month, today.day, hour, 0, 0
                            )
                            actual = 45 + line_idx * 3 + p_idx * 5 + (hour % 5) * 2
                            defect = (hour + line_idx + p_idx) % 4
                            db.add(
                                ProductionOutputRecord(
                                    record_at=record_at,
                                    production_line_id=line.id,
                                    product_id=product.id,
                                    process_card_no=f"PC-{line.code}-{today:%m%d}-{hour:02d}-{p_idx}",
                                    actual_qty=actual,
                                    area_output=round(actual * 1.85, 2),
                                    defect_qty=defect,
                                    incoming_boards=actual + defect + 2,
                                )
                            )
                    else:
                        # 历史按日汇总一条
                        actual = int(plan_qty * (0.88 + (p_idx % 3) * 0.03))
                        defect = 8 + line_idx + p_idx + (day_offset % 5)
                        record_at = datetime(
                            plan_day.year, plan_day.month, plan_day.day, 18, 0, 0
                        )
                        db.add(
                            ProductionOutputRecord(
                                record_at=record_at,
                                production_line_id=line.id,
                                product_id=product.id,
                                process_card_no=f"PC-{line.code}-{plan_day:%m%d}-{p_idx}",
                                actual_qty=actual,
                                area_output=round(actual * 1.85, 2),
                                defect_qty=defect,
                                incoming_boards=actual + defect + 10,
                            )
                        )

        # ---------- WIP / 产能快照 ----------
        snapshot_at = now.replace(minute=0, second=0, microsecond=0)
        for line_idx, line in enumerate(lines):
            product = products_by_line[line.name][0]
            for s_idx, status in enumerate(WIP_STATUSES):
                qty = 40 + line_idx * 15 + s_idx * 25 + (line_idx * s_idx)
                db.add(
                    WipSnapshot(
                        snapshot_at=snapshot_at,
                        production_line_id=line.id,
                        product_id=product.id,
                        status=status,
                        quantity=qty,
                    )
                )
            load_rate = round(72.0 + line_idx * 4.5, 2)
            capacity_util = round(68.0 + line_idx * 5.0, 2)
            db.add(
                LineCapacitySnapshot(
                    snapshot_at=snapshot_at,
                    production_line_id=line.id,
                    station_name=f"{line.name}-主工位",
                    load_rate=load_rate,
                    capacity_utilization=capacity_util,
                )
            )

        # ---------- 设备扩容（不足 10 台则补充） ----------
        existing_codes = {
            row[0] for row in db.query(Equipment.equipment_code).all()
        }
        equipment_count = db.query(Equipment).count()
        if equipment_count < 10:
            for item in EXTRA_EQUIPMENT:
                if equipment_count >= 10:
                    break
                if item["equipment_code"] in existing_codes:
                    continue
                db.add(Equipment(**item))
                existing_codes.add(item["equipment_code"])
                equipment_count += 1
            db.flush()

        equipment_list = db.query(Equipment).order_by(Equipment.id).all()

        # ---------- 设备运行 / OEE / 告警 / 产量 ----------
        alarm_types = ["温度过高", "振动异常", "急停触发", "润滑不足", "通信中断"]
        for eq_idx, eq in enumerate(equipment_list):
            # 当日运行时段
            start_at = datetime(today.year, today.month, today.day, 8, 0, 0)
            end_at = datetime(today.year, today.month, today.day, 17, 0, 0)
            runtime_hours = round(8.5 + (eq_idx % 5) * 0.4, 2)
            db.add(
                EquipmentRuntimeLog(
                    equipment_id=eq.id,
                    start_at=start_at,
                    end_at=end_at if eq.status != "运行" else None,
                    status=eq.status if eq.status in ("运行", "停机", "待机", "维修") else "运行",
                    runtime_hours=runtime_hours,
                )
            )

            # 近 7 日日 OEE
            for day_back in range(6, -1, -1):
                period_start = today - timedelta(days=day_back)
                availability = round(85.0 + (eq_idx % 7) + (day_back % 3), 2)
                performance = round(88.0 + ((eq_idx + day_back) % 5), 2)
                quality = round(96.0 + (eq_idx % 3) * 0.5, 2)
                oee = round(availability * performance * quality / 10000, 2)
                db.add(
                    EquipmentOeeSnapshot(
                        equipment_id=eq.id,
                        period_type="day",
                        period_start=period_start,
                        availability=availability,
                        performance=performance,
                        quality=quality,
                        oee=oee,
                    )
                )

            # 若干告警
            for a_idx in range(3):
                occurred = now - timedelta(hours=6 + eq_idx + a_idx * 8)
                cleared = None if a_idx == 0 and eq_idx % 3 == 0 else occurred + timedelta(hours=1)
                db.add(
                    EquipmentAlarm(
                        equipment_id=eq.id,
                        alarm_type=alarm_types[(eq_idx + a_idx) % len(alarm_types)],
                        severity="high" if a_idx == 0 else "normal",
                        occurred_at=occurred,
                        cleared_at=cleared,
                        description=f"{eq.name}：{alarm_types[(eq_idx + a_idx) % len(alarm_types)]}",
                    )
                )

            # 近 7 日设备产量
            for day_back in range(6, -1, -1):
                record_date = today - timedelta(days=day_back)
                base_out = 600 + eq_idx * 40
                output_qty = base_out - day_back * 15 + (eq_idx % 4) * 10
                db.add(
                    EquipmentOutputRecord(
                        equipment_id=eq.id,
                        record_date=record_date,
                        output_qty=max(output_qty, 50),
                    )
                )

        # ---------- 仓库 / 库位 ----------
        warehouse = Warehouse(code="WH-01", name="一号原料仓")
        db.add(warehouse)
        db.flush()

        occupied_codes = {row[8] for row in MATERIAL_SEED}
        locations_by_code: dict[str, WarehouseLocation] = {}
        for loc_idx, loc_code in enumerate(LOCATION_CODES):
            if loc_code in occupied_codes:
                status = "occupied"
            elif loc_idx in (9, 11):
                status = "abnormal"
            else:
                status = "free"
            loc = WarehouseLocation(
                warehouse_id=warehouse.id,
                location_code=loc_code,
                status=status,
            )
            db.add(loc)
            locations_by_code[loc_code] = loc
        db.flush()

        # ---------- 物料 / 库存余额 ----------
        materials_by_code: dict[str, Material] = {}
        for (
            m_code,
            m_name,
            category,
            spec,
            unit,
            stock_qty,
            safety_stock,
            max_stock,
            loc_code,
        ) in MATERIAL_SEED:
            material = Material(
                material_code=m_code,
                material_name=m_name,
                category=category,
                spec=spec,
                unit=unit,
                safety_stock=safety_stock,
                max_stock=max_stock,
            )
            db.add(material)
            materials_by_code[m_code] = material
        db.flush()

        for (
            m_code,
            _m_name,
            _category,
            _spec,
            _unit,
            stock_qty,
            _safety_stock,
            _max_stock,
            loc_code,
        ) in MATERIAL_SEED:
            material = materials_by_code[m_code]
            location = locations_by_code[loc_code]
            db.add(
                InventoryBalance(
                    material_id=material.id,
                    location_id=location.id,
                    quantity=stock_qty,
                    updated_at=now - timedelta(hours=_stable_int(m_code, 1, 48)),
                )
            )

        # ---------- 近 2 日出入库 / 移库 / 盘点 ----------
        txn_defs = [
            ("PCB-2024-A", "A-01-03", "out", 30, 1, 17, 10, "OUT-PCB-A"),
            ("CONN-USB-C", "B-02-05", "out", 50, 1, 17, 28, "OUT-USB-1"),
            ("HEATSINK-40", "C-01-08", "in", 500, 1, 17, 15, "IN-HS-40"),
            ("RES-0805-10K", "A-02-06", "move", 200, 1, 16, 52, "MV-RES-10K"),
            ("CAP-0603-1UF", "B-03-02", "in", 1000, 1, 16, 38, "IN-CAP-1UF"),
            ("CONN-USB-C", "C-02-09", "out", 80, 1, 16, 22, "OUT-USB-2"),
            ("HEADER-254", "A-04-07", "in", 2000, 1, 15, 48, "IN-HDR-254"),
            ("PCB-2024-A", "A-01-03", "check", 120, 1, 16, 5, "CHK-A-01-03"),
            ("DIODE-1N4148", "A-05-02", "in", 800, 0, 9, 12, "IN-DIODE"),
            ("FUSE-2A", "C-03-01", "out", 150, 0, 8, 45, "OUT-FUSE"),
            ("SOLDER-PB", "E-01-01", "in", 10, 0, 10, 0, "IN-SOLDER"),
            ("MOSFET-N", "D-01-08", "out", 40, 0, 13, 20, "OUT-MOS"),
            ("IND-4R7", "B-04-08", "move", 100, 0, 14, 30, "MV-IND"),
            ("WIRE-AWG22", "E-02-03", "check", 12, 0, 15, 0, "CHK-WIRE"),
            ("IC-STM32F407", "D-01-01", "in", 50, 1, 10, 20, "IN-STM32"),
            ("LED-5050-W", "D-02-03", "out", 20, 0, 11, 0, "OUT-LED"),
        ]
        for m_code, loc_code, txn_type, qty, day_back, hour, minute, ref in txn_defs:
            txn_day = today - timedelta(days=day_back)
            db.add(
                InventoryTransaction(
                    material_id=materials_by_code[m_code].id,
                    location_id=locations_by_code[loc_code].id,
                    txn_type=txn_type,
                    quantity=qty,
                    txn_at=datetime(txn_day.year, txn_day.month, txn_day.day, hour, minute, 0),
                    ref_no=ref,
                    remark=f"{txn_type}:{m_code}",
                )
            )

        # ---------- 销售订单 / 发货 ----------
        sales_defs = [
            ("SO-2024-1001", "华东电子有限公司", -5, "open", 2000, 800),
            ("SO-2024-1002", "南方智造股份", -2, "open", 1500, 600),
            ("SO-2024-1003", "北方精密科技", 3, "open", 3000, 1200),
            ("SO-2024-1004", "西部自动化集团", 7, "open", 1800, 1800),
            ("SO-2024-1005", "中原装备制造", 12, "closed", 2200, 2200),
            ("SO-2024-1006", "海河电子科技", -8, "open", 900, 200),
            ("SO-2024-1007", "粤海智能终端", 1, "open", 1100, 400),
            ("SO-2024-1008", "川渝机电股份", 20, "open", 2500, 0),
        ]
        sales_orders: list[SalesOrder] = []
        for order_no, customer, due_offset, status, plan_qty, shipped_qty in sales_defs:
            order = SalesOrder(
                order_no=order_no,
                customer=customer,
                due_date=today + timedelta(days=due_offset),
                status=status,
                plan_qty=plan_qty,
                shipped_qty=shipped_qty,
                created_at=now - timedelta(days=20 + abs(due_offset)),
            )
            db.add(order)
            sales_orders.append(order)
        db.flush()

        # 本周 / 本月发货记录
        shipment_plan = [
            (0, 0, 10, 200),
            (0, 1, 14, 150),
            (0, 3, 9, 300),
            (1, 2, 16, 180),
            (2, 5, 11, 250),
            (3, 8, 15, 400),
            (4, 12, 10, 500),
            (5, 1, 13, 100),
            (6, 4, 17, 220),
            (0, 18, 9, 160),
            (1, 22, 14, 120),
        ]
        for order_idx, day_back, hour, ship_qty in shipment_plan:
            order = sales_orders[order_idx % len(sales_orders)]
            ship_day = today - timedelta(days=day_back)
            db.add(
                ShipmentRecord(
                    sales_order_id=order.id,
                    ship_qty=ship_qty,
                    shipped_at=datetime(
                        ship_day.year, ship_day.month, ship_day.day, hour, 0, 0
                    ),
                )
            )

        # ---------- 工单（若为空） ----------
        if not db.query(WorkOrder).first():
            work_order_defs = [
                ("WO-AN-001", "pending", "high", 0, 0, 5),
                ("WO-AN-002", "pending", "normal", 0, 1, 6),
                ("WO-AN-003", "in_progress", "high", 420, 0, 3),
                ("WO-AN-004", "in_progress", "normal", 680, 1, 4),
                ("WO-AN-005", "in_progress", "urgent", 310, 2, 2),
                ("WO-AN-006", "completed", "normal", 1000, 5, 0),
                ("WO-AN-007", "completed", "normal", 850, 6, -1),
                ("WO-AN-008", "closed", "low", 1200, 10, -5),
                ("WO-AN-009", "closed", "normal", 900, 12, -7),
                ("WO-AN-010", "pending", "normal", 0, 2, 8),
                ("WO-AN-011", "in_progress", "normal", 540, 3, 5),
                ("WO-AN-012", "completed", "high", 760, 8, -2),
            ]
            assignees = ["张三", "李四", "王五", "赵六", "钱七"]
            for idx, (order_no, status, priority, actual, start_off, end_off) in enumerate(
                work_order_defs
            ):
                line = lines[idx % len(lines)]
                product = products_by_line[line.name][idx % 3]
                plan_qty = 800 + idx * 50
                start_date = today - timedelta(days=start_off)
                end_date = today + timedelta(days=end_off)
                db.add(
                    WorkOrder(
                        order_no=order_no,
                        product_name=product.product_name,
                        product_code=product.product_code,
                        production_line=line.name,
                        plan_quantity=plan_qty,
                        actual_quantity=actual if status != "pending" else 0,
                        status=status,
                        priority=priority,
                        assignee=assignees[idx % len(assignees)],
                        start_date=start_date,
                        end_date=end_date,
                        remark="分析看板演示工单",
                        created_at=now - timedelta(days=start_off + 1),
                        updated_at=now - timedelta(hours=idx),
                    )
                )

        # ---------- 工作台待办 ----------
        if not db.query(DashboardTodo).first():
            todos = [
                DashboardTodo(
                    type="work_order",
                    title="跟进逾期销售订单 SO-2024-1001",
                    description="华东电子有限公司订单已逾期，请协调发货。",
                    priority="high",
                    link="/sales/orders",
                    status="open",
                    created_at=now - timedelta(hours=5),
                ),
                DashboardTodo(
                    type="inventory",
                    title="处理 PCB-2024-A 低库存预警",
                    description="当前库存 120，低于安全库存 200。",
                    priority="high",
                    link="/warehouse",
                    status="open",
                    created_at=now - timedelta(hours=4),
                ),
                DashboardTodo(
                    type="equipment",
                    title="确认自动包装线维修进度",
                    description="EQ-2024-004 处于维修状态，影响包装产能。",
                    priority="medium",
                    link="/equipment",
                    status="open",
                    created_at=now - timedelta(hours=3),
                ),
                DashboardTodo(
                    type="quality",
                    title="复核 SMT-1 线今日不良批次",
                    description="今日缺陷累计偏高，请质量工程师复核。",
                    priority="medium",
                    link="/quality",
                    status="open",
                    created_at=now - timedelta(hours=2),
                ),
                DashboardTodo(
                    type="production",
                    title="排产确认：测试线明日计划",
                    description="测试线明日计划量需与组装线出货对齐。",
                    priority="low",
                    link="/production",
                    status="open",
                    created_at=now - timedelta(hours=1),
                ),
            ]
            db.add_all(todos)

        db.commit()
    finally:
        db.close()


def backfill_recent_operational_data(days: int = 7) -> None:
    """把看板/总览依赖的事实表补到「今天」，已有日期跳过，可重复调用。"""
    db = SessionLocal()
    try:
        today = date.today()
        now = datetime.now()
        start_day = today - timedelta(days=days - 1)

        lines = db.query(ProductionLine).order_by(ProductionLine.id).all()
        products = db.query(Product).order_by(Product.id).all()
        equipment_list = db.query(Equipment).order_by(Equipment.id).all()
        if not lines:
            return

        products_by_line: dict[int, list[Product]] = {ln.id: [] for ln in lines}
        for product in products:
            if product.default_line_id in products_by_line:
                products_by_line[product.default_line_id].append(product)

        # ---------- 生产计划 + 产量 ----------
        for day_offset in range(days - 1, -1, -1):
            the_day = today - timedelta(days=day_offset)
            for line_idx, line in enumerate(lines):
                line_products = products_by_line.get(line.id) or products[:3]
                for p_idx, product in enumerate(line_products[:3]):
                    exists_plan = (
                        db.query(ProductionPlan)
                        .filter(
                            ProductionPlan.plan_date == the_day,
                            ProductionPlan.production_line_id == line.id,
                            ProductionPlan.product_id == product.id,
                        )
                        .first()
                    )
                    plan_qty = 800 + line_idx * 40 + p_idx * 60 + (days - 1 - day_offset) * 5
                    if not exists_plan:
                        db.add(
                            ProductionPlan(
                                plan_date=the_day,
                                production_line_id=line.id,
                                product_id=product.id,
                                plan_qty=plan_qty,
                            )
                        )

                    if the_day == today:
                        day_start = datetime(the_day.year, the_day.month, the_day.day, 0, 0, 0)
                        day_end = day_start + timedelta(days=1)
                        has_hourly = (
                            db.query(ProductionOutputRecord)
                            .filter(
                                ProductionOutputRecord.production_line_id == line.id,
                                ProductionOutputRecord.product_id == product.id,
                                ProductionOutputRecord.record_at >= day_start,
                                ProductionOutputRecord.record_at < day_end,
                            )
                            .count()
                        )
                        if has_hourly < 8:
                            last_hour = min(now.hour, 20)
                            for hour in range(8, max(last_hour, 8) + 1):
                                record_at = datetime(
                                    the_day.year, the_day.month, the_day.day, hour, 0, 0
                                )
                                dup = (
                                    db.query(ProductionOutputRecord)
                                    .filter(
                                        ProductionOutputRecord.production_line_id == line.id,
                                        ProductionOutputRecord.product_id == product.id,
                                        ProductionOutputRecord.record_at == record_at,
                                    )
                                    .first()
                                )
                                if dup:
                                    continue
                                actual = 45 + line_idx * 3 + p_idx * 5 + (hour % 5) * 2
                                defect = (hour + line_idx + p_idx) % 4
                                db.add(
                                    ProductionOutputRecord(
                                        record_at=record_at,
                                        production_line_id=line.id,
                                        product_id=product.id,
                                        process_card_no=f"PC-{line.code}-{the_day:%m%d}-{hour:02d}-{p_idx}",
                                        actual_qty=actual,
                                        area_output=round(actual * 1.85, 2),
                                        defect_qty=defect,
                                        incoming_boards=actual + defect + 2,
                                    )
                                )
                    else:
                        record_at = datetime(the_day.year, the_day.month, the_day.day, 18, 0, 0)
                        exists_out = (
                            db.query(ProductionOutputRecord)
                            .filter(
                                ProductionOutputRecord.production_line_id == line.id,
                                ProductionOutputRecord.product_id == product.id,
                                ProductionOutputRecord.record_at == record_at,
                            )
                            .first()
                        )
                        if exists_out:
                            continue
                        actual = int(plan_qty * (0.88 + (p_idx % 3) * 0.03))
                        defect = 8 + line_idx + p_idx + (day_offset % 5)
                        db.add(
                            ProductionOutputRecord(
                                record_at=record_at,
                                production_line_id=line.id,
                                product_id=product.id,
                                process_card_no=f"PC-{line.code}-{the_day:%m%d}-{p_idx}",
                                actual_qty=actual,
                                area_output=round(actual * 1.85, 2),
                                defect_qty=defect,
                                incoming_boards=actual + defect + 10,
                            )
                        )

        # ---------- 今日 WIP / 负荷快照 ----------
        snapshot_at = now.replace(minute=0, second=0, microsecond=0)
        has_wip_today = (
            db.query(WipSnapshot)
            .filter(WipSnapshot.snapshot_at >= datetime.combine(today, datetime.min.time()))
            .first()
        )
        if not has_wip_today:
            for line_idx, line in enumerate(lines):
                product = (products_by_line.get(line.id) or products)[0]
                for s_idx, status in enumerate(WIP_STATUSES):
                    qty = 40 + line_idx * 15 + s_idx * 25 + (today.day % 7)
                    db.add(
                        WipSnapshot(
                            snapshot_at=snapshot_at,
                            production_line_id=line.id,
                            product_id=product.id,
                            status=status,
                            quantity=qty,
                        )
                    )
                db.add(
                    LineCapacitySnapshot(
                        snapshot_at=snapshot_at,
                        production_line_id=line.id,
                        station_name=f"{line.name}-主工位",
                        load_rate=round(72.0 + line_idx * 4.5 + (today.day % 5), 2),
                        capacity_utilization=round(68.0 + line_idx * 5.0, 2),
                    )
                )

        # ---------- 品质日汇总 ----------
        processes = ["贴片", "焊接", "AOI检测", "功能测试", "包装"]
        for day_offset in range(days - 1, -1, -1):
            the_day = today - timedelta(days=day_offset)
            for line in lines:
                for process in processes:
                    exists = (
                        db.query(QualityMetrics)
                        .filter(
                            QualityMetrics.record_date == the_day,
                            QualityMetrics.production_line == line.name,
                            QualityMetrics.process == process,
                        )
                        .first()
                    )
                    if exists:
                        continue
                    total = 800 + day_offset * 3 + _stable_int(f"{line.name}{process}{the_day}", 40, 120)
                    defect = int(total * 0.018) + (day_offset % 4)
                    scrap = max(int(total * 0.004), 1)
                    good = max(total - defect - scrap, 0)
                    db.add(
                        QualityMetrics(
                            record_date=the_day,
                            production_line=line.name,
                            process=process,
                            good_count=good,
                            defect_count=defect,
                            scrap_count=scrap,
                            total_inspected=total,
                        )
                    )

        # ---------- 设备 OEE / 产量 / 当日运行 / 近期告警 ----------
        alarm_types = ["温度过高", "振动异常", "急停触发", "润滑不足", "通信中断"]
        for eq_idx, eq in enumerate(equipment_list):
            start_at = datetime(today.year, today.month, today.day, 8, 0, 0)
            has_runtime = (
                db.query(EquipmentRuntimeLog)
                .filter(
                    EquipmentRuntimeLog.equipment_id == eq.id,
                    EquipmentRuntimeLog.start_at == start_at,
                )
                .first()
            )
            if not has_runtime:
                end_at = datetime(today.year, today.month, today.day, min(now.hour, 17), 0, 0)
                db.add(
                    EquipmentRuntimeLog(
                        equipment_id=eq.id,
                        start_at=start_at,
                        end_at=end_at if eq.status != "运行" else None,
                        status=eq.status if eq.status in ("运行", "停机", "待机", "维修") else "运行",
                        runtime_hours=round(max((end_at - start_at).seconds / 3600, 1), 2),
                    )
                )

            for day_back in range(days - 1, -1, -1):
                period_start = today - timedelta(days=day_back)
                has_oee = (
                    db.query(EquipmentOeeSnapshot)
                    .filter(
                        EquipmentOeeSnapshot.equipment_id == eq.id,
                        EquipmentOeeSnapshot.period_type == "day",
                        EquipmentOeeSnapshot.period_start == period_start,
                    )
                    .first()
                )
                if not has_oee:
                    availability = round(85.0 + (eq_idx % 7) + (day_back % 3), 2)
                    performance = round(88.0 + ((eq_idx + day_back) % 5), 2)
                    quality = round(96.0 + (eq_idx % 3) * 0.5, 2)
                    oee = round(availability * performance * quality / 10000, 2)
                    db.add(
                        EquipmentOeeSnapshot(
                            equipment_id=eq.id,
                            period_type="day",
                            period_start=period_start,
                            availability=availability,
                            performance=performance,
                            quality=quality,
                            oee=oee,
                        )
                    )
                has_out = (
                    db.query(EquipmentOutputRecord)
                    .filter(
                        EquipmentOutputRecord.equipment_id == eq.id,
                        EquipmentOutputRecord.record_date == period_start,
                    )
                    .first()
                )
                if not has_out:
                    output_qty = max(600 + eq_idx * 40 - day_back * 15 + (eq_idx % 4) * 10, 50)
                    db.add(
                        EquipmentOutputRecord(
                            equipment_id=eq.id,
                            record_date=period_start,
                            output_qty=output_qty,
                        )
                    )

            recent_alarm = (
                db.query(EquipmentAlarm)
                .filter(
                    EquipmentAlarm.equipment_id == eq.id,
                    EquipmentAlarm.occurred_at >= datetime.combine(today - timedelta(days=1), datetime.min.time()),
                )
                .first()
            )
            if not recent_alarm and eq_idx % 2 == 0:
                db.add(
                    EquipmentAlarm(
                        equipment_id=eq.id,
                        alarm_type=alarm_types[eq_idx % len(alarm_types)],
                        severity="normal",
                        occurred_at=now - timedelta(hours=2 + eq_idx),
                        cleared_at=now - timedelta(hours=1),
                        description=f"{eq.name}：{alarm_types[eq_idx % len(alarm_types)]}",
                    )
                )

        # ---------- 近几日出入库流水 ----------
        materials = db.query(Material).order_by(Material.id).all()
        locations = db.query(WarehouseLocation).order_by(WarehouseLocation.id).all()
        if materials and locations:
            today_txn = (
                db.query(InventoryTransaction)
                .filter(
                    InventoryTransaction.txn_at >= datetime.combine(today, datetime.min.time())
                )
                .first()
            )
            if not today_txn:
                sample = [
                    (0, "in", 80, 9, 12),
                    (1, "out", 40, 10, 5),
                    (2, "in", 120, 11, 20),
                    (3, "out", 25, 13, 40),
                    (4, "in", 60, 14, 15),
                    (0, "out", 18, 15, 8),
                    (5, "check", 10, 16, 0),
                ]
                for m_idx, txn_type, qty, hour, minute in sample:
                    material = materials[m_idx % len(materials)]
                    loc = locations[m_idx % len(locations)]
                    db.add(
                        InventoryTransaction(
                            material_id=material.id,
                            location_id=loc.id,
                            txn_type=txn_type,
                            quantity=qty,
                            txn_at=datetime(today.year, today.month, today.day, hour, minute, 0),
                            ref_no=f"{txn_type.upper()}-{today:%m%d}-{m_idx}",
                            remark=f"{txn_type}:{material.material_code}",
                        )
                    )
                yesterday = today - timedelta(days=1)
                y_start = datetime.combine(yesterday, datetime.min.time())
                y_end = y_start + timedelta(days=1)
                y_txn = (
                    db.query(InventoryTransaction)
                    .filter(
                        InventoryTransaction.txn_at >= y_start,
                        InventoryTransaction.txn_at < y_end,
                    )
                    .first()
                )
                if not y_txn:
                    db.add(
                        InventoryTransaction(
                            material_id=materials[0].id,
                            location_id=locations[0].id,
                            txn_type="in",
                            quantity=200,
                            txn_at=datetime(yesterday.year, yesterday.month, yesterday.day, 10, 0, 0),
                            ref_no=f"IN-{yesterday:%m%d}-0",
                            remark=f"in:{materials[0].material_code}",
                        )
                    )

        # ---------- 近几日发货 ----------
        orders = db.query(SalesOrder).order_by(SalesOrder.id).all()
        if orders:
            for day_back in range(min(days, 5) - 1, -1, -1):
                the_day = today - timedelta(days=day_back)
                shipped_at = datetime(the_day.year, the_day.month, the_day.day, 15, 0, 0)
                exists = (
                    db.query(ShipmentRecord)
                    .filter(ShipmentRecord.shipped_at == shipped_at)
                    .first()
                )
                if exists:
                    continue
                order = orders[day_back % len(orders)]
                qty = 80 + day_back * 15
                db.add(
                    ShipmentRecord(
                        sales_order_id=order.id,
                        ship_qty=qty,
                        shipped_at=shipped_at,
                    )
                )
                order.shipped_qty = (order.shipped_qty or 0) + qty

        # ---------- 近几日点检记录 ----------
        plans = db.query(InspectionPlan).order_by(InspectionPlan.id).all()
        inspectors = ["张三", "李四", "王五"]
        if plans:
            devices = db.query(Device).order_by(Device.id).all()
            for day_back in range(min(3, days) - 1, -1, -1):
                the_day = today - timedelta(days=day_back)
                if not devices:
                    break
                device = devices[day_back % len(devices)]
                plan = plans[day_back % len(plans)]
                exists = (
                    db.query(InspectionRecord)
                    .filter(
                        InspectionRecord.device_id == device.id,
                        InspectionRecord.inspect_date == the_day,
                    )
                    .first()
                )
                if exists:
                    continue
                record = InspectionRecord(
                    device_id=device.id,
                    plan_id=plan.id,
                    inspector=inspectors[day_back % len(inspectors)],
                    inspect_date=the_day,
                    status="normal",
                    remark="运行正常" if day_back else "当日点检完成",
                )
                db.add(record)
                db.flush()
                for item in plan.items[:3]:
                    db.add(
                        InspectionRecordItem(
                            record_id=record.id,
                            item_name=item.item_name,
                            standard_value=item.standard_value,
                            actual_value=item.standard_value,
                            result="ok",
                            remark=None,
                        )
                    )

        ensure_rich_work_orders(db, today=today, now=now, target_count=100)
        _rebase_live_records_to_today(db, today, now)

        db.commit()
    finally:
        db.close()


def _shift_date(value: date | None, delta: timedelta) -> date | None:
    return value + delta if value else None


def _shift_dt(value: datetime | None, delta: timedelta) -> datetime | None:
    return value + delta if value else None


def _rebase_live_records_to_today(db, today: date, now: datetime) -> None:
    """把工单/保养/维修/异常/待办/订单等业务日期整体平移到今天，当天已对齐则跳过。"""
    anchors: list[date] = []
    for ts in (
        db.query(func.max(WorkOrder.updated_at)).scalar(),
        db.query(func.max(EquipmentRepair.created_at)).scalar(),
        db.query(func.max(DashboardTodo.created_at)).scalar(),
        db.query(func.max(QualityAnomaly.discovered_at)).scalar(),
    ):
        if ts:
            anchors.append(ts.date() if hasattr(ts, "date") else ts)
    if not anchors:
        return
    delta_days = (today - max(anchors)).days
    if delta_days <= 0:
        return
    delta = timedelta(days=delta_days)

    for wo in db.query(WorkOrder).all():
        wo.start_date = _shift_date(wo.start_date, delta)
        wo.end_date = _shift_date(wo.end_date, delta)
        wo.actual_start_time = _shift_dt(wo.actual_start_time, delta)
        wo.actual_end_time = _shift_dt(wo.actual_end_time, delta)
        wo.created_at = _shift_dt(wo.created_at, delta) or now
        wo.updated_at = now

    for plan in db.query(EquipmentMaintenancePlan).all():
        plan.next_due_at = _shift_dt(plan.next_due_at, delta)
        plan.created_at = _shift_dt(plan.created_at, delta) or now
        plan.updated_at = now

    for order in db.query(EquipmentMaintenanceOrder).all():
        order.planned_start_at = _shift_dt(order.planned_start_at, delta) or now
        order.actual_start_at = _shift_dt(order.actual_start_at, delta)
        order.actual_end_at = _shift_dt(order.actual_end_at, delta)
        order.created_at = _shift_dt(order.created_at, delta) or now
        order.updated_at = now

    for repair in db.query(EquipmentRepair).all():
        repair.start_time = _shift_dt(repair.start_time, delta)
        repair.repair_completed_at = _shift_dt(repair.repair_completed_at, delta)
        repair.created_at = _shift_dt(repair.created_at, delta) or now
        repair.updated_at = now

    for anomaly in db.query(QualityAnomaly).all():
        anomaly.discovered_at = _shift_dt(anomaly.discovered_at, delta) or now

    for todo in db.query(DashboardTodo).all():
        todo.created_at = _shift_dt(todo.created_at, delta) or now

    for so in db.query(SalesOrder).all():
        so.due_date = _shift_date(so.due_date, delta) or today
        so.created_at = _shift_dt(so.created_at, delta) or now

    for bal in db.query(InventoryBalance).all():
        bal.updated_at = _shift_dt(bal.updated_at, delta) or now

    for board in db.query(KanbanBoard).all():
        board.updated_at = now

    today_start = datetime.combine(today, datetime.min.time())
    has_today_mo = (
        db.query(EquipmentMaintenanceOrder)
        .filter(EquipmentMaintenanceOrder.planned_start_at >= today_start)
        .first()
    )
    plan = (
        db.query(EquipmentMaintenancePlan)
        .filter(EquipmentMaintenancePlan.status == "enabled")
        .first()
    )
    if plan and not has_today_mo:
        exists_no = (
            db.query(EquipmentMaintenanceOrder)
            .filter(EquipmentMaintenanceOrder.order_no == f"MO-{today.strftime('%Y%m%d')}-0001")
            .first()
        )
        if not exists_no:
            db.add(
                EquipmentMaintenanceOrder(
                    plan_id=plan.id,
                    equipment_id=plan.equipment_id,
                    order_no=f"MO-{today.strftime('%Y%m%d')}-0001",
                    status="pending",
                    planned_start_at=now.replace(minute=0, second=0, microsecond=0),
                )
            )


# 工单分析用状态分布（合计 100）
_WORK_ORDER_STATUS_MIX = (
    ["pending"] * 18
    + ["in_progress"] * 28
    + ["completed"] * 24
    + ["closed"] * 18
    + ["cancelled"] * 12
)
_WORK_ORDER_PRIORITIES = ["urgent", "high", "high", "normal", "normal", "normal", "low"]
_WORK_ORDER_ASSIGNEES = [
    "张三",
    "李四",
    "王五",
    "赵六",
    "钱七",
    "孙八",
    "周九",
    "吴十",
    "郑十一",
    "冯十二",
]
_WORK_ORDER_REMARKS = [
    "正常排产",
    "客户加急订单",
    "换线首件确认中",
    "物料齐套后开工",
    "节拍偏慢，跟进中",
    "已完成入库待关闭",
    "质检复核后关闭",
    "客户取消，工单作废",
    "设备故障暂停后恢复",
    "跨产线协作工单",
    "今日计划内工单",
    "昨日结转在制",
]


def _work_order_profile(idx: int, today: date, now: datetime) -> dict:
    """按序号生成一条可分析的工单字段画像（对齐今天、覆盖多状态）。"""
    status = _WORK_ORDER_STATUS_MIX[idx % len(_WORK_ORDER_STATUS_MIX)]
    priority = _WORK_ORDER_PRIORITIES[idx % len(_WORK_ORDER_PRIORITIES)]
    if status in ("pending", "in_progress") and idx % 11 == 0:
        priority = "urgent"
    plan_qty = 200 + (idx % 20) * 50 + (idx % 7) * 10
    hour = 8 + (idx % 10)
    minute = (idx * 7) % 60

    if status == "pending":
        start_off = -(idx % 3)  # 今天或近两日开立
        end_off = 2 + (idx % 5)
        actual = 0
        actual_start = None
        actual_end = None
        created_off = max(start_off + 1, 1)
    elif status == "in_progress":
        start_off = idx % 4  # 0~3 天前开工
        # 约 1/4 逾期（计划结束早于今天）
        end_off = -1 - (idx % 2) if idx % 4 == 0 else 1 + (idx % 4)
        ratio = 0.25 + (idx % 8) * 0.08
        actual = max(int(plan_qty * ratio), 1)
        actual_start = datetime(
            today.year, today.month, today.day, hour, minute, 0
        ) - timedelta(days=start_off)
        actual_end = None
        created_off = start_off + 1
    elif status == "completed":
        start_off = 1 + (idx % 5)
        end_off = -(idx % 2)  # 今天或昨天计划结束
        finish_days_ago = abs(end_off)
        over_under = 1.0 + ((idx % 5) - 2) * 0.03
        actual = max(int(plan_qty * over_under), 1)
        actual_start = datetime(
            today.year, today.month, today.day, 8, minute, 0
        ) - timedelta(days=start_off)
        actual_end = datetime(
            today.year, today.month, today.day, min(hour + 2, 20), minute, 0
        ) - timedelta(days=finish_days_ago)
        created_off = start_off + 1
    elif status == "closed":
        start_off = 3 + (idx % 7)
        end_off = -(1 + idx % 4)
        actual = plan_qty + (idx % 3) * 5
        actual_start = datetime(
            today.year, today.month, today.day, 8, 0, 0
        ) - timedelta(days=start_off)
        actual_end = datetime(
            today.year, today.month, today.day, 16, minute, 0
        ) - timedelta(days=abs(end_off))
        created_off = start_off + 2
    else:  # cancelled
        start_off = idx % 6
        end_off = 1 + (idx % 3)
        actual = 0 if idx % 2 == 0 else max(int(plan_qty * 0.1), 1)
        actual_start = None
        if actual > 0:
            actual_start = datetime(
                today.year, today.month, today.day, 9, minute, 0
            ) - timedelta(days=start_off)
        actual_end = None
        created_off = start_off + 1

    return {
        "status": status,
        "priority": priority,
        "plan_quantity": plan_qty,
        "actual_quantity": actual,
        "current_process": derive_current_process(status, plan_qty, actual),
        "assignee": _WORK_ORDER_ASSIGNEES[idx % len(_WORK_ORDER_ASSIGNEES)],
        "start_date": today - timedelta(days=start_off),
        "end_date": today + timedelta(days=end_off),
        "actual_start_time": actual_start,
        "actual_end_time": actual_end,
        "remark": _WORK_ORDER_REMARKS[idx % len(_WORK_ORDER_REMARKS)],
        "created_at": now - timedelta(days=created_off, hours=idx % 12),
        "updated_at": now - timedelta(minutes=idx % 90),
    }


def ensure_rich_work_orders(
    db,
    *,
    today: date | None = None,
    now: datetime | None = None,
    target_count: int = 100,
) -> None:
    """补齐并刷新工单至 target_count 条：多状态/优先级/产线，日期对齐今天。可重复调用。"""
    today = today or date.today()
    now = now or datetime.now()
    lines = db.query(ProductionLine).order_by(ProductionLine.id).all()
    products = db.query(Product).order_by(Product.id).all()
    if not lines or not products:
        return

    products_by_line: dict[int, list[Product]] = {ln.id: [] for ln in lines}
    for product in products:
        if product.default_line_id in products_by_line:
            products_by_line[product.default_line_id].append(product)

    existing = db.query(WorkOrder).order_by(WorkOrder.id).all()
    # 刷新已有工单画像，保证分析维度齐全且对齐今天
    for idx, wo in enumerate(existing):
        line = lines[idx % len(lines)]
        line_products = products_by_line.get(line.id) or products
        product = line_products[idx % len(line_products)]
        profile = _work_order_profile(idx, today, now)
        wo.product_name = product.product_name
        wo.product_code = product.product_code
        wo.production_line = line.name
        for key, value in profile.items():
            setattr(wo, key, value)

    need = target_count - len(existing)
    if need <= 0:
        return

    used_nos = {wo.order_no for wo in existing}
    next_seq = 1
    for i in range(need):
        idx = len(existing) + i
        while True:
            order_no = f"WO-AN-{next_seq:03d}"
            next_seq += 1
            if order_no not in used_nos:
                used_nos.add(order_no)
                break
        line = lines[idx % len(lines)]
        line_products = products_by_line.get(line.id) or products
        product = line_products[idx % len(line_products)]
        profile = _work_order_profile(idx, today, now)
        db.add(
            WorkOrder(
                order_no=order_no,
                product_name=product.product_name,
                product_code=product.product_code,
                production_line=line.name,
                **profile,
            )
        )


def seed_rich_work_orders(target_count: int = 100) -> None:
    """独立入口：补齐丰富工单数据（供脚本/手工触发）。"""
    db = SessionLocal()
    try:
        ensure_rich_work_orders(db, target_count=target_count)
        db.commit()
    finally:
        db.close()

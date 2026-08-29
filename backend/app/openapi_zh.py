"""OpenAPI 中文说明：接口摘要与分组标签。

在 FastAPI 的 /docs（Swagger）与 /redoc 中展示中文，便于业务人员阅读。
"""

from __future__ import annotations

# OpenAPI 分组标签（Swagger 左侧分类）
OPENAPI_TAGS: list[dict] = [
    {"name": "系统", "description": "健康检查等系统级接口"},
    {"name": "认证", "description": "登录与当前用户信息"},
    {"name": "工作台", "description": "首页工作台统计、待办与制造看板数据"},
    {"name": "生产工单", "description": "生产工单的增删改查与状态变更"},
    {"name": "生产总览", "description": "生产概览 KPI、趋势与产线负荷（查库聚合）"},
    {"name": "生产看板", "description": "车间生产看板实时展示数据"},
    {"name": "综合看板", "description": "生产/品质/设备/交付/物料五大模块综合监控"},
    {"name": "看板配置", "description": "看板元数据配置管理"},
    {"name": "点检设备", "description": "点检用设备主数据"},
    {"name": "设备点检", "description": "点检计划、记录与统计"},
    {"name": "设备台账", "description": "设备台账 CRUD、导入导出"},
    {"name": "设备保养", "description": "保养计划、工单、派工执行与到期预警"},
    {"name": "设备维修", "description": "维修工单与配件明细"},
    {"name": "设备看板", "description": "设备运行状态、OEE、利用率、告警与产量"},
    {"name": "品质管理", "description": "品质 KPI、趋势、不良分布与异常"},
    {"name": "报表中心", "description": "MES 报表查询与导出"},
    {"name": "仓储看板", "description": "库存 KPI、出入库趋势、库位与物料明细"},
]

# (HTTP方法大写, 路径) -> {summary, description}
# 路径需与 OpenAPI 中的 path 一致（含路径参数花括号）
API_ZH: dict[tuple[str, str], dict[str, str]] = {
    # ----- 系统 -----
    ("GET", "/api/health"): {
        "summary": "健康检查",
        "description": "探测后端服务是否正常运行，无需登录。返回 `{\"status\":\"ok\"}`。",
    },
    # ----- 认证 -----
    ("POST", "/api/auth/login"): {
        "summary": "用户登录",
        "description": (
            "使用用户名、密码和企业编码登录。"
            "校验通过后返回 JWT `access_token`，后续接口请在 Header 中携带："
            "`Authorization: Bearer <token>`。"
        ),
    },
    ("GET", "/api/auth/me"): {
        "summary": "获取当前登录用户",
        "description": "根据 Token 返回当前用户的 id、用户名和角色信息。",
    },
    # ----- 工作台 -----
    ("GET", "/api/dashboard"): {
        "summary": "获取工作台首页数据",
        "description": (
            "从工单、产量事实、品质异常、待办等表聚合首页数据，包括："
            "待处理工单数、今日产量、活跃异常、本月完成率、产量趋势、工单状态分布、待办列表，"
            "以及制造看板（月/日产量、效率、异常占比等）。"
        ),
    },
    # ----- 生产工单 -----
    ("GET", "/api/work-orders"): {
        "summary": "查询生产工单列表",
        "description": "分页查询生产工单，支持按状态、产线、关键词等条件筛选（以实际 Query 参数为准）。",
    },
    ("GET", "/api/work-orders/{work_order_id}"): {
        "summary": "获取生产工单详情",
        "description": "按工单 ID 返回单条生产工单的完整信息。",
    },
    ("POST", "/api/work-orders"): {
        "summary": "新建生产工单",
        "description": "创建一条生产工单并写入 `work_orders` 表。",
    },
    ("PUT", "/api/work-orders/{work_order_id}"): {
        "summary": "更新生产工单",
        "description": "按 ID 全量/部分更新工单字段。",
    },
    ("PATCH", "/api/work-orders/{work_order_id}/status"): {
        "summary": "变更生产工单状态",
        "description": "仅更新工单状态（如 pending / in_progress / completed 等）。开工时若未记录实际开始时间则自动写入，完工时若未记录实际结束时间则自动写入。",
    },
    ("DELETE", "/api/work-orders/{work_order_id}"): {
        "summary": "删除生产工单",
        "description": "按 ID 删除生产工单。",
    },
    # ----- 生产总览 -----
    ("GET", "/api/production/overview"): {
        "summary": "生产概览（经典版）",
        "description": (
            "从当日产量事实表聚合完成数、面积产出、不良率、来料板数，"
            "并返回时段完成曲线与明细行。"
        ),
    },
    ("GET", "/api/production/overview-v2"): {
        "summary": "生产概览（联动版）",
        "description": (
            "支持按时间粒度（日/周/月）与产线筛选。"
            "从生产计划、产量、WIP、负荷、工单、品质等表聚合 KPI、达成对比、产出趋势、"
            "工单状态、产线负荷、在制品分布、品质与设备利用率。"
        ),
    },
    # ----- 生产看板 -----
    ("GET", "/api/kanban/production"): {
        "summary": "生产看板数据",
        "description": (
            "车间大屏用生产看板：从当日产量事实表聚合分时累计产量、不良率、"
            "达成率及流程卡明细。"
        ),
    },
    # ----- 综合看板 -----
    ("GET", "/api/kanban/general"): {
        "summary": "综合看板数据",
        "description": (
            "五大模块一次返回：生产进度、品质概览、设备监控、订单交付、物料库存。"
            "全部由工单、计划、产量、品质、设备、销售订单、发货、库存等表聚合。"
        ),
    },
    # ----- 看板配置 -----
    ("GET", "/api/kanban-boards"): {
        "summary": "查询看板配置列表",
        "description": "分页查询看板元数据配置（`kanban_boards` 表）。",
    },
    ("GET", "/api/kanban-boards/{board_id}"): {
        "summary": "获取看板配置详情",
        "description": "按 ID 返回单条看板配置。",
    },
    ("POST", "/api/kanban-boards"): {
        "summary": "新建看板配置",
        "description": "创建看板配置记录。",
    },
    ("PUT", "/api/kanban-boards/{board_id}"): {
        "summary": "更新看板配置",
        "description": "按 ID 更新看板配置字段。",
    },
    ("PATCH", "/api/kanban-boards/{board_id}/status"): {
        "summary": "变更看板配置状态",
        "description": "仅更新看板状态（如 draft / published）。",
    },
    ("DELETE", "/api/kanban-boards/{board_id}"): {
        "summary": "删除看板配置",
        "description": "按 ID 删除看板配置。",
    },
    # ----- 点检设备 -----
    ("GET", "/api/devices"): {
        "summary": "查询点检设备列表",
        "description": "返回点检域设备及设备类型列表（`devices` / `device_types`）。",
    },
    # ----- 设备点检 -----
    ("GET", "/api/inspection/plans"): {
        "summary": "查询点检计划列表",
        "description": "分页查询点检计划及其检查项。",
    },
    ("POST", "/api/inspection/plans"): {
        "summary": "新建点检计划",
        "description": "创建点检计划及下属检查项。",
    },
    ("PUT", "/api/inspection/plans/{plan_id}"): {
        "summary": "更新点检计划",
        "description": "更新点检计划内容与检查项。",
    },
    ("PATCH", "/api/inspection/plans/{plan_id}/toggle"): {
        "summary": "启用/停用点检计划",
        "description": "切换计划的 `is_active` 状态。",
    },
    ("DELETE", "/api/inspection/plans/{plan_id}"): {
        "summary": "删除点检计划",
        "description": "删除点检计划及其检查项。",
    },
    ("GET", "/api/inspection/records"): {
        "summary": "查询点检记录列表",
        "description": "分页查询点检执行记录，可按设备、日期等筛选。",
    },
    ("POST", "/api/inspection/records"): {
        "summary": "新建点检记录",
        "description": "提交一次点检执行结果及各检查项实测值。",
    },
    ("GET", "/api/inspection/records/{record_id}"): {
        "summary": "获取点检记录详情",
        "description": "按 ID 返回点检记录及明细项。",
    },
    ("PUT", "/api/inspection/records/{record_id}"): {
        "summary": "更新点检记录",
        "description": "修改点检记录内容与明细。",
    },
    ("GET", "/api/inspection/dashboard/stats"): {
        "summary": "点检看板统计",
        "description": "从点检计划与记录表聚合完成率、异常数等统计指标。",
    },
    ("GET", "/api/inspection/plan-items/by-device/{device_id}"): {
        "summary": "按设备获取点检项模板",
        "description": "根据设备匹配适用点检计划，返回待执行检查项列表，供现场执行页使用。",
    },
    # ----- 设备台账 -----
    ("GET", "/api/equipment"): {
        "summary": "查询设备台账列表",
        "description": "分页查询设备台账，支持状态、部门、关键词等筛选。",
    },
    ("GET", "/api/equipment/export"): {
        "summary": "导出设备台账 Excel",
        "description": "将当前筛选条件下的设备台账导出为 Excel 文件下载。",
    },
    ("GET", "/api/equipment/{equipment_id}"): {
        "summary": "获取设备台账详情",
        "description": "按 ID 返回单台设备台账信息。",
    },
    ("POST", "/api/equipment"): {
        "summary": "新建设备台账",
        "description": "新增一台设备到台账表。",
    },
    ("PUT", "/api/equipment/{equipment_id}"): {
        "summary": "更新设备台账",
        "description": "按 ID 更新设备台账字段。",
    },
    ("DELETE", "/api/equipment/{equipment_id}"): {
        "summary": "删除设备台账",
        "description": "按 ID 删除设备（需注意关联保养/维修数据）。",
    },
    ("POST", "/api/equipment/import"): {
        "summary": "导入设备台账 Excel",
        "description": "上传 Excel 批量导入/更新设备台账，返回成功与失败明细。",
    },
    # ----- 设备保养 -----
    ("GET", "/api/equipment-maintenance/plans"): {
        "summary": "查询保养计划列表",
        "description": "分页查询设备保养计划。",
    },
    ("GET", "/api/equipment-maintenance/plans/{plan_id}"): {
        "summary": "获取保养计划详情",
        "description": "按 ID 返回保养计划详情。",
    },
    ("POST", "/api/equipment-maintenance/plans"): {
        "summary": "新建保养计划",
        "description": "为指定设备创建周期性保养计划。",
    },
    ("PUT", "/api/equipment-maintenance/plans/{plan_id}"): {
        "summary": "更新保养计划",
        "description": "更新保养计划周期、项目与状态等。",
    },
    ("DELETE", "/api/equipment-maintenance/plans/{plan_id}"): {
        "summary": "删除保养计划",
        "description": "删除指定保养计划。",
    },
    ("GET", "/api/equipment-maintenance/orders"): {
        "summary": "查询保养工单列表",
        "description": "分页查询保养工单。",
    },
    ("GET", "/api/equipment-maintenance/orders/{order_id}"): {
        "summary": "获取保养工单详情",
        "description": "按 ID 返回保养工单详情。",
    },
    ("POST", "/api/equipment-maintenance/orders"): {
        "summary": "新建保养工单",
        "description": "手工创建保养工单。",
    },
    ("POST", "/api/equipment-maintenance/orders/generate-from-plan/{plan_id}"): {
        "summary": "按计划生成保养工单",
        "description": "根据保养计划自动生成一条待执行保养工单。",
    },
    ("PUT", "/api/equipment-maintenance/orders/{order_id}"): {
        "summary": "更新保养工单",
        "description": "更新保养工单字段。",
    },
    ("DELETE", "/api/equipment-maintenance/orders/{order_id}"): {
        "summary": "删除保养工单",
        "description": "删除指定保养工单。",
    },
    ("POST", "/api/equipment-maintenance/orders/{order_id}/dispatch"): {
        "summary": "派工保养工单",
        "description": "为保养工单指定执行人并进入待执行状态。",
    },
    ("POST", "/api/equipment-maintenance/orders/{order_id}/start"): {
        "summary": "开始执行保养工单",
        "description": "标记保养工单开始执行，记录实际开始时间。",
    },
    ("POST", "/api/equipment-maintenance/orders/{order_id}/execute"): {
        "summary": "提交保养执行结果",
        "description": "填写保养项目执行结果并完成工单。",
    },
    ("GET", "/api/equipment-maintenance/alerts"): {
        "summary": "保养到期预警",
        "description": "查询即将到期或已逾期的保养计划/工单预警列表。",
    },
    ("GET", "/api/equipment-maintenance/equipment/{equipment_id}/status"): {
        "summary": "单台设备保养状态",
        "description": "汇总指定设备的保养计划进度与下次到期时间。",
    },
    # ----- 设备维修 -----
    ("GET", "/api/equipment-repairs"): {
        "summary": "查询维修工单列表",
        "description": "分页查询设备维修工单，支持状态、紧急度等筛选。",
    },
    ("GET", "/api/equipment-repairs/{repair_id}"): {
        "summary": "获取维修工单详情",
        "description": "返回维修工单及更换配件明细。",
    },
    ("GET", "/api/equipment-repairs/{repair_id}/parts"): {
        "summary": "查询维修配件明细",
        "description": "仅返回某维修单下的配件更换列表。",
    },
    ("POST", "/api/equipment-repairs"): {
        "summary": "新建维修工单",
        "description": "登记设备故障并创建维修工单（可含配件）。",
    },
    ("PUT", "/api/equipment-repairs/{repair_id}"): {
        "summary": "更新维修工单",
        "description": "更新维修状态、维修说明、配件等。",
    },
    ("DELETE", "/api/equipment-repairs/{repair_id}"): {
        "summary": "删除维修工单",
        "description": "删除维修工单及其配件明细。",
    },
    # ----- 设备看板 -----
    ("GET", "/api/device/status/summary"): {
        "summary": "设备状态汇总",
        "description": "按运行/停机/待机/维修统计设备台数与占比（来自 `equipment` 表）。",
    },
    ("GET", "/api/device/oee"): {
        "summary": "设备综合 OEE",
        "description": "对当日（或最近）OEE 快照求平均，返回可用率、性能率、质量率与 OEE。",
    },
    ("GET", "/api/device/list"): {
        "summary": "设备看板列表",
        "description": "分页列出设备，附累计运行小时与最近告警时间。",
    },
    ("GET", "/api/device/utilization"): {
        "summary": "设备利用率趋势",
        "description": "按日/周/月返回设备可用率（利用率）趋势序列，数据来自 OEE 快照。",
    },
    ("GET", "/api/device/alarms/trend"): {
        "summary": "设备告警趋势",
        "description": "近 10 日告警数量趋势及按告警类型的分布（`equipment_alarms`）。",
    },
    ("GET", "/api/device/output"): {
        "summary": "设备产量排行",
        "description": "返回各设备今日与本周产量（`equipment_output_records`），按今日产量排序。",
    },
    # ----- 品质 -----
    ("GET", "/api/quality/kpi"): {
        "summary": "品质 KPI",
        "description": "从品质日汇总表计算良率、不良率、报废率等核心指标。",
    },
    ("GET", "/api/quality/trend"): {
        "summary": "品质趋势",
        "description": "按日期返回良率/不良趋势曲线数据。",
    },
    ("GET", "/api/quality/process-yield"): {
        "summary": "工序良率",
        "description": "按工序维度汇总良率对比。",
    },
    ("GET", "/api/quality/defect-distribution"): {
        "summary": "不良分布",
        "description": "按缺陷类型汇总不良数量分布。",
    },
    ("GET", "/api/quality/anomalies"): {
        "summary": "品质异常列表",
        "description": "查询品质异常明细；支持 status 筛选与 page/page_size 分页（entity=quality-anomalies）。",
    },
    ("GET", "/api/quality/top-defects"): {
        "summary": "Top 不良项",
        "description": "返回数量最高的不良类型排行。",
    },
    # ----- 仓储 -----
    ("GET", "/api/warehouse/dashboard"): {
        "summary": "仓储看板数据",
        "description": (
            "从仓库、库位、物料、库存余额、库存流水表聚合："
            "总库存、SKU 数、库位使用率、周转率、出入库趋势、预警、库位分布、"
            "实时流水与物料明细表。"
        ),
    },
    ("GET", "/api/warehouse/inventory-stock"): {
        "summary": "物料库存列表",
        "description": (
            "分页查询 inventory_stock 表，支持按物料编码、物料名称、仓库名称筛选；"
            "返回库存数量、单位、安全库存、更新时间等字段。"
        ),
    },
    ("GET", "/api/warehouse/warehouses"): {
        "summary": "仓库下拉选项",
        "description": "返回全部仓库，供物料库存筛选使用。",
    },
    ("GET", "/api/warehouse/materials"): {
        "summary": "物料下拉选项",
        "description": "返回全部物料主数据，供入库表单选择物料。",
    },
    ("GET", "/api/warehouse/locations"): {
        "summary": "库位下拉选项",
        "description": "返回库位列表，可按 warehouse_id 筛选，供入库表单选择库位。",
    },
    ("GET", "/api/warehouse/material-inbound"): {
        "summary": "物料入库列表",
        "description": (
            "分页查询 material_inbounds 表，支持按入库单号、物料编码/名称、"
            "状态（pending=待入库/completed=已入库）、入库日期范围筛选。"
        ),
    },
    ("POST", "/api/warehouse/material-inbound"): {
        "summary": "新增物料入库",
        "description": (
            "创建入库单并写入 material_inbounds 表；"
            "状态为 completed（已入库）时同步更新 inventory_balances、"
            "inventory_transactions 与 inventory_stock。"
        ),
    },
    # ----- 报表中心 -----
    ("GET", "/api/reports/wip"): {
        "summary": "在制品报表",
        "description": (
            "按工单维度查询在制品（wip 口径：未完工且非取消）。"
            "在制数量 = 计划数量 - 实际数量；"
            "支持按状态、工序、计划开始/结束日期筛选与分页。"
        ),
    },
    ("GET", "/api/reports/wip/processes"): {
        "summary": "在制品报表工序选项",
        "description": "返回标准工序列表，供报表筛选下拉使用。",
    },
    ("GET", "/api/reports/daily-output"): {
        "summary": "日产报表",
        "description": (
            "按生产日期、产线、产品聚合日产量（计划/实际/不良/达成率/不良率）。"
            "默认近 7 日；支持日期范围、产线筛选与分页。报表中心「日产报表」页使用本接口。"
        ),
    },
    ("GET", "/api/reports/daily-output/lines"): {
        "summary": "日产报表产线选项",
        "description": "返回产线名称列表，供日产报表筛选下拉使用。",
    },
}

# 路由模块 tags 中文映射（用于把代码里的英文 tag 替换进 OpenAPI）
TAG_ZH_MAP: dict[str, str] = {
    "auth": "认证",
    "dashboard": "工作台",
    "work-orders": "生产工单",
    "production": "生产总览",
    "kanban-production": "生产看板",
    "kanban-general": "综合看板",
    "kanban-boards": "看板配置",
    "devices": "点检设备",
    "inspection": "设备点检",
    "equipment": "设备台账",
    "equipment-maintenance": "设备保养",
    "设备维修": "设备维修",
    "device-dashboard": "设备看板",
    "quality": "品质管理",
    "reports": "报表中心",
    "warehouse": "仓储管理",
}


def apply_chinese_openapi(schema: dict) -> dict:
    """就地增强 OpenAPI schema：中文 summary / description / tags。"""
    paths = schema.get("paths") or {}
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        for method, operation in methods.items():
            if method.startswith("x-") or not isinstance(operation, dict):
                continue
            key = (method.upper(), path)
            meta = API_ZH.get(key)
            if meta:
                operation["summary"] = meta["summary"]
                operation["description"] = meta["description"]
            # 标签中文化
            tags = operation.get("tags") or []
            operation["tags"] = [TAG_ZH_MAP.get(t, t) for t in tags]
            if path == "/api/health":
                operation["tags"] = ["系统"]
    return schema

"""综合看板 API — 五大模块综合数据"""

from fastapi import APIRouter, Depends

from app.auth import get_current_user
from app.models import User
from app.schemas import (
    CompKanbanDefectItem,
    CompKanbanDeviceAlert,
    CompKanbanDeviceCard,
    CompKanbanDeviceMonitor,
    CompKanbanLineStatus,
    CompKanbanMaterialInventory,
    CompKanbanMaterialItem,
    CompKanbanOrderDelivery,
    CompKanbanOverdueOrder,
    CompKanbanProductionProgress,
    CompKanbanQualityOverview,
    CompKanbanShipmentStats,
    CompKanbanStatusPie,
    CompKanbanTrendPoint,
    ComprehensiveKanbanResponse,
)

router = APIRouter(prefix="/api/kanban", tags=["kanban-general"])


def _mock_production_progress() -> CompKanbanProductionProgress:
    return CompKanbanProductionProgress(
        active_orders=47,
        completion_rate=82.5,
        schedule_achievement_trend=[
            CompKanbanTrendPoint(label="08-01", value=78.0),
            CompKanbanTrendPoint(label="08-02", value=81.2),
            CompKanbanTrendPoint(label="08-03", value=79.5),
            CompKanbanTrendPoint(label="08-04", value=83.1),
            CompKanbanTrendPoint(label="08-05", value=85.0),
            CompKanbanTrendPoint(label="08-06", value=82.8),
            CompKanbanTrendPoint(label="08-07", value=82.5),
        ],
        line_status=[
            CompKanbanLineStatus(line_name="SMT-1线", in_production=12, completed=340, pending=5),
            CompKanbanLineStatus(line_name="SMT-2线", in_production=8, completed=285, pending=3),
            CompKanbanLineStatus(line_name="DIP线", in_production=10, completed=412, pending=7),
            CompKanbanLineStatus(line_name="组装线", in_production=11, completed=398, pending=4),
            CompKanbanLineStatus(line_name="测试线", in_production=6, completed=520, pending=2),
        ],
    )


def _mock_quality_overview() -> CompKanbanQualityOverview:
    return CompKanbanQualityOverview(
        yield_trend=[
            CompKanbanTrendPoint(label="08-01", value=96.2),
            CompKanbanTrendPoint(label="08-02", value=95.8),
            CompKanbanTrendPoint(label="08-03", value=96.5),
            CompKanbanTrendPoint(label="08-04", value=95.1),
            CompKanbanTrendPoint(label="08-05", value=96.8),
            CompKanbanTrendPoint(label="08-06", value=97.0),
            CompKanbanTrendPoint(label="08-07", value=96.4),
        ],
        yield_target=95.0,
        first_pass_rate=92.8,
        defect_distribution=[
            CompKanbanDefectItem(name="开路", value=128),
            CompKanbanDefectItem(name="短路", value=95),
            CompKanbanDefectItem(name="残铜", value=72),
            CompKanbanDefectItem(name="缺口", value=58),
            CompKanbanDefectItem(name="其它", value=41),
        ],
    )


def _mock_device_monitor() -> CompKanbanDeviceMonitor:
    return CompKanbanDeviceMonitor(
        devices=[
            CompKanbanDeviceCard(code="EQ-001", name="1号CNC加工中心", utilization=88.5, status="运行"),
            CompKanbanDeviceCard(code="EQ-002", name="2号CNC加工中心", utilization=82.1, status="运行"),
            CompKanbanDeviceCard(code="EQ-003", name="1号注塑机", utilization=45.2, status="停机"),
            CompKanbanDeviceCard(code="EQ-004", name="自动包装线", utilization=0.0, status="维修"),
            CompKanbanDeviceCard(code="EQ-005", name="精密磨床", utilization=76.8, status="运行"),
            CompKanbanDeviceCard(code="EQ-006", name="冲压机A", utilization=60.3, status="待机"),
            CompKanbanDeviceCard(code="EQ-007", name="激光切割机", utilization=91.2, status="运行"),
            CompKanbanDeviceCard(code="EQ-008", name="折弯机B", utilization=55.4, status="待机"),
        ],
        status_distribution=[
            CompKanbanStatusPie(name="运行", value=4, color="#52c41a"),
            CompKanbanStatusPie(name="待机", value=2, color="#faad14"),
            CompKanbanStatusPie(name="维修", value=1, color="#fa8c16"),
            CompKanbanStatusPie(name="停机", value=1, color="#ff4d4f"),
        ],
        alerts=[
            CompKanbanDeviceAlert(
                id=1,
                device_code="EQ-004",
                device_name="自动包装线",
                alert_type="传动故障",
                severity="urgent",
                time="08:10",
                description="传送带跑偏严重，驱动辊筒磨损异响",
            ),
            CompKanbanDeviceAlert(
                id=2,
                device_code="EQ-003",
                device_name="1号注塑机",
                alert_type="液压故障",
                severity="high",
                time="07:45",
                description="液压系统压力不稳定，合模异响",
            ),
            CompKanbanDeviceAlert(
                id=3,
                device_code="EQ-001",
                device_name="1号CNC加工中心",
                alert_type="控制系统",
                severity="normal",
                time="06:30",
                description="控制系统偶尔黑屏重启，待排查",
            ),
        ],
    )


def _mock_order_delivery() -> CompKanbanOrderDelivery:
    return CompKanbanOrderDelivery(
        delivery_rate=88.2,
        monthly_trend=[
            CompKanbanTrendPoint(label="1月", value=90.5),
            CompKanbanTrendPoint(label="2月", value=87.3),
            CompKanbanTrendPoint(label="3月", value=91.2),
            CompKanbanTrendPoint(label="4月", value=85.8),
            CompKanbanTrendPoint(label="5月", value=89.0),
            CompKanbanTrendPoint(label="6月", value=92.1),
            CompKanbanTrendPoint(label="7月", value=86.5),
            CompKanbanTrendPoint(label="8月", value=88.2),
        ],
        overdue_orders=[
            CompKanbanOverdueOrder(order_no="WO-2024-0876", customer="深圳华强电子", overdue_days=4, status="生产中"),
            CompKanbanOverdueOrder(order_no="WO-2024-0891", customer="东莞信科", overdue_days=2, status="待发货"),
            CompKanbanOverdueOrder(order_no="WO-2024-0885", customer="惠州威博", overdue_days=1, status="品质检验"),
        ],
        shipment_stats=CompKanbanShipmentStats(this_week=1850, this_month=7820),
    )


def _mock_material_inventory() -> CompKanbanMaterialInventory:
    return CompKanbanMaterialInventory(
        critical_materials=[
            CompKanbanMaterialItem(name="FR4基板(1.6mm)", current_stock=3200, safety_line=1000, max_stock=5000, status="normal"),
            CompKanbanMaterialItem(name="铜箔(35μm)", current_stock=850, safety_line=800, max_stock=3000, status="warning"),
            CompKanbanMaterialItem(name="阻焊油墨(绿)", current_stock=420, safety_line=600, max_stock=2000, status="shortage"),
            CompKanbanMaterialItem(name="干膜", current_stock=2800, safety_line=1000, max_stock=4000, status="normal"),
            CompKanbanMaterialItem(name="金盐", current_stock=180, safety_line=150, max_stock=500, status="warning"),
            CompKanbanMaterialItem(name="钻孔刀具(0.3mm)", current_stock=5200, safety_line=2000, max_stock=8000, status="normal"),
        ],
        shortage_alerts=[
            "阻焊油墨(绿) 库存仅420单位，低于安全线600",
            "铜箔(35μm) 库存接近安全线，建议本周补货",
            "金盐 库存水位偏低，当前180单位",
        ],
        turnover_days_trend=[
            CompKanbanTrendPoint(label="第1周", value=28.5),
            CompKanbanTrendPoint(label="第2周", value=26.8),
            CompKanbanTrendPoint(label="第3周", value=30.2),
            CompKanbanTrendPoint(label="第4周", value=27.1),
            CompKanbanTrendPoint(label="第5周", value=25.4),
            CompKanbanTrendPoint(label="第6周", value=24.9),
            CompKanbanTrendPoint(label="第7周", value=23.6),
            CompKanbanTrendPoint(label="第8周", value=22.8),
        ],
    )


@router.get("/general", response_model=ComprehensiveKanbanResponse)
def get_comprehensive_kanban(_current_user: User = Depends(get_current_user)):
    return ComprehensiveKanbanResponse(
        production_progress=_mock_production_progress(),
        quality_overview=_mock_quality_overview(),
        device_monitor=_mock_device_monitor(),
        order_delivery=_mock_order_delivery(),
        material_inventory=_mock_material_inventory(),
    )

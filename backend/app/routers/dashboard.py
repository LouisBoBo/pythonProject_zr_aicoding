from fastapi import APIRouter, Depends

from app.auth import get_current_user
from app.models import User
from app.schemas import (
    AnomalySegment,
    DashboardResponse,
    DashboardStatItem,
    HourlyStats,
    ManufacturingDashboard,
    ProductionTrendPoint,
    TodoItem,
    WorkOrderStatusItem,
)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _mock_manufacturing_data() -> ManufacturingDashboard:
    return ManufacturingDashboard(
        display_date="2022.12.30",
        monthly_output=3535,
        last_month_output=4590,
        daily_current=1810,
        daily_target=2500,
        efficiency_count=197,
        efficiency_rate=85,
        efficiency_trend=[420, 480, 520, 610, 580, 640, 720, 680, 750, 800, 760, 790],
        anomaly_percent=81,
        anomaly_segments=[
            AnomalySegment(name="10", value=10),
            AnomalySegment(name="20", value=20),
            AnomalySegment(name="30", value=30),
            AnomalySegment(name="40", value=40),
        ],
        production_trend_value=4316.0,
        production_trend=[3200, 3450, 3680, 3900, 4050, 4180, 4250, 4316],
        hourly_avg=20.45,
        hourly_bars=[18, 22, 15, 12, 10, 12, 8, 5, 6, 10, 18, 25],
        hourly_output_trend=[150, 375, 420, 500, 160, 140],
        hourly_stats=HourlyStats(
            production_time="7:08",
            daily_output=525,
            daily_avg=354,
        ),
    )


def _mock_dashboard_data() -> DashboardResponse:
    return DashboardResponse(
        stats=[
            DashboardStatItem(
                key="pending_orders",
                label="待处理工单",
                value=23,
                unit="个",
                trend="+3",
            ),
            DashboardStatItem(
                key="today_output",
                label="今日产量",
                value=1847,
                unit="件",
                trend="+12%",
            ),
            DashboardStatItem(
                key="active_exceptions",
                label="活跃异常",
                value=5,
                unit="项",
                trend="-2",
            ),
            DashboardStatItem(
                key="monthly_completion",
                label="本月完成率",
                value=94.6,
                unit="%",
                trend="+1.2%",
            ),
        ],
        production_trend=[
            ProductionTrendPoint(date="08-01", output=1520),
            ProductionTrendPoint(date="08-02", output=1680),
            ProductionTrendPoint(date="08-03", output=1450),
            ProductionTrendPoint(date="08-04", output=1720),
            ProductionTrendPoint(date="08-05", output=1847),
            ProductionTrendPoint(date="08-06", output=1760),
            ProductionTrendPoint(date="08-07", output=1890),
        ],
        work_order_status=[
            WorkOrderStatusItem(status="待处理", count=23),
            WorkOrderStatusItem(status="进行中", count=45),
            WorkOrderStatusItem(status="已完成", count=128),
            WorkOrderStatusItem(status="已关闭", count=67),
        ],
        todos=[
            TodoItem(
                id=1,
                type="exception",
                title="工单 WO-2024-0892 品质异常",
                description="外观检验不合格，需重新加工",
                priority="high",
                link="/work-orders/WO-2024-0892",
            ),
            TodoItem(
                id=2,
                type="timeout",
                title="工单 WO-2024-0876 已超时",
                description="计划完成时间已过 4 小时",
                priority="high",
                link="/work-orders/WO-2024-0876",
            ),
            TodoItem(
                id=3,
                type="review",
                title="生产计划 PP-0812 待审核",
                description="8 月第二周生产排程待主管确认",
                priority="medium",
                link="/production-plan/PP-0812",
            ),
            TodoItem(
                id=4,
                type="exception",
                title="设备 EQ-003 维护提醒",
                description="CNC 机床例行保养到期",
                priority="medium",
                link="/equipment/EQ-003",
            ),
            TodoItem(
                id=5,
                type="review",
                title="入库单 WH-0456 待审核",
                description="原材料入库数量与采购单不符",
                priority="low",
                link="/warehouse/WH-0456",
            ),
        ],
        manufacturing=_mock_manufacturing_data(),
    )


@router.get("", response_model=DashboardResponse)
def get_dashboard(_current_user: User = Depends(get_current_user)):
    return _mock_dashboard_data()

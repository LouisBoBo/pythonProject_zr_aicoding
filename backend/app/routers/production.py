from fastapi import APIRouter, Depends

from app.auth import get_current_user
from app.models import User
from app.schemas import (
    CompletionChartPoint,
    ProductionDetailRow,
    ProductionOverviewResponse,
    ProductionStatsRow,
)

router = APIRouter(prefix="/api/production", tags=["production"])


def _mock_production_overview() -> ProductionOverviewResponse:
    return ProductionOverviewResponse(
        achievement_rate=4,
        production_area=4,
        stats_rows=[
            ProductionStatsRow(
                time="08:00",
                today_completed=1250,
                today_area_output=3850.5,
                today_defect_total=12,
                daily_defect_rate="0.96%",
                today_incoming_boards=1300,
            ),
            ProductionStatsRow(
                time="09:00",
                today_completed=2480,
                today_area_output=7620.0,
                today_defect_total=18,
                daily_defect_rate="0.73%",
                today_incoming_boards=2550,
            ),
            ProductionStatsRow(
                time="10:00",
                today_completed=3720,
                today_area_output=11450.8,
                today_defect_total=25,
                daily_defect_rate="0.67%",
                today_incoming_boards=3800,
            ),
        ],
        completion_chart=[
            CompletionChartPoint(label="08:00", lot_output=1200000, model_output=980000),
            CompletionChartPoint(label="10:00", lot_output=2800000, model_output=2100000),
            CompletionChartPoint(label="12:00", lot_output=4500000, model_output=3600000),
            CompletionChartPoint(label="14:00", lot_output=5200000, model_output=4100000),
        ],
        detail_rows=[
            ProductionDetailRow(
                time="08:46:12",
                process_card_no="PC-20260807-001",
                product_model="ZR-A100",
                quantity=500,
                today_completed=480,
                total_completed=480,
            ),
            ProductionDetailRow(
                time="08:46:28",
                process_card_no="PC-20260807-002",
                product_model="ZR-B200",
                quantity=800,
                today_completed=750,
                total_completed=750,
            ),
            ProductionDetailRow(
                time="08:46:35",
                process_card_no="PC-20260807-003",
                product_model="ZR-C300",
                quantity=600,
                today_completed=580,
                total_completed=580,
            ),
            ProductionDetailRow(
                time="08:46:41",
                process_card_no="PC-20260807-004",
                product_model="ZR-D400",
                quantity=400,
                today_completed=390,
                total_completed=390,
            ),
        ],
    )


@router.get("/overview", response_model=ProductionOverviewResponse)
def get_production_overview(_current_user: User = Depends(get_current_user)):
    return _mock_production_overview()

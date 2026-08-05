from pydantic import BaseModel, Field


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1)


class UserResponse(BaseModel):
    id: int
    username: str
    role: str

    model_config = {"from_attributes": True}


class DashboardStatItem(BaseModel):
    key: str
    label: str
    value: float | int
    unit: str = ""
    trend: str | None = None


class ProductionTrendPoint(BaseModel):
    date: str
    output: int


class WorkOrderStatusItem(BaseModel):
    status: str
    count: int


class TodoItem(BaseModel):
    id: int
    type: str
    title: str
    description: str
    priority: str
    link: str


class DashboardResponse(BaseModel):
    stats: list[DashboardStatItem]
    production_trend: list[ProductionTrendPoint]
    work_order_status: list[WorkOrderStatusItem]
    todos: list[TodoItem]

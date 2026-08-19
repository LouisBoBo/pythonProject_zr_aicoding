# ERP 制造执行系统 API 接口文档

| 项目 | 说明 |
|------|------|
| 基址 | `http://127.0.0.1:8009`（本地默认） |
| 在线调试 | Swagger：[/docs](http://127.0.0.1:8009/docs)　·　ReDoc：[/redoc](http://127.0.0.1:8009/redoc) |
| 认证方式 | Header：`Authorization: Bearer <access_token>` |
| 数据来源 | **全部业务接口从数据库查询/写入，无 Mock** |
| 表结构文档 | [DATABASE_SCHEMA.md](./DATABASE_SCHEMA.md) |
| 文档版本 | 2026-08-17 |

---

## 1. 使用说明

1. 调用「用户登录」获取 Token。
2. 后续请求在 Header 携带：`Authorization: Bearer <token>`。
3. 成功多返回 JSON；删除类接口可能返回 `204`。
4. 失败时响应体含 `detail` 说明原因。

### 登录示例

```bash
curl -X POST http://127.0.0.1:8009/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123","enterprise_code":"江西中软电子有限公司"}'
```

---

## 2. 接口一览

| 模块 | 方法 | 路径 | 中文说明 |
|------|------|------|----------|
| 系统 | `GET` | `/api/health` | 健康检查 |
| 认证 | `POST` | `/api/auth/login` | 用户登录 |
| 认证 | `GET` | `/api/auth/me` | 获取当前登录用户 |
| 工作台 | `GET` | `/api/dashboard` | 获取工作台首页数据 |
| 生产工单 | `GET` | `/api/work-orders` | 查询生产工单列表 |
| 生产工单 | `POST` | `/api/work-orders` | 新建生产工单 |
| 生产工单 | `DELETE` | `/api/work-orders/{work_order_id}` | 删除生产工单 |
| 生产工单 | `GET` | `/api/work-orders/{work_order_id}` | 获取生产工单详情 |
| 生产工单 | `PUT` | `/api/work-orders/{work_order_id}` | 更新生产工单 |
| 生产工单 | `PATCH` | `/api/work-orders/{work_order_id}/status` | 变更生产工单状态 |
| 生产总览 | `GET` | `/api/production/overview` | 生产概览（经典版） |
| 生产总览 | `GET` | `/api/production/overview-v2` | 生产概览（联动版） |
| 生产看板 | `GET` | `/api/kanban/production` | 生产看板数据 |
| 综合看板 | `GET` | `/api/kanban/general` | 综合看板数据 |
| 看板配置 | `GET` | `/api/kanban-boards` | 查询看板配置列表 |
| 看板配置 | `POST` | `/api/kanban-boards` | 新建看板配置 |
| 看板配置 | `DELETE` | `/api/kanban-boards/{board_id}` | 删除看板配置 |
| 看板配置 | `GET` | `/api/kanban-boards/{board_id}` | 获取看板配置详情 |
| 看板配置 | `PUT` | `/api/kanban-boards/{board_id}` | 更新看板配置 |
| 看板配置 | `PATCH` | `/api/kanban-boards/{board_id}/status` | 变更看板配置状态 |
| 点检设备 | `GET` | `/api/devices` | 查询点检设备列表 |
| 设备点检 | `GET` | `/api/inspection/dashboard/stats` | 点检看板统计 |
| 设备点检 | `GET` | `/api/inspection/plan-items/by-device/{device_id}` | 按设备获取点检项模板 |
| 设备点检 | `GET` | `/api/inspection/plans` | 查询点检计划列表 |
| 设备点检 | `POST` | `/api/inspection/plans` | 新建点检计划 |
| 设备点检 | `DELETE` | `/api/inspection/plans/{plan_id}` | 删除点检计划 |
| 设备点检 | `PUT` | `/api/inspection/plans/{plan_id}` | 更新点检计划 |
| 设备点检 | `PATCH` | `/api/inspection/plans/{plan_id}/toggle` | 启用/停用点检计划 |
| 设备点检 | `GET` | `/api/inspection/records` | 查询点检记录列表 |
| 设备点检 | `POST` | `/api/inspection/records` | 新建点检记录 |
| 设备点检 | `GET` | `/api/inspection/records/{record_id}` | 获取点检记录详情 |
| 设备点检 | `PUT` | `/api/inspection/records/{record_id}` | 更新点检记录 |
| 设备台账 | `GET` | `/api/equipment` | 查询设备台账列表 |
| 设备台账 | `POST` | `/api/equipment` | 新建设备台账 |
| 设备台账 | `GET` | `/api/equipment/export` | 导出设备台账 Excel |
| 设备台账 | `POST` | `/api/equipment/import` | 导入设备台账 Excel |
| 设备台账 | `DELETE` | `/api/equipment/{equipment_id}` | 删除设备台账 |
| 设备台账 | `GET` | `/api/equipment/{equipment_id}` | 获取设备台账详情 |
| 设备台账 | `PUT` | `/api/equipment/{equipment_id}` | 更新设备台账 |
| 设备保养 | `GET` | `/api/equipment-maintenance/alerts` | 保养到期预警 |
| 设备保养 | `GET` | `/api/equipment-maintenance/equipment/{equipment_id}/status` | 单台设备保养状态 |
| 设备保养 | `GET` | `/api/equipment-maintenance/orders` | 查询保养工单列表 |
| 设备保养 | `POST` | `/api/equipment-maintenance/orders` | 新建保养工单 |
| 设备保养 | `POST` | `/api/equipment-maintenance/orders/generate-from-plan/{plan_id}` | 按计划生成保养工单 |
| 设备保养 | `DELETE` | `/api/equipment-maintenance/orders/{order_id}` | 删除保养工单 |
| 设备保养 | `GET` | `/api/equipment-maintenance/orders/{order_id}` | 获取保养工单详情 |
| 设备保养 | `PUT` | `/api/equipment-maintenance/orders/{order_id}` | 更新保养工单 |
| 设备保养 | `POST` | `/api/equipment-maintenance/orders/{order_id}/dispatch` | 派工保养工单 |
| 设备保养 | `POST` | `/api/equipment-maintenance/orders/{order_id}/execute` | 提交保养执行结果 |
| 设备保养 | `POST` | `/api/equipment-maintenance/orders/{order_id}/start` | 开始执行保养工单 |
| 设备保养 | `GET` | `/api/equipment-maintenance/plans` | 查询保养计划列表 |
| 设备保养 | `POST` | `/api/equipment-maintenance/plans` | 新建保养计划 |
| 设备保养 | `DELETE` | `/api/equipment-maintenance/plans/{plan_id}` | 删除保养计划 |
| 设备保养 | `GET` | `/api/equipment-maintenance/plans/{plan_id}` | 获取保养计划详情 |
| 设备保养 | `PUT` | `/api/equipment-maintenance/plans/{plan_id}` | 更新保养计划 |
| 设备维修 | `GET` | `/api/equipment-repairs` | 查询维修工单列表 |
| 设备维修 | `POST` | `/api/equipment-repairs` | 新建维修工单 |
| 设备维修 | `DELETE` | `/api/equipment-repairs/{repair_id}` | 删除维修工单 |
| 设备维修 | `GET` | `/api/equipment-repairs/{repair_id}` | 获取维修工单详情 |
| 设备维修 | `PUT` | `/api/equipment-repairs/{repair_id}` | 更新维修工单 |
| 设备维修 | `GET` | `/api/equipment-repairs/{repair_id}/parts` | 查询维修配件明细 |
| 设备看板 | `GET` | `/api/device/alarms/trend` | 设备告警趋势 |
| 设备看板 | `GET` | `/api/device/list` | 设备看板列表 |
| 设备看板 | `GET` | `/api/device/oee` | 设备综合 OEE |
| 设备看板 | `GET` | `/api/device/output` | 设备产量排行 |
| 设备看板 | `GET` | `/api/device/status/summary` | 设备状态汇总 |
| 设备看板 | `GET` | `/api/device/utilization` | 设备利用率趋势 |
| 品质管理 | `GET` | `/api/quality/anomalies` | 品质异常列表 |
| 品质管理 | `GET` | `/api/quality/defect-distribution` | 不良分布 |
| 品质管理 | `GET` | `/api/quality/kpi` | 品质 KPI |
| 品质管理 | `GET` | `/api/quality/process-yield` | 工序良率 |
| 品质管理 | `GET` | `/api/quality/top-defects` | Top 不良项 |
| 品质管理 | `GET` | `/api/quality/trend` | 品质趋势 |
| 仓储看板 | `GET` | `/api/warehouse/dashboard` | 仓储看板数据 |

**合计：74 个接口**

---

## 3. 接口明细

### 系统

> 健康检查等系统级接口

#### 健康检查

- **方法 / 路径**：`GET` `/api/health`
- **说明**：探测后端服务是否正常运行，无需登录。返回 `{"status":"ok"}`。
- **数据来源**：数据库查询/写入
- **鉴权**：不需要

### 认证

> 登录与当前用户信息

#### 用户登录

- **方法 / 路径**：`POST` `/api/auth/login`
- **说明**：使用用户名、密码和企业编码登录。校验通过后返回 JWT `access_token`，后续接口请在 Header 中携带：`Authorization: Bearer <token>`。
- **数据来源**：数据库查询/写入
- **鉴权**：不需要（本接口用于获取 Token）

#### 获取当前登录用户

- **方法 / 路径**：`GET` `/api/auth/me`
- **说明**：根据 Token 返回当前用户的 id、用户名和角色信息。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

### 工作台

> 首页工作台统计、待办与制造看板数据

#### 获取工作台首页数据

- **方法 / 路径**：`GET` `/api/dashboard`
- **说明**：从工单、产量事实、品质异常、待办等表聚合首页数据，包括：待处理工单数、今日产量、活跃异常、本月完成率、产量趋势、工单状态分布、待办列表，以及制造看板（月/日产量、效率、异常占比等）。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

### 生产工单

> 生产工单的增删改查与状态变更

#### 查询生产工单列表

- **方法 / 路径**：`GET` `/api/work-orders`
- **说明**：分页查询生产工单，支持按状态、产线、关键词等条件筛选（以实际 Query 参数为准）。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

#### 新建生产工单

- **方法 / 路径**：`POST` `/api/work-orders`
- **说明**：创建一条生产工单并写入 `work_orders` 表。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

#### 删除生产工单

- **方法 / 路径**：`DELETE` `/api/work-orders/{work_order_id}`
- **说明**：按 ID 删除生产工单。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

#### 获取生产工单详情

- **方法 / 路径**：`GET` `/api/work-orders/{work_order_id}`
- **说明**：按工单 ID 返回单条生产工单的完整信息。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

#### 更新生产工单

- **方法 / 路径**：`PUT` `/api/work-orders/{work_order_id}`
- **说明**：按 ID 全量/部分更新工单字段。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

#### 变更生产工单状态

- **方法 / 路径**：`PATCH` `/api/work-orders/{work_order_id}/status`
- **说明**：仅更新工单状态（如 pending / in_progress / completed 等）。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

### 生产总览

> 生产概览 KPI、趋势与产线负荷（查库聚合）

#### 生产概览（经典版）

- **方法 / 路径**：`GET` `/api/production/overview`
- **说明**：从当日产量事实表聚合完成数、面积产出、不良率、来料板数，并返回时段完成曲线与明细行。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

#### 生产概览（联动版）

- **方法 / 路径**：`GET` `/api/production/overview-v2`
- **说明**：支持按时间粒度（日/周/月）与产线筛选。从生产计划、产量、WIP、负荷、工单、品质等表聚合 KPI、达成对比、产出趋势、工单状态、产线负荷、在制品分布、品质与设备利用率。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

### 生产看板

> 车间生产看板实时展示数据

#### 生产看板数据

- **方法 / 路径**：`GET` `/api/kanban/production`
- **说明**：车间大屏用生产看板：从当日产量事实表聚合分时累计产量、不良率、达成率及流程卡明细。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

### 综合看板

> 生产/品质/设备/交付/物料五大模块综合监控

#### 综合看板数据

- **方法 / 路径**：`GET` `/api/kanban/general`
- **说明**：五大模块一次返回：生产进度、品质概览、设备监控、订单交付、物料库存。全部由工单、计划、产量、品质、设备、销售订单、发货、库存等表聚合。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

### 看板配置

> 看板元数据配置管理

#### 查询看板配置列表

- **方法 / 路径**：`GET` `/api/kanban-boards`
- **说明**：分页查询看板元数据配置（`kanban_boards` 表）。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

#### 新建看板配置

- **方法 / 路径**：`POST` `/api/kanban-boards`
- **说明**：创建看板配置记录。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

#### 删除看板配置

- **方法 / 路径**：`DELETE` `/api/kanban-boards/{board_id}`
- **说明**：按 ID 删除看板配置。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

#### 获取看板配置详情

- **方法 / 路径**：`GET` `/api/kanban-boards/{board_id}`
- **说明**：按 ID 返回单条看板配置。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

#### 更新看板配置

- **方法 / 路径**：`PUT` `/api/kanban-boards/{board_id}`
- **说明**：按 ID 更新看板配置字段。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

#### 变更看板配置状态

- **方法 / 路径**：`PATCH` `/api/kanban-boards/{board_id}/status`
- **说明**：仅更新看板状态（如 draft / published）。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

### 点检设备

> 点检用设备主数据

#### 查询点检设备列表

- **方法 / 路径**：`GET` `/api/devices`
- **说明**：返回点检域设备及设备类型列表（`devices` / `device_types`）。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

### 设备点检

> 点检计划、记录与统计

#### 点检看板统计

- **方法 / 路径**：`GET` `/api/inspection/dashboard/stats`
- **说明**：从点检计划与记录表聚合完成率、异常数等统计指标。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

#### 按设备获取点检项模板

- **方法 / 路径**：`GET` `/api/inspection/plan-items/by-device/{device_id}`
- **说明**：根据设备匹配适用点检计划，返回待执行检查项列表，供现场执行页使用。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

#### 查询点检计划列表

- **方法 / 路径**：`GET` `/api/inspection/plans`
- **说明**：分页查询点检计划及其检查项。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

#### 新建点检计划

- **方法 / 路径**：`POST` `/api/inspection/plans`
- **说明**：创建点检计划及下属检查项。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

#### 删除点检计划

- **方法 / 路径**：`DELETE` `/api/inspection/plans/{plan_id}`
- **说明**：删除点检计划及其检查项。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

#### 更新点检计划

- **方法 / 路径**：`PUT` `/api/inspection/plans/{plan_id}`
- **说明**：更新点检计划内容与检查项。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

#### 启用/停用点检计划

- **方法 / 路径**：`PATCH` `/api/inspection/plans/{plan_id}/toggle`
- **说明**：切换计划的 `is_active` 状态。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

#### 查询点检记录列表

- **方法 / 路径**：`GET` `/api/inspection/records`
- **说明**：分页查询点检执行记录，可按设备、日期等筛选。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

#### 新建点检记录

- **方法 / 路径**：`POST` `/api/inspection/records`
- **说明**：提交一次点检执行结果及各检查项实测值。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

#### 获取点检记录详情

- **方法 / 路径**：`GET` `/api/inspection/records/{record_id}`
- **说明**：按 ID 返回点检记录及明细项。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

#### 更新点检记录

- **方法 / 路径**：`PUT` `/api/inspection/records/{record_id}`
- **说明**：修改点检记录内容与明细。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

### 设备台账

> 设备台账 CRUD、导入导出

#### 查询设备台账列表

- **方法 / 路径**：`GET` `/api/equipment`
- **说明**：分页查询设备台账，支持状态、部门、关键词等筛选。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

#### 新建设备台账

- **方法 / 路径**：`POST` `/api/equipment`
- **说明**：新增一台设备到台账表。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

#### 导出设备台账 Excel

- **方法 / 路径**：`GET` `/api/equipment/export`
- **说明**：将当前筛选条件下的设备台账导出为 Excel 文件下载。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

#### 导入设备台账 Excel

- **方法 / 路径**：`POST` `/api/equipment/import`
- **说明**：上传 Excel 批量导入/更新设备台账，返回成功与失败明细。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

#### 删除设备台账

- **方法 / 路径**：`DELETE` `/api/equipment/{equipment_id}`
- **说明**：按 ID 删除设备（需注意关联保养/维修数据）。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

#### 获取设备台账详情

- **方法 / 路径**：`GET` `/api/equipment/{equipment_id}`
- **说明**：按 ID 返回单台设备台账信息。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

#### 更新设备台账

- **方法 / 路径**：`PUT` `/api/equipment/{equipment_id}`
- **说明**：按 ID 更新设备台账字段。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

### 设备保养

> 保养计划、工单、派工执行与到期预警

#### 保养到期预警

- **方法 / 路径**：`GET` `/api/equipment-maintenance/alerts`
- **说明**：查询即将到期或已逾期的保养计划/工单预警列表。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

#### 单台设备保养状态

- **方法 / 路径**：`GET` `/api/equipment-maintenance/equipment/{equipment_id}/status`
- **说明**：汇总指定设备的保养计划进度与下次到期时间。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

#### 查询保养工单列表

- **方法 / 路径**：`GET` `/api/equipment-maintenance/orders`
- **说明**：分页查询保养工单。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

#### 新建保养工单

- **方法 / 路径**：`POST` `/api/equipment-maintenance/orders`
- **说明**：手工创建保养工单。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

#### 按计划生成保养工单

- **方法 / 路径**：`POST` `/api/equipment-maintenance/orders/generate-from-plan/{plan_id}`
- **说明**：根据保养计划自动生成一条待执行保养工单。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

#### 删除保养工单

- **方法 / 路径**：`DELETE` `/api/equipment-maintenance/orders/{order_id}`
- **说明**：删除指定保养工单。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

#### 获取保养工单详情

- **方法 / 路径**：`GET` `/api/equipment-maintenance/orders/{order_id}`
- **说明**：按 ID 返回保养工单详情。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

#### 更新保养工单

- **方法 / 路径**：`PUT` `/api/equipment-maintenance/orders/{order_id}`
- **说明**：更新保养工单字段。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

#### 派工保养工单

- **方法 / 路径**：`POST` `/api/equipment-maintenance/orders/{order_id}/dispatch`
- **说明**：为保养工单指定执行人并进入待执行状态。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

#### 提交保养执行结果

- **方法 / 路径**：`POST` `/api/equipment-maintenance/orders/{order_id}/execute`
- **说明**：填写保养项目执行结果并完成工单。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

#### 开始执行保养工单

- **方法 / 路径**：`POST` `/api/equipment-maintenance/orders/{order_id}/start`
- **说明**：标记保养工单开始执行，记录实际开始时间。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

#### 查询保养计划列表

- **方法 / 路径**：`GET` `/api/equipment-maintenance/plans`
- **说明**：分页查询设备保养计划。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

#### 新建保养计划

- **方法 / 路径**：`POST` `/api/equipment-maintenance/plans`
- **说明**：为指定设备创建周期性保养计划。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

#### 删除保养计划

- **方法 / 路径**：`DELETE` `/api/equipment-maintenance/plans/{plan_id}`
- **说明**：删除指定保养计划。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

#### 获取保养计划详情

- **方法 / 路径**：`GET` `/api/equipment-maintenance/plans/{plan_id}`
- **说明**：按 ID 返回保养计划详情。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

#### 更新保养计划

- **方法 / 路径**：`PUT` `/api/equipment-maintenance/plans/{plan_id}`
- **说明**：更新保养计划周期、项目与状态等。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

### 设备维修

> 维修工单与配件明细

#### 查询维修工单列表

- **方法 / 路径**：`GET` `/api/equipment-repairs`
- **说明**：分页查询设备维修工单，支持状态、紧急度等筛选。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

#### 新建维修工单

- **方法 / 路径**：`POST` `/api/equipment-repairs`
- **说明**：登记设备故障并创建维修工单（可含配件）。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

#### 删除维修工单

- **方法 / 路径**：`DELETE` `/api/equipment-repairs/{repair_id}`
- **说明**：删除维修工单及其配件明细。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

#### 获取维修工单详情

- **方法 / 路径**：`GET` `/api/equipment-repairs/{repair_id}`
- **说明**：返回维修工单及更换配件明细。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

#### 更新维修工单

- **方法 / 路径**：`PUT` `/api/equipment-repairs/{repair_id}`
- **说明**：更新维修状态、维修说明、配件等。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

#### 查询维修配件明细

- **方法 / 路径**：`GET` `/api/equipment-repairs/{repair_id}/parts`
- **说明**：仅返回某维修单下的配件更换列表。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

### 设备看板

> 设备运行状态、OEE、利用率、告警与产量

#### 设备告警趋势

- **方法 / 路径**：`GET` `/api/device/alarms/trend`
- **说明**：近 10 日告警数量趋势及按告警类型的分布（`equipment_alarms`）。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

#### 设备看板列表

- **方法 / 路径**：`GET` `/api/device/list`
- **说明**：分页列出设备，附累计运行小时与最近告警时间。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

#### 设备综合 OEE

- **方法 / 路径**：`GET` `/api/device/oee`
- **说明**：对当日（或最近）OEE 快照求平均，返回可用率、性能率、质量率与 OEE。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

#### 设备产量排行

- **方法 / 路径**：`GET` `/api/device/output`
- **说明**：返回各设备今日与本周产量（`equipment_output_records`），按今日产量排序。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

#### 设备状态汇总

- **方法 / 路径**：`GET` `/api/device/status/summary`
- **说明**：按运行/停机/待机/维修统计设备台数与占比（来自 `equipment` 表）。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

#### 设备利用率趋势

- **方法 / 路径**：`GET` `/api/device/utilization`
- **说明**：按日/周/月返回设备可用率（利用率）趋势序列，数据来自 OEE 快照。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

### 品质管理

> 品质 KPI、趋势、不良分布与异常

#### 品质异常列表

- **方法 / 路径**：`GET` `/api/quality/anomalies`
- **说明**：查询品质异常工单列表。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

#### 不良分布

- **方法 / 路径**：`GET` `/api/quality/defect-distribution`
- **说明**：按缺陷类型汇总不良数量分布。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

#### 品质 KPI

- **方法 / 路径**：`GET` `/api/quality/kpi`
- **说明**：从品质日汇总表计算良率、不良率、报废率等核心指标。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

#### 工序良率

- **方法 / 路径**：`GET` `/api/quality/process-yield`
- **说明**：按工序维度汇总良率对比。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

#### Top 不良项

- **方法 / 路径**：`GET` `/api/quality/top-defects`
- **说明**：返回数量最高的不良类型排行。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

#### 品质趋势

- **方法 / 路径**：`GET` `/api/quality/trend`
- **说明**：按日期返回良率/不良趋势曲线数据。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

### 仓储看板

> 库存 KPI、出入库趋势、库位与物料明细

#### 仓储看板数据

- **方法 / 路径**：`GET` `/api/warehouse/dashboard`
- **说明**：从仓库、库位、物料、库存余额、库存流水表聚合：总库存、SKU 数、库位使用率、周转率、出入库趋势、预警、库位分布、实时流水与物料明细表。
- **数据来源**：数据库查询/写入
- **鉴权**：需要登录 Token

---

## 4. 数据来源确认

| 结论 | 说明 |
|------|------|
| ✅ 业务接口全部查库 | 工作台、生产、看板、设备、品质、仓储等均从对应表聚合或 CRUD |
| ✅ 无 Mock 接口 | 原硬编码路由已改造为查库；前端演示数据回退已移除 |
| ℹ️ 聚合类接口 | 看板/总览会联合多表计算 KPI，结果仍全部源于库内数据 |

更完整的交互式说明请打开后端 Swagger：`http://127.0.0.1:8009/docs`。

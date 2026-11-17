<template>
  <div class="low-stock-alerts-page">
    <el-card shadow="never" class="search-card">
      <div class="page-heading">
        <h2 class="page-title">低库存预警</h2>
        <p class="page-desc">
          展示当前库存低于安全库存的物料；缺口 = 安全库存 − 现存量，按缺口降序排列。
        </p>
      </div>
      <el-form :model="filters" inline class="search-form">
        <el-form-item label="仓库">
          <el-input
            v-model="filters.warehouseName"
            placeholder="仓库名称"
            clearable
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="关键词">
          <el-input
            v-model="filters.keyword"
            placeholder="物料编码 / 名称"
            clearable
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="table-card">
      <div class="table-toolbar">
        <span class="table-title">预警明细</span>
        <span v-if="total > 0" class="table-summary">共 {{ total }} 条低库存记录</span>
      </div>

      <el-empty
        v-if="!loading && total === 0"
        description="暂无低库存预警数据"
        :image-size="80"
      />

      <template v-else>
        <el-table v-loading="loading" :data="items" stripe border style="width: 100%">
          <el-table-column prop="shortage" label="缺口" width="90" align="right" fixed="left">
            <template #default="{ row }">
              <span class="shortage-value">{{ row.shortage.toLocaleString() }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="material_code" label="编码" min-width="120" fixed="left" />
          <el-table-column prop="sales_order_in_stock" label="销售订单在库内" width="130" align="center" />
          <el-table-column prop="no_order_ship_page" label="无建单与发货页" width="140" align="center" />
          <el-table-column prop="over_ship_no_check" label="超发无校验" width="110" align="center" />
          <el-table-column prop="sales_order_list" label="销售订单列表" min-width="160" show-overflow-tooltip />
          <el-table-column prop="new_build" label="新" min-width="110" />
          <el-table-column prop="project_name" label="本项目" min-width="140" show-overflow-tooltip />
          <el-table-column label="登记发货数量" width="130" align="right">
            <template #default="{ row }">
              <el-input-number
                v-if="row.sales_order_id && !row.order_closed"
                v-model="row._shipQty"
                :min="1"
                :max="row.remaining_shippable"
                :controls="false"
                size="small"
                class="ship-qty-input"
              />
              <span v-else>{{ row.ship_register_qty ?? '—' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="登记发货时间" width="200">
            <template #default="{ row }">
              <el-date-picker
                v-if="row.sales_order_id && !row.order_closed"
                v-model="row._shipAt"
                type="datetime"
                value-format="YYYY-MM-DDTHH:mm:ss"
                placeholder="选择时间"
                size="small"
                style="width: 100%"
              />
              <span v-else>{{ formatDateTime(row.ship_register_at) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="current_item" label="本项" width="100" align="center" />
          <el-table-column prop="remaining_shippable" label="剩余可发" width="100" align="right">
            <template #default="{ row }">{{ row.remaining_shippable.toLocaleString() }}</template>
          </el-table-column>
          <el-table-column label="发满关单" width="100" align="center">
            <template #default="{ row }">
              <el-tag v-if="row.order_closed" type="success" size="small">已关单</el-tag>
              <el-tag v-else type="info" size="small">未关单</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="p0" label="P0" width="70" align="center">
            <template #default="{ row }">{{ row.p0 || '—' }}</template>
          </el-table-column>
          <el-table-column prop="production_delivery_rate" label="生产·交付达成" width="130" align="center" />
          <el-table-column label="操作" width="100" fixed="right" align="center">
            <template #default="{ row }">
              <el-button
                v-if="row.sales_order_id && !row.order_closed"
                type="primary"
                link
                size="small"
                :loading="row._submitting"
                @click="handleRegisterShipment(row)"
              >
                登记
              </el-button>
              <span v-else class="muted-text">—</span>
            </template>
          </el-table-column>
        </el-table>

        <div class="pagination-wrap">
          <el-pagination
            v-model:current-page="page"
            v-model:page-size="pageSize"
            :total="total"
            :page-sizes="[10, 20, 50]"
            layout="total, sizes, prev, pager, next, jumper"
            background
            @size-change="loadList"
            @current-change="loadList"
          />
        </div>
      </template>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchInventoryLowStock, registerLowStockShipment } from '../../api/inventoryLowStock'

const filters = reactive({
  warehouseName: '',
  keyword: '',
})

const items = ref([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)

function formatDateTime(value) {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return String(value).slice(0, 16).replace('T', ' ')
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function decorateRows(rawItems) {
  const now = new Date()
  const pad = (n) => String(n).padStart(2, '0')
  const defaultAt = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}T${pad(now.getHours())}:${pad(now.getMinutes())}:00`
  return (rawItems || []).map((row) => ({
    ...row,
    _shipQty: row.remaining_shippable > 0 ? 1 : 1,
    _shipAt: defaultAt,
    _submitting: false,
  }))
}

async function loadList() {
  loading.value = true
  try {
    const data = await fetchInventoryLowStock({
      page: page.value,
      size: pageSize.value,
      warehouseName: filters.warehouseName || undefined,
      keyword: filters.keyword || undefined,
    })
    items.value = decorateRows(data.items)
    total.value = data.total || 0
  } catch (err) {
    ElMessage.error(err.message || '加载低库存预警失败')
  } finally {
    loading.value = false
  }
}

async function handleRegisterShipment(row) {
  if (!row.sales_order_id) return
  const qty = Number(row._shipQty)
  if (!qty || qty < 1) {
    ElMessage.warning('请填写登记发货数量')
    return
  }
  if (qty > row.remaining_shippable) {
    ElMessage.warning(`登记发货数量不能超过剩余可发（${row.remaining_shippable}）`)
    return
  }
  row._submitting = true
  try {
    const updated = await registerLowStockShipment(row.id, {
      salesOrderId: row.sales_order_id,
      shipQty: qty,
      shippedAt: row._shipAt || undefined,
    })
    Object.assign(row, decorateRows([updated])[0])
    ElMessage.success(updated.order_closed ? '登记成功，订单已发满关单' : '登记发货成功')
  } catch (err) {
    ElMessage.error(err.message || '登记发货失败')
  } finally {
    row._submitting = false
  }
}

function handleSearch() {
  page.value = 1
  loadList()
}

function handleReset() {
  filters.warehouseName = ''
  filters.keyword = ''
  page.value = 1
  loadList()
}

onMounted(() => {
  loadList()
})
</script>

<style scoped>
.low-stock-alerts-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 100%;
}

.search-card,
.table-card {
  border-radius: 4px;
}

.page-heading {
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid #ebeef5;
}

.page-title {
  margin: 0 0 4px;
  font-size: 17px;
  font-weight: 600;
  color: #303133;
}

.page-desc {
  margin: 0;
  font-size: 13px;
  color: #909399;
}

.search-form {
  margin-bottom: 0;
}

.table-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.table-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.table-summary {
  font-size: 13px;
  color: #606266;
}

.shortage-value {
  color: #f56c6c;
  font-weight: 600;
}

.ship-qty-input {
  width: 100%;
}

.muted-text {
  color: #c0c4cc;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>

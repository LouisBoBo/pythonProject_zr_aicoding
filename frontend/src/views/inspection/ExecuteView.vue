<template>
  <div class="inspection-execute">
    <div class="execute-header">
      <div class="step-indicator">
        <div class="step" :class="{ active: step >= 1, done: step > 1 }">
          <span class="step-num">1</span>
          <span class="step-label">选择设备</span>
        </div>
        <div class="step-line" :class="{ done: step > 1 }" />
        <div class="step" :class="{ active: step >= 2, done: step > 2 }">
          <span class="step-num">2</span>
          <span class="step-label">逐项检查</span>
        </div>
        <div class="step-line" :class="{ done: step > 2 }" />
        <div class="step" :class="{ active: step >= 3 }">
          <span class="step-num">3</span>
          <span class="step-label">提交记录</span>
        </div>
      </div>
    </div>

    <div v-show="step === 1" class="step-panel">
      <h3 class="panel-title">选择待检设备</h3>
      <el-select
        v-model="form.device_id"
        filterable
        remote
        :remote-method="searchDevices"
        placeholder="搜索设备名称或编号"
        style="width: 100%; max-width: 480px"
        @change="onDeviceChange"
      >
        <el-option
          v-for="d in deviceOptions"
          :key="d.id"
          :label="`${d.code} · ${d.name}`"
          :value="d.id"
        />
      </el-select>

      <div v-if="recentDevices.length" class="recent-devices">
        <span class="recent-label">最近点检：</span>
        <button
          v-for="d in recentDevices"
          :key="d.id"
          class="recent-chip"
          @click="selectDevice(d)"
        >
          {{ d.code }}
        </button>
      </div>

      <el-form-item label="关联点检计划" style="margin-top: 20px">
        <el-select
          v-model="form.plan_id"
          placeholder="可选，自动匹配默认计划"
          clearable
          style="width: 100%; max-width: 480px"
          @change="loadTemplateItems"
        >
          <el-option
            v-for="p in planOptions"
            :key="p.id"
            :label="p.name"
            :value="p.id"
          />
        </el-select>
      </el-form-item>

      <div class="step-actions">
        <el-button type="primary" :disabled="!form.device_id" @click="goStep(2)">
          下一步：开始检查
        </el-button>
      </div>
    </div>

    <div v-show="step === 2" class="step-panel">
      <div class="check-header">
        <h3 class="panel-title">
          {{ selectedDeviceLabel }} — 点检项目
        </h3>
        <span v-if="matchedPlanName" class="plan-badge">{{ matchedPlanName }}</span>
      </div>

      <div v-if="!form.items.length" class="empty-items">
        未找到点检模板，请先在点检计划中配置检查项
      </div>

      <div v-for="(item, idx) in form.items" :key="idx" class="check-item">
        <div class="check-item-head">
          <span class="check-index">{{ idx + 1 }}</span>
          <span class="check-name">{{ item.item_name }}</span>
          <span class="check-std">标准：{{ item.standard_value || '-' }}</span>
          <span class="check-judge">{{ item.judge_type === 'numeric' ? '数值判定' : 'OK/NG' }}</span>
        </div>
        <div class="check-item-body">
          <template v-if="item.judge_type === 'ok_ng'">
            <el-radio-group v-model="item.result" size="default">
              <el-radio-button value="OK">OK 正常</el-radio-button>
              <el-radio-button value="NG">NG 异常</el-radio-button>
            </el-radio-group>
          </template>
          <template v-else>
            <el-input
              v-model="item.actual_value"
              placeholder="输入实测值"
              style="width: 160px"
              @blur="autoJudgeNumeric(item)"
            />
            <span v-if="item.result" class="auto-result" :class="item.result === 'OK' ? 'ok' : 'ng'">
              {{ item.result }}
            </span>
          </template>
          <el-input
            v-model="item.remark"
            placeholder="备注（可选）"
            style="flex: 1; max-width: 280px"
          />
        </div>
      </div>

      <div class="step-actions">
        <el-button @click="goStep(1)">上一步</el-button>
        <el-button type="primary" :disabled="!form.items.length" @click="goStep(3)">
          下一步：确认提交
        </el-button>
      </div>
    </div>

    <div v-show="step === 3" class="step-panel">
      <h3 class="panel-title">确认并提交</h3>
      <el-form label-width="90px" style="max-width: 560px">
        <el-form-item label="点检人">
          <el-input v-model="form.inspector" placeholder="请输入点检人姓名" />
        </el-form-item>
        <el-form-item label="点检日期">
          <el-date-picker
            v-model="form.inspect_date"
            type="date"
            value-format="YYYY-MM-DD"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="整体备注">
          <el-input v-model="form.remark" type="textarea" :rows="3" placeholder="整体备注（可选）" />
        </el-form-item>
      </el-form>

      <div class="summary-box">
        <div class="summary-row">
          <span>设备</span>
          <span>{{ selectedDeviceLabel }}</span>
        </div>
        <div class="summary-row">
          <span>检查项</span>
          <span>{{ form.items.length }} 项</span>
        </div>
        <div class="summary-row">
          <span>异常项</span>
          <span :class="{ 'text-danger': ngCount > 0 }">{{ ngCount }} 项</span>
        </div>
      </div>

      <div class="step-actions">
        <el-button @click="goStep(2)">上一步</el-button>
        <el-button :loading="saving" @click="saveDraft">暂存草稿</el-button>
        <el-button type="primary" :loading="saving" @click="submitRecord">提交点检</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { fetchDevices } from '../../api/devices'
import {
  createInspectionRecord,
  fetchInspectionPlans,
  fetchPlanItemsForDevice,
} from '../../api/inspection'
import { fetchCurrentUser } from '../../api/auth'

const router = useRouter()
const step = ref(1)
const saving = ref(false)
const deviceOptions = ref([])
const planOptions = ref([])
const recentDevices = ref([])
const matchedPlanName = ref('')

const form = reactive({
  device_id: null,
  plan_id: null,
  inspector: '',
  inspect_date: new Date().toISOString().slice(0, 10),
  remark: '',
  items: [],
})

const selectedDeviceLabel = computed(() => {
  const d = deviceOptions.value.find((x) => x.id === form.device_id)
  return d ? `${d.code} · ${d.name}` : ''
})

const ngCount = computed(() => form.items.filter((i) => i.result === 'NG').length)

function goStep(n) {
  step.value = n
}

async function searchDevices(query) {
  const data = await fetchDevices({ search: query || undefined, pageSize: 30 })
  deviceOptions.value = data.items
}

function selectDevice(d) {
  form.device_id = d.id
  if (!deviceOptions.value.find((x) => x.id === d.id)) {
    deviceOptions.value.unshift(d)
  }
  onDeviceChange()
}

async function onDeviceChange() {
  form.plan_id = null
  await loadTemplateItems()
}

async function loadTemplateItems() {
  if (!form.device_id) return
  try {
    const data = await fetchPlanItemsForDevice(form.device_id, form.plan_id)
    matchedPlanName.value = data.plan_name || ''
    if (data.plan_id && !form.plan_id) {
      form.plan_id = data.plan_id
    }
    form.items = (data.items || []).map((i) => ({
      item_name: i.item_name,
      standard_value: i.standard_value,
      judge_type: i.judge_type,
      actual_value: '',
      result: i.judge_type === 'ok_ng' ? '' : '',
      remark: '',
    }))
  } catch (e) {
    ElMessage.error(e.message)
  }
}

function autoJudgeNumeric(item) {
  if (!item.actual_value) {
    item.result = ''
    return
  }
  item.result = 'OK'
}

async function buildPayload(status) {
  return {
    device_id: form.device_id,
    plan_id: form.plan_id || undefined,
    inspector: form.inspector,
    inspect_date: form.inspect_date,
    remark: form.remark || undefined,
    status,
    items: form.items.map((i) => ({
      item_name: i.item_name,
      standard_value: i.standard_value,
      actual_value: i.actual_value || undefined,
      result: i.result || undefined,
      remark: i.remark || undefined,
    })),
  }
}

async function saveDraft() {
  if (!form.inspector) {
    ElMessage.warning('请填写点检人')
    return
  }
  saving.value = true
  try {
    await createInspectionRecord(await buildPayload('draft'))
    ElMessage.success('草稿已暂存')
    router.push('/inspection/records?status=draft')
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    saving.value = false
  }
}

async function submitRecord() {
  if (!form.inspector) {
    ElMessage.warning('请填写点检人')
    return
  }
  const unfilled = form.items.filter((i) => !i.result && !i.actual_value)
  if (unfilled.length) {
    ElMessage.warning(`还有 ${unfilled.length} 项未完成`)
    return
  }
  saving.value = true
  try {
    await createInspectionRecord(await buildPayload('normal'))
    ElMessage.success('点检记录已提交')
    router.push('/inspection/records')
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  try {
    const [devicesRes, plansRes, user] = await Promise.all([
      fetchDevices({ pageSize: 30 }),
      fetchInspectionPlans({ pageSize: 50, isActive: true }),
      fetchCurrentUser(),
    ])
    deviceOptions.value = devicesRes.items
    planOptions.value = plansRes.items
    form.inspector = user.username
    recentDevices.value = devicesRes.items.slice(0, 4)
  } catch {
    /* ignore */
  }
})
</script>

<style scoped>
.inspection-execute {
  max-width: 800px;
  margin: 0 auto;
}

.execute-header {
  margin-bottom: 28px;
}

.step-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0;
}

.step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.step-num {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #e4e7ed;
  color: #909399;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  transition: all 0.2s;
}

.step.active .step-num {
  background: #409eff;
  color: #fff;
}

.step.done .step-num {
  background: #67c23a;
  color: #fff;
}

.step-label {
  font-size: 12px;
  color: #909399;
}

.step.active .step-label {
  color: #409eff;
  font-weight: 500;
}

.step-line {
  width: 80px;
  height: 2px;
  background: #e4e7ed;
  margin: 0 8px 20px;
}

.step-line.done {
  background: #67c23a;
}

.step-panel {
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 28px 32px;
}

.panel-title {
  margin: 0 0 20px;
  font-size: 16px;
  color: #303133;
}

.recent-devices {
  margin-top: 16px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.recent-label {
  font-size: 13px;
  color: #909399;
}

.recent-chip {
  background: #f0f5ff;
  border: 1px solid #b3d8ff;
  color: #409eff;
  font-size: 12px;
  padding: 4px 12px;
  border-radius: 2px;
  cursor: pointer;
}

.recent-chip:hover {
  background: #409eff;
  color: #fff;
}

.step-actions {
  margin-top: 28px;
  display: flex;
  gap: 12px;
}

.check-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.plan-badge {
  font-size: 12px;
  background: #ecf5ff;
  color: #409eff;
  padding: 2px 10px;
  border-radius: 2px;
}

.check-item {
  border: 1px solid #ebeef5;
  border-radius: 6px;
  margin-bottom: 12px;
  overflow: hidden;
}

.check-item-head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  background: #fafafa;
  font-size: 13px;
}

.check-index {
  width: 22px;
  height: 22px;
  background: #409eff;
  color: #fff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  flex-shrink: 0;
}

.check-name {
  font-weight: 500;
  color: #303133;
  flex: 1;
}

.check-std {
  color: #909399;
}

.check-judge {
  font-size: 11px;
  color: #c0c4cc;
}

.check-item-body {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
}

.auto-result {
  font-weight: 600;
  font-size: 13px;
}

.auto-result.ok {
  color: #67c23a;
}

.auto-result.ng {
  color: #f56c6c;
}

.empty-items {
  text-align: center;
  padding: 40px;
  color: #909399;
}

.summary-box {
  background: #fafafa;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  padding: 16px 20px;
  margin-top: 16px;
  max-width: 560px;
}

.summary-row {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
  font-size: 14px;
  color: #606266;
}

.text-danger {
  color: #f56c6c;
  font-weight: 600;
}
</style>

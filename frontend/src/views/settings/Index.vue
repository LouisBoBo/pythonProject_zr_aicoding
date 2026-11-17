<template>
  <div class="settings-page">
    <header class="page-header">
      <div>
        <h1 class="page-title">系统设置</h1>
        <p class="page-sub">修改登录密码；管理员可维护账号</p>
      </div>
    </header>

    <el-card shadow="never" class="section-card">
      <template #header>
        <span class="section-title">修改密码</span>
      </template>
      <el-form
        ref="pwdFormRef"
        :model="pwdForm"
        :rules="pwdRules"
        label-width="100px"
        style="max-width: 420px"
        @submit.prevent
      >
        <el-form-item label="原密码" prop="oldPassword">
          <el-input
            v-model="pwdForm.oldPassword"
            type="password"
            show-password
            autocomplete="current-password"
          />
        </el-form-item>
        <el-form-item label="新密码" prop="newPassword">
          <el-input
            v-model="pwdForm.newPassword"
            type="password"
            show-password
            autocomplete="new-password"
          />
        </el-form-item>
        <el-form-item label="确认新密码" prop="confirmPassword">
          <el-input
            v-model="pwdForm.confirmPassword"
            type="password"
            show-password
            autocomplete="new-password"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="pwdSaving" @click="handleChangePassword">
            保存新密码
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card v-if="canManageUsers" shadow="never" class="section-card">
      <template #header>
        <div class="section-header">
          <span class="section-title">用户管理</span>
          <el-button type="primary" @click="openCreate">新建用户</el-button>
        </div>
      </template>

      <el-table v-loading="usersLoading" :data="users" stripe border style="width: 100%">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="username" label="用户名" min-width="140" />
        <el-table-column prop="role" label="角色" width="120">
          <template #default="{ row }">
            <el-tag size="small" effect="light">{{ roleLabel(row.role) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openReset(row)">
              重置密码
            </el-button>
            <el-button link type="warning" size="small" @click="openRole(row)">
              改角色
            </el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无用户" />
        </template>
      </el-table>
    </el-card>

    <el-dialog v-model="createVisible" title="新建用户" width="420px" destroy-on-close>
      <el-form ref="createFormRef" :model="createForm" :rules="createRules" label-width="80px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="createForm.username" maxlength="50" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="createForm.password" type="password" show-password />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="createForm.role" style="width: 100%">
            <el-option label="管理员" value="admin" />
            <el-option label="经理" value="manager" />
            <el-option label="普通用户" value="user" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="createSaving" @click="handleCreate">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="resetVisible" title="重置密码" width="420px" destroy-on-close>
      <p class="dialog-tip">用户：{{ resetTarget?.username }}</p>
      <el-form ref="resetFormRef" :model="resetForm" :rules="resetRules" label-width="90px">
        <el-form-item label="新密码" prop="password">
          <el-input v-model="resetForm.password" type="password" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resetVisible = false">取消</el-button>
        <el-button type="primary" :loading="resetSaving" @click="handleReset">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="roleVisible" title="修改角色" width="420px" destroy-on-close>
      <p class="dialog-tip">用户：{{ roleTarget?.username }}</p>
      <el-form label-width="80px">
        <el-form-item label="角色">
          <el-select v-model="roleForm.role" style="width: 100%">
            <el-option label="管理员" value="admin" />
            <el-option label="经理" value="manager" />
            <el-option label="普通用户" value="user" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="roleVisible = false">取消</el-button>
        <el-button type="primary" :loading="roleSaving" @click="handleRole">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { usePermissions } from '../../composables/usePermissions'
import {
  changePassword,
  createUser,
  fetchUsers,
  resetUserPassword,
  updateUserRole,
} from '../../api/users'

const { can } = usePermissions()
const canManageUsers = computed(() => can('settings.admin'))

const pwdFormRef = ref(null)
const pwdSaving = ref(false)
const pwdForm = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: '',
})

const pwdRules = {
  oldPassword: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '至少 6 位', trigger: 'blur' },
  ],
  confirmPassword: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    {
      validator: (_r, v, cb) => {
        if (v !== pwdForm.newPassword) cb(new Error('两次输入不一致'))
        else cb()
      },
      trigger: 'blur',
    },
  ],
}

async function handleChangePassword() {
  const ok = await pwdFormRef.value?.validate().catch(() => false)
  if (!ok) return
  pwdSaving.value = true
  try {
    await changePassword({
      oldPassword: pwdForm.oldPassword,
      newPassword: pwdForm.newPassword,
    })
    ElMessage.success('密码已更新')
    pwdForm.oldPassword = ''
    pwdForm.newPassword = ''
    pwdForm.confirmPassword = ''
    pwdFormRef.value?.resetFields()
  } catch (err) {
    ElMessage.error(err.message || '修改失败')
  } finally {
    pwdSaving.value = false
  }
}

const users = ref([])
const usersLoading = ref(false)

function roleLabel(role) {
  return { admin: '管理员', manager: '经理', user: '普通用户' }[role] || role
}

async function loadUsers() {
  if (!canManageUsers.value) return
  usersLoading.value = true
  try {
    const data = await fetchUsers()
    users.value = data.items || []
  } catch (err) {
    users.value = []
    ElMessage.error(err.message || '加载用户失败')
  } finally {
    usersLoading.value = false
  }
}

const createVisible = ref(false)
const createSaving = ref(false)
const createFormRef = ref(null)
const createForm = reactive({ username: '', password: '', role: 'user' })
const createRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 2, message: '至少 2 个字符', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '至少 6 位', trigger: 'blur' },
  ],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }],
}

function openCreate() {
  createForm.username = ''
  createForm.password = ''
  createForm.role = 'user'
  createVisible.value = true
}

async function handleCreate() {
  const ok = await createFormRef.value?.validate().catch(() => false)
  if (!ok) return
  createSaving.value = true
  try {
    await createUser({ ...createForm })
    ElMessage.success('用户已创建')
    createVisible.value = false
    await loadUsers()
  } catch (err) {
    ElMessage.error(err.message || '创建失败')
  } finally {
    createSaving.value = false
  }
}

const resetVisible = ref(false)
const resetSaving = ref(false)
const resetTarget = ref(null)
const resetFormRef = ref(null)
const resetForm = reactive({ password: '' })
const resetRules = {
  password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '至少 6 位', trigger: 'blur' },
  ],
}

function openReset(row) {
  resetTarget.value = row
  resetForm.password = ''
  resetVisible.value = true
}

async function handleReset() {
  const ok = await resetFormRef.value?.validate().catch(() => false)
  if (!ok || !resetTarget.value) return
  resetSaving.value = true
  try {
    await resetUserPassword(resetTarget.value.id, resetForm.password)
    ElMessage.success('密码已重置')
    resetVisible.value = false
  } catch (err) {
    ElMessage.error(err.message || '重置失败')
  } finally {
    resetSaving.value = false
  }
}

const roleVisible = ref(false)
const roleSaving = ref(false)
const roleTarget = ref(null)
const roleForm = reactive({ role: 'user' })

function openRole(row) {
  roleTarget.value = row
  roleForm.role = row.role
  roleVisible.value = true
}

async function handleRole() {
  if (!roleTarget.value) return
  roleSaving.value = true
  try {
    await updateUserRole(roleTarget.value.id, roleForm.role)
    ElMessage.success('角色已更新')
    roleVisible.value = false
    await loadUsers()
  } catch (err) {
    ElMessage.error(err.message || '更新失败')
  } finally {
    roleSaving.value = false
  }
}

watch(canManageUsers, (ok) => {
  if (ok) loadUsers()
}, { immediate: true })
</script>

<style scoped>
.settings-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}

.page-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #1f2937;
}

.page-sub {
  margin: 4px 0 0;
  font-size: 13px;
  color: #6b7280;
}

.section-card {
  border-radius: 10px;
  border: 1px solid #e8ecf2;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  color: #374151;
}

.dialog-tip {
  margin: 0 0 12px;
  color: #6b7280;
  font-size: 13px;
}
</style>

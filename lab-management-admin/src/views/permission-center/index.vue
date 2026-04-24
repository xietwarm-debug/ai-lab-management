<template>
  <div class="permission-page">
    <section class="hero-card">
      <div class="hero-copy">
        <span class="eyebrow">权限治理</span>
        <h2>细粒度权限中心</h2>
        <p>按人配置通用权限与 AI 权限。教师和学生授权后立即生效，过期后会自动失效；管理员默认拥有全部权限，无需额外配置。</p>
      </div>
      <div class="hero-actions">
        <el-button @click="resetFilters">重置</el-button>
        <el-button type="primary" :loading="loading" @click="queryUsers">刷新列表</el-button>
      </div>
    </section>

    <section class="panel-grid">
      <article class="panel-card">
        <div class="panel-head">
          <div>
            <h3>用户选择</h3>
            <span>先选择需要配置权限的账号</span>
          </div>
        </div>
        <el-form inline class="filter-form">
          <el-form-item label="关键字">
            <el-input v-model="filters.keyword" placeholder="账号 / 昵称 / 班级" clearable @keyup.enter="queryUsers" />
          </el-form-item>
          <el-form-item label="角色">
            <el-select v-model="filters.role" style="width: 160px">
              <el-option label="全部" value="" />
              <el-option label="管理员" value="admin" />
              <el-option label="教师" value="teacher" />
              <el-option label="学生" value="student" />
            </el-select>
          </el-form-item>
        </el-form>
        <el-table v-loading="loading" :data="users" stripe highlight-current-row @current-change="selectUser">
          <el-table-column prop="username" label="账号" min-width="140" />
          <el-table-column prop="nickname" label="昵称" min-width="120" />
          <el-table-column prop="role" label="角色" width="100" />
          <el-table-column prop="className" label="班级" min-width="140" />
        </el-table>
        <div class="pager-row">
          <el-pagination
            v-model:current-page="page"
            v-model:page-size="pageSize"
            layout="total, sizes, prev, pager, next"
            :total="total"
            :page-sizes="[10, 20, 50]"
            @current-change="fetchUsers"
            @size-change="handlePageSizeChange"
          />
        </div>
      </article>

      <article class="panel-card">
        <div class="panel-head">
          <div>
            <h3>权限配置</h3>
            <span>{{ selectedUser ? `${selectedUser.username} / ${selectedUser.role}` : '先从左侧选择账号' }}</span>
          </div>
          <el-button :disabled="!selectedUser" :loading="permissionLoading" @click="loadPermissions">刷新权限</el-button>
        </div>
        <el-empty v-if="!selectedUser" description="未选择用户" />
        <template v-else>
          <el-alert
            v-if="!canManageSelectedUser"
            title="管理员默认拥有全部权限，当前仅支持为教师和学生编辑附加权限。"
            type="info"
            :closable="false"
            show-icon
            class="state-alert"
          />
          <el-alert
            v-else
            title="授权后立即生效；重新授权可以覆盖有效期；撤销后会立刻失效。"
            type="success"
            :closable="false"
            show-icon
            class="state-alert"
          />

          <div class="summary-tags">
            <el-tag v-for="item in grantedPermissions" :key="item.key" :type="item.kind === 'ai' ? 'warning' : 'success'" effect="light">
              {{ item.label }}
            </el-tag>
            <span v-if="!grantedPermissions.length" class="muted-text">当前没有额外授权项</span>
          </div>

          <section class="permission-section">
            <div class="section-head">
              <h4>通用权限</h4>
              <span>影响后台菜单和业务操作</span>
            </div>
            <el-table v-loading="permissionLoading" :data="generalPermissionRows" stripe>
              <el-table-column prop="permissionCode" label="权限码" min-width="180" />
              <el-table-column label="名称" min-width="160">
                <template #default="{ row }">
                  {{ permissionLabel(row.permissionCode) }}
                </template>
              </el-table-column>
              <el-table-column label="状态" width="120">
                <template #default="{ row }">
                  <el-tag size="small" :type="permissionTagType(row)">
                    {{ permissionStatusLabel(row) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="来源" width="120">
                <template #default="{ row }">
                  {{ permissionSourceLabel(row) }}
                </template>
              </el-table-column>
              <el-table-column label="有效期" min-width="180">
                <template #default="{ row }">
                  {{ row.expiresAt || (row.granted ? '长期有效' : '-') }}
                </template>
              </el-table-column>
              <el-table-column label="操作" width="220" fixed="right">
                <template #default="{ row }">
                  <el-button
                    link
                    type="primary"
                    :disabled="!canManageSelectedUser"
                    :loading="permissionLoading"
                    @click="grantPermission(row.permissionCode)"
                  >
                    {{ row.granted ? '更新有效期' : '授权' }}
                  </el-button>
                  <el-button
                    link
                    type="danger"
                    :disabled="!canRevokePermission(row)"
                    :loading="permissionLoading"
                    @click="revokePermission(row.permissionCode)"
                  >
                    撤销
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </section>

          <section class="permission-section">
            <div class="section-head">
              <h4>AI 权限</h4>
              <span>影响 AI 助手能否查看预约占用人等敏感信息</span>
            </div>
            <el-table v-loading="permissionLoading" :data="aiPermissionRows" stripe>
              <el-table-column prop="permissionCode" label="权限码" min-width="220" />
              <el-table-column label="名称" min-width="180">
                <template #default="{ row }">
                  {{ aiPermissionLabel(row.permissionCode) }}
                </template>
              </el-table-column>
              <el-table-column label="状态" width="120">
                <template #default="{ row }">
                  <el-tag size="small" :type="permissionTagType(row)">
                    {{ permissionStatusLabel(row) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="来源" width="120">
                <template #default="{ row }">
                  {{ permissionSourceLabel(row) }}
                </template>
              </el-table-column>
              <el-table-column label="有效期" min-width="180">
                <template #default="{ row }">
                  {{ row.expiresAt || (row.granted ? '长期有效' : '-') }}
                </template>
              </el-table-column>
              <el-table-column label="操作" width="220" fixed="right">
                <template #default="{ row }">
                  <el-button
                    link
                    type="primary"
                    :disabled="!canManageSelectedUser"
                    :loading="permissionLoading"
                    @click="grantAiPermission(row.permissionCode)"
                  >
                    {{ row.granted ? '更新有效期' : '授权' }}
                  </el-button>
                  <el-button
                    link
                    type="danger"
                    :disabled="!canRevokePermission(row)"
                    :loading="permissionLoading"
                    @click="revokeAiPermission(row.permissionCode)"
                  >
                    撤销
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </section>
        </template>
      </article>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getUserAiPermissions,
  getUserPermissions,
  getUsers,
  grantUserAiPermission,
  grantUserPermission,
  revokeUserAiPermission,
  revokeUserPermission
} from '@/api/users'
import { PERMISSION_LABEL_MAP } from '@/utils/constants'

const AI_PERMISSION_LABEL_MAP = {
  'ai.reservation.view_owner': '查看预约占用人'
}

const GENERAL_PERMISSION_CODES = ['asset.read_basic', 'asset.manager', 'audit.viewer', 'duty.operator', 'schedule.manager']
const AI_PERMISSION_CODES = ['ai.reservation.view_owner']

const loading = ref(false)
const permissionLoading = ref(false)
const users = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const selectedUser = ref(null)
const generalPermissionAllRows = ref([])
const aiPermissionAllRows = ref([])

const filters = reactive({
  keyword: '',
  role: ''
})

const canManageSelectedUser = computed(() => {
  const role = String(selectedUser.value?.role || '').trim()
  return role === 'teacher' || role === 'student'
})

const generalPermissionRows = computed(() => {
  const rows = Array.isArray(generalPermissionAllRows.value) ? generalPermissionAllRows.value : []
  return rows.filter((item) => GENERAL_PERMISSION_CODES.includes(String(item.permissionCode || '').trim()))
})

const aiPermissionRows = computed(() => {
  const rows = Array.isArray(aiPermissionAllRows.value) ? aiPermissionAllRows.value : []
  return rows.filter((item) => AI_PERMISSION_CODES.includes(String(item.permissionCode || '').trim()))
})

const grantedPermissions = computed(() => {
  const general = generalPermissionRows.value
    .filter((item) => item.granted)
    .map((item) => ({
      key: `general:${item.permissionCode}`,
      kind: 'general',
      label: permissionLabel(item.permissionCode)
    }))
  const ai = aiPermissionRows.value
    .filter((item) => item.granted)
    .map((item) => ({
      key: `ai:${item.permissionCode}`,
      kind: 'ai',
      label: `AI: ${aiPermissionLabel(item.permissionCode)}`
    }))
  return [...general, ...ai]
})

function permissionLabel(code) {
  return PERMISSION_LABEL_MAP[code] || code || '-'
}

function aiPermissionLabel(code) {
  return AI_PERMISSION_LABEL_MAP[code] || code || '-'
}

function permissionStatusLabel(row) {
  if (row?.granted) return row?.source === 'role_default' ? '默认拥有' : '已授权'
  if (row?.source === 'expired') return '已过期'
  return '未授权'
}

function permissionTagType(row) {
  if (row?.granted) return 'success'
  if (row?.source === 'expired') return 'warning'
  return 'info'
}

function permissionSourceLabel(row) {
  if (row?.source === 'role_default') return '角色默认'
  if (row?.source === 'user_grant') return '人工授权'
  if (row?.source === 'expired') return '授权过期'
  return '未授权'
}

function canRevokePermission(row) {
  if (!canManageSelectedUser.value) return false
  return !!row?.granted || row?.source === 'expired'
}

function buildParams() {
  return {
    page: page.value,
    pageSize: pageSize.value,
    keyword: filters.keyword,
    role: filters.role
  }
}

async function fetchUsers() {
  loading.value = true
  try {
    const response = await getUsers(buildParams())
    users.value = Array.isArray(response.data?.data) ? response.data.data : []
    total.value = Number(response.data?.meta?.total || 0)
    if (selectedUser.value) {
      const matched = users.value.find((item) => Number(item.id) === Number(selectedUser.value.id))
      if (matched) {
        selectedUser.value = matched
      }
    }
  } finally {
    loading.value = false
  }
}

async function loadPermissions() {
  if (!selectedUser.value?.id) return
  permissionLoading.value = true
  try {
    const [generalResponse, aiResponse] = await Promise.all([
      getUserPermissions(selectedUser.value.id),
      getUserAiPermissions(selectedUser.value.id)
    ])
    generalPermissionAllRows.value = Array.isArray(generalResponse.data?.data?.items) ? generalResponse.data.data.items : []
    aiPermissionAllRows.value = Array.isArray(aiResponse.data?.data?.items) ? aiResponse.data.data.items : []
  } finally {
    permissionLoading.value = false
  }
}

function selectUser(row) {
  selectedUser.value = row || null
  generalPermissionAllRows.value = []
  aiPermissionAllRows.value = []
  if (selectedUser.value?.id) {
    loadPermissions()
  }
}

function queryUsers() {
  page.value = 1
  fetchUsers()
}

function resetFilters() {
  filters.keyword = ''
  filters.role = ''
  queryUsers()
}

function handlePageSizeChange(size) {
  pageSize.value = size
  page.value = 1
  fetchUsers()
}

async function promptExpiresAt(title) {
  try {
    const result = await ElMessageBox.prompt(
      '可留空表示长期有效；如需设置过期时间，请输入 YYYY-MM-DD HH:mm:ss',
      title,
      {
        confirmButtonText: '确认',
        cancelButtonText: '取消',
        inputPlaceholder: '例如 2026-12-31 23:59:59',
        inputPattern: /^$|^\d{4}-\d{2}-\d{2}(?:\s|T)\d{2}:\d{2}:\d{2}$/,
        inputErrorMessage: '请输入 YYYY-MM-DD HH:mm:ss，或留空'
      }
    )
    return String(result?.value || '').trim()
  } catch (error) {
    return null
  }
}

async function grantPermission(permissionCode) {
  if (!selectedUser.value?.id || !canManageSelectedUser.value) return
  const expiresAt = await promptExpiresAt(`授权 ${permissionLabel(permissionCode)}`)
  if (expiresAt === null) return

  permissionLoading.value = true
  try {
    await grantUserPermission(selectedUser.value.id, {
      permissionCode,
      expiresAt: expiresAt || undefined
    })
    await loadPermissions()
    ElMessage.success('通用权限已更新并立即生效')
  } finally {
    permissionLoading.value = false
  }
}

async function revokePermission(permissionCode) {
  if (!selectedUser.value?.id || !canManageSelectedUser.value) return
  await ElMessageBox.confirm(`确认撤销 ${permissionLabel(permissionCode)} 吗？`, '撤销权限', { type: 'warning' })

  permissionLoading.value = true
  try {
    await revokeUserPermission(selectedUser.value.id, { permissionCode })
    await loadPermissions()
    ElMessage.success('通用权限已撤销')
  } finally {
    permissionLoading.value = false
  }
}

async function grantAiPermission(permissionCode) {
  if (!selectedUser.value?.id || !canManageSelectedUser.value) return
  const expiresAt = await promptExpiresAt(`授权 ${aiPermissionLabel(permissionCode)}`)
  if (expiresAt === null) return

  permissionLoading.value = true
  try {
    await grantUserAiPermission(selectedUser.value.id, {
      permissionCode,
      expiresAt: expiresAt || undefined
    })
    await loadPermissions()
    ElMessage.success('AI 权限已更新并立即生效')
  } finally {
    permissionLoading.value = false
  }
}

async function revokeAiPermission(permissionCode) {
  if (!selectedUser.value?.id || !canManageSelectedUser.value) return
  await ElMessageBox.confirm(`确认撤销 ${aiPermissionLabel(permissionCode)} 吗？`, '撤销 AI 权限', { type: 'warning' })

  permissionLoading.value = true
  try {
    await revokeUserAiPermission(selectedUser.value.id, { permissionCode })
    await loadPermissions()
    ElMessage.success('AI 权限已撤销')
  } finally {
    permissionLoading.value = false
  }
}

onMounted(() => {
  fetchUsers()
})
</script>

<style scoped lang="scss">
.permission-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.hero-card,
.panel-card {
  border: 1px solid var(--app-border);
  border-radius: 24px;
  background: var(--app-surface);
  box-shadow: var(--app-shadow);
}

.hero-card,
.hero-actions,
.panel-head,
.pager-row,
.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.hero-card {
  padding: 28px;
  background:
    radial-gradient(circle at top right, rgba(14, 165, 233, 0.14), transparent 30%),
    linear-gradient(135deg, #f7fcff 0%, #eef8ff 100%);
}

.hero-copy {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.hero-card h2,
.panel-head h3,
.section-head h4 {
  margin: 0;
}

.hero-copy p,
.panel-head span,
.section-head span,
.muted-text {
  color: var(--app-muted);
}

.eyebrow {
  display: inline-flex;
  width: fit-content;
  padding: 6px 10px;
  border-radius: 999px;
  background: #e0f2fe;
  color: #0369a1;
  font-size: 12px;
  font-weight: 700;
}

.panel-grid {
  display: grid;
  grid-template-columns: 1.1fr 1.4fr;
  gap: 20px;
}

.panel-card {
  padding: 24px;
}

.filter-form {
  margin-bottom: 16px;
}

.state-alert {
  margin-bottom: 16px;
}

.summary-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 16px;
}

.permission-section + .permission-section {
  margin-top: 18px;
}

.section-head {
  margin-bottom: 12px;
}

.pager-row {
  margin-top: 16px;
  justify-content: flex-end;
}

@media (max-width: 1100px) {
  .panel-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .hero-card,
  .hero-actions,
  .panel-head,
  .section-head {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>

<template>
  <div class="permission-page">
    <section class="hero-card">
      <div class="hero-copy">
        <span class="eyebrow">Access Control</span>
        <h2>细粒度权限中心</h2>
        <p>为教师或学生账号按人授予值班员、资产管理员、排课管理员、审计查看员等后台岗位权限。</p>
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
            <span>请选择要配置权限的账号</span>
          </div>
        </div>
        <el-form inline class="filter-form">
          <el-form-item label="关键字">
            <el-input v-model="filters.keyword" placeholder="账号 / 昵称 / 班级" clearable @keyup.enter="queryUsers" />
          </el-form-item>
          <el-form-item label="角色">
            <el-select v-model="filters.role" style="width: 160px">
              <el-option label="全部" value="" />
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
            <h3>岗位权限</h3>
            <span>{{ selectedUser ? `${selectedUser.username} / ${selectedUser.role}` : '先从左侧选择账号' }}</span>
          </div>
          <el-button :disabled="!selectedUser" :loading="permissionLoading" @click="loadPermissions">刷新权限</el-button>
        </div>
        <el-empty v-if="!selectedUser" description="未选择用户" />
        <template v-else>
          <div class="summary-tags">
            <el-tag v-for="item in grantedPermissions" :key="item.permissionCode" type="success" effect="light">
              {{ permissionLabel(item.permissionCode) }}
            </el-tag>
            <span v-if="!grantedPermissions.length" class="muted-text">当前未授予任何岗位权限</span>
          </div>
          <el-table v-loading="permissionLoading" :data="permissionRows" stripe>
            <el-table-column prop="permissionCode" label="权限码" min-width="180" />
            <el-table-column label="名称" min-width="140">
              <template #default="{ row }">
                {{ permissionLabel(row.permissionCode) }}
              </template>
            </el-table-column>
            <el-table-column label="状态" width="120">
              <template #default="{ row }">
                <el-tag size="small" :type="row.granted ? 'success' : row.source === 'expired' ? 'warning' : 'info'">
                  {{ permissionStatusLabel(row) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="有效期" min-width="180">
              <template #default="{ row }">
                {{ row.expiresAt || (row.granted ? '长期有效' : '-') }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="180" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" :loading="permissionLoading" @click="grantPermission(row.permissionCode)">
                  授权
                </el-button>
                <el-button
                  link
                  type="danger"
                  :disabled="!row.granted && row.source !== 'expired'"
                  :loading="permissionLoading"
                  @click="revokePermission(row.permissionCode)"
                >
                  撤销
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </template>
      </article>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getUsers, getUserPermissions, grantUserPermission, revokeUserPermission } from '@/api/users'
import { PERMISSION_LABEL_MAP } from '@/utils/constants'

const loading = ref(false)
const permissionLoading = ref(false)
const users = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const selectedUser = ref(null)
const permissionRows = ref([])

const filters = reactive({
  keyword: '',
  role: ''
})

const grantedPermissions = computed(() => permissionRows.value.filter((item) => item.granted))

function permissionLabel(code) {
  return PERMISSION_LABEL_MAP[code] || code || '-'
}

function permissionStatusLabel(row) {
  if (row?.granted) return row?.source === 'role_default' ? '默认拥有' : '已授权'
  if (row?.source === 'expired') return '已过期'
  return '未授权'
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
    const response = await getUserPermissions(selectedUser.value.id)
    permissionRows.value = Array.isArray(response.data?.data?.items) ? response.data.data.items : []
  } finally {
    permissionLoading.value = false
  }
}

function selectUser(row) {
  selectedUser.value = row || null
  permissionRows.value = []
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

async function grantPermission(permissionCode) {
  if (!selectedUser.value?.id) return
  let promptResult
  try {
    promptResult = await ElMessageBox.prompt(
      '可留空表示长期有效；如需设置有效期，请输入 YYYY-MM-DD HH:mm:ss',
      `授权 ${permissionLabel(permissionCode)}`,
      {
        confirmButtonText: '授权',
        cancelButtonText: '取消',
        inputPlaceholder: '例如 2026-03-31 23:59:59',
        inputPattern: /^$|^\d{4}-\d{2}-\d{2}(?:\s|T)\d{2}:\d{2}:\d{2}$/,
        inputErrorMessage: '请输入 YYYY-MM-DD HH:mm:ss 或留空'
      }
    )
  } catch (error) {
    return
  }

  permissionLoading.value = true
  try {
    const expiresAt = String(promptResult?.value || '').trim()
    await grantUserPermission(selectedUser.value.id, {
      permissionCode,
      expiresAt: expiresAt || undefined
    })
    await loadPermissions()
    ElMessage.success('权限已授权')
  } finally {
    permissionLoading.value = false
  }
}

async function revokePermission(permissionCode) {
  if (!selectedUser.value?.id) return
  await ElMessageBox.confirm(`确认撤销 ${permissionLabel(permissionCode)} 吗？`, '撤销权限', { type: 'warning' })
  permissionLoading.value = true
  try {
    await revokeUserPermission(selectedUser.value.id, { permissionCode })
    await loadPermissions()
    ElMessage.success('权限已撤销')
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
.pager-row {
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
.panel-head h3 {
  margin: 0;
}

.hero-copy p,
.panel-head span,
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
  grid-template-columns: 1.1fr 1.3fr;
  gap: 20px;
}

.panel-card {
  padding: 24px;
}

.filter-form {
  margin-bottom: 16px;
}

.summary-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 16px;
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
  .panel-head {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>

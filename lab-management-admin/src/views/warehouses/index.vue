<template>
  <div class="warehouses-page">
    <section class="panel-card hero-card">
      <div class="hero-top">
        <div class="hero-copy">
          <div class="title-row">
            <h2 class="page-title">仓库管理</h2>
            <span class="eyebrow">资产存储底座</span>
          </div>
          <p class="page-desc">管理所有的仓储节点，支持配置负责人和位置信息，可作为资产采购、调拨的目的地。</p>

          <div class="hero-meta">
            <div class="meta-item">
              <span class="meta-label">仓库总数</span>
              <strong class="meta-value">{{ warehouses.length }}</strong>
            </div>
          </div>
        </div>

        <div class="hero-actions">
          <el-button class="premium-btn" @click="reloadAll">刷新全部</el-button>
          <el-button class="premium-btn" type="primary" @click="openCreateDialog">
            <el-icon class="el-icon--left"><Plus /></el-icon>
            新增仓库
          </el-button>
        </div>
      </div>
    </section>

    <section class="filter-header-section panel-card">
      <div class="filter-header">
        <div>
          <h3 class="section-title">仓库列表</h3>
          <p class="section-subtitle">共 {{ filteredWarehouses.length }} 个存储空间</p>
        </div>

        <el-form inline class="filter-form" @submit.prevent>
          <el-form-item>
            <el-input
              v-model="keyword"
              placeholder="按名称或位置搜索..."
              clearable
              class="filter-input premium-input"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
          </el-form-item>

          <el-form-item>
            <el-select v-model="statusFilter" class="filter-select premium-input">
              <el-option label="全部状态" value="all" />
              <el-option label="正常启用" value="active" />
              <el-option label="已停用" value="disabled" />
            </el-select>
          </el-form-item>

          <el-form-item style="margin-right: 0">
            <el-button class="premium-btn" @click="resetFilters">重置</el-button>
          </el-form-item>
        </el-form>
      </div>
    </section>

    <section v-if="loading" class="warehouse-grid">
      <div v-for="i in 3" :key="i" class="warehouse-card loading-card panel-card">
        <el-skeleton :rows="4" animated />
      </div>
    </section>

    <section v-else class="warehouse-grid">
      <div
        v-for="warehouse in filteredWarehouses"
        :key="warehouse.id"
        class="warehouse-card panel-card"
        :class="{ 'is-disabled': warehouse.status !== 'active' }"
      >
        <div class="warehouse-header">
          <div class="header-main">
            <div class="title-with-badge">
              <h3 class="warehouse-title" :title="warehouse.name">{{ warehouse.name }}</h3>
              <div class="status-badge" :class="warehouse.status === 'active' ? 'bg-success' : 'bg-warning'">
                <span class="status-dot-white"></span>
                {{ warehouse.status === 'active' ? '启用中' : '已停用' }}
              </div>
            </div>
            <div class="sub-meta">
              <span>ID: {{ warehouse.id }}</span>
              <span v-if="warehouse.location">
                <el-icon><Location /></el-icon> {{ warehouse.location }}
              </span>
            </div>
          </div>
        </div>

        <div class="warehouse-body">
          <div class="info-row">
            <span class="info-label">负责人：</span>
            <span class="info-value">{{ warehouse.managerName || '未指定' }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">资产数量：</span>
            <span class="info-value text-primary"><strong>{{ warehouse.assetCount || 0 }}</strong> 件</span>
          </div>
          <div class="info-desc" :title="warehouse.description">
            {{ warehouse.description || '暂无详细描述。' }}
          </div>
        </div>

        <div class="warehouse-footer">
          <div class="footer-left">
            <span class="created-at">创建于 {{ warehouse.createdAt?.substring(0, 10) || '-' }}</span>
          </div>
          <div class="action-group">
            <el-button
              link
              type="primary"
              class="action-text-btn primary-text"
              @click="openEditDialog(warehouse)"
            >
              编辑
            </el-button>
            <el-popconfirm
              title="确定删除这个仓库吗？"
              @confirm="confirmDelete(warehouse)"
              width="220"
            >
              <template #reference>
                <el-button link type="danger" class="action-text-btn danger-text">
                  删除
                </el-button>
              </template>
            </el-popconfirm>
          </div>
        </div>
      </div>
    </section>

    <el-dialog
      v-model="dialogVisible"
      :title="isEditMode ? '编辑仓库' : '新增仓库'"
      width="540px"
      class="premium-dialog"
      :show-close="false"
    >
      <el-form label-position="top" class="custom-form">
        <el-form-item label="仓库名称">
          <el-input
            v-model="form.name"
            maxlength="64"
            placeholder="例如：主教学楼地下仓库"
            class="premium-input"
          />
        </el-form-item>

        <el-form-item label="具体位置">
          <el-input
            v-model="form.location"
            maxlength="128"
            placeholder="例如：B1-05"
            class="premium-input"
          />
        </el-form-item>

        <div class="dialog-grid">
          <el-form-item label="负责人姓名">
            <el-input
              v-model="form.managerName"
              maxlength="32"
              placeholder="例如：张三"
              class="premium-input"
            />
          </el-form-item>
          <el-form-item label="当前状态">
            <el-radio-group v-model="form.status" class="premium-radio">
              <el-radio-button label="active">启用</el-radio-button>
              <el-radio-button label="disabled">停用</el-radio-button>
            </el-radio-group>
          </el-form-item>
        </div>

        <el-form-item label="详细说明">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="3"
            maxlength="300"
            show-word-limit
            placeholder="说明存放物品类型等..."
            class="premium-input"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <span class="dialog-footer">
          <el-button class="premium-btn" @click="dialogVisible = false">取消</el-button>
          <el-button class="premium-btn" type="primary" :loading="submitting" @click="submitForm">
            保存配置
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Search, Location } from '@element-plus/icons-vue'
import { getWarehouses, createWarehouse, updateWarehouse, deleteWarehouse } from '@/api/warehouses'

const loading = ref(false)
const submitting = ref(false)
const warehouses = ref([])
const keyword = ref('')
const statusFilter = ref('all')
const dialogVisible = ref(false)
const editingId = ref(0)

const form = reactive({
  name: '',
  location: '',
  managerName: '',
  status: 'active',
  description: ''
})

const isEditMode = computed(() => editingId.value > 0)

const filteredWarehouses = computed(() => {
  const query = keyword.value.trim().toLowerCase()
  return warehouses.value.filter((w) => {
    const statusMatched = statusFilter.value === 'all' ? true : w.status === statusFilter.value
    if (!statusMatched) return false
    if (!query) return true
    return [
      String(w.name || '').toLowerCase(),
      String(w.location || '').toLowerCase()
    ].some((val) => val.includes(query))
  })
})

function resetForm() {
  editingId.value = 0
  Object.assign(form, {
    name: '',
    location: '',
    managerName: '',
    status: 'active',
    description: ''
  })
}

function openCreateDialog() {
  resetForm()
  dialogVisible.value = true
}

function openEditDialog(warehouse) {
  editingId.value = Number(warehouse.id || 0)
  Object.assign(form, {
    name: String(warehouse.name || ''),
    location: String(warehouse.location || ''),
    managerName: String(warehouse.managerName || ''),
    status: String(warehouse.status || 'active'),
    description: String(warehouse.description || '')
  })
  dialogVisible.value = true
}

function resetFilters() {
  keyword.value = ''
  statusFilter.value = 'all'
}

async function fetchWarehouseList() {
  loading.value = true
  try {
    const response = await getWarehouses({ page: 1, pageSize: 200 })
    warehouses.value = Array.isArray(response.data?.data?.items) ? response.data.data.items : []
  } finally {
    loading.value = false
  }
}

async function reloadAll() {
  await fetchWarehouseList()
}

async function submitForm() {
  if (!String(form.name || '').trim()) {
    ElMessage.warning('请填写仓库名称')
    return
  }

  submitting.value = true
  try {
    const payload = { ...form }
    if (isEditMode.value) {
      await updateWarehouse(editingId.value, payload)
      ElMessage.success('配置已更新')
    } else {
      await createWarehouse(payload)
      ElMessage.success('仓库已创建')
    }
    dialogVisible.value = false
    await reloadAll()
  } finally {
    submitting.value = false
  }
}

async function confirmDelete(warehouse) {
  try {
    await deleteWarehouse(warehouse.id)
    ElMessage.success('仓库已删除')
    await reloadAll()
  } catch (err) {
    if (err.msg) {
        ElMessage.error(err.msg)
    }
  }
}

onMounted(() => {
  reloadAll()
})
</script>

<style scoped lang="scss">
.warehouses-page {
  --color-primary: #2563eb;
  --color-primary-hover: #1d4ed8;
  --color-danger: #ef4444;
  --color-warning: #f59e0b;
  --color-success: #10b981;

  --bg-page: #f1f5f9;
  --bg-card: #ffffff;
  --bg-subtle: #f8fafc;
  
  --text-main: #0f172a;
  --text-regular: #334155;
  --text-muted: #64748b;

  --border-light: #d1d5db;
  --border-divider: #e5e7eb;

  --shadow-premium: 0 6px 16px rgba(15, 23, 42, 0.08);
  --shadow-hover: 0 12px 28px rgba(37, 99, 235, 0.12);

  --radius-md: 12px;
  --radius-lg: 16px;

  display: flex;
  flex-direction: column;
  gap: 24px;
  padding: 32px;
  background-color: var(--bg-page);
  min-height: 100vh;
  box-sizing: border-box;
}

.panel-card {
  background: var(--bg-card);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-premium);
  box-sizing: border-box;
}

.hero-card {
  padding: 28px 32px;
  border-width: 2px;
}
.hero-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 24px;
  flex-wrap: wrap;
}
.hero-copy {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-width: 760px;
}
.title-row {
  display: flex;
  align-items: center;
  gap: 14px;
}
.page-title {
  margin: 0;
  font-size: 26px;
  font-weight: 700;
  color: var(--text-main);
  letter-spacing: -0.02em;
}
.eyebrow {
  font-size: 13px;
  font-weight: 600;
  padding: 4px 10px;
  background: var(--color-primary);
  color: #fff;
  border-radius: 20px;
  letter-spacing: 0.02em;
}
.page-desc {
  margin: 0;
  font-size: 15px;
  color: var(--text-regular);
  line-height: 1.6;
}
.hero-meta {
  display: flex;
  gap: 32px;
  margin-top: 8px;
}
.meta-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.meta-label {
  font-size: 13px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: 600;
}
.meta-value {
  font-size: 26px;
  font-weight: 700;
  color: var(--text-main);
  font-feature-settings: "tnum";
}

.premium-btn {
  border-radius: 8px;
  font-weight: 600;
  transition: all 0.2s ease;
  border-color: var(--border-light);
  &.el-button--primary {
    border-color: var(--color-primary);
  }
}

.filter-header-section {
  padding: 20px 24px;
}
.filter-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 20px;
}
.section-title {
  margin: 0 0 6px 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--text-main);
}
.section-subtitle {
  margin: 0;
  font-size: 14px;
  color: var(--text-muted);
}
.filter-form {
  display: flex;
  align-items: center;
  gap: 12px;
  .el-form-item {
    margin-bottom: 0;
    margin-right: 0;
  }
}
.premium-input {
  :deep(.el-input__wrapper) {
    border-radius: 8px;
    box-shadow: 0 0 0 1px var(--border-light) inset;
    &:hover, &.is-focus {
      box-shadow: 0 0 0 1px var(--color-primary) inset;
    }
  }
}

.warehouse-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 24px;
}

.warehouse-card {
  display: flex;
  flex-direction: column;
  transition: transform 0.2s ease, box-shadow 0.3s ease;
  overflow: hidden;
  &:hover {
    transform: translateY(-4px);
    box-shadow: var(--shadow-hover);
  }
  &.is-disabled {
    opacity: 0.8;
    filter: grayscale(0.5);
  }
}

.warehouse-header {
  padding: 20px 24px 16px;
  border-bottom: 1px solid var(--border-divider);
  background: var(--bg-subtle);
}
.header-main {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.title-with-badge {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}
.warehouse-title {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: var(--text-main);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  font-size: 12px;
  font-weight: 600;
  color: #fff;
  border-radius: 20px;
  white-space: nowrap;
  &.bg-success { background: var(--color-success); }
  &.bg-warning { background: var(--color-warning); }
}
.status-dot-white {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgba(255,255,255,0.8);
}
.sub-meta {
  display: flex;
  gap: 16px;
  font-size: 13px;
  color: var(--text-muted);
  align-items: center;
}

.warehouse-body {
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  flex: 1;
}
.info-row {
  display: flex;
  align-items: center;
  font-size: 14px;
}
.info-label {
  color: var(--text-muted);
  width: 70px;
}
.info-value {
  color: var(--text-main);
  font-weight: 500;
}
.text-primary {
  color: var(--color-primary);
}
.info-desc {
  margin-top: 8px;
  font-size: 13px;
  color: var(--text-regular);
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  min-height: 39px;
}

.warehouse-footer {
  padding: 16px 24px;
  border-top: 1px solid var(--border-divider);
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: var(--bg-card);
}
.created-at {
  font-size: 13px;
  color: var(--text-muted);
}
.action-group {
  display: flex;
  gap: 12px;
  align-items: center;
}
.action-text-btn {
  font-size: 14px;
  font-weight: 600;
  margin: 0 !important;
  &:hover { opacity: 0.8; }
}

/* Dialog Styles */
.premium-dialog {
  :deep(.el-dialog) {
    border-radius: var(--radius-lg);
    overflow: hidden;
    box-shadow: 0 24px 48px rgba(15, 23, 42, 0.2);
  }
  :deep(.el-dialog__header) {
    margin-right: 0;
    padding: 24px 28px 20px;
    border-bottom: 1px solid var(--border-divider);
    .el-dialog__title {
      font-weight: 700;
      font-size: 18px;
      color: var(--text-main);
    }
  }
  :deep(.el-dialog__body) {
    padding: 28px;
    background: #fafafa;
  }
  :deep(.el-dialog__footer) {
    padding: 20px 28px;
    border-top: 1px solid var(--border-divider);
    background: #fff;
  }
}

.custom-form {
  :deep(.el-form-item__label) {
    font-weight: 600;
    color: var(--text-main);
    padding-bottom: 6px;
  }
}

.dialog-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.premium-radio {
  display: flex;
  border-radius: 8px;
  overflow: hidden;
  width: 100%;
  :deep(.el-radio-button__inner) {
    flex: 1;
    text-align: center;
  }
}
</style>

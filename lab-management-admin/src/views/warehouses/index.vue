<template>
  <div class="warehouses-page">
    <section class="hero-card">
      <div>
        <span class="eyebrow">Warehouse Hub</span>
        <h2>仓库管理</h2>
        <p>查看仓库详情、负责人、库存资产，并支持对仓库内资产进行轻量编辑。</p>
      </div>
      <div class="hero-actions">
        <el-button @click="reloadAll">刷新</el-button>
        <el-button type="primary" @click="openCreateDialog">新增仓库</el-button>
      </div>
    </section>

    <section class="panel-card">
      <el-form inline @submit.prevent>
        <el-form-item>
          <el-input v-model="keyword" placeholder="搜索仓库名称或位置" clearable />
        </el-form-item>
        <el-form-item>
          <el-select v-model="statusFilter" style="width: 140px">
            <el-option label="全部状态" value="all" />
            <el-option label="启用中" value="active" />
            <el-option label="已停用" value="disabled" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>
    </section>

    <section v-if="loading" class="card-grid">
      <div v-for="i in 3" :key="i" class="warehouse-card panel-card">
        <el-skeleton :rows="4" animated />
      </div>
    </section>

    <section v-else class="card-grid">
      <article
        v-for="warehouse in filteredWarehouses"
        :key="warehouse.id"
        class="warehouse-card panel-card"
        @click="openDetailDrawer(warehouse)"
      >
        <div class="card-head">
          <div>
            <h3>{{ warehouse.name }}</h3>
            <p>{{ warehouse.location || '未设置位置' }}</p>
          </div>
          <el-tag :type="warehouse.status === 'active' ? 'success' : 'warning'">
            {{ warehouse.status === 'active' ? '启用中' : '已停用' }}
          </el-tag>
        </div>

        <div class="meta-list">
          <div>负责人：{{ warehouse.managerName || '未指定' }}</div>
          <div>资产数量：{{ warehouse.assetCount || 0 }}</div>
          <div>创建时间：{{ warehouse.createdAt?.slice(0, 10) || '-' }}</div>
        </div>

        <p class="desc">{{ warehouse.description || '暂无仓库说明。' }}</p>

        <div class="card-actions">
          <el-button link type="primary" @click.stop="openEditDialog(warehouse)">编辑仓库</el-button>
          <el-popconfirm title="确认删除这个仓库吗？" @confirm="confirmDelete(warehouse)">
            <template #reference>
              <el-button link type="danger" @click.stop>删除</el-button>
            </template>
          </el-popconfirm>
        </div>
      </article>
    </section>

    <el-dialog v-model="dialogVisible" :title="isEditMode ? '编辑仓库' : '新增仓库'" width="540px">
      <el-form label-position="top">
        <el-form-item label="仓库名称">
          <el-input v-model="form.name" maxlength="64" />
        </el-form-item>
        <el-form-item label="位置">
          <el-input v-model="form.location" maxlength="128" />
        </el-form-item>
        <el-form-item label="负责人">
          <el-input v-model="form.managerName" maxlength="32" />
        </el-form-item>
        <el-form-item label="状态">
          <el-radio-group v-model="form.status">
            <el-radio-button label="active">启用</el-radio-button>
            <el-radio-button label="disabled">停用</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="form.description" type="textarea" :rows="3" maxlength="300" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitForm">保存</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="detailVisible" title="仓库详情" size="820px">
      <div v-if="activeWarehouse" class="detail-stack">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="仓库名称">{{ activeWarehouse.name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="负责人">{{ activeWarehouse.managerName || '-' }}</el-descriptions-item>
          <el-descriptions-item label="位置">{{ activeWarehouse.location || '-' }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ activeWarehouse.status === 'active' ? '启用中' : '已停用' }}</el-descriptions-item>
          <el-descriptions-item :span="2" label="说明">{{ activeWarehouse.description || '-' }}</el-descriptions-item>
        </el-descriptions>

        <div class="detail-head">
          <div>
            <h3>仓库资产</h3>
            <p>当前共 {{ warehouseAssets.length }} 项资产</p>
          </div>
          <el-button :loading="assetLoading" @click="fetchWarehouseAssets">刷新资产</el-button>
        </div>

        <el-table v-loading="assetLoading" :data="warehouseAssets" stripe>
          <el-table-column prop="assetCode" label="资产编号" min-width="150" />
          <el-table-column prop="name" label="资产名称" min-width="160" />
          <el-table-column prop="keeper" label="责任人" min-width="120" />
          <el-table-column label="状态" width="110">
            <template #default="{ row }">
              <el-tag size="small" :type="statusType(row.status)">{{ statusText(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="可借用" width="100">
            <template #default="{ row }">
              <el-tag size="small" :type="row.allowBorrow ? 'success' : 'info'">
                {{ row.allowBorrow ? '允许' : '禁止' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100">
            <template #default="{ row }">
              <el-button link type="primary" @click="openAssetEdit(row)">编辑</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <el-empty v-else description="暂无仓库详情" />
    </el-drawer>

    <el-dialog v-model="assetDialogVisible" title="编辑资产" width="560px">
      <el-form label-position="top">
        <el-form-item label="资产名称">
          <el-input v-model="assetForm.name" />
        </el-form-item>
        <el-form-item label="责任人">
          <el-input v-model="assetForm.keeper" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="assetForm.status" style="width: 100%">
            <el-option label="在用" value="in_service" />
            <el-option label="维修中" value="repairing" />
            <el-option label="已报废" value="scrapped" />
          </el-select>
        </el-form-item>
        <el-form-item label="允许借用">
          <el-switch v-model="assetForm.allowBorrow" />
        </el-form-item>
        <el-form-item label="资产照片">
          <el-input v-model="assetForm.imageUrl" placeholder="填写图片 URL 地址或直接上传">
            <template #append>
              <el-upload
                :show-file-list="false"
                :http-request="handleAssetImageUpload"
                accept=".jpg,.jpeg,.png,.gif,.webp"
              >
                <el-button :loading="assetImageUploading">上传图片</el-button>
              </el-upload>
            </template>
          </el-input>
          <div v-if="assetForm.imageUrl" class="preview-wrap">
            <img :src="resolveImageUrl(assetForm.imageUrl)" alt="asset-preview" class="preview-image" />
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="assetDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="assetSaving" @click="submitAssetEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, reactive, ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getEquipmentList, updateEquipment } from '@/api/equipments'
import { getWarehouses, createWarehouse, updateWarehouse, deleteWarehouse } from '@/api/warehouses'
import { uploadImage } from '@/api/upload'
import { buildApiUrl } from '@/utils/request'

const loading = ref(false)
const submitting = ref(false)
const assetLoading = ref(false)
const assetSaving = ref(false)
const assetImageUploading = ref(false)
const warehouses = ref([])
const warehouseAssets = ref([])
const keyword = ref('')
const statusFilter = ref('all')
const dialogVisible = ref(false)
const detailVisible = ref(false)
const assetDialogVisible = ref(false)
const editingId = ref(0)
const activeWarehouse = ref(null)

const form = reactive({
  name: '',
  location: '',
  managerName: '',
  status: 'active',
  description: ''
})

const assetForm = reactive({
  id: 0,
  assetCode: '',
  name: '',
  model: '',
  brand: '',
  labId: null,
  labName: '',
  warehouseId: null,
  warehouseName: '',
  keeper: '',
  purchaseDate: '',
  price: '',
  specJson: '',
  imageUrl: '',
  status: 'in_service',
  allowBorrow: false
})

const isEditMode = computed(() => editingId.value > 0)

const filteredWarehouses = computed(() => {
  const query = keyword.value.trim().toLowerCase()
  return warehouses.value.filter((item) => {
    const statusMatched = statusFilter.value === 'all' ? true : item.status === statusFilter.value
    if (!statusMatched) return false
    if (!query) return true
    return [item.name, item.location, item.managerName].some((value) =>
      String(value || '').toLowerCase().includes(query)
    )
  })
})

function statusText(status) {
  if (status === 'repairing') return '维修中'
  if (status === 'scrapped') return '已报废'
  return '在用'
}

function statusType(status) {
  if (status === 'repairing') return 'warning'
  if (status === 'scrapped') return 'danger'
  return 'success'
}

function resolveImageUrl(url) {
  const raw = String(url || '').trim()
  if (!raw) return ''
  return /^https?:\/\//i.test(raw) ? raw : buildApiUrl(raw)
}

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

async function fetchWarehouseAssets() {
  if (!activeWarehouse.value?.id) return
  assetLoading.value = true
  try {
    const response = await getEquipmentList({ page: 1, pageSize: 200, warehouseId: activeWarehouse.value.id })
    warehouseAssets.value = Array.isArray(response.data?.data) ? response.data.data : []
  } finally {
    assetLoading.value = false
  }
}

async function openDetailDrawer(warehouse) {
  activeWarehouse.value = warehouse
  detailVisible.value = true
  await fetchWarehouseAssets()
}

function openAssetEdit(asset) {
  Object.assign(assetForm, {
    id: Number(asset.id || 0),
    assetCode: String(asset.assetCode || ''),
    name: String(asset.name || ''),
    model: String(asset.model || ''),
    brand: String(asset.brand || ''),
    labId: asset.labId ?? null,
    labName: String(asset.labName || ''),
    warehouseId: asset.warehouseId ?? null,
    warehouseName: String(asset.warehouseName || ''),
    keeper: String(asset.keeper || ''),
    purchaseDate: String(asset.purchaseDate || ''),
    price: asset.price ?? '',
    specJson: String(asset.specJson || ''),
    imageUrl: String(asset.imageUrl || ''),
    status: String(asset.status || 'in_service'),
    allowBorrow: Boolean(asset.allowBorrow)
  })
  assetDialogVisible.value = true
}

async function handleAssetImageUpload(option) {
  assetImageUploading.value = true
  try {
    const response = await uploadImage(option.file)
    assetForm.imageUrl = String(response.data?.data?.url || '')
    ElMessage.success('图片上传成功')
    option.onSuccess?.(response.data)
  } catch (error) {
    option.onError?.(error)
  } finally {
    assetImageUploading.value = false
  }
}

async function submitAssetEdit() {
  if (!assetForm.id || !assetForm.name.trim()) {
    ElMessage.warning('请填写资产名称')
    return
  }
  assetSaving.value = true
  try {
    await updateEquipment(assetForm.id, {
      assetCode: assetForm.assetCode,
      name: assetForm.name.trim(),
      model: assetForm.model,
      brand: assetForm.brand,
      labId: assetForm.labId,
      labName: assetForm.labName,
      warehouseId: assetForm.warehouseId,
      warehouseName: assetForm.warehouseName,
      keeper: assetForm.keeper.trim(),
      purchaseDate: assetForm.purchaseDate,
      price: assetForm.price,
      specJson: assetForm.specJson,
      imageUrl: assetForm.imageUrl.trim(),
      status: assetForm.status,
      allowBorrow: assetForm.allowBorrow
    })
    ElMessage.success('资产已更新')
    assetDialogVisible.value = false
    await fetchWarehouseAssets()
  } finally {
    assetSaving.value = false
  }
}

async function reloadAll() {
  await fetchWarehouseList()
  if (detailVisible.value && activeWarehouse.value?.id) {
    const current = warehouses.value.find((item) => Number(item.id) === Number(activeWarehouse.value.id))
    if (current) activeWarehouse.value = current
    await fetchWarehouseAssets()
  }
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
      ElMessage.success('仓库已更新')
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
    if (err?.msg) ElMessage.error(err.msg)
  }
}

onMounted(() => {
  reloadAll()
})
</script>

<style scoped lang="scss">
.warehouses-page {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.hero-card,
.panel-card,
.warehouse-card {
  padding: 24px;
  border: 1px solid var(--app-border);
  border-radius: 24px;
  background: var(--app-surface);
  box-shadow: var(--app-shadow);
}

.hero-card,
.hero-actions,
.detail-head,
.card-head,
.card-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.hero-card,
.hero-actions,
.detail-head,
.card-head {
  flex-wrap: wrap;
}

.eyebrow {
  display: inline-flex;
  margin-bottom: 8px;
  color: #1d4ed8;
  font-size: 13px;
  letter-spacing: 0.08em;
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 16px;
}

.warehouse-card {
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}

.warehouse-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 14px 28px rgba(15, 23, 42, 0.1);
}

.card-head h3,
.detail-head h3 {
  margin: 0;
}

.card-head p,
.detail-head p,
.desc {
  margin: 6px 0 0;
  color: var(--app-text-secondary);
}

.meta-list {
  display: grid;
  gap: 8px;
  margin-top: 14px;
  color: var(--app-text-secondary);
}

.desc {
  min-height: 44px;
  margin-top: 14px;
}

.preview-wrap {
  margin-top: 12px;
  border-radius: 16px;
  overflow: hidden;
  border: 1px solid var(--app-border);
  background: #f8fafc;
}

.preview-image {
  display: block;
  width: 100%;
  max-height: 220px;
  object-fit: cover;
}

.card-actions {
  margin-top: 14px;
  justify-content: flex-end;
}

.detail-stack {
  display: flex;
  flex-direction: column;
  gap: 18px;
}
</style>

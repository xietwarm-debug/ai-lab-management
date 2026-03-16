<template>
  <div class="page-wrap">
    <section class="page-head">
      <div>
        <h2>设备管理</h2>
        <p>复用 `/equipments` 与 `/labs` 接口，支持查询、详情、创建、编辑和删除。</p>
      </div>
      <div class="head-actions">
        <el-button :loading="loading" @click="fetchRows">刷新</el-button>
        <el-button type="primary" @click="openCreateDialog">新增设备</el-button>
      </div>
    </section>

    <section class="page-card">
      <el-form inline>
        <el-form-item label="关键词">
          <el-input v-model="filters.keyword" placeholder="资产编号 / 设备名 / 实验室" clearable @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filters.status" style="width: 160px">
            <el-option label="全部" value="" />
            <el-option label="在用" value="in_service" />
            <el-option label="维修中" value="repairing" />
            <el-option label="已报废" value="scrapped" />
          </el-select>
        </el-form-item>
        <el-form-item label="实验室">
          <el-select v-model="filters.labId" style="width: 180px" clearable>
            <el-option label="全部" value="" />
            <el-option v-for="lab in labs" :key="lab.id" :label="lab.name" :value="lab.id" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button @click="resetFilters">重置</el-button>
          <el-button type="primary" :loading="loading" @click="handleSearch">查询</el-button>
        </el-form-item>
      </el-form>

      <div class="summary-row">
        <span class="summary-text">当前共 {{ total }} 台设备</span>
      </div>

      <el-table v-loading="loading" :data="rows">
        <el-table-column prop="assetCode" label="资产编号" min-width="140" />
        <el-table-column prop="name" label="设备名称" min-width="160" />
        <el-table-column prop="labName" label="实验室" min-width="140" />
        <el-table-column prop="brand" label="品牌" width="120" />
        <el-table-column prop="model" label="型号" width="140" />
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag size="small" :type="statusType(row.status)">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="可借用" width="90">
          <template #default="{ row }">{{ row.allowBorrow ? '是' : '否' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="260" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row)">详情</el-button>
            <el-button link type="primary" @click="openEditDialog(row)">编辑</el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>

        <template #empty>
          <el-empty description="当前筛选条件下暂无设备数据" />
        </template>
      </el-table>

      <div class="pager-row">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          layout="total, sizes, prev, pager, next"
          :total="total"
          :page-sizes="[10, 20, 50]"
          @current-change="fetchRows"
          @size-change="handlePageSizeChange"
        />
      </div>
    </section>

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑设备' : '新增设备'" width="720px">
      <el-form label-position="top">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="资产编号">
              <el-input v-model="form.assetCode" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="设备名称">
              <el-input v-model="form.name" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="实验室">
              <el-select v-model="form.labId" placeholder="请选择实验室" style="width: 100%" @change="syncLabName">
                <el-option v-for="lab in labs" :key="lab.id" :label="lab.name" :value="lab.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="状态">
              <el-select v-model="form.status" style="width: 100%">
                <el-option label="在用" value="in_service" />
                <el-option label="维修中" value="repairing" />
                <el-option label="已报废" value="scrapped" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="品牌">
              <el-input v-model="form.brand" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="型号">
              <el-input v-model="form.model" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="负责人">
              <el-input v-model="form.keeper" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="采购日期">
              <el-date-picker v-model="form.purchaseDate" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="价格">
              <el-input v-model="form.price" placeholder="例如：1999.00" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="可借用">
              <el-switch v-model="form.allowBorrow" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="规格 JSON">
              <el-input v-model="form.specJson" type="textarea" :rows="3" placeholder='例如：{"cpu":"i5","memory":"16G"}' />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="图片地址">
              <el-input v-model="form.imageUrl" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitForm">保存</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="detailVisible" title="设备详情" size="520px">
      <el-descriptions v-if="detail" :column="1" border>
        <el-descriptions-item label="设备编号">{{ detail.id }}</el-descriptions-item>
        <el-descriptions-item label="资产编号">{{ detail.assetCode || '-' }}</el-descriptions-item>
        <el-descriptions-item label="设备名称">{{ detail.name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="实验室">{{ detail.labName || '-' }}</el-descriptions-item>
        <el-descriptions-item label="状态">{{ statusLabel(detail.status) }}</el-descriptions-item>
        <el-descriptions-item label="品牌">{{ detail.brand || '-' }}</el-descriptions-item>
        <el-descriptions-item label="型号">{{ detail.model || '-' }}</el-descriptions-item>
        <el-descriptions-item label="负责人">{{ detail.keeper || '-' }}</el-descriptions-item>
        <el-descriptions-item label="采购日期">{{ detail.purchaseDate || '-' }}</el-descriptions-item>
        <el-descriptions-item label="价格">{{ detail.price || '-' }}</el-descriptions-item>
        <el-descriptions-item label="可借用">{{ detail.allowBorrow ? '是' : '否' }}</el-descriptions-item>
        <el-descriptions-item label="是否已借出">{{ detail.isBorrowed ? '是' : '否' }}</el-descriptions-item>
        <el-descriptions-item label="保修到期">{{ detail.warrantyUntil || '-' }}</el-descriptions-item>
        <el-descriptions-item label="下次保养">{{ detail.nextMaintenanceAt || '-' }}</el-descriptions-item>
        <el-descriptions-item label="规格 JSON">{{ detail.specJson || '-' }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ detail.createdAt || '-' }}</el-descriptions-item>
        <el-descriptions-item label="更新时间">{{ detail.updatedAt || '-' }}</el-descriptions-item>
      </el-descriptions>
      <el-empty v-else description="暂无设备详情" />
    </el-drawer>
  </div>
</template>

<script setup>
import { ElMessage, ElMessageBox } from 'element-plus'
import { createEquipment, deleteEquipment, getEquipmentDetail, getEquipmentList, updateEquipment } from '@/api/equipments'
import { getLabs } from '@/api/labs'

const loading = ref(false)
const saving = ref(false)
const detailLoading = ref(false)
const rows = ref([])
const labs = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const dialogVisible = ref(false)
const detailVisible = ref(false)
const detail = ref(null)

const filters = reactive({
  keyword: '',
  status: '',
  labId: ''
})

const form = reactive({
  id: 0,
  assetCode: '',
  name: '',
  model: '',
  brand: '',
  labId: undefined,
  labName: '',
  status: 'in_service',
  keeper: '',
  purchaseDate: '',
  price: '',
  specJson: '',
  imageUrl: '',
  allowBorrow: false
})

function statusLabel(status) {
  if (status === 'repairing') return '维修中'
  if (status === 'scrapped') return '已报废'
  return '在用'
}

function statusType(status) {
  if (status === 'repairing') return 'warning'
  if (status === 'scrapped') return 'danger'
  return 'success'
}

function buildParams() {
  return {
    page: page.value,
    pageSize: pageSize.value,
    keyword: filters.keyword,
    status: filters.status,
    labId: filters.labId
  }
}

function handleSearch() {
  page.value = 1
  fetchRows()
}

function resetForm() {
  form.id = 0
  form.assetCode = ''
  form.name = ''
  form.model = ''
  form.brand = ''
  form.labId = undefined
  form.labName = ''
  form.status = 'in_service'
  form.keeper = ''
  form.purchaseDate = ''
  form.price = ''
  form.specJson = ''
  form.imageUrl = ''
  form.allowBorrow = false
}

function validateForm() {
  if (!form.assetCode.trim() || !form.name.trim()) {
    ElMessage.warning('请填写资产编号和设备名称')
    return false
  }
  if (!form.labId || !form.labName.trim()) {
    ElMessage.warning('请选择实验室')
    return false
  }
  if (form.price && Number.isNaN(Number(form.price))) {
    ElMessage.warning('价格需为有效数字')
    return false
  }
  if (form.specJson.trim()) {
    try {
      JSON.parse(form.specJson)
    } catch (error) {
      ElMessage.warning('规格 JSON 格式不正确')
      return false
    }
  }
  return true
}

function syncLabName(value) {
  const target = labs.value.find((item) => Number(item.id) === Number(value))
  form.labName = target?.name || ''
}

function openCreateDialog() {
  resetForm()
  dialogVisible.value = true
}

function openEditDialog(row) {
  form.id = Number(row.id || 0)
  form.assetCode = row.assetCode || ''
  form.name = row.name || ''
  form.model = row.model || ''
  form.brand = row.brand || ''
  form.labId = row.labId
  form.labName = row.labName || ''
  form.status = row.status || 'in_service'
  form.keeper = row.keeper || ''
  form.purchaseDate = row.purchaseDate || ''
  form.price = row.price != null ? String(row.price) : ''
  form.specJson = row.specJson || ''
  form.imageUrl = row.imageUrl || ''
  form.allowBorrow = Boolean(row.allowBorrow)
  dialogVisible.value = true
}

async function openDetail(row) {
  detailVisible.value = true
  detailLoading.value = true
  detail.value = null
  try {
    const response = await getEquipmentDetail(row.id)
    detail.value = response.data?.data || null
  } finally {
    detailLoading.value = false
  }
}

async function fetchLabs() {
  const response = await getLabs()
  labs.value = Array.isArray(response.data?.data) ? response.data.data : []
}

async function fetchRows() {
  loading.value = true
  try {
    const response = await getEquipmentList(buildParams())
    rows.value = response.data?.data || []
    total.value = response.data?.meta?.total || 0
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filters.keyword = ''
  filters.status = ''
  filters.labId = ''
  handleSearch()
}

function handlePageSizeChange(size) {
  pageSize.value = size
  page.value = 1
  fetchRows()
}

async function submitForm() {
  if (!validateForm()) return

  const payload = {
    assetCode: form.assetCode.trim(),
    name: form.name.trim(),
    model: form.model.trim(),
    brand: form.brand.trim(),
    labId: form.labId,
    labName: form.labName.trim(),
    status: form.status,
    keeper: form.keeper.trim(),
    purchaseDate: form.purchaseDate,
    price: form.price,
    specJson: form.specJson.trim(),
    imageUrl: form.imageUrl.trim(),
    allowBorrow: form.allowBorrow
  }

  saving.value = true
  try {
    if (form.id) {
      await updateEquipment(form.id, payload)
      ElMessage.success('设备已更新')
    } else {
      await createEquipment(payload)
      ElMessage.success('设备已创建')
    }
    dialogVisible.value = false
    fetchRows()
  } finally {
    saving.value = false
  }
}

async function handleDelete(row) {
  await ElMessageBox.confirm(`确认删除设备 ${row.name} 吗？`, '删除设备', { type: 'warning' })
  await deleteEquipment(row.id)
  ElMessage.success('设备已删除')
  fetchRows()
}

onMounted(async () => {
  await fetchLabs()
  await fetchRows()
})
</script>

<style scoped lang="scss">
.page-wrap {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.page-head,
.page-card {
  padding: 24px;
  border: 1px solid var(--app-border);
  border-radius: 24px;
  background: var(--app-surface);
  box-shadow: var(--app-shadow);
}

.page-head,
.head-actions,
.pager-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.page-head h2 {
  margin: 0 0 8px;
}

.page-head p,
.summary-text {
  margin: 0;
  color: var(--app-muted);
}

.summary-row {
  margin: 6px 0 16px;
}

.pager-row {
  margin-top: 18px;
  justify-content: flex-end;
}
</style>

<template>
  <div class="labs-page">
    <section class="hero-card">
      <div class="hero-copy">
        <span class="eyebrow">实验室底座</span>
        <h2>实验室管理</h2>
        <p>统一维护实验室资料、环境监测状态和排课入口，方便后台从空间维度管理业务。</p>
        <div class="hero-meta">
          <span>实验室数：{{ labs.length }}</span>
          <span>监测刷新：{{ sensorUpdatedAt || '-' }}</span>
        </div>
      </div>
      <div class="hero-actions">
        <el-button type="primary" @click="openCreateDialog">新增实验室</el-button>
        <el-button @click="fetchSensorStatus(true)">刷新监测</el-button>
        <el-button @click="reloadAll">刷新全部</el-button>
        <el-button text @click="router.push('/schedule-manage')">进入排课管理</el-button>
      </div>
    </section>

    <section class="metric-grid">
      <article v-for="item in metrics" :key="item.key" class="metric-card">
        <span class="metric-label">{{ item.label }}</span>
        <strong class="metric-value">{{ item.value }}</strong>
        <span class="metric-sub">{{ item.hint }}</span>
      </article>
    </section>

    <section class="panel-card filter-card">
      <div class="panel-head">
        <div>
          <h3>筛选条件</h3>
          <span>匹配 {{ filteredLabs.length }} 个实验室</span>
        </div>
      </div>
      <el-form inline>
        <el-form-item label="关键词">
          <el-input v-model="keyword" placeholder="按名称或说明搜索" clearable />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="statusFilter" style="width: 160px">
            <el-option label="全部" value="all" />
            <el-option label="空闲" value="free" />
            <el-option label="使用中" value="busy" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>
    </section>

    <section v-if="loading" class="panel-card">
      <el-skeleton :rows="5" animated />
    </section>

    <section v-else class="lab-grid">
      <article v-for="lab in filteredLabs" :key="lab.id" class="lab-card">
        <div class="lab-top">
          <div>
            <h3>{{ lab.name || '-' }}</h3>
            <p>ID: {{ lab.id }}</p>
          </div>
          <el-tag :type="lab.status === 'free' ? 'success' : 'warning'">
            {{ lab.status === 'free' ? '空闲' : '使用中' }}
          </el-tag>
        </div>

        <div v-if="lab.imageUrl" class="cover-wrap">
          <img :src="resolveImageUrl(lab.imageUrl)" :alt="lab.name" class="cover-image">
        </div>
        <div v-else class="cover-fallback">
          <span>LAB</span>
        </div>

        <div class="meta-row">
          <span>容量 {{ lab.capacity || 0 }}</span>
          <span>设备 {{ lab.deviceCount || 0 }}</span>
        </div>

        <p class="description">{{ lab.description || '暂无说明' }}</p>

        <div class="sensor-panel">
          <div class="sensor-head">
            <strong>环境与安全监测</strong>
            <el-tag size="small" :type="sensorLevelType(sensorInfo(lab.id)?.level)">
              {{ sensorLevelLabel(sensorInfo(lab.id)?.level) }}
            </el-tag>
          </div>

          <div v-if="sensorInfo(lab.id)" class="sensor-grid">
            <span :class="sensorCellClass(sensorInfo(lab.id), 'temperature')">温度 {{ sensorInfo(lab.id).readings.temperatureC }}°C</span>
            <span :class="sensorCellClass(sensorInfo(lab.id), 'humidity')">湿度 {{ sensorInfo(lab.id).readings.humidityPct }}%</span>
            <span :class="sensorCellClass(sensorInfo(lab.id), 'smoke')">烟雾 {{ sensorInfo(lab.id).readings.smokePpm }}ppm</span>
            <span :class="sensorCellClass(sensorInfo(lab.id), 'voltage')">电压 {{ sensorInfo(lab.id).readings.voltageV }}V</span>
            <span :class="sensorCellClass(sensorInfo(lab.id), 'current')">电流 {{ sensorInfo(lab.id).readings.currentA }}A</span>
            <span :class="sensorCellClass(sensorInfo(lab.id), 'people')">人数 {{ sensorInfo(lab.id).readings.peopleCount }}</span>
          </div>
          <el-empty v-else description="暂无监测数据" :image-size="60" />

          <p v-if="sensorInfo(lab.id)?.alerts?.length" class="sensor-alert">
            {{ sensorInfo(lab.id).alerts.map((item) => item.message).join('；') }}
          </p>
          <p v-if="sensorInfo(lab.id)?.collectedAt" class="sensor-time">
            更新时间：{{ sensorInfo(lab.id).collectedAt }}
          </p>
        </div>

        <div class="lab-actions">
          <el-button @click="router.push({ path: '/room-map', query: { labId: lab.id } })">平面图</el-button>
          <el-button @click="openEditDialog(lab)">编辑</el-button>
          <el-button @click="router.push({ path: '/schedule-manage', query: { labId: lab.id } })">查看排课</el-button>
          <el-popconfirm title="确定删除这个实验室吗？" @confirm="handleDelete(lab)">
            <template #reference>
              <el-button type="danger" plain>删除</el-button>
            </template>
          </el-popconfirm>
        </div>
      </article>
    </section>

    <el-dialog v-model="dialogVisible" :title="isEditMode ? '编辑实验室' : '新增实验室'" width="620px">
      <el-form label-position="top">
        <el-form-item label="实验室名称">
          <el-input v-model="form.name" maxlength="60" />
        </el-form-item>
        <el-form-item label="实验室状态">
          <el-radio-group v-model="form.status">
            <el-radio-button label="free">空闲</el-radio-button>
            <el-radio-button label="busy">使用中</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <div class="dialog-grid">
          <el-form-item label="容纳人数">
            <el-input-number v-model="form.capacity" :min="0" :max="500" />
          </el-form-item>
          <el-form-item label="设备数量">
            <el-input-number v-model="form.deviceCount" :min="0" :max="5000" />
          </el-form-item>
        </div>
        <el-form-item label="实验室说明">
          <el-input v-model="form.description" type="textarea" :rows="4" maxlength="300" show-word-limit />
        </el-form-item>
        <el-form-item label="封面图片">
          <div class="upload-box">
            <el-upload
              :show-file-list="false"
              :http-request="handleUpload"
              accept=".jpg,.jpeg,.png,.gif,.webp"
            >
              <el-button :loading="uploading">上传图片</el-button>
            </el-upload>
            <el-input v-model="form.imageUrl" placeholder="或直接填写图片地址" />
          </div>
          <div v-if="form.imageUrl" class="preview-wrap">
            <img :src="resolveImageUrl(form.imageUrl)" alt="preview" class="preview-image">
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitForm">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { buildApiUrl } from '@/utils/request'
import {
  createLab,
  deleteLab,
  getLabs,
  getLabSensorStatus,
  updateLab,
  uploadLabImage
} from '@/api/labs'

const router = useRouter()

const loading = ref(false)
const submitting = ref(false)
const uploading = ref(false)
const labs = ref([])
const sensorMap = ref({})
const sensorUpdatedAt = ref('')
const keyword = ref('')
const statusFilter = ref('all')
const dialogVisible = ref(false)
const editingId = ref(0)
const form = reactive({
  name: '',
  status: 'free',
  capacity: 0,
  deviceCount: 0,
  description: '',
  imageUrl: ''
})

const isEditMode = computed(() => editingId.value > 0)

const filteredLabs = computed(() => {
  const query = keyword.value.trim().toLowerCase()
  return labs.value.filter((lab) => {
    const statusMatched = statusFilter.value === 'all' ? true : lab.status === statusFilter.value
    if (!statusMatched) return false
    if (!query) return true
    return [
      String(lab.name || '').toLowerCase(),
      String(lab.description || '').toLowerCase(),
      String(lab.id || '')
    ].some((item) => item.includes(query))
  })
})

const metrics = computed(() => {
  const warningCount = Object.values(sensorMap.value).filter((item) => item?.level === 'warning').length
  const alarmCount = Object.values(sensorMap.value).filter((item) => item?.level === 'alarm').length
  return [
    {
      key: 'total',
      label: '实验室总数',
      value: labs.value.length,
      hint: '系统全部空间'
    },
    {
      key: 'free',
      label: '空闲中',
      value: labs.value.filter((item) => item.status === 'free').length,
      hint: '当前可预约'
    },
    {
      key: 'warning',
      label: '预警中',
      value: warningCount,
      hint: '需要关注'
    },
    {
      key: 'alarm',
      label: '报警中',
      value: alarmCount,
      hint: '建议立即处理'
    }
  ]
})

function resetForm() {
  editingId.value = 0
  form.name = ''
  form.status = 'free'
  form.capacity = 0
  form.deviceCount = 0
  form.description = ''
  form.imageUrl = ''
}

function openCreateDialog() {
  resetForm()
  dialogVisible.value = true
}

function openEditDialog(lab) {
  editingId.value = Number(lab.id || 0)
  form.name = String(lab.name || '')
  form.status = String(lab.status || 'free')
  form.capacity = Number(lab.capacity || 0)
  form.deviceCount = Number(lab.deviceCount || 0)
  form.description = String(lab.description || '')
  form.imageUrl = String(lab.imageUrl || '')
  dialogVisible.value = true
}

function resetFilters() {
  keyword.value = ''
  statusFilter.value = 'all'
}

function resolveImageUrl(url) {
  const text = String(url || '').trim()
  if (!text) return ''
  return /^https?:\/\//i.test(text) ? text : buildApiUrl(text)
}

function sensorInfo(labId) {
  return sensorMap.value[String(labId)] || null
}

function sensorLevelLabel(level) {
  if (level === 'alarm') return '报警'
  if (level === 'warning') return '预警'
  return '正常'
}

function sensorLevelType(level) {
  if (level === 'alarm') return 'danger'
  if (level === 'warning') return 'warning'
  return 'success'
}

function sensorCellClass(sensor, moduleKey) {
  const status = sensor?.statusByModule?.[moduleKey]
  if (status === 'alarm') return 'sensor-cell sensor-cell--alarm'
  if (status === 'warning') return 'sensor-cell sensor-cell--warning'
  return 'sensor-cell sensor-cell--normal'
}

async function fetchLabsList() {
  loading.value = true
  try {
    const response = await getLabs()
    labs.value = Array.isArray(response.data?.data) ? response.data.data : []
  } finally {
    loading.value = false
  }
}

async function fetchSensorStatus(force = false) {
  try {
    const response = await getLabSensorStatus(force ? { force: 1 } : {})
    const rows = Array.isArray(response.data?.data) ? response.data.data : []
    sensorUpdatedAt.value = new Date().toLocaleString()
    sensorMap.value = rows.reduce((accumulator, item) => {
      accumulator[String(item.labId)] = item
      return accumulator
    }, {})
  } catch (error) {
    if (force) ElMessage.error('监测数据刷新失败')
  }
}

async function reloadAll() {
  await Promise.all([fetchLabsList(), fetchSensorStatus(true)])
}

async function handleUpload(option) {
  uploading.value = true
  try {
    const response = await uploadLabImage(option.file)
    form.imageUrl = String(response.data?.data?.url || '')
    ElMessage.success('图片上传成功')
  } finally {
    uploading.value = false
  }
}

async function submitForm() {
  if (!String(form.name || '').trim()) {
    ElMessage.warning('请填写实验室名称')
    return
  }
  submitting.value = true
  try {
    const payload = {
      name: String(form.name || '').trim(),
      status: form.status,
      capacity: Number(form.capacity || 0),
      deviceCount: Number(form.deviceCount || 0),
      description: String(form.description || '').trim(),
      imageUrl: String(form.imageUrl || '').trim()
    }
    if (isEditMode.value) {
      await updateLab(editingId.value, payload)
      ElMessage.success('实验室已更新')
    } else {
      await createLab(payload)
      ElMessage.success('实验室已创建')
    }
    dialogVisible.value = false
    await reloadAll()
  } finally {
    submitting.value = false
  }
}

async function handleDelete(lab) {
  await deleteLab(lab.id)
  ElMessage.success('实验室已删除')
  await reloadAll()
}

onMounted(() => {
  reloadAll()
})
</script>

<style scoped lang="scss">
.labs-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.hero-card,
.metric-card,
.panel-card,
.lab-card {
  border: 1px solid var(--app-border);
  border-radius: 24px;
  background: var(--app-surface);
  box-shadow: var(--app-shadow);
}

.hero-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 28px;
  background:
    radial-gradient(circle at top right, rgba(14, 165, 233, 0.16), transparent 30%),
    linear-gradient(135deg, #fbfdff 0%, #edf6fb 100%);
}

.hero-copy,
.meta-row,
.hero-meta,
.hero-actions,
.lab-actions,
.upload-box {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.hero-copy {
  flex-direction: column;
}

.hero-card h2,
.panel-head h3,
.lab-top h3 {
  margin: 0;
}

.hero-card p,
.hero-meta,
.metric-sub,
.metric-label,
.panel-head span,
.description,
.sensor-time,
.lab-top p {
  color: var(--app-muted);
}

.eyebrow {
  display: inline-flex;
  width: fit-content;
  padding: 6px 10px;
  border-radius: 999px;
  background: #dbeafe;
  color: #1d4ed8;
  font-size: 12px;
  font-weight: 700;
}

.metric-grid,
.lab-grid,
.dialog-grid,
.sensor-grid {
  display: grid;
  gap: 20px;
}

.metric-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.metric-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 24px;
}

.metric-value {
  font-size: 32px;
}

.panel-card,
.lab-card {
  padding: 24px;
}

.panel-head,
.lab-top,
.sensor-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.lab-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.lab-card {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.cover-wrap,
.preview-wrap {
  overflow: hidden;
  border-radius: 18px;
}

.cover-image,
.preview-image {
  width: 100%;
  display: block;
  object-fit: cover;
}

.cover-wrap {
  height: 220px;
}

.preview-wrap {
  width: 180px;
  margin-top: 10px;
}

.cover-fallback {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 220px;
  border-radius: 18px;
  background: linear-gradient(135deg, #dbeafe 0%, #f0f9ff 100%);
  color: #1e3a8a;
  font-size: 32px;
  font-weight: 700;
}

.meta-row span {
  padding: 6px 10px;
  border-radius: 999px;
  background: #f1f5f9;
  color: #334155;
  font-size: 12px;
}

.description {
  margin: 0;
  line-height: 1.7;
}

.sensor-panel {
  padding: 16px;
  border-radius: 20px;
  background: #f8fafc;
}

.sensor-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  margin-top: 12px;
  gap: 10px;
}

.sensor-cell {
  padding: 10px 12px;
  border-radius: 14px;
  border: 1px solid transparent;
  font-size: 12px;
}

.sensor-cell--normal {
  background: #eff6ff;
  border-color: #bfdbfe;
  color: #1d4ed8;
}

.sensor-cell--warning {
  background: #fffbeb;
  border-color: #fcd34d;
  color: #b45309;
}

.sensor-cell--alarm {
  background: #fff1f2;
  border-color: #fda4af;
  color: #be123c;
}

.sensor-alert {
  margin: 12px 0 0;
  color: #b42318;
  line-height: 1.7;
}

.dialog-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

@media (max-width: 1280px) {
  .metric-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .lab-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .hero-card,
  .panel-head,
  .lab-top,
  .sensor-head {
    flex-direction: column;
    align-items: flex-start;
  }

  .metric-grid,
  .sensor-grid,
  .dialog-grid {
    grid-template-columns: 1fr;
  }
}
</style>

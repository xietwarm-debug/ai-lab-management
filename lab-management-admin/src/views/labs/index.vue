<template>
  <div class="labs-page">
    <section class="panel-card hero-card">
      <div class="hero-top">
        <div class="hero-copy">
          <div class="title-row">
            <h2 class="page-title">实验室管理</h2>
            <span class="eyebrow">实验室底座</span>
          </div>
          <p class="page-desc">统一维护实验室资料、环境监测状态和排课入口，方便从空间维度查看运行情况与基础配置。</p>

          <div class="hero-meta">
            <div class="meta-item">
              <span class="meta-label">总数</span>
              <strong class="meta-value">{{ labs.length }}</strong>
            </div>
            <div class="meta-item">
              <span class="meta-label">监测更新时间</span>
              <strong class="meta-value text-primary">{{ sensorUpdatedAt || '-' }}</strong>
            </div>
          </div>
        </div>

        <div class="hero-actions">
          <el-button class="premium-btn" @click="fetchSensorStatus(true)">
            <el-icon class="el-icon--left"><RefreshRight /></el-icon>
            刷新监测
          </el-button>
          <el-button class="premium-btn" @click="reloadAll">刷新全部</el-button>
          <el-button class="premium-btn" type="primary" @click="openCreateDialog">
            <el-icon class="el-icon--left"><Plus /></el-icon>
            新增实验室
          </el-button>
        </div>
      </div>

      <div class="hero-bottom">
        <el-button
          class="premium-btn schedule-btn"
          type="primary"
          plain
          @click="router.push('/schedule-manage')"
        >
          进入排课管理
          <el-icon class="el-icon--right"><ArrowRight /></el-icon>
        </el-button>
      </div>
    </section>

    <section class="metric-grid">
      <article
        v-for="item in metrics"
        :key="item.key"
        class="metric-card panel-card"
        :class="`metric-${item.key}`"
      >
        <div class="metric-top">
          <span class="metric-label">{{ item.label }}</span>
          <span class="metric-dot"></span>
        </div>
        <div class="metric-data">
          <strong class="metric-value" :class="getMetricValueClass(item.key)">{{ item.value }}</strong>
          <span class="metric-sub">{{ item.hint }}</span>
        </div>
      </article>
    </section>

    <section class="filter-header-section panel-card">
      <div class="filter-header">
        <div>
          <h3 class="section-title">实验室列表</h3>
          <p class="section-subtitle">共 {{ filteredLabs.length }} 个空间，支持按状态与风险优先查看</p>
        </div>

        <el-form inline class="filter-form" @submit.prevent>
          <el-form-item>
            <el-input
              v-model="keyword"
              placeholder="按名称、说明或 ID 搜索..."
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
              <el-option label="全部使用状态" value="all" />
              <el-option label="空闲" value="free" />
              <el-option label="使用中" value="busy" />
            </el-select>
          </el-form-item>

          <el-form-item>
            <el-select v-model="levelFilter" class="filter-select premium-input">
              <el-option label="全部监测状态" value="all" />
              <el-option label="正常" value="normal" />
              <el-option label="预警" value="warning" />
              <el-option label="报警" value="alarm" />
            </el-select>
          </el-form-item>

          <el-form-item>
            <el-select v-model="sortBy" class="filter-select premium-input">
              <el-option label="默认排序" value="default" />
              <el-option label="按风险优先" value="riskDesc" />
              <el-option label="按温度降序" value="temperatureDesc" />
              <el-option label="按人数降序" value="peopleDesc" />
              <el-option label="按名称 A-Z" value="nameAsc" />
            </el-select>
          </el-form-item>

          <el-form-item style="margin-right: 0">
            <el-button class="premium-btn" @click="resetFilters">重置</el-button>
          </el-form-item>
        </el-form>
      </div>
    </section>

    <section v-if="loading" class="lab-grid">
      <div v-for="i in 3" :key="i" class="lab-card loading-card panel-card">
        <el-skeleton :rows="6" animated />
      </div>
    </section>

    <section v-else class="lab-grid">
      <article
        v-for="lab in filteredLabs"
        :key="lab.id"
        class="lab-card panel-card"
        :class="labCardClass(lab)"
      >
        <div class="cover-wrap">
          <img
            v-if="lab.imageUrl"
            :src="resolveImageUrl(lab.imageUrl)"
            :alt="lab.name"
            class="cover-image"
          />
          <div v-else class="cover-fallback">LABORATORY</div>

          <div class="status-badge" :class="usageStatusClass(lab.status)">
            <span class="status-dot-white"></span>
            {{ lab.status === 'free' ? '空闲' : '使用中' }}
          </div>

          <div
            class="risk-badge"
            :class="sensorLevelType(sensorInfo(lab.id)?.level)"
          >
            {{ sensorLevelLabel(sensorInfo(lab.id)?.level) }}
          </div>
        </div>

        <div class="lab-content">
          <div class="lab-header">
            <div class="lab-header-main">
              <h3 class="lab-title" :title="lab.name">{{ lab.name || '-' }}</h3>
              <div class="lab-subline">
                <span class="lab-id">ID: {{ lab.id }}</span>
                <span class="meta-inline">容量 {{ lab.capacity || 0 }}</span>
                <span class="meta-inline">设备 {{ lab.deviceCount || 0 }}</span>
              </div>
            </div>

            <el-dropdown trigger="click">
              <el-button link class="more-btn">
                <el-icon><MoreFilled /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click="router.push({ path: '/room-map', query: { labId: lab.id } })">
                    查看平面图
                  </el-dropdown-item>
                  <el-dropdown-item @click="router.push({ path: '/schedule-manage', query: { labId: lab.id } })">
                    进入排课
                  </el-dropdown-item>
                  <el-dropdown-item @click="openEditDialog(lab)">
                    编辑信息
                  </el-dropdown-item>
                  <el-dropdown-item divided @click="confirmDelete(lab)">
                    删除实验室
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>

          <p class="description" :title="lab.description">
            {{ lab.description || '暂无详细说明。' }}
          </p>

          <div class="sensor-panel">
            <div class="sensor-head">
              <span class="sensor-title">环境与安全监测</span>
              <span class="sensor-status" :class="sensorLevelType(sensorInfo(lab.id)?.level)">
                <span class="status-dot"></span>
                {{ sensorLevelLabel(sensorInfo(lab.id)?.level) }}
              </span>
            </div>

            <template v-if="sensorInfo(lab.id)">
              <div class="sensor-core-grid">
                <div
                  class="core-metric panel-card"
                  :class="sensorCellClass(sensorInfo(lab.id), 'temperature')"
                >
                  <span class="core-label">温度</span>
                  <strong class="core-value">{{ sensorInfo(lab.id).readings.temperatureC }}°C</strong>
                </div>

                <div
                  class="core-metric panel-card"
                  :class="sensorCellClass(sensorInfo(lab.id), 'humidity')"
                >
                  <span class="core-label">湿度</span>
                  <strong class="core-value">{{ sensorInfo(lab.id).readings.humidityPct }}%</strong>
                </div>

                <div
                  class="core-metric panel-card"
                  :class="sensorCellClass(sensorInfo(lab.id), 'people')"
                >
                  <span class="core-label">人数</span>
                  <strong class="core-value">{{ sensorInfo(lab.id).readings.peopleCount }}</strong>
                </div>
              </div>

              <div v-if="sensorInfo(lab.id)?.alerts?.length" class="sensor-alert panel-card">
                <el-icon class="alert-icon"><WarningFilled /></el-icon>
                <span>{{ formatAlerts(sensorInfo(lab.id).alerts) }}</span>
              </div>

              <div class="sensor-more-wrap">
                <el-button
                  link
                  class="toggle-btn"
                  @click="toggleExpanded(lab.id)"
                >
                  {{ expandedMap[String(lab.id)] ? '收起更多指标' : '查看更多指标' }}
                </el-button>
              </div>

              <div v-if="expandedMap[String(lab.id)]" class="sensor-list secondary-grid">
                <div class="sensor-item panel-card" :class="sensorCellClass(sensorInfo(lab.id), 'smoke')">
                  <span class="sensor-lbl">烟雾</span>
                  <span class="sensor-val">{{ sensorInfo(lab.id).readings.smokePpm }} ppm</span>
                </div>
                <div class="sensor-item panel-card" :class="sensorCellClass(sensorInfo(lab.id), 'voltage')">
                  <span class="sensor-lbl">电压</span>
                  <span class="sensor-val">{{ sensorInfo(lab.id).readings.voltageV }} V</span>
                </div>
                <div class="sensor-item panel-card" :class="sensorCellClass(sensorInfo(lab.id), 'current')">
                  <span class="sensor-lbl">电流</span>
                  <span class="sensor-val">{{ sensorInfo(lab.id).readings.currentA }} A</span>
                </div>
              </div>
            </template>

            <div v-else class="sensor-empty">
              <span>暂无设备回传数据</span>
            </div>
          </div>
        </div>

        <div class="lab-actions">
          <div class="action-group-left">
            <el-button
              link
              class="action-text-btn"
              @click="router.push({ path: '/room-map', query: { labId: lab.id } })"
            >
              平面图
            </el-button>
            <div class="divider"></div>
            <el-button
              link
              class="action-text-btn"
              @click="router.push({ path: '/schedule-manage', query: { labId: lab.id } })"
            >
              排课
            </el-button>
          </div>

          <div class="action-group-right">
            <el-button
              link
              type="primary"
              class="action-text-btn primary-text"
              @click="openEditDialog(lab)"
            >
              编辑
            </el-button>

            <el-popconfirm
              title="确定删除这个实验室吗？"
              @confirm="handleDelete(lab)"
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
      </article>
    </section>

    <el-dialog
      v-model="dialogVisible"
      :title="isEditMode ? '编辑实验室' : '新增实验室'"
      width="640px"
      class="premium-dialog"
      :show-close="false"
    >
      <el-form label-position="top" class="custom-form">
        <el-form-item label="实验室名称">
          <el-input
            v-model="form.name"
            maxlength="60"
            placeholder="例如：C405 高性能计算实验室"
            class="premium-input"
          />
        </el-form-item>

        <el-form-item label="当前状态">
          <el-radio-group v-model="form.status" class="premium-radio">
            <el-radio-button label="free">空闲中</el-radio-button>
            <el-radio-button label="busy">使用中</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <div class="dialog-grid">
          <el-form-item label="容纳人数">
            <el-input-number
              v-model="form.capacity"
              :min="0"
              :max="500"
              class="full-width-number premium-input"
              controls-position="right"
            />
          </el-form-item>
          <el-form-item label="设备数量">
            <el-input-number
              v-model="form.deviceCount"
              :min="0"
              :max="5000"
              class="full-width-number premium-input"
              controls-position="right"
            />
          </el-form-item>
        </div>

        <el-form-item label="实验室说明">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="3"
            maxlength="300"
            show-word-limit
            placeholder="描述该实验室的核心用途与软硬件配置..."
            class="premium-input"
          />
        </el-form-item>

        <el-form-item label="实景封面">
          <div class="upload-box">
            <el-input
              v-model="form.imageUrl"
              placeholder="填写图片 URL 地址或直接上传"
              class="upload-input premium-input"
            >
              <template #append>
                <el-upload
                  :show-file-list="false"
                  :http-request="handleUpload"
                  accept=".jpg,.jpeg,.png,.gif,.webp"
                  class="inline-upload"
                >
                  <el-button :loading="uploading">
                    <el-icon><Upload /></el-icon>
                    上传
                  </el-button>
                </el-upload>
              </template>
            </el-input>
          </div>

          <div v-if="form.imageUrl" class="preview-wrap panel-card">
            <img :src="resolveImageUrl(form.imageUrl)" alt="preview" class="preview-image" />
          </div>
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

    <el-popconfirm
      v-if="false"
      title=""
    />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Plus,
  ArrowRight,
  RefreshRight,
  WarningFilled,
  Search,
  Upload,
  MoreFilled
} from '@element-plus/icons-vue'
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
const levelFilter = ref('all')
const sortBy = ref('default')
const dialogVisible = ref(false)
const editingId = ref(0)
const expandedMap = ref({})

const form = reactive({
  name: '',
  status: 'free',
  capacity: 0,
  deviceCount: 0,
  description: '',
  imageUrl: ''
})

const isEditMode = computed(() => editingId.value > 0)

const metrics = computed(() => {
  const warningCount = Object.values(sensorMap.value).filter((item) => item?.level === 'warning').length
  const alarmCount = Object.values(sensorMap.value).filter((item) => item?.level === 'alarm').length

  return [
    { key: 'total', label: '实验室总数', value: labs.value.length, hint: '系统全部空间' },
    { key: 'free', label: '空闲中', value: labs.value.filter((item) => item.status === 'free').length, hint: '当前可预约' },
    { key: 'warning', label: '预警中', value: warningCount, hint: '需留意环境变化' },
    { key: 'alarm', label: '报警中', value: alarmCount, hint: '建议立即排查处理' }
  ]
})

const filteredLabs = computed(() => {
  const query = keyword.value.trim().toLowerCase()

  let result = labs.value.filter((lab) => {
    const labSensor = sensorInfo(lab.id)
    const statusMatched = statusFilter.value === 'all' ? true : lab.status === statusFilter.value
    const levelMatched =
      levelFilter.value === 'all'
        ? true
        : levelFilter.value === 'normal'
          ? !labSensor || !labSensor.level || labSensor.level === 'normal'
          : labSensor?.level === levelFilter.value

    if (!statusMatched || !levelMatched) return false

    if (!query) return true

    return [
      String(lab.name || '').toLowerCase(),
      String(lab.description || '').toLowerCase(),
      String(lab.id || '')
    ].some((item) => item.includes(query))
  })

  if (sortBy.value === 'riskDesc') {
    result = [...result].sort((a, b) => riskScore(sensorInfo(b.id)?.level) - riskScore(sensorInfo(a.id)?.level))
  } else if (sortBy.value === 'temperatureDesc') {
    result = [...result].sort((a, b) => {
      const av = Number(sensorInfo(a.id)?.readings?.temperatureC || 0)
      const bv = Number(sensorInfo(b.id)?.readings?.temperatureC || 0)
      return bv - av
    })
  } else if (sortBy.value === 'peopleDesc') {
    result = [...result].sort((a, b) => {
      const av = Number(sensorInfo(a.id)?.readings?.peopleCount || 0)
      const bv = Number(sensorInfo(b.id)?.readings?.peopleCount || 0)
      return bv - av
    })
  } else if (sortBy.value === 'nameAsc') {
    result = [...result].sort((a, b) => String(a.name || '').localeCompare(String(b.name || ''), 'zh-CN'))
  }

  return result
})

function riskScore(level) {
  if (level === 'alarm') return 3
  if (level === 'warning') return 2
  return 1
}

function getMetricValueClass(key) {
  if (key === 'alarm' && metrics.value.find((m) => m.key === 'alarm')?.value > 0) return 'text-danger'
  if (key === 'warning' && metrics.value.find((m) => m.key === 'warning')?.value > 0) return 'text-warning'
  if (key === 'free') return 'text-success'
  return 'text-main'
}

function labCardClass(lab) {
  const level = sensorInfo(lab.id)?.level
  if (level === 'alarm') return 'is-alarm'
  if (level === 'warning') return 'is-warning'
  return 'is-normal'
}

function usageStatusClass(status) {
  return status === 'free' ? 'bg-success' : 'bg-warning'
}

function resetForm() {
  editingId.value = 0
  Object.assign(form, {
    name: '',
    status: 'free',
    capacity: 0,
    deviceCount: 0,
    description: '',
    imageUrl: ''
  })
}

function openCreateDialog() {
  resetForm()
  dialogVisible.value = true
}

function openEditDialog(lab) {
  editingId.value = Number(lab.id || 0)
  Object.assign(form, {
    name: String(lab.name || ''),
    status: String(lab.status || 'free'),
    capacity: Number(lab.capacity || 0),
    deviceCount: Number(lab.deviceCount || 0),
    description: String(lab.description || ''),
    imageUrl: String(lab.imageUrl || '')
  })
  dialogVisible.value = true
}

function resetFilters() {
  keyword.value = ''
  statusFilter.value = 'all'
  levelFilter.value = 'all'
  sortBy.value = 'default'
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
  if (status === 'alarm') return 'alarm-val'
  if (status === 'warning') return 'warning-val'
  return 'normal-val'
}

function toggleExpanded(labId) {
  const key = String(labId)
  expandedMap.value[key] = !expandedMap.value[key]
}

function formatAlerts(alerts = []) {
  return alerts.map((item) => item.message).join('；')
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
    sensorMap.value = rows.reduce((acc, item) => {
      acc[String(item.labId)] = item
      return acc
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
    const payload = { ...form }
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

async function confirmDelete(lab) {
  try {
    await ElMessageBox.confirm(`确定删除“${lab.name}”吗？`, '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    })
    await handleDelete(lab)
  } catch (error) {
    // 用户取消
  }
}

onMounted(() => {
  reloadAll()
})
</script>

<style scoped lang="scss">
// 注意：Scoped 样式内 :root 往往失效，将变量直接挂在组件根类名上
.labs-page {
  --color-primary: #2563eb;
  --color-primary-hover: #1d4ed8;
  --color-primary-light: #eff6ff;

  --color-danger: #ef4444;
  --color-danger-light: #fef2f2;
  --color-warning: #f59e0b;
  --color-warning-light: #fffbeb;
  --color-success: #10b981;
  --color-success-light: #ecfdf5;

  // --- 配色修正，增强区分 ---
  --bg-page: #f1f5f9;       // 深灰色背景，拉开与卡片的距离
  --bg-card: #ffffff;       // 卡片保持纯白
  --bg-subtle: #e2e8f0;     // 卡片内嵌面板使用更深的灰色

  --text-main: #0f172a;
  --text-regular: #334155;
  --text-muted: #64748b;

  // --- 边框和阴影增强 ---
  --border-light: #d1d5db;   // 边框加深
  --border-divider: #e5e7eb;

  --shadow-premium: 0 6px 16px rgba(15, 23, 42, 0.08); // 阴影加深
  --shadow-premium-hover: 0 12px 28px rgba(37, 99, 235, 0.12);

  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;

  // 全局页面样式修复
  display: flex;
  flex-direction: column;
  gap: 24px;
  padding: 32px;
  background-color: var(--bg-page);
  min-height: 100vh;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  box-sizing: border-box;
}

// 统一卡片基础样式
.panel-card {
  background: var(--bg-card);
  border: 1px solid var(--border-light); // 所有卡片默认带边框
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-premium);
  box-sizing: border-box;
}

/* hero */
.hero-card {
  padding: 28px 32px;
  border-width: 2px; // 强化顶部 Hero
}

.hero-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 24px;
  flex-wrap: wrap;
}

.hero-bottom {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid var(--border-divider);
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
  flex-wrap: wrap;
}

.page-title {
  margin: 0;
  font-size: 26px;
  font-weight: 700;
  letter-spacing: -0.5px;
  color: var(--text-main);
}

.eyebrow {
  padding: 5px 10px;
  border-radius: 999px;
  background: var(--color-primary-light);
  color: var(--color-primary);
  font-size: 12px;
  font-weight: 600;
}

.page-desc {
  margin: 0;
  font-size: 14px;
  color: var(--text-muted);
  line-height: 1.6;
}

.hero-meta {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
  margin-top: 6px;
}

.meta-item {
  display: flex;
  align-items: baseline;
  gap: 8px;
  padding: 10px 14px;
  background: var(--bg-page); // 使用页面背景色做内嵌
  border: 1px solid var(--border-divider);
  border-radius: 12px;
  font-size: 14px;
}

.meta-label {
  color: var(--text-muted);
}

.meta-value {
  font-weight: 700;
  color: var(--text-main);
}

.text-primary {
  color: var(--color-primary);
}

.hero-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.premium-btn {
  border-radius: var(--radius-sm);
  font-weight: 600;
  height: 40px;
  padding: 0 18px;
  transition: all 0.2s ease;

  &.el-button--default {
    border: 1px solid var(--border-light);
    color: var(--text-regular);
    background: var(--bg-card);

    &:hover {
      background: var(--bg-subtle);
      border-color: #cbd5e1;
      color: var(--text-main);
    }
  }

  &.el-button--primary {
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.18);

    &:hover {
      transform: translateY(-1px);
      box-shadow: 0 6px 16px rgba(37, 99, 235, 0.24);
    }
  }
}

.schedule-btn {
  border-width: 2px;
}

/* metrics */
.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
}

.metric-card {
  padding: 22px 24px;
  border-width: 1px;
}

.metric-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}

.metric-label {
  font-size: 14px;
  color: var(--text-main);
  font-weight: 600;
}

.metric-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #cbd5e1;
  border: 2px solid var(--bg-card);
  box-shadow: 0 0 0 1px var(--border-light);
}

.metric-total .metric-dot {
  background: var(--text-muted);
}

.metric-free .metric-dot {
  background: var(--color-success);
}

.metric-warning .metric-dot {
  background: var(--color-warning);
}

.metric-alarm .metric-dot {
  background: var(--color-danger);
}

.metric-data {
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.metric-value {
  font-size: 36px;
  line-height: 1;
  font-weight: 800;
  letter-spacing: -1px;
}

.metric-sub {
  font-size: 13px;
  color: var(--text-muted);
}

.text-main {
  color: var(--text-main);
}

.text-danger {
  color: var(--color-danger);
}

.text-warning {
  color: var(--color-warning);
}

.text-success {
  color: var(--color-success);
}

/* filter header */
.filter-header-section {
  padding: 20px 24px;
  margin-bottom: 8px;
}

.filter-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  flex-wrap: wrap;
  gap: 16px;
}

.section-title {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  color: var(--text-main);
}

.section-subtitle {
  margin: 6px 0 0;
  font-size: 13px;
  color: var(--text-muted);
}

.filter-form .el-form-item {
  margin-bottom: 0;
  margin-right: 12px;
}

.premium-input :deep(.el-input__wrapper),
.premium-input :deep(.el-select__wrapper) {
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-light);
  box-shadow: none !important;

  &:hover, &.is-focus {
    border-color: var(--color-primary);
  }
}

/* grid */
.lab-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 28px; // 加大间距
}

.lab-card {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: all 0.3s ease;
  border-width: 1px; // 强化基础边框

  &:hover {
    box-shadow: var(--shadow-premium-hover);
    transform: translateY(-5px);
    border-color: var(--border-light); // 保持边框
  }
}

// 状态卡片强化
.lab-card.is-warning {
  border-color: var(--color-warning);
  border-width: 2px;
  box-shadow: 0 10px 30px rgba(245, 158, 11, 0.12);
}

.lab-card.is-alarm {
  border-color: var(--color-danger);
  border-width: 2px;
  box-shadow: 0 12px 32px rgba(239, 68, 68, 0.15);
}

.loading-card {
  padding: 24px;
}

/* cover */
.cover-wrap {
  position: relative;
  height: 180px;
  background: var(--bg-subtle);
  border-bottom: 1px solid var(--border-divider);
}

.cover-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.cover-fallback {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #f1f5f9 0%, #d1d5db 100%);
  color: #94a3b8;
  font-size: 22px;
  font-weight: 800;
  letter-spacing: 2px;
}

.status-badge,
.risk-badge {
  position: absolute;
  top: 16px;
  padding: 6px 14px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  color: #fff;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
  backdrop-filter: blur(4px);
}

.status-badge {
  right: 16px;
}

.risk-badge {
  left: 16px;
  background: rgba(15, 23, 42, 0.85); // 默认背景
}

.bg-success {
  background-color: rgba(16, 185, 129, 0.95);
}

.bg-warning {
  background-color: rgba(245, 158, 11, 0.95);
}

// 风险等级颜色，不透明，对比更强
.risk-badge.success {
  background: rgba(71, 85, 105, 0.98);
}

.risk-badge.warning {
  background: #f59e0b;
}

.risk-badge.danger {
  background: #ef4444;
}

.status-dot-white {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background-color: #fff;
}

/* content */
.lab-content {
  padding: 22px;
  display: flex;
  flex-direction: column;
  gap: 16px; // 加大内部元素间距
  flex: 1;
}

.lab-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.lab-header-main {
  min-width: 0;
  flex: 1;
}

.lab-title {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: var(--text-main);
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.lab-subline {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 8px;
}

.lab-id,
.meta-inline {
  font-size: 12px;
  color: var(--text-regular);
  font-weight: 500;
  padding: 4px 10px;
  background: var(--bg-page);
  border: 1px solid var(--border-divider);
  border-radius: 999px;
}

.more-btn {
  color: var(--text-muted);
  font-size: 18px;
  padding: 4px;
}

.description {
  margin: 0;
  font-size: 14px;
  color: var(--text-regular); // 颜色加深，更易读
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  min-height: 44px;
}

/* sensor */
.sensor-panel {
  margin-top: auto;
  padding: 18px;
  border-radius: var(--radius-md);
  background: var(--bg-subtle); // 使用较深的内部灰色背景
  border: 1px solid var(--border-divider);
}

.sensor-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}

.sensor-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-main);
}

.sensor-status {
  font-size: 12px;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 3px 8px;
  border-radius: 999px;
  background: #fff; // 状态默认背景纯白
  border: 1px solid var(--border-divider);
}

// 增强传感器面板内部的状态颜色区分
.sensor-status.success {
  color: var(--color-success);
  background: var(--color-success-light);
  border-color: rgba(16, 185, 129, 0.2);
}

.sensor-status.warning {
  color: var(--color-warning);
  background: var(--color-warning-light);
  border-color: rgba(245, 158, 11, 0.2);
}

.sensor-status.danger {
  color: var(--color-danger);
  background: var(--color-danger-light);
  border-color: rgba(239, 68, 68, 0.2);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: currentColor;
}

.sensor-core-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.core-metric {
  background: #fff;
  border: 1px solid var(--border-divider);
  border-radius: 12px;
  padding: 12px 14px;
  min-height: 78px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 8px;
  box-shadow: none; // 移除内嵌卡片的阴影
}

.core-label {
  font-size: 12px;
  color: var(--text-muted);
}

.core-value {
  font-size: 20px;
  line-height: 1;
  font-weight: 800;
  color: var(--text-main);
}

.warning-val.core-metric,
.warning-val {
  background: linear-gradient(180deg, rgba(245, 158, 11, 0.12), rgba(245, 158, 11, 0.05));
  border-color: rgba(245, 158, 11, 0.3);
}

.alarm-val.core-metric,
.alarm-val {
  background: linear-gradient(180deg, rgba(239, 68, 68, 0.12), rgba(239, 68, 68, 0.05));
  border-color: rgba(239, 68, 68, 0.3);
}

.warning-val .core-value,
.warning-val .sensor-val {
  color: #b45309; // 稍微加深一点预警时的数值颜色，使其在黄底上易读
}

.alarm-val .core-value,
.alarm-val .sensor-val {
  color: var(--color-danger);
}

.sensor-alert {
  margin-top: 14px;
  display: flex;
  gap: 8px;
  align-items: flex-start;
  font-size: 13px;
  color: #b91c1c;
  line-height: 1.6;
  padding: 10px 14px;
  border-radius: 10px;
  background: var(--color-danger-light);
  border: 1px solid rgba(239, 68, 68, 0.3);
}

.alert-icon {
  color: var(--color-danger);
  margin-top: 2px;
}

.sensor-more-wrap {
  margin-top: 12px;
  text-align: center;
}

.toggle-btn {
  font-size: 13px;
  font-weight: 600;
  background: #fff;
  padding: 5px 12px;
  border-radius: 999px;
  border: 1px solid var(--border-divider);
}

.secondary-grid {
  margin-top: 12px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  row-gap: 10px;
  column-gap: 14px;
}

.sensor-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  background: #fff;
  border: 1px solid var(--border-divider);
  border-radius: 10px;
  padding: 10px 14px;
}

.sensor-lbl {
  color: var(--text-muted);
}

.sensor-val {
  color: var(--text-main);
  font-weight: 600;
}

.sensor-empty {
  font-size: 13px;
  color: var(--text-muted);
  text-align: center;
  padding: 24px 0 14px;
  border: 1px dashed var(--border-divider);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.5);
}

/* footer actions */
.lab-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 22px;
  border-top: 1px solid var(--border-divider);
  background: #fdfdfd; // 底部轻微背景，使其看起来更稳定
}

.action-group-left,
.action-group-right {
  display: flex;
  align-items: center;
  gap: 14px;
}

.action-text-btn {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-regular);
  padding: 4px;
  height: auto;
}

.action-text-btn:hover {
  color: var(--text-main);
  background: var(--bg-page);
}

.action-text-btn.primary-text {
  color: var(--color-primary);
}

.action-text-btn.primary-text:hover {
  color: var(--color-primary-hover);
  background: var(--color-primary-light);
}

.action-text-btn.danger-text {
  color: var(--color-danger);
}

.action-text-btn.danger-text:hover {
  color: #b91c1c;
  background: var(--color-danger-light);
}

.divider {
  width: 1px;
  height: 14px;
  background: var(--border-divider);
}

/* dialog */
:deep(.premium-dialog) {
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.2);
  border: 1px solid var(--border-light);

  .el-dialog__header {
    padding: 24px 32px 18px;
    margin-right: 0;
    border-bottom: 1px solid var(--border-divider);
    background: var(--bg-card);

    .el-dialog__title {
      font-weight: 700;
      font-size: 18px;
      color: var(--text-main);
    }
  }

  .el-dialog__body {
    padding: 24px 32px 32px;
    background: #fdfdfd;
  }

  .el-dialog__footer {
    padding: 16px 32px 24px;
    border-top: 1px solid var(--border-divider);
    background: #fff;
  }
}

.custom-form :deep(.el-form-item__label) {
  font-weight: 600;
  color: var(--text-main);
  padding-bottom: 6px;
}

.dialog-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 24px;
}

.full-width-number {
  width: 100%;
}

.upload-box :deep(.el-input-group__append) {
  padding: 0;
  overflow: hidden;

  .el-upload {
    display: flex;
    height: 100%;
  }

  .el-button {
    border: none;
    border-radius: 0;
    height: 100%;
    margin: 0;
    font-weight: 600;
  }
}

.preview-wrap {
  margin-top: 16px;
  border-radius: var(--radius-md);
  overflow: hidden;
  height: 160px;
  background: var(--bg-subtle);
  border: 1px solid var(--border-divider);
}

.preview-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* responsive */
@media (max-width: 1200px) {
  .metric-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  // 小屏幕温度指标不拆分，保持 3 列，否则不好看
  // .sensor-core-grid {
  //   grid-template-columns: 1fr;
  // }
}

@media (max-width: 768px) {
  .labs-page {
    padding: 16px;
  }

  .hero-card {
    padding: 20px;
  }

  .hero-top,
  .filter-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .metric-grid,
  .lab-grid,
  .dialog-grid,
  .secondary-grid {
    grid-template-columns: 1fr;
  }

  // 手机端核心监测可以换成一列
  .sensor-core-grid {
    grid-template-columns: 1fr;
  }

  .filter-form {
    display: flex;
    flex-direction: column;
    width: 100%;
    gap: 12px;

    .el-form-item {
      margin-right: 0;
      width: 100%;

      .el-input, .el-select {
        width: 100%;
      }
    }
  }

  .lab-actions {
    flex-direction: column;
    align-items: stretch;
    gap: 14px;
    padding: 16px;

    .action-group-left,
    .action-group-right {
      justify-content: center;
      width: 100%;
    }
  }
}
</style>

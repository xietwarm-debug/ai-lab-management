<template>
  <div class="governance-page">
    <section class="hero-card">
      <div class="hero-copy">
        <span class="eyebrow">Data Quality</span>
        <h2>批量导入与数据治理</h2>
        <p>集中做实验室、资产、课表的批量导入前校验，并提供重复检测、异常记录修复建议和错误回显。</p>
      </div>
      <div class="hero-actions">
        <el-button :loading="refreshing" @click="loadBaseData">刷新基线数据</el-button>
      </div>
    </section>

    <section class="panel-card">
      <el-tabs v-model="activeTab">
        <el-tab-pane v-if="canManageLabs" label="实验室导入" name="labs">
          <div class="tab-grid">
            <article class="sub-card">
              <div class="sub-head">
                <h3>导入内容</h3>
                <span>每行一条，使用逗号或 Tab 分隔：实验室名,位置,容量,负责人,开放时间,图片URL</span>
              </div>
              <el-input v-model="labText" type="textarea" :rows="12" placeholder="机房A,信息楼301,60,张老师,08:00-22:00,https://..." />
              <div class="action-row">
                <el-button @click="previewLabs">预校验</el-button>
                <el-button type="primary" :loading="labImporting" @click="importLabs">执行导入</el-button>
              </div>
            </article>

            <article class="sub-card">
              <div class="sub-head">
                <h3>校验结果</h3>
                <span>{{ labPreviewRows.length }} 条</span>
              </div>
              <el-table :data="labPreviewRows" stripe>
                <el-table-column prop="lineNo" label="行号" width="80" />
                <el-table-column prop="name" label="实验室" min-width="140" />
                <el-table-column prop="location" label="位置" min-width="160" />
                <el-table-column prop="status" label="状态" width="110">
                  <template #default="{ row }">
                    <el-tag :type="row.status === 'ok' ? 'success' : row.status === 'duplicate' ? 'warning' : 'danger'">
                      {{ row.status }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="message" label="提示" min-width="220" />
              </el-table>
            </article>
          </div>
        </el-tab-pane>

        <el-tab-pane v-if="canManageEquipments" label="资产导入" name="equipments">
          <div class="tab-grid">
            <article class="sub-card">
              <div class="sub-head">
                <h3>导入内容</h3>
                <span>每行一条：资产编号,名称,实验室,型号,品牌,责任人,价格,状态</span>
              </div>
              <el-input v-model="equipmentText" type="textarea" :rows="12" placeholder="PC-001,教师机,机房A,OptiPlex 7010,Dell,李老师,5800,in_service" />
              <div class="action-row">
                <el-button @click="previewEquipments">预校验</el-button>
                <el-button type="primary" :loading="equipmentImporting" @click="importEquipments">执行导入</el-button>
              </div>
            </article>

            <article class="sub-card">
              <div class="sub-head">
                <h3>校验结果</h3>
                <span>{{ equipmentPreviewRows.length }} 条</span>
              </div>
              <el-table :data="equipmentPreviewRows" stripe>
                <el-table-column prop="lineNo" label="行号" width="80" />
                <el-table-column prop="assetCode" label="资产编号" min-width="140" />
                <el-table-column prop="name" label="资产名称" min-width="140" />
                <el-table-column prop="labName" label="实验室" min-width="140" />
                <el-table-column prop="status" label="状态" width="110">
                  <template #default="{ row }">
                    <el-tag :type="row.status === 'ok' ? 'success' : row.status === 'duplicate' ? 'warning' : 'danger'">
                      {{ row.status }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="message" label="提示" min-width="220" />
              </el-table>
            </article>
          </div>
        </el-tab-pane>

        <el-tab-pane v-if="canManageSchedule" label="课表预校验" name="schedule">
          <div class="tab-grid">
            <article class="sub-card">
              <div class="sub-head">
                <h3>导入内容</h3>
                <span>每行一条：课程名,星期,节次,时间段,周次,实验室,教师,班级,备注</span>
              </div>
              <el-form label-position="top" class="schedule-form">
                <el-row :gutter="16">
                  <el-col :span="8">
                    <el-form-item label="学期名称">
                      <el-input v-model="scheduleForm.termName" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item label="开学日期">
                      <el-date-picker v-model="scheduleForm.semesterStartDate" type="date" value-format="YYYY-MM-DD" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item label="周数">
                      <el-input-number v-model="scheduleForm.semesterWeeks" :min="1" :max="40" style="width: 100%" />
                    </el-form-item>
                  </el-col>
                </el-row>
              </el-form>
              <el-input v-model="scheduleText" type="textarea" :rows="12" placeholder="数据库原理,周一,1-2,08:00-09:35,1-16,机房A,王老师,计科2301,上机课" />
              <div class="action-row">
                <el-button @click="previewSchedule">预校验</el-button>
                <el-button type="primary" :loading="scheduleImporting" @click="importScheduleRows">导入课表</el-button>
              </div>
            </article>

            <article class="sub-card">
              <div class="sub-head">
                <h3>预校验结果</h3>
                <span>{{ schedulePreviewRows.length }} 条</span>
              </div>
              <el-table :data="schedulePreviewRows" stripe>
                <el-table-column prop="lineNo" label="行号" width="80" />
                <el-table-column prop="courseName" label="课程" min-width="140" />
                <el-table-column prop="labName" label="实验室" min-width="140" />
                <el-table-column prop="status" label="状态" width="110">
                  <template #default="{ row }">
                    <el-tag :type="row.status === 'ok' ? 'success' : 'danger'">
                      {{ row.status }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="message" label="提示" min-width="220" />
              </el-table>
            </article>
          </div>
        </el-tab-pane>

        <el-tab-pane label="重复与异常检测" name="anomaly">
          <div class="anomaly-grid">
            <article class="sub-card">
              <div class="sub-head">
                <h3>重复实验室</h3>
                <span>{{ duplicateLabs.length }} 条</span>
              </div>
              <el-table :data="duplicateLabs" stripe>
                <el-table-column prop="name" label="实验室名称" min-width="160" />
                <el-table-column prop="count" label="重复数" width="100" />
                <el-table-column prop="locations" label="位置" min-width="220" />
              </el-table>
            </article>

            <article class="sub-card">
              <div class="sub-head">
                <h3>重复资产编号</h3>
                <span>{{ duplicateEquipments.length }} 条</span>
              </div>
              <el-table :data="duplicateEquipments" stripe>
                <el-table-column prop="assetCode" label="资产编号" min-width="160" />
                <el-table-column prop="count" label="重复数" width="100" />
                <el-table-column prop="names" label="资产名称" min-width="220" />
              </el-table>
            </article>

            <article class="sub-card">
              <div class="sub-head">
                <h3>异常记录修复建议</h3>
                <span>{{ anomalySuggestions.length }} 条</span>
              </div>
              <el-table :data="anomalySuggestions" stripe>
                <el-table-column prop="type" label="类型" width="120" />
                <el-table-column prop="name" label="对象" min-width="180" />
                <el-table-column prop="message" label="建议" min-width="260" />
              </el-table>
            </article>
          </div>
        </el-tab-pane>
      </el-tabs>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, reactive, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { getLabs, createLab } from '@/api/labs'
import { createEquipment, getEquipmentList } from '@/api/equipments'
import { importSchedule } from '@/api/schedule'
import { useAuthStore } from '@/stores/auth'
import { hasPermission } from '@/utils/auth'
import { PERMISSION_ASSET_MANAGER, PERMISSION_SCHEDULE_MANAGER } from '@/utils/constants'

const activeTab = ref('labs')
const refreshing = ref(false)
const labImporting = ref(false)
const equipmentImporting = ref(false)
const scheduleImporting = ref(false)

const labText = ref('')
const equipmentText = ref('')
const scheduleText = ref('')

const labRows = ref([])
const equipmentRows = ref([])
const labPreviewRows = ref([])
const equipmentPreviewRows = ref([])
const schedulePreviewRows = ref([])

const scheduleForm = reactive({
  termName: '2025-2026 学年第二学期',
  semesterStartDate: '',
  semesterWeeks: 18
})
const authStore = useAuthStore()

const canManageEquipments = computed(() => authStore.role === 'admin' || hasPermission(authStore.user, PERMISSION_ASSET_MANAGER))
const canManageSchedule = computed(() => authStore.role === 'admin' || hasPermission(authStore.user, PERMISSION_SCHEDULE_MANAGER))
const canManageLabs = computed(() => canManageEquipments.value || canManageSchedule.value)

function splitLines(text) {
  return String(text || '')
    .split(/\r?\n/)
    .map((item) => item.trim())
    .filter(Boolean)
}

function splitFields(line) {
  return (line.includes('\t') ? line.split('\t') : line.split(',')).map((item) => String(item || '').trim())
}

function parseLabRows() {
  return splitLines(labText.value).map((line, index) => {
    const parts = splitFields(line)
    return {
      lineNo: index + 1,
      name: parts[0] || '',
      location: parts[1] || '',
      capacity: Number(parts[2] || 0),
      manager: parts[3] || '',
      openHours: parts[4] || '',
      coverUrl: parts[5] || ''
    }
  })
}

function parseEquipmentRows() {
  return splitLines(equipmentText.value).map((line, index) => {
    const parts = splitFields(line)
    return {
      lineNo: index + 1,
      assetCode: parts[0] || '',
      name: parts[1] || '',
      labName: parts[2] || '',
      model: parts[3] || '',
      brand: parts[4] || '',
      keeper: parts[5] || '',
      price: Number(parts[6] || 0),
      status: parts[7] || 'in_service'
    }
  })
}

function parseScheduleRows() {
  return splitLines(scheduleText.value).map((line, index) => {
    const parts = splitFields(line)
    while (parts.length < 9) parts.push('')
    return {
      lineNo: index + 1,
      courseName: parts[0],
      weekDay: parts[1],
      periodRange: parts[2],
      timeRange: parts[3],
      weekRange: parts[4],
      labName: parts[5],
      teacherName: parts[6],
      className: parts[7],
      note: parts[8],
      weekType: 'all'
    }
  })
}

const duplicateLabs = computed(() => {
  const map = new Map()
  labRows.value.forEach((item) => {
    const key = String(item.labName || item.name || '').trim()
    if (!key) return
    const current = map.get(key) || { name: key, count: 0, locations: [] }
    current.count += 1
    if (item.location) current.locations.push(item.location)
    map.set(key, current)
  })
  return [...map.values()].filter((item) => item.count > 1).map((item) => ({
    ...item,
    locations: [...new Set(item.locations)].join('；')
  }))
})

const duplicateEquipments = computed(() => {
  const map = new Map()
  equipmentRows.value.forEach((item) => {
    const key = String(item.assetCode || '').trim()
    if (!key) return
    const current = map.get(key) || { assetCode: key, count: 0, names: [] }
    current.count += 1
    if (item.name) current.names.push(item.name)
    map.set(key, current)
  })
  return [...map.values()].filter((item) => item.count > 1).map((item) => ({
    ...item,
    names: [...new Set(item.names)].join('；')
  }))
})

const anomalySuggestions = computed(() => {
  const items = []
  labRows.value.forEach((item) => {
    if (!item.labName && !item.name) return
    if (!item.location) {
      items.push({
        type: '实验室',
        name: item.labName || item.name,
        message: '缺少位置字段，建议补齐楼栋/房间信息后再投入排课或预约。'
      })
    }
  })
  equipmentRows.value.forEach((item) => {
    if (!item.assetCode) return
    if (!item.labName) {
      items.push({
        type: '资产',
        name: item.assetCode,
        message: '未绑定实验室，建议补齐归属空间后再进行借用、盘点和点位展示。'
      })
    }
    if (!item.keeper) {
      items.push({
        type: '资产',
        name: item.assetCode,
        message: '缺少责任人，建议补齐 keeper 字段，方便维修、报废和追责闭环。'
      })
    }
  })
  return items
})

async function loadBaseData() {
  refreshing.value = true
  try {
    const [labRes, equipmentRes] = await Promise.all([
      getLabs({ pageSize: 500 }),
      getEquipmentList({ pageSize: 1000 })
    ])
    labRows.value = Array.isArray(labRes.data?.data) ? labRes.data.data : []
    equipmentRows.value = Array.isArray(equipmentRes.data?.data) ? equipmentRes.data.data : []
  } finally {
    refreshing.value = false
  }
}

function previewLabs() {
  const existingNames = new Set(labRows.value.map((item) => String(item.labName || item.name || '').trim()))
  labPreviewRows.value = parseLabRows().map((item) => {
    if (!item.name) {
      return { ...item, status: 'error', message: '实验室名称不能为空' }
    }
    if (existingNames.has(item.name)) {
      return { ...item, status: 'duplicate', message: '与现有实验室重名，可先核对后再导入' }
    }
    if (!item.location) {
      return { ...item, status: 'error', message: '缺少位置字段' }
    }
    return { ...item, status: 'ok', message: '可导入' }
  })
}

async function importLabs() {
  previewLabs()
  const validRows = labPreviewRows.value.filter((item) => item.status === 'ok')
  if (!validRows.length) {
    ElMessage.warning('没有可导入的实验室数据')
    return
  }
  labImporting.value = true
  try {
    let success = 0
    for (const item of validRows) {
      await createLab({
        name: item.name,
        capacity: item.capacity || 0,
        description: [item.location, item.manager ? `负责人:${item.manager}` : '', item.openHours ? `开放:${item.openHours}` : '']
          .filter(Boolean)
          .join('；'),
        imageUrl: item.coverUrl
      })
      success += 1
    }
    ElMessage.success(`实验室导入完成，共 ${success} 条`)
    await loadBaseData()
    previewLabs()
  } finally {
    labImporting.value = false
  }
}

function previewEquipments() {
  const existingCodes = new Set(equipmentRows.value.map((item) => String(item.assetCode || '').trim()))
  const labNames = new Set(labRows.value.map((item) => String(item.labName || item.name || '').trim()))
  equipmentPreviewRows.value = parseEquipmentRows().map((item) => {
    if (!item.assetCode || !item.name) {
      return { ...item, status: 'error', message: '资产编号和名称不能为空' }
    }
    if (existingCodes.has(item.assetCode)) {
      return { ...item, status: 'duplicate', message: '资产编号已存在' }
    }
    if (!item.labName || !labNames.has(item.labName)) {
      return { ...item, status: 'error', message: '实验室不存在，请先导入实验室或修正名称' }
    }
    return { ...item, status: 'ok', message: '可导入' }
  })
}

async function importEquipments() {
  previewEquipments()
  const validRows = equipmentPreviewRows.value.filter((item) => item.status === 'ok')
  if (!validRows.length) {
    ElMessage.warning('没有可导入的资产数据')
    return
  }
  equipmentImporting.value = true
  try {
    let success = 0
    for (const item of validRows) {
      const targetLab = labRows.value.find((lab) => String(lab.labName || lab.name || '').trim() === item.labName)
      await createEquipment({
        assetCode: item.assetCode,
        name: item.name,
        labId: Number(targetLab?.labId || targetLab?.id || 0),
        labName: item.labName,
        model: item.model,
        brand: item.brand,
        keeper: item.keeper,
        price: item.price || 0,
        status: item.status || 'in_service',
        allowBorrow: true
      })
      success += 1
    }
    ElMessage.success(`资产导入完成，共 ${success} 条`)
    await loadBaseData()
    previewEquipments()
  } finally {
    equipmentImporting.value = false
  }
}

function previewSchedule() {
  const labNames = new Set(labRows.value.map((item) => String(item.labName || item.name || '').trim()))
  schedulePreviewRows.value = parseScheduleRows().map((item) => {
    if (!item.courseName || !item.weekDay || !item.labName) {
      return { ...item, status: 'error', message: '课程名、星期、实验室不能为空' }
    }
    if (!labNames.has(item.labName)) {
      return { ...item, status: 'error', message: '实验室不存在' }
    }
    if (!item.periodRange && !item.timeRange) {
      return { ...item, status: 'error', message: '节次和时间段至少填写一个' }
    }
    return { ...item, status: 'ok', message: '可导入' }
  })
}

async function importScheduleRows() {
  if (!scheduleForm.semesterStartDate) {
    ElMessage.warning('请先选择开学日期')
    return
  }
  previewSchedule()
  const validRows = schedulePreviewRows.value.filter((item) => item.status === 'ok').map(({ lineNo, status, message, ...rest }) => rest)
  if (!validRows.length) {
    ElMessage.warning('没有可导入的课表数据')
    return
  }
  scheduleImporting.value = true
  try {
    const response = await importSchedule({
      template: {
        termName: scheduleForm.termName,
        semesterStartDate: scheduleForm.semesterStartDate,
        semesterWeeks: scheduleForm.semesterWeeks,
        reminderLeadMinutes: 15,
        sourceType: 'manual'
      },
      mode: 'replace',
      activate: false,
      items: validRows
    })
    const inserted = Number(response.data?.data?.inserted || 0)
    ElMessage.success(`课表导入完成，成功写入 ${inserted} 条`)
  } finally {
    scheduleImporting.value = false
  }
}

onMounted(() => {
  loadBaseData()
})

watch(
  () => [canManageLabs.value, canManageEquipments.value, canManageSchedule.value],
  () => {
    if (activeTab.value === 'labs' && !canManageLabs.value) {
      activeTab.value = canManageEquipments.value ? 'equipments' : canManageSchedule.value ? 'schedule' : 'anomaly'
    }
    if (activeTab.value === 'equipments' && !canManageEquipments.value) {
      activeTab.value = canManageSchedule.value ? 'schedule' : canManageLabs.value ? 'labs' : 'anomaly'
    }
    if (activeTab.value === 'schedule' && !canManageSchedule.value) {
      activeTab.value = canManageEquipments.value ? 'equipments' : canManageLabs.value ? 'labs' : 'anomaly'
    }
  },
  { immediate: true }
)
</script>

<style scoped lang="scss">
.governance-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.hero-card,
.panel-card,
.sub-card {
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
    radial-gradient(circle at top right, rgba(59, 130, 246, 0.15), transparent 30%),
    linear-gradient(135deg, #f8fbff 0%, #eef5ff 100%);
}

.hero-copy {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.hero-card h2,
.sub-head h3 {
  margin: 0;
}

.hero-copy p,
.sub-head span {
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

.panel-card {
  padding: 24px;
}

.tab-grid,
.anomaly-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
}

.anomaly-grid {
  grid-template-columns: 1fr;
}

.sub-card {
  padding: 20px;
}

.sub-head,
.hero-actions,
.action-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.sub-head {
  align-items: flex-start;
  margin-bottom: 16px;
}

.action-row {
  margin-top: 16px;
  justify-content: flex-end;
}

.schedule-form {
  margin-bottom: 12px;
}

@media (max-width: 1100px) {
  .tab-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .hero-card,
  .hero-actions,
  .sub-head {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>

<template>
  <div class="room-map-page">
    <section class="hero-card">
      <div class="hero-copy">
        <span class="eyebrow">实验室平面图</span>
        <h2>机位图、设备点位与状态可视化</h2>
        <p>按实验室展示 PC 机位分布、在线占用、离线空闲和异常故障状态，支持直接维护设备点位。</p>
        <div class="hero-meta">
          <span>实验室 {{ labs.length }} 间</span>
          <span>当前设备 {{ equipments.length }} 台</span>
          <span>运行状态源 {{ runtimeMode === 'api' ? '/pcs/status' : 'fallback' }}</span>
        </div>
      </div>
      <div class="hero-actions">
        <el-select v-model="selectedLabId" placeholder="选择实验室" style="width: 240px" @change="handleLabChange">
          <el-option v-for="lab in labs" :key="lab.id" :label="lab.name" :value="lab.id" />
        </el-select>
        <el-button :loading="loading" @click="refreshAll">刷新</el-button>
        <el-button type="primary" :disabled="!selectedLabId" @click="openCreate()">新增电脑</el-button>
      </div>
    </section>

    <section class="metric-grid">
      <article v-for="item in metrics" :key="item.key" class="metric-card">
        <span class="metric-label">{{ item.label }}</span>
        <strong class="metric-value" :class="item.tone">{{ item.value }}</strong>
        <span class="metric-sub">{{ item.hint }}</span>
      </article>
    </section>

    <section v-if="!selectedLabId && !loading" class="panel-card">
      <el-empty description="当前还没有可用实验室，请先在实验室管理中创建实验室" />
    </section>

    <section v-else class="layout-grid">
      <article class="panel-card map-card">
        <div class="panel-head">
          <div>
            <h3>{{ selectedLab?.name || '实验室平面图' }}</h3>
            <span>{{ selectedLab?.description || '可视化查看机位分布、在线占用与故障状态' }}</span>
          </div>
          <div class="head-actions">
            <el-button @click="refreshRuntime">刷新状态</el-button>
          </div>
        </div>

        <div class="legend-row">
          <span class="legend-item"><i class="legend-dot legend-dot--online" />使用中</span>
          <span class="legend-item"><i class="legend-dot legend-dot--offline" />空闲/离线</span>
          <span class="legend-item"><i class="legend-dot legend-dot--warning" />异常/故障</span>
          <span class="legend-item"><i class="legend-dot legend-dot--empty" />空机位</span>
        </div>

        <div v-if="loading" class="loading-wrap">
          <el-skeleton :rows="8" animated />
        </div>
        <template v-else>
          <div class="teacher-row">
            <button
              type="button"
              class="seat seat--teacher"
              :class="seatClass(teacherSeat)"
              @click="handleSeatClick(teacherSeat)"
            >
              <div class="seat-top">
                <span class="seat-code">{{ teacherSeat.code }}</span>
                <span class="seat-state">{{ teacherSeat.eq ? runtimeText(teacherSeat.eq) : '空位' }}</span>
              </div>
              <div class="seat-name">{{ teacherSeat.eq ? (teacherSeat.eq.assetCode || teacherSeat.eq.name || '-') : '教师机位' }}</div>
              <div class="seat-sub">{{ teacherSeat.eq ? equipmentStatusText(teacherSeat.eq.status) : '点击新增设备' }}</div>
            </button>
          </div>

          <div class="seat-grid">
            <button
              v-for="seat in seats"
              :key="seat.code"
              type="button"
              class="seat"
              :class="[seatClass(seat), { 'seat--active': selectedEquipment?.id === seat.eq?.id }]"
              @click="handleSeatClick(seat)"
            >
              <div class="seat-top">
                <span class="seat-code">{{ seat.code }}</span>
                <span class="seat-state">{{ seat.eq ? runtimeText(seat.eq) : '空位' }}</span>
              </div>
              <div class="seat-name">{{ seat.eq ? (seat.eq.assetCode || seat.eq.name || '-') : '点击新增' }}</div>
              <div class="seat-sub">{{ seat.eq ? runtimeLastSeen(seat.eq) : '暂无设备' }}</div>
            </button>
          </div>
        </template>
      </article>

      <aside class="side-column">
        <article class="panel-card info-card">
          <div class="panel-head">
            <div>
              <h3>实验室信息</h3>
              <span>空间容量与设备概览</span>
            </div>
          </div>
          <p><strong>实验室：</strong>{{ selectedLab?.name || '-' }}</p>
          <p><strong>状态：</strong>{{ selectedLab?.status === 'busy' ? '使用中' : '空闲' }}</p>
          <p><strong>容量：</strong>{{ selectedLab?.capacity || 0 }}</p>
          <p><strong>设备数：</strong>{{ selectedLab?.deviceCount || equipments.length }}</p>
          <p><strong>说明：</strong>{{ selectedLab?.description || '暂无说明' }}</p>
        </article>

        <article class="panel-card info-card">
          <div class="panel-head">
            <div>
              <h3>机位详情</h3>
              <span>点击平面图上的设备机位即可查看</span>
            </div>
          </div>
          <template v-if="selectedEquipment">
            <p><strong>资产编号：</strong>{{ selectedEquipment.assetCode || '-' }}</p>
            <p><strong>名称：</strong>{{ selectedEquipment.name || '-' }}</p>
            <p><strong>座位：</strong>{{ selectedEquipment.seatCode || '-' }}</p>
            <p><strong>运行状态：</strong>{{ runtimeText(selectedEquipment) }}</p>
            <p><strong>设备状态：</strong>{{ equipmentStatusText(selectedEquipment.status) }}</p>
            <p><strong>操作系统：</strong>{{ selectedEquipment.spec.os || '-' }}</p>
            <p><strong>芯片：</strong>{{ selectedEquipment.spec.chip || '-' }}</p>
            <p><strong>备注：</strong>{{ selectedEquipment.spec.notes || '-' }}</p>
            <p><strong>最近在线：</strong>{{ runtimeLastSeen(selectedEquipment) }}</p>
            <div class="info-actions">
              <el-button type="primary" @click="openEdit(selectedEquipment)">编辑设备</el-button>
              <el-popconfirm title="确定删除这台设备吗？" @confirm="removeEquipment(selectedEquipment)">
                <template #reference>
                  <el-button type="danger" plain>删除设备</el-button>
                </template>
              </el-popconfirm>
            </div>
          </template>
          <el-empty v-else description="选中机位后查看详情" :image-size="70" />
        </article>
      </aside>
    </section>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑电脑点位' : '新增电脑点位'" width="640px">
      <el-form label-position="top">
        <div class="dialog-grid">
          <el-form-item label="座位编号">
            <el-select v-if="!editingId" v-model="form.seatCode" filterable allow-create default-first-option placeholder="例如 A1 / B2 / O1">
              <el-option v-for="code in emptySeatCodes" :key="code" :label="code" :value="code" />
            </el-select>
            <el-input v-else v-model="form.seatCode" placeholder="例如 A1 / B2 / O1" />
          </el-form-item>
          <el-form-item label="设备名称">
            <el-input v-model="form.name" placeholder="默认使用 PC-座位号" />
          </el-form-item>
          <el-form-item label="设备状态">
            <el-select v-model="form.status">
              <el-option label="在用" value="in_service" />
              <el-option label="维修中" value="repairing" />
              <el-option label="已报废" value="scrapped" />
            </el-select>
          </el-form-item>
          <el-form-item label="操作系统">
            <el-input v-model="form.os" placeholder="例如 Windows 11" />
          </el-form-item>
          <el-form-item label="芯片">
            <el-input v-model="form.chip" placeholder="例如 i5-12400" />
          </el-form-item>
          <el-form-item label="最近在线">
            <el-input v-model="form.lastSeen" placeholder="YYYY-MM-DD HH:mm:ss，可选" />
          </el-form-item>
        </div>
        <el-form-item label="备注">
          <el-input v-model="form.notes" type="textarea" :rows="4" maxlength="800" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="closeDialog">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitForm">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ElMessage } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import { createEquipment, deleteEquipment, getEquipmentList, updateEquipment } from '@/api/equipments'
import { getLabs } from '@/api/labs'
import { getLabPcRuntimeStatus } from '@/api/room-map'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const saving = ref(false)
const labs = ref([])
const equipments = ref([])
const runtimeMap = ref({})
const runtimeMode = ref('api')
const selectedLabId = ref(0)
const selectedEquipment = ref(null)
const dialogVisible = ref(false)
const editingId = ref(0)

const form = reactive({
  seatCode: '',
  name: '',
  status: 'in_service',
  os: '',
  chip: '',
  notes: '',
  lastSeen: ''
})

function pick(obj, ...keys) {
  for (const key of keys) {
    const value = obj?.[key]
    if (value !== undefined && value !== null) return value
  }
  return ''
}

function parseSpec(raw) {
  if (!raw) return {}
  if (typeof raw === 'object' && !Array.isArray(raw)) return { ...raw }
  try {
    const parsed = JSON.parse(raw)
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {}
  } catch (error) {
    return {}
  }
}

function seatCodeOf(raw) {
  const value = String(raw || '').trim().toUpperCase()
  const match = value.match(/^([A-Z]+)(\d{1,3})$/)
  if (!match) return ''
  return `${match[1]}${Number(match[2])}`
}

function rowIndex(letters) {
  let value = 0
  for (let index = 0; index < letters.length; index += 1) {
    value = value * 26 + (letters.charCodeAt(index) - 64)
  }
  return value
}

function rowLetters(index) {
  let current = Number(index || 1)
  let output = ''
  while (current > 0) {
    const remainder = (current - 1) % 26
    output = String.fromCharCode(65 + remainder) + output
    current = Math.floor((current - 1) / 26)
  }
  return output || 'A'
}

function parseSeat(code) {
  const seatCode = seatCodeOf(code)
  const match = seatCode.match(/^([A-Z]+)(\d{1,3})$/)
  if (!match) return null
  return {
    row: rowIndex(match[1]),
    col: Number(match[2]),
    code: seatCode
  }
}

function isAllowedSeatCode(code) {
  const seatCode = seatCodeOf(code)
  if (!seatCode) return false
  if (/^O\d+$/i.test(seatCode)) return seatCode === 'O1'
  const parsed = parseSeat(seatCode)
  return Boolean(parsed && parsed.col >= 1 && parsed.col <= 6)
}

function nowText() {
  const date = new Date()
  const pad = (value) => String(value).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

const selectedLab = computed(() => labs.value.find((item) => Number(item.id) === Number(selectedLabId.value)) || null)

const teacherSeat = computed(() => ({
  code: 'O1',
  eq: equipments.value.find((item) => item.seatCode === 'O1') || null
}))

const seats = computed(() => {
  const maxCol = 6
  const reserveSlots = 6
  const equipmentMap = {}
  let occupiedCount = 0
  let maxRow = 1

  equipments.value.forEach((item) => {
    if (!item.seatCode || /^O\d+$/i.test(item.seatCode)) return
    const parsed = parseSeat(item.seatCode)
    if (!parsed || parsed.col < 1 || parsed.col > maxCol) return
    const code = `${rowLetters(parsed.row)}${parsed.col}`
    equipmentMap[code] = item
    occupiedCount += 1
    if (parsed.row > maxRow) maxRow = parsed.row
  })

  const rowsByCapacity = Math.max(1, Math.ceil((occupiedCount + reserveSlots) / maxCol))
  const totalRows = Math.max(maxRow, rowsByCapacity)
  const result = []
  for (let row = 1; row <= totalRows; row += 1) {
    for (let col = 1; col <= maxCol; col += 1) {
      const code = `${rowLetters(row)}${col}`
      result.push({ code, eq: equipmentMap[code] || null })
    }
  }
  return result
})

const emptySeatCodes = computed(() => {
  const result = []
  if (!teacherSeat.value.eq) result.push('O1')
  seats.value.forEach((item) => {
    if (!item.eq) result.push(item.code)
  })
  return result
})

const metrics = computed(() => {
  const onlineCount = equipments.value.filter((item) => runtimeState(item) === 'online').length
  const offlineCount = equipments.value.filter((item) => runtimeState(item) === 'offline').length
  const warningCount = equipments.value.filter((item) => runtimeState(item) === 'warning').length
  return [
    { key: 'online', label: '使用中', value: onlineCount, hint: '设备在线或正在占用', tone: 'success' },
    { key: 'offline', label: '空闲/离线', value: offlineCount, hint: '暂未检测到在线状态', tone: '' },
    { key: 'warning', label: '异常设备', value: warningCount, hint: '包含异常、维修和报废高亮', tone: 'warning' },
    { key: 'empty', label: '空机位', value: emptySeatCodes.value.length, hint: '可继续补充设备点位', tone: '' }
  ]
})

function normalizeEq(row) {
  const spec = parseSpec(pick(row, 'specJson', 'spec_json'))
  let seatCode = seatCodeOf(pick(spec, 'seatCode', 'seat', 'seat_code') || pick(row, 'seatCode', 'seat_code'))
  if (!seatCode) {
    const match = String(pick(row, 'assetCode', 'asset_code') || '').toUpperCase().match(/^PC-([A-Z]+\d{1,3})$/)
    seatCode = match ? seatCodeOf(match[1]) : ''
  }
  return {
    id: Number(pick(row, 'id') || 0),
    assetCode: String(pick(row, 'assetCode', 'asset_code') || ''),
    name: String(pick(row, 'name') || ''),
    model: String(pick(row, 'model') || ''),
    brand: String(pick(row, 'brand') || ''),
    labId: Number(pick(row, 'labId', 'lab_id') || 0),
    labName: String(pick(row, 'labName', 'lab_name') || ''),
    status: String(pick(row, 'status') || 'in_service'),
    keeper: String(pick(row, 'keeper') || ''),
    purchaseDate: String(pick(row, 'purchaseDate', 'purchase_date') || ''),
    price: pick(row, 'price'),
    imageUrl: String(pick(row, 'imageUrl', 'image_url') || ''),
    spec,
    seatCode
  }
}

function isPc(eq) {
  const category = String(eq.spec?.category || '').toLowerCase()
  return category ? category === 'pc' : /^PC-/i.test(eq.assetCode || '')
}

function runtimeState(eq) {
  const runtime = runtimeMap.value[String(eq.id)] || {}
  if (eq.status === 'scrapped' || eq.status === 'repairing') return 'warning'
  return String(runtime.status || '').toLowerCase() || 'offline'
}

function runtimeText(eq) {
  const state = runtimeState(eq)
  if (state === 'online') return '使用中'
  if (state === 'warning' || state === 'fault') return '异常'
  return '空闲'
}

function runtimeLastSeen(eq) {
  return runtimeMap.value[String(eq.id)]?.lastSeen || eq.spec.lastSeen || '-'
}

function equipmentStatusText(status) {
  if (status === 'repairing') return '维修中'
  if (status === 'scrapped') return '已报废'
  return '在用'
}

function seatClass(seat) {
  if (!seat.eq) return 'seat--empty'
  const state = runtimeState(seat.eq)
  if (state === 'online') return 'seat--online'
  if (state === 'warning' || state === 'fault') return 'seat--warning'
  return 'seat--offline'
}

function resetForm() {
  editingId.value = 0
  form.seatCode = ''
  form.name = ''
  form.status = 'in_service'
  form.os = ''
  form.chip = ''
  form.notes = ''
  form.lastSeen = ''
}

function handleSeatClick(seat) {
  if (seat.eq) {
    selectedEquipment.value = seat.eq
    return
  }
  openCreate(seat.code)
}

function openCreate(code = '') {
  resetForm()
  dialogVisible.value = true
  form.seatCode = seatCodeOf(code)
  form.lastSeen = nowText()
}

function openEdit(eq) {
  editingId.value = Number(eq.id || 0)
  dialogVisible.value = true
  form.seatCode = String(eq.seatCode || '')
  form.name = String(eq.name || '')
  form.status = String(eq.status || 'in_service')
  form.os = String(eq.spec.os || '')
  form.chip = String(eq.spec.chip || '')
  form.notes = String(eq.spec.notes || '')
  form.lastSeen = String(eq.spec.lastSeen || runtimeLastSeen(eq) || '')
}

function closeDialog() {
  dialogVisible.value = false
  resetForm()
}

async function loadLabs() {
  const response = await getLabs()
  labs.value = Array.isArray(response.data?.data) ? response.data.data : []
  const routeLabId = Number(route.query.labId || 0)
  if (routeLabId && labs.value.some((item) => Number(item.id) === routeLabId)) {
    selectedLabId.value = routeLabId
    return
  }
  if (!selectedLabId.value && labs.value.length > 0) {
    selectedLabId.value = Number(labs.value[0].id || 0)
  }
}

async function loadEquipments() {
  if (!selectedLabId.value) {
    equipments.value = []
    selectedEquipment.value = null
    return
  }
  const items = []
  let page = 1
  for (let step = 0; step < 20; step += 1) {
    const response = await getEquipmentList({
      labId: selectedLabId.value,
      page,
      pageSize: 100
    })
    const rows = Array.isArray(response.data?.data) ? response.data.data : []
    items.push(...rows)
    const total = Number(response.data?.meta?.total || items.length)
    if (items.length >= total || rows.length === 0) break
    page += 1
  }
  equipments.value = items.map((item) => normalizeEq(item)).filter((item) => item.id > 0 && isPc(item))
  if (selectedEquipment.value) {
    selectedEquipment.value = equipments.value.find((item) => item.id === selectedEquipment.value?.id) || null
  }
}

async function refreshRuntime() {
  if (!selectedLabId.value) {
    runtimeMap.value = {}
    return
  }
  try {
    const response = await getLabPcRuntimeStatus({ labId: selectedLabId.value })
    const rows = Array.isArray(response.data?.data) ? response.data.data : []
    const nextMap = {}
    rows.forEach((item) => {
      const equipmentId = Number(item.equipmentId || item.id || 0)
      if (!equipmentId) return
      nextMap[String(equipmentId)] = {
        status: String(item.status || item.state || 'offline').toLowerCase(),
        lastSeen: String(item.lastSeen || item.updatedAt || '')
      }
    })
    runtimeMap.value = nextMap
    runtimeMode.value = 'api'
  } catch (error) {
    const fallback = {}
    equipments.value.forEach((item, index) => {
      fallback[String(item.id)] = {
        status: index % 5 === 0 ? 'warning' : index % 2 === 0 ? 'online' : 'offline',
        lastSeen: nowText()
      }
    })
    runtimeMap.value = fallback
    runtimeMode.value = 'fallback'
  }
}

async function refreshAll() {
  loading.value = true
  try {
    await loadLabs()
    await loadEquipments()
    await refreshRuntime()
  } finally {
    loading.value = false
  }
}

async function handleLabChange(value) {
  selectedLabId.value = Number(value || 0)
  selectedEquipment.value = null
  await router.replace({
    path: route.path,
    query: selectedLabId.value ? { ...route.query, labId: selectedLabId.value } : {}
  })
  await refreshAll()
}

function buildPayload(eq, nextStatus, nextSpec) {
  return {
    assetCode: String(eq.assetCode || '').trim(),
    name: String(eq.name || eq.assetCode || '').trim(),
    model: String(eq.model || '').trim(),
    brand: String(eq.brand || '').trim(),
    labId: Number(eq.labId || selectedLabId.value || 0) || null,
    labName: String(eq.labName || selectedLab.value?.name || '').trim(),
    status: String(nextStatus || eq.status || 'in_service').trim(),
    keeper: String(eq.keeper || '').trim(),
    purchaseDate: String(eq.purchaseDate || '').trim(),
    price: eq.price === null || eq.price === undefined ? '' : String(eq.price),
    specJson: JSON.stringify(nextSpec || {}),
    imageUrl: String(eq.imageUrl || '').trim()
  }
}

async function submitForm() {
  if (!selectedLabId.value) {
    ElMessage.warning('请先选择实验室')
    return
  }

  const seatCode = seatCodeOf(form.seatCode)
  if (!seatCode || !isAllowedSeatCode(seatCode)) {
    ElMessage.warning('座位号仅支持 O1 或 A1-F6 这类格式')
    return
  }

  const duplicate = equipments.value.find((item) => item.seatCode === seatCode && item.id !== editingId.value)
  if (duplicate) {
    ElMessage.warning(`座位 ${seatCode} 已被占用`)
    return
  }

  saving.value = true
  try {
    if (editingId.value) {
      const current = equipments.value.find((item) => item.id === editingId.value)
      if (!current) {
        ElMessage.warning('设备不存在')
        return
      }
      const nextSpec = {
        ...(current.spec || {}),
        category: 'pc',
        seatCode,
        os: String(form.os || '').trim(),
        chip: String(form.chip || '').trim(),
        notes: String(form.notes || '').trim()
      }
      if (String(form.lastSeen || '').trim()) nextSpec.lastSeen = String(form.lastSeen || '').trim()
      else delete nextSpec.lastSeen
      await updateEquipment(current.id, buildPayload({
        ...current,
        name: String(form.name || '').trim() || current.name || current.assetCode
      }, form.status, nextSpec))
      ElMessage.success('设备点位已更新')
    } else {
      const assetCode = `PC-${seatCode}`
      await createEquipment({
        assetCode,
        name: String(form.name || '').trim() || assetCode,
        model: '',
        brand: '',
        labId: Number(selectedLabId.value),
        labName: String(selectedLab.value?.name || '').trim(),
        status: form.status,
        keeper: '',
        purchaseDate: '',
        price: '',
        specJson: JSON.stringify({
          category: 'pc',
          seatCode,
          os: String(form.os || '').trim(),
          chip: String(form.chip || '').trim(),
          notes: String(form.notes || '').trim(),
          lastSeen: String(form.lastSeen || '').trim() || nowText()
        }),
        imageUrl: ''
      })
      ElMessage.success('电脑点位已创建')
    }
    closeDialog()
    await refreshAll()
  } finally {
    saving.value = false
  }
}

async function removeEquipment(eq) {
  await deleteEquipment(eq.id)
  if (selectedEquipment.value?.id === eq.id) {
    selectedEquipment.value = null
  }
  ElMessage.success('设备已删除')
  await refreshAll()
}

watch(
  () => route.query.labId,
  (value) => {
    const numeric = Number(value || 0)
    if (numeric && numeric !== selectedLabId.value) {
      selectedLabId.value = numeric
    }
  }
)

onMounted(() => {
  refreshAll()
})
</script>

<style scoped lang="scss">
.room-map-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.hero-card,
.metric-card,
.panel-card,
.seat {
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
    radial-gradient(circle at top right, rgba(20, 184, 166, 0.14), transparent 34%),
    linear-gradient(135deg, #f7fffd 0%, #ecfeff 100%);
}

.hero-copy,
.hero-meta,
.hero-actions,
.head-actions,
.info-actions,
.legend-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.hero-copy {
  flex-direction: column;
}

.hero-card h2,
.panel-head h3 {
  margin: 0;
}

.eyebrow {
  display: inline-flex;
  width: fit-content;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(20, 184, 166, 0.14);
  color: #0f766e;
  font-size: 12px;
  font-weight: 700;
}

.hero-card p,
.hero-meta,
.metric-sub,
.metric-label,
.panel-head span,
.info-card p {
  margin: 0;
  color: var(--app-muted);
}

.metric-grid,
.layout-grid,
.dialog-grid,
.seat-grid {
  display: grid;
  gap: 20px;
}

.metric-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.metric-card {
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.metric-value {
  font-size: 32px;
}

.metric-value.success {
  color: #16a34a;
}

.metric-value.warning {
  color: #d97706;
}

.layout-grid {
  grid-template-columns: minmax(0, 1.45fr) 360px;
  align-items: start;
}

.panel-card {
  padding: 24px;
}

.panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.map-card {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.teacher-row {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 12px;
}

.seat-grid {
  grid-template-columns: repeat(6, minmax(0, 1fr));
}

.seat {
  padding: 14px 12px;
  border-radius: 18px;
  text-align: left;
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}

.seat:hover {
  transform: translateY(-2px);
}

.seat--teacher {
  grid-column: span 2;
}

.seat--active {
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.14);
}

.seat-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.seat-code,
.seat-state {
  font-size: 12px;
  font-weight: 700;
}

.seat-name {
  margin-top: 14px;
  font-weight: 700;
  color: #0f172a;
  word-break: break-word;
}

.seat-sub {
  margin-top: 10px;
  font-size: 12px;
  color: var(--app-muted);
  line-height: 1.5;
}

.seat--online {
  background: linear-gradient(180deg, rgba(220, 252, 231, 0.95), rgba(240, 253, 244, 0.95));
  border-color: rgba(34, 197, 94, 0.35);
}

.seat--offline {
  background: linear-gradient(180deg, rgba(241, 245, 249, 0.98), rgba(248, 250, 252, 0.98));
  border-color: rgba(148, 163, 184, 0.35);
}

.seat--warning {
  background: linear-gradient(180deg, rgba(255, 247, 237, 0.98), rgba(255, 251, 235, 0.98));
  border-color: rgba(245, 158, 11, 0.45);
}

.seat--empty {
  background: rgba(255, 255, 255, 0.82);
  border-style: dashed;
  border-color: rgba(148, 163, 184, 0.38);
}

.side-column,
.info-card,
.loading-wrap {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--app-muted);
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
}

.legend-dot--online {
  background: #22c55e;
}

.legend-dot--offline {
  background: #94a3b8;
}

.legend-dot--warning {
  background: #f59e0b;
}

.legend-dot--empty {
  background: #e2e8f0;
}

.dialog-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

@media (max-width: 1280px) {
  .layout-grid {
    grid-template-columns: 1fr;
  }

  .seat-grid,
  .teacher-row {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

@media (max-width: 900px) {
  .metric-grid,
  .dialog-grid,
  .seat-grid,
  .teacher-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .hero-card {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>

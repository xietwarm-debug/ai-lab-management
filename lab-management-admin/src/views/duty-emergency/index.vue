<template>
  <div class="page-container duty-page">
    <!-- 顶部 Hero 区 (带入场动画，应急专属红色调) -->
    <section class="hero-card overview-section is-danger-theme">
      <div class="hero-content">
        <div class="hero-copy">
          <span class="eyebrow">值班与应急</span>
          <h1 class="page-title">值班与应急处置</h1>
          <p class="page-desc">统一管理值班排班、事故上报、应急联系人和处置闭环，支持实验室日常值守与突发响应。</p>
        </div>
        <div class="hero-actions">
          <el-button type="danger" plain :loading="loading" @click="loadAll" :icon="RefreshRight" class="hover-lift">
            刷新全局状态
          </el-button>
        </div>
      </div>
      <div class="hero-decoration"></div>
    </section>

    <!-- 核心操作区 (Tabs面板) -->
    <section class="panel-card main-tabs-panel panel-fade-in">
      <el-tabs v-model="activeTab" class="custom-tabs">
        <!-- 1. 值班表 Tab -->
        <el-tab-pane name="duty">
          <template #label>
            <span class="tab-label-custom"><el-icon><Calendar /></el-icon> 值班表</span>
          </template>

          <div class="duty-layout mt-4">
            <article class="sub-card calendar-card panel-fade-in">
              <div class="sub-head duty-calendar-head">
                <div class="head-left">
                  <h3>周值班日历</h3>
                  <span>一次查看一周，按早 / 中 / 晚三个时段安排值班。</span>
                </div>
                <div class="calendar-toolbar">
                  <el-button-group>
                    <el-button @click="changeWeek(-1)">上一周</el-button>
                    <el-button @click="goCurrentWeek">本周</el-button>
                    <el-button @click="changeWeek(1)">下一周</el-button>
                  </el-button-group>
                  <span class="calendar-range">{{ weekRangeLabel }}</span>
                </div>
              </div>

              <div class="duty-calendar">
                <div class="calendar-corner">时段</div>
                <div v-for="day in weekDays" :key="day.date" class="calendar-day-head">
                  <strong>{{ day.weekday }}</strong>
                  <span>{{ day.display }}</span>
                </div>

                <template v-for="slot in dutySlots" :key="slot.key">
                  <div class="calendar-slot-head">
                    <strong>{{ slot.label }}</strong>
                    <span>{{ slot.time }}</span>
                  </div>
                  <button
                    v-for="day in weekDays"
                    :key="`${day.date}-${slot.key}`"
                    type="button"
                    class="calendar-cell"
                    :class="{
                      'is-active': isSelectedSlot(day.date, slot.key),
                      'is-empty': !getDutyCell(day.date, slot.key),
                      'is-today': day.isToday
                    }"
                    @click="selectDutySlot(day, slot)"
                  >
                    <template v-if="getDutyCell(day.date, slot.key)">
                      <div class="cell-top">
                        <div class="cell-title-group">
                          <span class="cell-assignee">{{ getDutyCell(day.date, slot.key).assigneeName || '未填写' }}</span>
                        </div>
                      </div>
                      <div class="cell-status-row">
                        <el-tag size="small" :type="getStatusType(getDutyCell(day.date, slot.key).status)" class="custom-tag compact-tag">
                          {{ getStatusLabel(getDutyCell(day.date, slot.key).status) }}
                        </el-tag>
                        <span
                          v-if="isDefaultFilledCell(day.date, slot.key)"
                          class="default-badge"
                        >
                          默认
                        </span>
                      </div>
                      <p class="cell-phone" :title="getDutyCell(day.date, slot.key).assigneePhone || '未留电话'">
                        {{ getDutyCell(day.date, slot.key).assigneePhone || '未留电话' }}
                      </p>
                      <p class="cell-note">{{ getDutyCell(day.date, slot.key).note || '点击可继续编辑该时段安排' }}</p>
                    </template>
                    <template v-else>
                      <span class="empty-plus">+</span>
                      <span class="empty-copy">点击填写{{ slot.label }}</span>
                    </template>
                  </button>
                </template>
              </div>
            </article>

            <article v-if="selectedDutySlot.date" class="sub-card panel-fade-in" style="animation-delay: 0.1s;">
              <div class="sub-head">
                <div class="head-left">
                  <h3>{{ dutyForm.id ? '编辑值班信息' : '新增值班信息' }}</h3>
                  <span>{{ selectedDutySummary }}</span>
                </div>
              </div>
              <el-form label-position="top" class="custom-form">
                <el-row :gutter="20">
                  <el-col :xs="24" :sm="12">
                    <el-form-item label="日期">
                      <el-date-picker v-model="dutyForm.dutyDate" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
                    </el-form-item>
                  </el-col>
                  <el-col :xs="24" :sm="12">
                    <el-form-item label="班次">
                      <el-select v-model="dutyForm.shiftName" style="width: 100%">
                        <el-option v-for="slot in dutySlots" :key="slot.key" :label="slot.label" :value="slot.label" />
                      </el-select>
                    </el-form-item>
                  </el-col>
                  <el-col :xs="24" :sm="12">
                    <el-form-item label="值班人">
                      <el-input v-model="dutyForm.assigneeName" placeholder="填写值班人姓名" />
                    </el-form-item>
                  </el-col>
                  <el-col :xs="24" :sm="12">
                    <el-form-item label="值班电话">
                      <el-input v-model="dutyForm.assigneePhone" placeholder="填写联系电话" />
                    </el-form-item>
                  </el-col>
                  <el-col :xs="24" :sm="12">
                    <el-form-item label="备岗人">
                      <el-input v-model="dutyForm.backupName" placeholder="无人可留空" />
                    </el-form-item>
                  </el-col>
                  <el-col :xs="24" :sm="12">
                    <el-form-item label="备岗电话">
                      <el-input v-model="dutyForm.backupPhone" placeholder="备岗联系方式" />
                    </el-form-item>
                  </el-col>
                  <el-col :xs="24" :sm="12">
                    <el-form-item label="状态">
                      <el-select v-model="dutyForm.status" style="width: 100%">
                        <el-option label="待值班" value="scheduled" />
                        <el-option label="值班中" value="on_duty" />
                        <el-option label="已完成" value="completed" />
                        <el-option label="已关闭" value="closed" />
                      </el-select>
                    </el-form-item>
                  </el-col>
                  <el-col :span="24">
                    <el-form-item label="备注">
                      <el-input v-model="dutyForm.note" type="textarea" :rows="3" placeholder="填写交接事项、重点巡检内容或临时提醒" />
                    </el-form-item>
                  </el-col>
                </el-row>
              </el-form>
              <div class="action-row">
                <el-button type="warning" plain @click="toggleDutyDefault">
                  {{ hasDefaultForSelectedSlot ? '取消默认排班' : '设为默认排班' }}
                </el-button>
                <el-button @click="resetDutyForm">清空</el-button>
                <el-button type="primary" :loading="savingDuty" @click="saveDuty" class="hover-lift">保存值班</el-button>
              </div>
            </article>

            <article v-else class="sub-card panel-fade-in duty-empty-state" style="animation-delay: 0.1s;">
              <div class="sub-head">
                <div class="head-left">
                  <h3>选择时段后再编辑</h3>
                  <span>先点击左侧周日历中的任意一个早 / 中 / 晚时段，再填写值班信息。</span>
                </div>
              </div>
              <el-empty description="当前还没有选中具体时段" />
            </article>
          </div>
        </el-tab-pane>

        <!-- 2. 事故处置 Tab -->
        <el-tab-pane name="incident">
          <template #label>
            <span class="tab-label-custom"><el-icon><Warning /></el-icon> 事故处置</span>
          </template>
          
          <div class="tab-grid mt-4">
            <article class="sub-card panel-fade-in">
              <div class="sub-head">
                <div class="head-left">
                  <h3 class="danger-border">事故上报</h3>
                  <span>支持实验室事故、异常事件和处置闭环</span>
                </div>
              </div>
              <el-form label-position="top" class="custom-form">
                <el-row :gutter="20">
                  <el-col :xs="24" :sm="12">
                    <el-form-item label="实验室">
                      <el-select v-model="incidentForm.labId" style="width: 100%" clearable @change="syncIncidentLabName">
                        <el-option v-for="lab in labOptions" :key="lab.labId || lab.id" :label="lab.labName || lab.name" :value="lab.labId || lab.id" />
                      </el-select>
                    </el-form-item>
                  </el-col>
                  <el-col :xs="24" :sm="12">
                    <el-form-item label="事故等级">
                      <el-select v-model="incidentForm.incidentLevel" style="width: 100%">
                        <el-option label="低 (Low)" value="low" />
                        <el-option label="中 (Medium)" value="medium" />
                        <el-option label="高 (High)" value="high" />
                        <el-option label="严重 (Critical)" value="critical" />
                      </el-select>
                    </el-form-item>
                  </el-col>
                  <el-col :xs="24" :sm="12">
                    <el-form-item label="标题">
                      <el-input v-model="incidentForm.title" placeholder="简述事故核心现象" />
                    </el-form-item>
                  </el-col>
                  <el-col :xs="24" :sm="12">
                    <el-form-item label="状态">
                      <el-select v-model="incidentForm.status" style="width: 100%">
                        <el-option label="已上报" value="reported" />
                        <el-option label="处理中" value="processing" />
                        <el-option label="已闭环" value="closed" />
                      </el-select>
                    </el-form-item>
                  </el-col>
                  <el-col :xs="24" :sm="12">
                    <el-form-item label="上报人">
                      <el-input v-model="incidentForm.reporterName" />
                    </el-form-item>
                  </el-col>
                  <el-col :xs="24" :sm="12">
                    <el-form-item label="联系电话">
                      <el-input v-model="incidentForm.reporterPhone" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="24">
                    <el-form-item label="事件描述">
                      <el-input v-model="incidentForm.description" type="textarea" :rows="3" placeholder="详细描述发生时间、地点、涉事设备及人员..." />
                    </el-form-item>
                  </el-col>
                  <el-col :span="24">
                    <el-form-item label="处置记录">
                      <el-input v-model="incidentForm.disposalNote" type="textarea" :rows="3" placeholder="填写后续跟进、处理方案及结果..." />
                    </el-form-item>
                  </el-col>
                </el-row>
              </el-form>
              <div class="action-row">
                <el-button @click="resetIncidentForm">清空</el-button>
                <el-button type="danger" :loading="savingIncident" @click="saveIncidentRecord" class="hover-lift">保存事故记录</el-button>
              </div>
            </article>

            <article class="sub-card table-card panel-fade-in" style="animation-delay: 0.1s;">
              <div class="sub-head">
                <div class="head-left">
                  <h3>事故列表</h3>
                  <span class="count-badge">{{ incidentRows.length }} 条</span>
                </div>
              </div>
              <div class="table-wrapper">
                <el-table :data="incidentRows" style="width: 100%">
                  <el-table-column prop="title" label="标题" min-width="160" show-overflow-tooltip />
                  <el-table-column prop="labName" label="实验室" min-width="120" show-overflow-tooltip />
                  <el-table-column prop="incidentLevel" label="等级" width="90">
                     <template #default="{ row }">
                      <span class="severity-dot" :class="`is-${row.incidentLevel}`"></span>
                      {{ getLevelLabel(row.incidentLevel) }}
                     </template>
                  </el-table-column>
                  <el-table-column prop="status" label="状态" width="100">
                     <template #default="{ row }">
                      <el-tag size="small" :type="row.status === 'closed' ? 'info' : (row.status === 'reported' ? 'danger' : 'warning')" class="custom-tag">
                        {{ row.status === 'closed' ? '已闭环' : (row.status === 'processing' ? '处理中' : '已上报') }}
                      </el-tag>
                     </template>
                  </el-table-column>
                  <el-table-column label="操作" width="160" fixed="right" align="right">
                    <template #default="{ row }">
                      <div class="row-actions">
                        <el-button link type="primary" @click="editIncident(row)">编辑</el-button>
                        <el-button link type="warning" @click="quickIncidentStatus(row, 'processing')" v-if="row.status !== 'processing' && row.status !== 'closed'">处理</el-button>
                        <el-button link type="success" @click="quickIncidentStatus(row, 'closed')" v-if="row.status !== 'closed'">闭环</el-button>
                      </div>
                    </template>
                  </el-table-column>
                </el-table>
              </div>
            </article>
          </div>
        </el-tab-pane>

        <!-- 3. 应急联系人 Tab -->
        <el-tab-pane name="contacts">
          <template #label>
            <span class="tab-label-custom"><el-icon><Phone /></el-icon> 应急联系人</span>
          </template>
          
          <div class="tab-grid mt-4">
            <article class="sub-card panel-fade-in">
              <div class="sub-head">
                <div class="head-left">
                  <h3>联系人维护</h3>
                  <span>值班电话、网络中心、保卫处、后勤等统一维护</span>
                </div>
              </div>
              <el-form label-position="top" class="custom-form">
                <el-row :gutter="20">
                  <el-col :xs="24" :sm="12">
                    <el-form-item label="姓名 / 部门">
                      <el-input v-model="contactForm.name" placeholder="如：保卫处报警中心" />
                    </el-form-item>
                  </el-col>
                  <el-col :xs="24" :sm="12">
                    <el-form-item label="岗位 / 职责">
                      <el-input v-model="contactForm.roleName" placeholder="如：校区安保" />
                    </el-form-item>
                  </el-col>
                  <el-col :xs="24" :sm="12">
                    <el-form-item label="电话">
                      <el-input v-model="contactForm.phone" />
                    </el-form-item>
                  </el-col>
                  <el-col :xs="24" :sm="12">
                    <el-form-item label="显示优先级">
                      <el-input-number v-model="contactForm.priorityNo" :min="1" :max="999" style="width: 100%" />
                    </el-form-item>
                  </el-col>
                  <el-col :xs="24" :sm="12">
                    <el-form-item label="状态">
                      <el-select v-model="contactForm.status" style="width: 100%">
                        <el-option label="启用" value="active" />
                        <el-option label="停用" value="inactive" />
                      </el-select>
                    </el-form-item>
                  </el-col>
                  <el-col :span="24">
                    <el-form-item label="补充说明">
                      <el-input v-model="contactForm.description" placeholder="支持24小时接听等说明..." />
                    </el-form-item>
                  </el-col>
                </el-row>
              </el-form>
              <div class="action-row">
                <el-button @click="resetContactForm">清空</el-button>
                <el-button type="primary" :loading="savingContact" @click="saveContactRecord" class="hover-lift">保存联系人</el-button>
              </div>
            </article>

            <article class="sub-card table-card panel-fade-in" style="animation-delay: 0.1s;">
              <div class="sub-head">
                <div class="head-left">
                  <h3>联系人名录</h3>
                  <span class="count-badge">{{ contactRows.length }} 条</span>
                </div>
              </div>
              <div class="table-wrapper">
                <el-table :data="contactRows" style="width: 100%">
                  <el-table-column prop="priorityNo" label="优先级" width="80" align="center" />
                  <el-table-column prop="name" label="姓名/部门" min-width="130" />
                  <el-table-column prop="phone" label="电话" min-width="130">
                    <template #default="{ row }">
                      <strong class="text-primary">{{ row.phone }}</strong>
                    </template>
                  </el-table-column>
                  <el-table-column prop="status" label="状态" width="90">
                     <template #default="{ row }">
                      <el-tag size="small" :type="row.status === 'active' ? 'success' : 'info'" class="custom-tag">
                        {{ row.status === 'active' ? '启用' : '停用' }}
                      </el-tag>
                     </template>
                  </el-table-column>
                  <el-table-column label="操作" width="120" fixed="right" align="right">
                    <template #default="{ row }">
                      <div class="row-actions">
                        <el-button link type="primary" @click="editContact(row)">编辑</el-button>
                        <el-button link type="danger" @click="deleteContactRecord(row)">删除</el-button>
                      </div>
                    </template>
                  </el-table-column>
                </el-table>
              </div>
            </article>
          </div>
        </el-tab-pane>
      </el-tabs>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { RefreshRight, Calendar, Warning, Phone } from '@element-plus/icons-vue'

// 假设的 API
import { getLabs } from '@/api/labs'
import {
  deleteEmergencyContact,
  getDutyRoster,
  getEmergencyContacts,
  getIncidents,
  saveDutyRoster,
  saveEmergencyContact,
  saveIncident,
  updateDutyRosterStatus,
  updateIncidentStatus
} from '@/api/duty'

const activeTab = ref('duty')
const loading = ref(false)
const savingDuty = ref(false)
const savingIncident = ref(false)
const savingContact = ref(false)
const applyingDutyDefaults = ref(false)

const dutyRows = ref([])
const incidentRows = ref([])
const contactRows = ref([])
const labOptions = ref([])
const dutyDefaultTemplates = ref({})
const dutyDefaultStorageKey = 'lab_admin_duty_defaults'

const dutyForm = reactive({
  id: null, dutyDate: '', shiftName: '', assigneeName: '', assigneePhone: '', backupName: '', backupPhone: '', status: 'scheduled', note: ''
})

const incidentForm = reactive({
  id: null, labId: null, labName: '', title: '', incidentLevel: 'medium', status: 'reported', reporterName: '', reporterPhone: '', emergencyContactName: '', description: '', disposalNote: ''
})

const contactForm = reactive({
  id: null, name: '', roleName: '', phone: '', priorityNo: 10, status: 'active', description: ''
})


const dutySlots = [
  { key: 'morning', label: '早班', time: '08:00 - 12:00', aliases: ['早班', '白班', '上午'] },
  { key: 'midday', label: '中班', time: '12:00 - 18:00', aliases: ['中班', '午班', '中午', '下午'] },
  { key: 'evening', label: '晚班', time: '18:00 - 22:00', aliases: ['晚班', '夜班'] }
]

const weekdayLabels = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
const selectedDutySlot = ref({ date: '', slotKey: '' })
const currentWeekStart = ref(getWeekStart(new Date()))

const weekDays = computed(() => {
  return Array.from({ length: 7 }, (_, index) => {
    const value = addDays(currentWeekStart.value, index)
    const date = formatDate(value)
    const today = formatDate(new Date())
    return {
      date,
      weekday: weekdayLabels[index],
      display: `${String(value.getMonth() + 1).padStart(2, '0')}/${String(value.getDate()).padStart(2, '0')}`,
      isToday: date === today
    }
  })
})

const weekRangeLabel = computed(() => {
  const first = weekDays.value[0]
  const last = weekDays.value[weekDays.value.length - 1]
  return first && last ? `${first.date} - ${last.date}` : ''
})

const selectedDutySummary = computed(() => {
  const slot = dutySlots.find((item) => item.key === selectedDutySlot.value.slotKey)
  if (!selectedDutySlot.value.date || !slot) {
    return '请选择日期、时段，并填写对应值班信息。'
  }
  return `正在编辑 ${selectedDutySlot.value.date} ${slot.label} 的值班安排。`
})

const selectedDutyDefaultKey = computed(() => {
  if (!selectedDutySlot.value.date || !selectedDutySlot.value.slotKey) return ''
  return getDefaultTemplateKey(selectedDutySlot.value.date, selectedDutySlot.value.slotKey)
})

const hasDefaultForSelectedSlot = computed(() => {
  return Boolean(selectedDutyDefaultKey.value && dutyDefaultTemplates.value[selectedDutyDefaultKey.value])
})

// --- UI 辅助函数 ---
const getStatusType = (status) => {
  const map = { scheduled: 'info', on_duty: 'primary', completed: 'success', closed: 'info' }
  return map[status] || 'info'
}

const getStatusLabel = (status) => {
  const map = { scheduled: '待值班', on_duty: '值班中', completed: '已完成', closed: '已关闭' }
  return map[status] || status
}

const getLevelLabel = (level) => {
  const map = { low: '低', medium: '中', high: '高', critical: '严重' }
  return map[level] || level
}

function getWeekStart(input) {
  const value = new Date(input)
  value.setHours(0, 0, 0, 0)
  const day = value.getDay() || 7
  value.setDate(value.getDate() - day + 1)
  return value
}

function addDays(input, days) {
  const value = new Date(input)
  value.setDate(value.getDate() + days)
  return value
}

function formatDate(input) {
  const value = new Date(input)
  const year = value.getFullYear()
  const month = String(value.getMonth() + 1).padStart(2, '0')
  const day = String(value.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function getWeekdayIndex(dateText) {
  const value = new Date(dateText)
  const day = value.getDay() || 7
  return day - 1
}

function getDefaultTemplateKey(dateText, slotKey) {
  return `${getWeekdayIndex(dateText)}-${slotKey}`
}

function loadDutyDefaultTemplates() {
  try {
    const raw = localStorage.getItem(dutyDefaultStorageKey)
    dutyDefaultTemplates.value = raw ? JSON.parse(raw) : {}
  } catch (error) {
    dutyDefaultTemplates.value = {}
  }
}

function saveDutyDefaultTemplates() {
  localStorage.setItem(dutyDefaultStorageKey, JSON.stringify(dutyDefaultTemplates.value))
}

function buildDefaultDutyTemplate(slot) {
  return {
    shiftName: slot?.label || dutyForm.shiftName || '',
    assigneeName: dutyForm.assigneeName || '',
    assigneePhone: dutyForm.assigneePhone || '',
    backupName: dutyForm.backupName || '',
    backupPhone: dutyForm.backupPhone || '',
    note: dutyForm.note || '',
    status: dutyForm.status || 'scheduled'
  }
}

function applyDefaultTemplateToForm(template, day, slot) {
  resetDutyForm()
  selectedDutySlot.value = { date: day.date, slotKey: slot.key }
  dutyForm.dutyDate = day.date
  dutyForm.shiftName = slot.label
  dutyForm.assigneeName = template.assigneeName || ''
  dutyForm.assigneePhone = template.assigneePhone || ''
  dutyForm.backupName = template.backupName || ''
  dutyForm.backupPhone = template.backupPhone || ''
  dutyForm.note = template.note || ''
  dutyForm.status = template.status || 'scheduled'
}

function resolveDutySlot(shiftName) {
  const source = String(shiftName || '').trim()
  return dutySlots.find((slot) => slot.aliases.some((alias) => source.includes(alias))) || null
}

function getDutyCell(date, slotKey) {
  return dutyRows.value.find((row) => row.dutyDate === date && resolveDutySlot(row.shiftName)?.key === slotKey) || null
}

function isSelectedSlot(date, slotKey) {
  return selectedDutySlot.value.date === date && selectedDutySlot.value.slotKey === slotKey
}

function isDefaultFilledCell(date, slotKey) {
  const key = getDefaultTemplateKey(date, slotKey)
  const row = getDutyCell(date, slotKey)
  if (!key || !row) return false
  const template = dutyDefaultTemplates.value[key]
  if (!template) return false

  return (
    (template.assigneeName || '') === (row.assigneeName || '') &&
    (template.assigneePhone || '') === (row.assigneePhone || '') &&
    (template.backupName || '') === (row.backupName || '') &&
    (template.backupPhone || '') === (row.backupPhone || '') &&
    (template.note || '') === (row.note || '') &&
    (template.status || 'scheduled') === (row.status || 'scheduled')
  )
}

function selectDutySlot(day, slot) {
  const row = getDutyCell(day.date, slot.key)
  selectedDutySlot.value = { date: day.date, slotKey: slot.key }
  if (row) {
    editDuty(row)
    return
  }
  const template = dutyDefaultTemplates.value[getDefaultTemplateKey(day.date, slot.key)]
  if (template) {
    applyDefaultTemplateToForm(template, day, slot)
    return
  }
  resetDutyForm()
  selectedDutySlot.value = { date: day.date, slotKey: slot.key }
  dutyForm.dutyDate = day.date
  dutyForm.shiftName = slot.label
}

async function ensureDutyDefaultsForCurrentWeek() {
  if (applyingDutyDefaults.value) return
  const drafts = []
  weekDays.value.forEach((day) => {
    dutySlots.forEach((slot) => {
      const template = dutyDefaultTemplates.value[getDefaultTemplateKey(day.date, slot.key)]
      if (!template) return
      if (getDutyCell(day.date, slot.key)) return
      drafts.push({
        dutyDate: day.date,
        shiftName: slot.label,
        assigneeName: template.assigneeName || '',
        assigneePhone: template.assigneePhone || '',
        backupName: template.backupName || '',
        backupPhone: template.backupPhone || '',
        note: template.note || '',
        status: template.status || 'scheduled'
      })
    })
  })
  if (!drafts.length) return

  applyingDutyDefaults.value = true
  try {
    await Promise.all(drafts.map((item) => saveDutyRoster(item)))
    const dutyRes = await getDutyRoster({}).catch(() => ({ data: { data: [] } }))
    dutyRows.value = Array.isArray(dutyRes.data?.data) ? dutyRes.data.data : []
  } finally {
    applyingDutyDefaults.value = false
  }
}

async function changeWeek(offset) {
  currentWeekStart.value = addDays(currentWeekStart.value, offset * 7)
  await ensureDutyDefaultsForCurrentWeek()
}

async function goCurrentWeek() {
  currentWeekStart.value = getWeekStart(new Date())
  await ensureDutyDefaultsForCurrentWeek()
}

// --- 业务逻辑保持原样 ---
function resetDutyForm() {
  dutyForm.id = null; dutyForm.dutyDate = ''; dutyForm.shiftName = ''; dutyForm.assigneeName = ''; dutyForm.assigneePhone = ''; dutyForm.backupName = ''; dutyForm.backupPhone = ''; dutyForm.status = 'scheduled'; dutyForm.note = ''
  selectedDutySlot.value = { date: '', slotKey: '' }
}

function resetIncidentForm() {
  incidentForm.id = null; incidentForm.labId = null; incidentForm.labName = ''; incidentForm.title = ''; incidentForm.incidentLevel = 'medium'; incidentForm.status = 'reported'; incidentForm.reporterName = ''; incidentForm.reporterPhone = ''; incidentForm.emergencyContactName = ''; incidentForm.description = ''; incidentForm.disposalNote = ''
}

function resetContactForm() {
  contactForm.id = null; contactForm.name = ''; contactForm.roleName = ''; contactForm.phone = ''; contactForm.priorityNo = 10; contactForm.status = 'active'; contactForm.description = ''
}

function toggleDutyDefault() {
  if (!selectedDutySlot.value.date || !selectedDutySlot.value.slotKey) {
    ElMessage.info('请先选择一个具体时段')
    return
  }
  const key = selectedDutyDefaultKey.value
  if (!key) return

  if (hasDefaultForSelectedSlot.value) {
    const next = { ...dutyDefaultTemplates.value }
    delete next[key]
    dutyDefaultTemplates.value = next
    saveDutyDefaultTemplates()
    ElMessage.success('已取消该时段的默认排班')
    return
  }

  if (!dutyForm.assigneeName) {
    ElMessage.warning('请先填写值班人，再设为默认排班')
    return
  }

  dutyDefaultTemplates.value = {
    ...dutyDefaultTemplates.value,
    [key]: buildDefaultDutyTemplate(dutySlots.find((item) => item.key === selectedDutySlot.value.slotKey))
  }
  saveDutyDefaultTemplates()
  ElMessage.success('已设为默认排班，下一周同一时段会自动带出')
}

function syncIncidentLabName() {
  const matched = labOptions.value.find((item) => Number(item.labId || item.id) === Number(incidentForm.labId || 0))
  incidentForm.labName = matched ? String(matched.labName || matched.name || '') : ''
}

async function loadAll() {
  loading.value = true
  try {
    const [labRes, dutyRes, incidentRes, contactRes] = await Promise.all([
      getLabs({ pageSize: 500 }).catch(() => ({ data: { data: [] } })),
      getDutyRoster({}).catch(() => ({ data: { data: [] } })),
      getIncidents({}).catch(() => ({ data: { data: [] } })),
      getEmergencyContacts({}).catch(() => ({ data: { data: [] } }))
    ])
    labOptions.value = Array.isArray(labRes.data?.data) ? labRes.data.data : []
    dutyRows.value = Array.isArray(dutyRes.data?.data) ? dutyRes.data.data : []
    incidentRows.value = Array.isArray(incidentRes.data?.data) ? incidentRes.data.data : []
    contactRows.value = Array.isArray(contactRes.data?.data) ? contactRes.data.data : []
    await ensureDutyDefaultsForCurrentWeek()
  } finally {
    loading.value = false
  }
}

async function saveDuty() {
  if (!dutyForm.dutyDate || !dutyForm.shiftName || !dutyForm.assigneeName) {
    ElMessage.warning('请至少填写日期、班次和值班人')
    return
  }
  savingDuty.value = true
  try {
    await saveDutyRoster({ ...dutyForm })
    if (hasDefaultForSelectedSlot.value && selectedDutyDefaultKey.value) {
      dutyDefaultTemplates.value = {
        ...dutyDefaultTemplates.value,
        [selectedDutyDefaultKey.value]: buildDefaultDutyTemplate(dutySlots.find((item) => item.key === selectedDutySlot.value.slotKey))
      }
      saveDutyDefaultTemplates()
    }
    ElMessage.success('值班信息已保存')
    resetDutyForm()
    await loadAll()
  } catch (e) {} finally { savingDuty.value = false }
}

function editDuty(row) {
  Object.assign(dutyForm, { ...row })
  selectedDutySlot.value = {
    date: row.dutyDate || '',
    slotKey: resolveDutySlot(row.shiftName)?.key || ''
  }
}

async function quickDutyStatus(row, status) {
  try {
    await updateDutyRosterStatus(row.id, { status, note: row.note || '' })
    ElMessage.success('值班状态已更新')
    await loadAll()
  } catch (e) {}
}

async function saveIncidentRecord() {
  if (!incidentForm.title) {
    ElMessage.warning('请填写事故标题')
    return
  }
  savingIncident.value = true
  try {
    await saveIncident({ ...incidentForm })
    ElMessage.success('事故记录已保存')
    resetIncidentForm()
    await loadAll()
  } catch (e) {} finally { savingIncident.value = false }
}

function editIncident(row) { Object.assign(incidentForm, { ...row }) }

async function quickIncidentStatus(row, status) {
  const disposalNote = status === 'closed'
    ? `${row.disposalNote || ''}\n${new Date().toLocaleString()} 已闭环`.trim()
    : row.disposalNote || ''
  try {
    await updateIncidentStatus(row.id, { status, disposalNote })
    ElMessage.success('事故状态已更新')
    await loadAll()
  } catch (e) {}
}

async function saveContactRecord() {
  if (!contactForm.name || !contactForm.phone) {
    ElMessage.warning('请填写联系人姓名和电话')
    return
  }
  savingContact.value = true
  try {
    await saveEmergencyContact({ ...contactForm })
    ElMessage.success('联系人已保存')
    resetContactForm()
    await loadAll()
  } catch (e) {} finally { savingContact.value = false }
}

function editContact(row) { Object.assign(contactForm, { ...row }) }

async function deleteContactRecord(row) {
  try {
    await ElMessageBox.confirm(`确认删除联系人 ${row.name} 吗？`, '删除联系人', { type: 'warning' })
    await deleteEmergencyContact(row.id)
    ElMessage.success('联系人已删除')
    await loadAll()
  } catch (e) { /* 用户取消或失败 */ }
}

onMounted(() => {
  loadDutyDefaultTemplates()
  loadAll()
})
</script>

<style scoped lang="scss">
// 统一的学术极简设计变量
$bg-color: #f8fafc;
$card-bg: #ffffff;
$text-main: #0f172a;
$text-regular: #475569;
$text-light: #94a3b8;
$border-color: #e2e8f0;
$primary: #3b82f6;
$danger: #ef4444;
$danger-light: #fef2f2;
$warning: #f59e0b;
$success: #10b981;
$radius-lg: 16px;
$radius-md: 12px;
$shadow-soft: 0 10px 30px rgba(0, 0, 0, 0.03);
$shadow-hover: 0 15px 35px rgba(59, 130, 246, 0.06);
$shadow-danger-hover: 0 15px 35px rgba(239, 68, 68, 0.08);

// --- 入场动画 Keyframes ---
@keyframes fadeSlideUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.page-container {
  padding: 32px;
  background-color: $bg-color;
  min-height: 100vh;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

// 工具类
.mt-4 { margin-top: 16px; }
.text-primary { color: $primary; }
.hover-lift { transition: transform 0.2s ease; &:hover { transform: translateY(-1px); } }
.panel-fade-in {
  animation: fadeSlideUp 0.6s cubic-bezier(0.2, 0.8, 0.2, 1) both;
  &:nth-child(n+1) { animation-delay: 0.1s; }
  &:nth-child(n+2) { animation-delay: 0.15s; }
}

/* --- Hero 区域 (应急专属红色主题) --- */
.hero-card {
  position: relative;
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  padding: 32px;
  background: #ffffff;
  border-radius: $radius-lg;
  box-shadow: $shadow-soft;
  overflow: hidden;
  animation: fadeSlideUp 0.6s cubic-bezier(0.2, 0.8, 0.2, 1) both;

  &.is-danger-theme {
    background: radial-gradient(circle at top right, rgba(239, 68, 68, 0.08), transparent 60%),
                linear-gradient(135deg, #ffffff 0%, #fff5f5 100%);
    border: 1px solid rgba(239, 68, 68, 0.1);
  }

  .hero-decoration {
    position: absolute; right: 0; top: 0; width: 300px; height: 100%;
    pointer-events: none;
    background-image: radial-gradient(#ef4444 1px, transparent 1px);
    background-size: 20px 20px;
    opacity: 0.05;
    mask-image: linear-gradient(to left, white, transparent);
  }

  .hero-content {
    position: relative; z-index: 1; display: flex; justify-content: space-between;
    align-items: flex-end; width: 100%; flex-wrap: wrap; gap: 24px;
  }

  .eyebrow {
    display: inline-flex; width: fit-content; padding: 6px 12px; border-radius: 999px;
    background: $danger-light; color: #b91c1c; font-size: 13px; font-weight: 700;
    margin-bottom: 12px; letter-spacing: 0.05em;
  }

  .page-title { font-size: 28px; font-weight: 700; color: $text-main; margin: 0 0 12px 0; }
  .page-desc { color: $text-regular; font-size: 14px; margin: 0; max-width: 600px; line-height: 1.6; }
}

/* --- 面板基础与 Tabs --- */
.panel-card {
  background: $card-bg; border-radius: $radius-lg; padding: 24px;
  box-shadow: $shadow-soft; border: 1px solid transparent;
}

.main-tabs-panel { padding-top: 16px; }

:deep(.custom-tabs) {
  .el-tabs__nav-wrap::after { height: 1px; background-color: $border-color; }
  .el-tabs__active-bar { background-color: $primary; height: 3px; border-radius: 3px 3px 0 0; }
  .el-tabs__item {
    font-size: 16px; color: $text-regular; font-weight: 500; padding: 0 24px; transition: all 0.3s;
    &:hover { color: $primary; }
    &.is-active { color: $text-main; font-weight: 600; }
  }
  .tab-label-custom { display: flex; align-items: center; gap: 8px; }
}

/* --- 内部网格布局 --- */
.tab-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(0, 1.8fr); // 左侧表单较窄，右侧表格较宽
  gap: 24px;
}

.duty-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.7fr) minmax(360px, 1fr);
  gap: 24px;
}

/* --- 子卡片 (表单区与表格区) --- */
.sub-card {
  background: #f8fafc; border-radius: $radius-md; padding: 24px;
  border: 1px solid rgba(226, 232, 240, 0.8);
  transition: all 0.3s ease;
  display: flex; flex-direction: column;

  &:hover { box-shadow: $shadow-hover; background: #ffffff; border-color: rgba(59, 130, 246, 0.1); }
  &.table-card { padding: 0; background: #ffffff; overflow: hidden; }
}

.sub-head {
  display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px;
  
  .head-left {
    h3 { 
      font-size: 16px; font-weight: 600; color: $text-main; margin: 0 0 6px 0;
      border-left: 4px solid $primary; padding-left: 10px;
      &.danger-border { border-left-color: $danger; }
    }
    span { color: $text-light; font-size: 13px; padding-left: 14px; display: block;}
    .count-badge { display: inline-block; background: #f1f5f9; padding: 2px 10px; border-radius: 12px; margin-left: 14px; padding-left: 10px; }
  }
}

.table-card .sub-head { padding: 20px 24px 0 24px; margin-bottom: 16px; }

.action-row { display: flex; justify-content: flex-end; gap: 12px; margin-top: auto; padding-top: 24px; }

.calendar-card {
  overflow: hidden;
}

.duty-calendar-head {
  gap: 16px;
}

.calendar-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.calendar-range {
  color: $text-regular;
  font-size: 13px;
  font-weight: 600;
}

.duty-calendar {
  display: grid;
  grid-template-columns: 100px repeat(7, minmax(0, 1fr));
  gap: 10px;
}

.calendar-corner,
.calendar-day-head,
.calendar-slot-head,
.calendar-cell {
  border-radius: 12px;
  border: 1px solid rgba(226, 232, 240, 0.85);
  background: #ffffff;
}

.calendar-corner,
.calendar-day-head,
.calendar-slot-head {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 62px;
  padding: 12px;
}

.calendar-corner,
.calendar-slot-head {
  flex-direction: column;
  background: #f8fafc;
}

.calendar-day-head {
  flex-direction: column;
  gap: 4px;
}

.calendar-day-head strong,
.calendar-slot-head strong {
  color: $text-main;
  font-size: 14px;
}

.calendar-day-head span,
.calendar-slot-head span {
  color: $text-light;
  font-size: 12px;
}

.calendar-cell {
  min-height: 132px;
  padding: 12px 10px;
  text-align: left;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 8px;
  transition: all 0.2s ease;
  overflow: hidden;
}

.calendar-cell:hover {
  border-color: rgba(59, 130, 246, 0.35);
  box-shadow: $shadow-hover;
  transform: translateY(-1px);
}

.calendar-cell.is-empty {
  align-items: center;
  justify-content: center;
  color: $text-light;
  background: linear-gradient(180deg, #ffffff, #f8fbff);
}

.calendar-cell.is-active {
  border-color: rgba(59, 130, 246, 0.55);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.08);
}

.calendar-cell.is-today {
  background: linear-gradient(180deg, #ffffff, #fff7f7);
}

.cell-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  min-width: 0;
}

.cell-title-group {
  display: flex;
  align-items: center;
  min-width: 0;
  flex: 1;
  overflow: hidden;
}

.cell-assignee {
  color: $text-main;
  font-size: 14px;
  font-weight: 700;
  min-width: 0;
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.default-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 6px;
  border-radius: 999px;
  background: rgba(245, 158, 11, 0.14);
  color: #b45309;
  font-size: 10px;
  font-weight: 700;
  line-height: 1;
  flex-shrink: 0;
  white-space: nowrap;
}

.cell-status-row {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.compact-tag {
  max-width: 100%;
  flex-shrink: 0;
}

.cell-phone,
.cell-note {
  margin: 0;
  color: $text-regular;
  font-size: 12px;
  line-height: 1.4;
}

.cell-phone {
  color: #475569;
  font-family: 'DIN Alternate', 'Roboto Mono', 'Consolas', monospace;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.cell-note {
  color: $text-light;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  word-break: break-word;
}

.empty-plus {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: rgba(59, 130, 246, 0.1);
  color: $primary;
  font-size: 18px;
  font-weight: 600;
}

.empty-copy {
  font-size: 12px;
}

.duty-empty-state {
  justify-content: center;
}

/* --- 表单样式优化 (Academic Minimalist) --- */
:deep(.custom-form) {
  .el-form-item__label { font-weight: 500; color: $text-regular; padding-bottom: 4px; }
  .el-input__wrapper, .el-select__wrapper {
    background-color: #ffffff; border-radius: 8px; box-shadow: 0 0 0 1px $border-color inset; transition: all 0.2s;
    &:hover { box-shadow: 0 0 0 1px rgba(59, 130, 246, 0.5) inset; }
    &.is-focus { box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2) inset, 0 0 0 1px $primary inset !important; }
  }
  .el-textarea__inner {
    border-radius: 8px; box-shadow: 0 0 0 1px $border-color inset; padding: 12px; font-family: inherit;
    &:focus { box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2) inset, 0 0 0 1px $primary inset; }
  }
}

/* --- 表格样式优化 (去除边框，增加呼吸感) --- */
.table-wrapper {
  padding: 0 24px 24px 24px;
}

:deep(.el-table) {
  --el-table-border-color: #f1f5f9;
  --el-table-header-bg-color: #f8fafc;
  --el-table-header-text-color: #64748b;
  border-radius: 8px;
  
  th.el-table__cell { font-weight: 600; font-size: 13px; }
  td.el-table__cell { padding: 12px 0; color: $text-main; }
  
  &::before, .el-table__inner-wrapper::before { display: none; } // 移除最底部边框
  .el-table__row { transition: background-color 0.2s; }
  .el-table__row:hover > td.el-table__cell { background-color: #f8fafc !important; }
}

.row-actions { display: flex; gap: 4px; justify-content: flex-end; }

/* --- 状态标签与圆点 --- */
:deep(.custom-tag) { border-radius: 6px; font-weight: 500; border: none; }

.severity-dot {
  display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px;
  &.is-low { background-color: $success; }
  &.is-medium { background-color: $warning; }
  &.is-high { background-color: #f97316; } // 橙红色
  &.is-critical { background-color: $danger; box-shadow: 0 0 0 3px $danger-light; }
}

/* --- 响应式 --- */
@media (max-width: 1200px) {
  .tab-grid,
  .duty-layout { grid-template-columns: 1fr; }
  .table-card { min-height: 400px; }
}

@media (max-width: 768px) {
  .hero-content, .sub-head { flex-direction: column; align-items: flex-start; }
  .page-container { padding: 16px; }
  .calendar-toolbar { width: 100%; }
  .duty-calendar {
    grid-template-columns: 84px repeat(7, minmax(120px, 1fr));
    overflow-x: auto;
    padding-bottom: 4px;
  }
}
</style>

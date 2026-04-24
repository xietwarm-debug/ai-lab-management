<template>
  <div class="schedule-page">
    <section class="hero-card">
      <div class="hero-copy">
        <span class="eyebrow">课表与门禁</span>
        <h2>排课管理</h2>
        <p>统一处理学期课表导入、模板启用、开门提醒和实验室排课查询，让教学安排与门禁联动更顺畅。</p>
        <div class="hero-meta">
          <span>当前模板：{{ activeTemplate?.termName || '未启用' }}</span>
          <span>今日待处理：{{ pendingCount }}</span>
        </div>
      </div>
      <div class="hero-actions">
        <el-button type="primary" @click="openCreateImport">导入课表</el-button>
        <el-button :loading="pageLoading" @click="reloadAll">刷新全部</el-button>
      </div>
    </section>

    <section class="metric-grid">
      <article class="metric-card">
        <span class="metric-label">模板总数</span>
        <strong class="metric-value">{{ templates.length }}</strong>
        <span class="metric-sub">支持草稿与启用态</span>
      </article>
      <article class="metric-card">
        <span class="metric-label">今日提醒</span>
        <strong class="metric-value">{{ todayList.length }}</strong>
        <span class="metric-sub">来自门禁提醒</span>
      </article>
      <article class="metric-card">
        <span class="metric-label">待确认开门</span>
        <strong class="metric-value warning">{{ pendingCount }}</strong>
        <span class="metric-sub">建议今日处理</span>
      </article>
      <article class="metric-card">
        <span class="metric-label">实验室数</span>
        <strong class="metric-value">{{ labs.length }}</strong>
        <span class="metric-sub">可用于排课</span>
      </article>
    </section>

    <section class="panel-card">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="模板与导入" name="templates">
          <div class="template-list">
            <article v-for="item in templates" :key="item.id" class="template-card">
              <div class="template-head">
                <div>
                  <strong>{{ item.termName || `模板 #${item.id}` }}</strong>
                  <p>开学：{{ item.semesterStartDate || '-' }} · 周数：{{ item.semesterWeeks || '-' }} · 明细：{{ item.itemCount || 0 }}</p>
                  <p>课程：{{ item.courseCount || 0 }} 门<span v-if="item.coursePreview?.length"> · {{ item.coursePreview.join(' / ') }}<template v-if="(item.courseCount || 0) > item.coursePreview.length"> 等</template></span></p>
                  <p>来源：{{ item.sourceType || '-' }} · 提前提醒：{{ item.reminderLeadMinutes || 20 }} 分钟</p>
                </div>
                <div class="tag-row">
                  <el-tag :type="item.status === 'active' ? 'success' : 'info'">
                    {{ item.status === 'active' ? '当前启用' : item.status || 'draft' }}
                  </el-tag>
                </div>
              </div>
              <div class="template-actions">
                <el-button v-if="item.status !== 'active'" @click="activateTemplate(item)">设为启用</el-button>
                <el-button @click="openEditImport(item)">编辑</el-button>
                <el-popconfirm title="确定删除这个模板吗？" @confirm="removeTemplate(item)">
                  <template #reference>
                    <el-button type="danger" plain>删除</el-button>
                  </template>
                </el-popconfirm>
              </div>
            </article>
          </div>
          <el-empty v-if="!templates.length" description="暂无课表模板" />
        </el-tab-pane>

        <el-tab-pane label="今日开门提醒" name="today">
          <div v-if="todayList.length" class="template-list">
            <article v-for="item in todayList" :key="item.id" class="template-card">
              <div class="template-head">
                <div>
                  <strong>{{ item.labName || '-' }} · {{ item.courseName || '-' }}</strong>
                  <p>{{ item.occurrenceDate || '-' }} · {{ item.periodText || '-' }}</p>
                  <p>{{ item.teacherName || '-' }} · {{ item.className || '-' }}</p>
                </div>
                <div class="tag-row">
                  <el-tag :type="item.doorStatus === 'pending' ? 'warning' : 'success'">{{ item.doorStatus || '-' }}</el-tag>
                </div>
              </div>
              <div class="template-actions">
                <el-button v-if="item.doorStatus === 'pending'" type="primary" @click="confirmOpen(item)">确认开门</el-button>
                <el-button v-if="item.doorStatus === 'pending'" @click="ignoreReminder(item)">忽略</el-button>
              </div>
            </article>
          </div>
          <el-empty v-else description="今日没有开门提醒" />
        </el-tab-pane>

        <el-tab-pane label="实验室课表" name="schedule">
          <section class="query-card">
            <el-form inline>
              <el-form-item label="实验室">
                <el-select v-model="labQuery.labId" style="width: 220px" @change="loadLabSchedule">
                  <el-option v-for="lab in labs" :key="lab.id" :label="lab.name" :value="lab.id" />
                </el-select>
              </el-form-item>
              <el-form-item label="日期">
                <el-date-picker v-model="labQuery.date" type="date" value-format="YYYY-MM-DD" @change="loadLabSchedule" />
              </el-form-item>
              <el-form-item label="视图">
                <el-radio-group v-model="labQuery.mode" @change="loadLabSchedule">
                  <el-radio-button label="day">按天</el-radio-button>
                  <el-radio-button label="week">按周</el-radio-button>
                </el-radio-group>
              </el-form-item>
            </el-form>
          </section>

          <div v-if="labQuery.mode === 'day'">
            <div v-if="daySchedule.length" class="template-list">
              <article v-for="item in daySchedule" :key="item.id" class="template-card">
                <strong>{{ item.periodText || '-' }} · {{ item.courseName || '-' }}</strong>
                <p>{{ item.teacherName || '-' }} · {{ item.className || '-' }}</p>
                <p>{{ item.startAt || '-' }} ~ {{ item.endAt || '-' }}</p>
              </article>
            </div>
            <el-empty v-else description="当天暂无排课" />
          </div>

          <div v-else>
            <div v-if="weekSchedule.length" class="week-list">
              <article v-for="day in weekSchedule" :key="day.date" class="week-card">
                <strong>{{ day.date }} · {{ weekdayText(day.weekDay) }}</strong>
                <div v-if="day.list?.length" class="day-list">
                  <div v-for="item in day.list" :key="item.id" class="day-item">
                    <span>{{ item.periodText || '-' }}</span>
                    <span>{{ item.courseName || '-' }}</span>
                    <span>{{ item.teacherName || '-' }}</span>
                  </div>
                </div>
                <p v-else class="muted-copy">当天无排课</p>
              </article>
            </div>
            <el-empty v-else description="本周暂无排课" />
          </div>
        </el-tab-pane>

        <el-tab-pane label="提醒记录" name="records">
          <section class="query-card">
            <el-form inline>
              <el-form-item label="开始日期">
                <el-date-picker v-model="recordFilters.startDate" type="date" value-format="YYYY-MM-DD" />
              </el-form-item>
              <el-form-item label="结束日期">
                <el-date-picker v-model="recordFilters.endDate" type="date" value-format="YYYY-MM-DD" />
              </el-form-item>
              <el-form-item label="提醒状态">
                <el-select v-model="recordFilters.remindStatus" style="width: 160px">
                  <el-option label="全部" value="" />
                  <el-option label="pending" value="pending" />
                  <el-option label="confirmed" value="confirmed" />
                  <el-option label="ignored" value="ignored" />
                </el-select>
              </el-form-item>
              <el-form-item label="门禁状态">
                <el-select v-model="recordFilters.doorStatus" style="width: 160px">
                  <el-option label="全部" value="" />
                  <el-option label="pending" value="pending" />
                  <el-option label="opened" value="opened" />
                  <el-option label="ignored" value="ignored" />
                </el-select>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" @click="queryRecords">查询</el-button>
              </el-form-item>
            </el-form>
          </section>
          <el-table :data="reminderRecords" stripe>
            <el-table-column prop="occurrenceDate" label="日期" min-width="120" />
            <el-table-column prop="labName" label="实验室" min-width="160" />
            <el-table-column prop="courseName" label="课程" min-width="180" />
            <el-table-column prop="periodText" label="节次" min-width="140" />
            <el-table-column prop="doorStatus" label="门禁状态" min-width="120" />
            <el-table-column prop="remindStatus" label="提醒状态" min-width="120" />
            <el-table-column prop="handledBy" label="处理人" min-width="120" />
            <el-table-column prop="handledAt" label="处理时间" min-width="180" />
          </el-table>
          <div class="pager-row">
            <el-pagination
              v-model:current-page="recordPage"
              v-model:page-size="recordPageSize"
              layout="total, sizes, prev, pager, next"
              :total="recordTotal"
              :page-sizes="[10, 20, 50]"
              @current-change="loadReminderRecords"
              @size-change="handleRecordPageSizeChange"
            />
          </div>
        </el-tab-pane>
      </el-tabs>
    </section>

    <section class="panel-card">
      <div class="panel-head">
        <div>
          <h3>本周总览</h3>
          <span>{{ weekRangeText }}</span>
        </div>
      </div>
      <div class="overview-table">
        <div class="overview-row overview-row--head">
          <span class="overview-lab">实验室</span>
          <span v-for="day in weekColumns" :key="day.weekDay" class="overview-cell">
            {{ day.label }}<small>{{ day.mmdd }}</small>
          </span>
        </div>
        <div v-for="row in weekOverviewRows" :key="row.key" class="overview-row">
          <span class="overview-lab">{{ row.labName }}</span>
          <button
            v-for="day in weekColumns"
            :key="`${row.key}-${day.weekDay}`"
            type="button"
            class="overview-cell overview-cell--button"
            :class="{ 'overview-cell--empty': !row.cells[day.weekDay].length, 'overview-cell--interactive': row.cells[day.weekDay].length }"
            @click="openOverviewCell(row, day)"
          >
            <template v-if="row.cells[day.weekDay].length">
              <strong>{{ row.cells[day.weekDay].length }} 节</strong>
              <small>{{ overviewPreviewText(row.cells[day.weekDay]) }}</small>
              <small class="overview-hint">点击查看课程详情</small>
            </template>
            <template v-else>-</template>
          </button>
        </div>
      </div>
    </section>

    <el-drawer v-model="importVisible" :title="editingTemplateId ? '编辑课表模板' : '导入课表'" size="720px">
      <el-form label-position="top">
        <div class="drawer-grid">
          <el-form-item label="学期名称">
            <el-input v-model="importForm.termName" placeholder="例如 2025-2026-2" />
          </el-form-item>
          <el-form-item label="开学日期">
            <el-date-picker v-model="importForm.semesterStartDate" type="date" value-format="YYYY-MM-DD" />
          </el-form-item>
          <el-form-item label="教学周数">
            <el-input-number v-model="importForm.semesterWeeks" :min="1" :max="30" />
          </el-form-item>
          <el-form-item label="提醒提前分钟">
            <el-input-number v-model="importForm.reminderLeadMinutes" :min="1" :max="180" />
          </el-form-item>
        </div>
        <div class="drawer-grid">
          <el-form-item label="来源类型">
            <el-select v-model="importForm.sourceType">
              <el-option label="manual" value="manual" />
              <el-option label="excel" value="excel" />
            </el-select>
          </el-form-item>
          <el-form-item label="导入模式">
            <el-radio-group v-model="importForm.mode">
              <el-radio-button label="replace">覆盖</el-radio-button>
              <el-radio-button label="append">追加</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="导入后启用">
            <el-switch v-model="importForm.activate" />
          </el-form-item>
          <el-form-item label="录入方式">
            <el-radio-group v-model="importForm.inputType">
              <el-radio-button label="json">JSON</el-radio-button>
              <el-radio-button label="paste">粘贴表格</el-radio-button>
            </el-radio-group>
          </el-form-item>
        </div>
        <el-form-item :label="importForm.inputType === 'json' ? '课表 JSON' : '粘贴内容'">
          <el-input
            v-model="importForm.rawText"
            type="textarea"
            :rows="18"
            :placeholder="importForm.inputType === 'json' ? '请输入课表 JSON 数组' : '按课程名、星期几、节次、时间段、周次、实验室、教师、班级、备注的顺序粘贴'"
          />
        </el-form-item>
        <p class="hint-copy">当前解析预览：{{ parsedImportItems.length }} 条</p>
        <p class="hint-copy">本次导入包含 {{ parsedImportCourseGroups.length }} 门课程<span v-if="parsedImportCourseGroups.length"> · {{ parsedImportCourseGroups.slice(0, 4).map(item => `${item.courseName}(${item.count})`).join(' / ') }}</span></p>
        <div class="import-preview">
          <div class="tag-row">
            <el-tag type="success">有效 {{ parsedImportItems.length }}</el-tag>
            <el-tag :type="parsedImportErrors.length ? 'danger' : 'info'">异常 {{ parsedImportErrors.length }}</el-tag>
          </div>
          <el-alert
            v-if="parsedImportErrorText"
            type="error"
            show-icon
            :closable="false"
            :title="parsedImportErrorText"
          />
          <el-alert v-else-if="parsedImportErrors.length" type="warning" show-icon :closable="false">
            <template #title>发现 {{ parsedImportErrors.length }} 条待修正记录，建议先修正后再导入。</template>
            <div class="import-error-list">
              <div v-for="item in parsedImportErrors.slice(0, 6)" :key="`${item.rowNo}-${item.reason}`">
                第 {{ item.rowNo }} 行：{{ item.reason }}
              </div>
            </div>
          </el-alert>
          <el-table v-if="parsedImportItems.length" :data="parsedImportItems.slice(0, 8)" size="small" stripe>
            <el-table-column prop="courseName" label="课程" min-width="160" />
            <el-table-column prop="weekDay" label="星期" min-width="90" />
            <el-table-column label="节次/时间段" min-width="180">
              <template #default="{ row }">
                {{ row.periodRange || row.timeRange || '-' }}
              </template>
            </el-table-column>
            <el-table-column prop="weekRange" label="周次" min-width="100" />
            <el-table-column prop="labName" label="实验室" min-width="140" />
            <el-table-column prop="teacherName" label="教师" min-width="120" />
          </el-table>
          <p v-if="parsedImportItems.length > 8" class="hint-copy">仅展示前 8 条预览，提交时会按全部有效数据导入。</p>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="importVisible = false">取消</el-button>
        <el-button type="primary" :loading="importing" @click="submitImport">提交导入</el-button>
      </template>
    </el-drawer>
    <el-dialog v-model="overviewDetailVisible" title="课程详情" width="640px">
      <div class="overview-detail-head">
        <strong>{{ overviewDetail.labName || '-' }}</strong>
        <span>{{ overviewDetail.date || '-' }} · {{ overviewDetail.dayLabel || '-' }}</span>
      </div>
      <el-empty v-if="!overviewDetail.list.length" description="当天暂无课程" />
      <div v-else class="template-list">
        <article v-for="item in overviewDetail.list" :key="item.id || item.key" class="template-card">
          <strong>{{ item.periodText || '-' }} · {{ item.courseName || '-' }}</strong>
          <p>{{ item.teacherName || '-' }} · {{ item.className || '-' }}</p>
          <p>{{ item.startAt || '-' }} ~ {{ item.endAt || '-' }}</p>
        </article>
      </div>
      <template #footer>
        <el-button @click="overviewDetailVisible = false">关闭</el-button>
        <el-button type="primary" @click="openOverviewInSchedule">在实验室课表中打开</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRoute } from 'vue-router'
import { getLabs } from '@/api/labs'
import {
  activateScheduleTemplate,
  confirmDoorReminderOpen,
  deleteScheduleTemplate,
  getDoorReminderRecords,
  getDoorRemindersToday,
  getDoorRemindersWeek,
  getLabScheduleDay,
  getLabScheduleWeek,
  getScheduleTemplateDetail,
  getScheduleTemplates,
  ignoreDoorReminder,
  importSchedule
} from '@/api/schedule'

const route = useRoute()

const pageLoading = ref(false)
const templates = ref([])
const todayList = ref([])
const weekList = ref([])
const labs = ref([])
const activeTab = ref('templates')
const daySchedule = ref([])
const weekSchedule = ref([])
const reminderRecords = ref([])
const recordTotal = ref(0)
const recordPage = ref(1)
const recordPageSize = ref(20)
const importVisible = ref(false)
const editingTemplateId = ref(0)
const importing = ref(false)
const overviewDetailVisible = ref(false)
const overviewDetail = reactive({
  labId: 0,
  labName: '',
  date: '',
  dayLabel: '',
  list: []
})
const importForm = reactive({
  termName: '',
  semesterStartDate: '',
  semesterWeeks: 20,
  reminderLeadMinutes: 20,
  sourceType: 'manual',
  activate: true,
  mode: 'replace',
  inputType: 'paste',
  rawText: ''
})

const labQuery = reactive({
  labId: 0,
  date: '',
  mode: 'week'
})

const recordFilters = reactive({
  startDate: '',
  endDate: '',
  remindStatus: '',
  doorStatus: ''
})

const activeTemplate = computed(() => templates.value.find((item) => item.status === 'active') || null)
const pendingCount = computed(() => todayList.value.filter((item) => item.doorStatus === 'pending').length)

const weekColumns = computed(() => {
  const base = mondayOf(workweekAnchor(labQuery.date || todayText()))
  const labels = ['周一', '周二', '周三', '周四', '周五']
  return labels.map((label, index) => {
    const date = addDays(base, index)
    return {
      label,
      weekDay: index + 1,
      mmdd: date.slice(5),
      date
    }
  })
})

const weekRangeText = computed(() => {
  const columns = weekColumns.value
  return columns.length ? `${columns[0].date} ~ ${columns[columns.length - 1].date}` : '-'
})

const weekOverviewRows = computed(() => {
  const map = {}
  labs.value.forEach((lab) => {
    map[lab.id] = {
      key: `lab-${lab.id}`,
      labId: Number(lab.id || 0),
      labName: lab.name || `LAB-${lab.id}`,
      cells: { 1: [], 2: [], 3: [], 4: [], 5: [] }
    }
  })
  weekList.value.forEach((item, index) => {
    const labId = Number(item.labId || 0)
    if (!map[labId]) {
      map[labId] = {
        key: `lab-${labId}-${index}`,
        labId,
        labName: item.labName || `LAB-${labId}`,
        cells: { 1: [], 2: [], 3: [], 4: [], 5: [] }
      }
    }
    if (map[labId].cells[item.weekDay]) {
      map[labId].cells[item.weekDay].push(item)
    }
  })
  Object.values(map).forEach((row) => {
    Object.keys(row.cells).forEach((weekDay) => {
      row.cells[weekDay].sort((a, b) => {
        const sa = Number(a.periodStart || 0)
        const sb = Number(b.periodStart || 0)
        if (sa !== sb) return sa - sb
        return Number(a.periodEnd || 0) - Number(b.periodEnd || 0)
      })
    })
  })
  return Object.values(map)
})

const parsedImportResult = computed(() => parseImportItems(importForm.inputType, importForm.rawText, labs.value))
const parsedImportItems = computed(() => parsedImportResult.value.items)
const parsedImportErrors = computed(() => parsedImportResult.value.errors)
const parsedImportErrorText = computed(() => parsedImportResult.value.parseError)
const parsedImportCourseGroups = computed(() => {
  const map = new Map()
  parsedImportItems.value.forEach((item) => {
    const courseName = normalizeText(item.courseName) || '未命名课程'
    const next = map.get(courseName) || { courseName, count: 0 }
    next.count += 1
    map.set(courseName, next)
  })
  return Array.from(map.values()).sort((a, b) => {
    if (b.count !== a.count) return b.count - a.count
    return a.courseName.localeCompare(b.courseName, 'zh-Hans-CN')
  })
})

function formatDateText(date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function parseDateText(dateText) {
  const text = String(dateText || '').trim()
  return text ? new Date(`${text}T00:00:00`) : new Date()
}

function todayText() {
  return formatDateText(new Date())
}

function workweekAnchor(dateText) {
  const date = parseDateText(dateText || todayText())
  if (date.getDay() === 0) {
    date.setDate(date.getDate() + 1)
  }
  return formatDateText(date)
}

function mondayOf(dateText) {
  const date = parseDateText(dateText || todayText())
  const day = date.getDay()
  const offset = day === 0 ? -6 : 1 - day
  date.setDate(date.getDate() + offset)
  return formatDateText(date)
}

function addDays(dateText, delta) {
  const date = parseDateText(dateText)
  date.setDate(date.getDate() + Number(delta || 0))
  return formatDateText(date)
}

function weekdayText(day) {
  return ['', '周一', '周二', '周三', '周四', '周五', '周六', '周日'][Number(day) || 0] || '-'
}

function normalizeText(value) {
  return String(value || '').trim()
}

function splitImportLine(line) {
  if (line.includes('\t')) {
    return line.split('\t').map((item) => normalizeText(item))
  }
  return line.split(/,|，/).map((item) => normalizeText(item))
}

function buildPasteImportItem(parts, rowNo) {
  if (!Array.isArray(parts) || !parts.length) return { skip: true }
  const values = parts.slice()
  while (values.length < 9) values.push('')
  const firstCell = normalizeText(values[0])
  if (!firstCell || firstCell === '课程名' || firstCell === '课程名称') {
    return { skip: true }
  }
  const originalLength = parts.length
  let weekDay = ''
  let periodRange = ''
  let timeRange = ''
  let weekRange = ''
  let labName = ''
  let teacherName = ''
  let className = ''
  let note = ''
  if (originalLength >= 9) {
    weekDay = values[1]
    periodRange = values[2]
    timeRange = values[3]
    weekRange = values[4]
    labName = values[5]
    teacherName = values[6]
    className = values[7]
    note = values[8]
  } else {
    weekDay = values[1]
    periodRange = values[2]
    weekRange = values[3]
    labName = values[4]
    teacherName = values[5]
    className = values[6]
    note = values[7]
  }
  return {
    skip: false,
    item: {
      rowNo,
      courseName: firstCell,
      weekDay,
      periodRange,
      timeRange,
      weekRange,
      labName,
      teacherName,
      className,
      note,
      weekType: 'all'
    }
  }
}

function findLabMatch(item, labRows = []) {
  const labId = Number(item.labId || 0)
  const labName = normalizeText(item.labName)
  return labRows.find((lab) => {
    if (labId > 0 && Number(lab.id || 0) === labId) return true
    if (labName && normalizeText(lab.name) === labName) return true
    return false
  })
}

function validateImportItem(item, labRows = []) {
  const reasons = []
  if (!normalizeText(item.courseName)) reasons.push('缺少课程名')
  if (!normalizeText(item.weekDay)) reasons.push('缺少星期')
  if (!normalizeText(item.periodRange) && !normalizeText(item.timeRange)) reasons.push('缺少节次或时间段')
  if (!normalizeText(item.weekRange)) reasons.push('缺少周次')
  if (!normalizeText(item.labName) && Number(item.labId || 0) <= 0) {
    reasons.push('缺少实验室')
  } else if (Array.isArray(labRows) && labRows.length && !findLabMatch(item, labRows)) {
    reasons.push('实验室未匹配到系统数据')
  }
  return reasons
}

function parseImportItems(inputType, rawText, labRows = []) {
  const text = normalizeText(rawText)
  if (!text) {
    return { items: [], errors: [], parseError: '' }
  }
  if (inputType === 'json') {
    try {
      const parsed = JSON.parse(text)
      if (!Array.isArray(parsed)) {
        return { items: [], errors: [], parseError: 'JSON 必须是数组格式。' }
      }
      const items = []
      const errors = []
      parsed.forEach((item, index) => {
        const rowNo = Number(item?.rowNo || index + 1)
        const normalizedItem = { weekType: 'all', ...(item || {}), rowNo }
        const reasons = validateImportItem(normalizedItem, labRows)
        if (reasons.length) {
          errors.push({ rowNo, reason: reasons.join('；') })
          return
        }
        items.push(normalizedItem)
      })
      return { items, errors, parseError: '' }
    } catch (error) {
      return { items: [], errors: [], parseError: error?.message || 'JSON 解析失败，请检查格式。' }
    }
  }

  const items = []
  const errors = []
  text
    .split(/\r?\n/)
    .map((line) => normalizeText(line))
    .filter(Boolean)
    .forEach((line, index) => {
      const rowNo = index + 1
      const built = buildPasteImportItem(splitImportLine(line), rowNo)
      if (built.skip) return
      const reasons = validateImportItem(built.item, labRows)
      if (reasons.length) {
        errors.push({ rowNo, reason: reasons.join('；') })
        return
      }
      items.push(built.item)
    })
  return { items, errors, parseError: '' }
}

function overviewPreviewText(list = []) {
  const names = list
    .map((item) => normalizeText(item.courseName))
    .filter(Boolean)
    .slice(0, 2)
  if (!names.length) return '-'
  if (list.length > 2) return `${names.join(' / ')} 等`
  return names.join(' / ')
}

function buildRecordParams() {
  return {
    page: recordPage.value,
    pageSize: recordPageSize.value,
    startDate: recordFilters.startDate,
    endDate: recordFilters.endDate,
    remindStatus: recordFilters.remindStatus,
    doorStatus: recordFilters.doorStatus
  }
}

function resetImportForm() {
  editingTemplateId.value = 0
  importForm.termName = ''
  importForm.semesterStartDate = todayText()
  importForm.semesterWeeks = 20
  importForm.reminderLeadMinutes = 20
  importForm.sourceType = 'manual'
  importForm.activate = true
  importForm.mode = 'replace'
  importForm.inputType = 'paste'
  importForm.rawText = ''
}

async function loadTemplates() {
  const response = await getScheduleTemplates()
  templates.value = Array.isArray(response.data?.data) ? response.data.data : []
}

async function loadTodayReminders() {
  const response = await getDoorRemindersToday()
  todayList.value = Array.isArray(response.data?.data?.list) ? response.data.data.list : []
}

async function loadWeekOverview() {
  const response = await getDoorRemindersWeek({
    date: mondayOf(workweekAnchor(labQuery.date || todayText()))
  })
  weekList.value = Array.isArray(response.data?.data?.list) ? response.data.data.list : []
}

async function loadLabs() {
  const response = await getLabs()
  labs.value = Array.isArray(response.data?.data) ? response.data.data : []
  if (!labQuery.labId && labs.value.length) {
    const routeLabId = Number(route.query.labId || 0)
    labQuery.labId = routeLabId || Number(labs.value[0].id || 0)
  }
}

async function loadLabSchedule() {
  if (!labQuery.labId) return
  if (labQuery.mode === 'day') {
    const response = await getLabScheduleDay(labQuery.labId, {
      date: labQuery.date
    })
    daySchedule.value = Array.isArray(response.data?.data?.list) ? response.data.data.list : []
    weekSchedule.value = []
    return
  }
  const response = await getLabScheduleWeek(labQuery.labId, {
    date: workweekAnchor(labQuery.date)
  })
  weekSchedule.value = Array.isArray(response.data?.data?.days) ? response.data.data.days : []
  daySchedule.value = []
}

async function loadReminderRecords() {
  const response = await getDoorReminderRecords(buildRecordParams())
  reminderRecords.value = Array.isArray(response.data?.data) ? response.data.data : []
  recordTotal.value = Number(response.data?.meta?.total || 0)
}

async function reloadAll() {
  pageLoading.value = true
  try {
    await Promise.all([loadTemplates(), loadTodayReminders(), loadLabs(), loadReminderRecords()])
    if (!labQuery.date) {
      labQuery.date = String(route.query.date || todayText())
    }
    if (!route.query.date) {
      labQuery.date = workweekAnchor(labQuery.date)
    }
    await loadWeekOverview()
    await loadLabSchedule()
  } finally {
    pageLoading.value = false
  }
}

async function activateTemplate(item) {
  await activateScheduleTemplate(item.id)
  ElMessage.success('模板已启用')
  await reloadAll()
}

async function removeTemplate(item) {
  await deleteScheduleTemplate(item.id)
  ElMessage.success('模板已删除')
  await reloadAll()
}

async function confirmOpen(item) {
  await confirmDoorReminderOpen(item.id, {})
  ElMessage.success('已确认开门')
  await Promise.all([loadTodayReminders(), loadReminderRecords()])
}

async function ignoreReminder(item) {
  await ignoreDoorReminder(item.id, {})
  ElMessage.success('已忽略提醒')
  await Promise.all([loadTodayReminders(), loadReminderRecords()])
}

function openCreateImport() {
  resetImportForm()
  importVisible.value = true
}

async function openEditImport(item) {
  resetImportForm()
  editingTemplateId.value = Number(item.id || 0)
  const response = await getScheduleTemplateDetail(item.id)
  const template = response.data?.data?.template || {}
  const items = Array.isArray(response.data?.data?.items) ? response.data.data.items : []
  importForm.termName = template.termName || ''
  importForm.semesterStartDate = template.semesterStartDate || todayText()
  importForm.semesterWeeks = Number(template.semesterWeeks || 20)
  importForm.reminderLeadMinutes = Number(template.reminderLeadMinutes || 20)
  importForm.sourceType = template.sourceType || 'manual'
  importForm.activate = template.status === 'active'
  importForm.inputType = 'json'
  importForm.rawText = JSON.stringify(items, null, 2)
  importVisible.value = true
}

function openOverviewCell(row, day) {
  const list = Array.isArray(row?.cells?.[day.weekDay]) ? row.cells[day.weekDay] : []
  if (!list.length) return
  overviewDetail.labId = Number(row.labId || 0)
  overviewDetail.labName = row.labName || '-'
  overviewDetail.date = day.date || ''
  overviewDetail.dayLabel = day.label || weekdayText(day.weekDay)
  overviewDetail.list = list.slice()
  overviewDetailVisible.value = true
}

async function openOverviewInSchedule() {
  if (!overviewDetail.labId) {
    overviewDetailVisible.value = false
    return
  }
  labQuery.labId = overviewDetail.labId
  labQuery.date = overviewDetail.date || todayText()
  labQuery.mode = 'day'
  activeTab.value = 'schedule'
  overviewDetailVisible.value = false
  await loadLabSchedule()
}

async function submitImport() {
  if (!importForm.semesterStartDate) {
    ElMessage.warning('请选择开学日期')
    return
  }
  const result = parsedImportResult.value
  if (result.parseError) {
    ElMessage.error(result.parseError)
    return
  }
  if (result.errors.length) {
    ElMessage.warning(`发现 ${result.errors.length} 条异常数据，请先修正后再导入`)
    return
  }
  const items = result.items
  if (!items.length) {
    ElMessage.warning('请先提供课表数据')
    return
  }
  importing.value = true
  try {
    const response = await importSchedule({
      template: {
        id: editingTemplateId.value || undefined,
        termName: importForm.termName,
        semesterStartDate: importForm.semesterStartDate,
        semesterWeeks: importForm.semesterWeeks,
        reminderLeadMinutes: importForm.reminderLeadMinutes,
        sourceType: importForm.sourceType
      },
      mode: importForm.mode,
      activate: importForm.activate,
      items
    })
    const data = response.data?.data || {}
    const backendErrors = Array.isArray(data.errors) ? data.errors : []
    ElMessage.success(`导入完成，成功写入 ${data.inserted || 0} 条`)
    if (backendErrors.length) {
      await ElMessageBox.alert(
        backendErrors
          .slice(0, 8)
          .map((item) => `第 ${item.row || item.rowNo || '-'} 行：${item.reason || '格式异常'}`)
          .join('<br/>'),
        '部分记录未导入',
        {
          dangerouslyUseHTMLString: true,
          type: 'warning'
        }
      )
    }
    importVisible.value = false
    await reloadAll()
  } catch (error) {
    ElMessage.error('导入失败，请检查数据格式')
  } finally {
    importing.value = false
  }
}

function queryRecords() {
  recordPage.value = 1
  loadReminderRecords()
}

function handleRecordPageSizeChange(size) {
  recordPageSize.value = size
  recordPage.value = 1
  loadReminderRecords()
}

onMounted(() => {
  if (!labQuery.date) {
    labQuery.date = String(route.query.date || todayText())
  }
  if (!route.query.date) {
    labQuery.date = workweekAnchor(labQuery.date)
  }
  reloadAll()
})
</script>

<style scoped lang="scss">
.schedule-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.hero-card,
.metric-card,
.panel-card,
.template-card,
.week-card {
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
    radial-gradient(circle at top right, rgba(59, 130, 246, 0.16), transparent 30%),
    linear-gradient(135deg, #fbfdff 0%, #eff6ff 100%);
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

.hero-card p,
.hero-meta,
.metric-sub,
.metric-label,
.template-card p,
.panel-head span,
.muted-copy,
.hint-copy {
  color: var(--app-muted);
}

.hero-meta,
.hero-actions,
.template-actions,
.pager-row,
.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
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
.drawer-grid,
.day-list {
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

.metric-value.warning {
  color: #b45309;
}

.panel-card,
.template-card,
.week-card {
  padding: 24px;
}

.template-list,
.week-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.import-preview,
.import-error-list,
.overview-detail-head {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.template-head,
.panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.query-card {
  margin-bottom: 20px;
  padding: 18px;
  border-radius: 20px;
  background: #f8fafc;
}

.day-list {
  grid-template-columns: 1fr;
  margin-top: 12px;
}

.day-item {
  display: grid;
  grid-template-columns: 140px 1fr 160px;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid #e2e8f0;
}

.overview-table {
  overflow-x: auto;
}

.overview-row {
  display: grid;
  grid-template-columns: 180px repeat(5, minmax(140px, 1fr));
}

.overview-row span,
.overview-row button {
  padding: 12px;
  border-right: 1px solid #e2e8f0;
  border-bottom: 1px solid #e2e8f0;
  background: #fff;
  font-size: 13px;
}

.overview-row--head span,
.overview-row--head button {
  background: #f8fafc;
  font-weight: 700;
}

.overview-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
  white-space: normal;
}

.overview-cell small {
  color: var(--app-muted);
}

.overview-cell--button {
  appearance: none;
  border: none;
  width: 100%;
  text-align: left;
  align-items: flex-start;
  justify-content: center;
  cursor: default;
}

.overview-cell--interactive {
  cursor: pointer;
  background: linear-gradient(180deg, rgba(239, 246, 255, 0.7), rgba(255, 255, 255, 0.96));
}

.overview-cell--interactive:hover {
  background: linear-gradient(180deg, rgba(219, 234, 254, 0.95), rgba(239, 246, 255, 0.96));
}

.overview-cell--empty {
  color: var(--app-muted);
}

.overview-hint {
  color: #2563eb;
}

.drawer-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.pager-row {
  margin-top: 18px;
  justify-content: flex-end;
}

@media (max-width: 1200px) {
  .metric-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .drawer-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .hero-card,
  .panel-head,
  .template-head {
    flex-direction: column;
    align-items: flex-start;
  }

  .metric-grid {
    grid-template-columns: 1fr;
  }

  .day-item {
    grid-template-columns: 1fr;
  }
}
</style>

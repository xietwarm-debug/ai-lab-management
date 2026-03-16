<template>
  <view class="container boardPage">
    <view class="stack">
      <view class="card heroCard">
        <view class="rowBetween heroTop">
          <view>
            <view class="title">预约排班与冲突看板</view>
            <view class="subtitle">按全局资源占用视角处理审批</view>
          </view>
          <button class="btnSecondary miniBtn" size="mini" :loading="loading" @click="refreshBoard(true)">刷新</button>
        </view>
        <view class="heroMeta muted">范围：{{ rangeStart || "-" }} 至 {{ rangeEnd || "-" }}</view>
        <view class="heroMeta muted">预约 {{ reservationRows.length }} 条 · 待审批 {{ pendingRows.length }} 条</view>
      </view>

      <view class="card">
        <view class="rowBetween sectionHeader">
          <view class="cardTitle">筛选与视图</view>
          <button class="btnPrimary miniBtn" size="mini" @click="toggleRecommendMode">
            {{ recommendMode ? "返回全局看板" : "空闲实验室推荐" }}
          </button>
        </view>

        <view class="label">查看范围</view>
        <view class="chipRow">
          <view
            v-for="item in viewModes"
            :key="item.value"
            class="chip"
            :class="{ chipOn: viewMode === item.value }"
            @click="setViewMode(item.value)"
          >
            {{ item.label }}
          </view>
        </view>

        <view class="grid2">
          <view>
            <view class="label">锚点日期</view>
            <picker mode="date" :value="anchorDate" @change="onAnchorDateChange">
              <view class="pickerField">{{ anchorDate || "请选择日期" }}</view>
            </picker>
          </view>
          <view>
            <view class="label">实验室筛选</view>
            <picker :range="labPickerOptions" range-key="labName" :value="labFilterIndex" @change="onLabFilterChange">
              <view class="pickerField">{{ currentLabFilterLabel }}</view>
            </picker>
          </view>
        </view>
      </view>

      <view class="card" v-if="recommendMode">
        <view class="rowBetween sectionHeader">
          <view>
            <view class="cardTitle">空闲实验室推荐</view>
            <view class="muted">一键切换后的空闲资源视角</view>
          </view>
        </view>

        <view class="grid2">
          <view>
            <view class="label">推荐日期</view>
            <picker mode="date" :value="recommendDate" @change="onRecommendDateChange">
              <view class="pickerField">{{ recommendDate || "请选择日期" }}</view>
            </picker>
          </view>
          <view>
            <view class="label">推荐时段</view>
            <picker :range="recommendSlotOptions" :value="recommendSlotPickerValue" @change="onRecommendSlotChange">
              <view class="pickerField">{{ recommendSlot || "请选择时段" }}</view>
            </picker>
          </view>
        </view>

        <view class="recommendList" v-if="recommendRows.length > 0">
          <view class="pendingItem" v-for="(item, idx) in recommendRows" :key="`recommend-${item.labName}`">
            <view class="rowBetween">
              <view class="pendingLab">{{ idx + 1 }}. {{ item.labName }}</view>
              <view class="statusTag success">空闲</view>
            </view>
            <view class="pendingMeta">当前范围占用率：{{ item.utilPercent }}%</view>
            <view class="pendingMeta">时段容量：{{ item.capacitySlots }} 段 · 已占用 {{ item.bookedSlots }} 段</view>
            <view class="pendingMeta">实验室容量：{{ item.capacity > 0 ? `${item.capacity} 人` : "未设置" }}</view>
            <view class="pendingActions">
              <button class="btnSecondary miniBtn" size="mini" @click="goLabCalendar(item.labName)">看日历</button>
              <button class="btnPrimary miniBtn" size="mini" @click="goReserve(item.labName)">立即预约</button>
            </view>
          </view>
        </view>
        <view class="empty" v-else>该日期和时段暂无可推荐实验室</view>
      </view>

      <view class="card matrixCard">
        <view class="rowBetween sectionHeader">
          <view class="cardTitle">预约排班矩阵（{{ modeText }}）</view>
          <view class="muted">{{ matrixRows.length }} 个实验室 · {{ dateHeaders.length }} 天</view>
        </view>
        <scroll-view scroll-x class="matrixScroll" v-if="matrixRows.length > 0 && dateHeaders.length > 0">
          <view class="matrixTable">
            <view class="matrixRow matrixHeader">
              <view class="matrixCell stickyCol">实验室</view>
              <view class="matrixCell dayHead" v-for="dateText in dateHeaders" :key="`head-${dateText}`">
                <view>{{ shortDate(dateText) }}</view>
                <view class="tiny muted">{{ weekdayText(dateText) }}</view>
              </view>
            </view>
            <view class="matrixRow" v-for="row in matrixRows" :key="`row-${row.labName}`">
              <view class="matrixCell stickyCol labCell">
                <view class="lineClampOne">{{ row.labName }}</view>
                <view class="tiny muted">占用 {{ row.utilPercent }}% · 待审 {{ row.pendingCount }}</view>
              </view>
              <view
                class="matrixCell dayCell"
                v-for="cell in row.days"
                :key="`${row.labName}-${cell.date}`"
                :class="cellTone(cell)"
              >
                <view class="cellMain">{{ cell.bookedSlots }}/{{ cell.capacitySlots }}</view>
                <view class="cellSub" v-if="cell.pendingCount > 0">待{{ cell.pendingCount }}</view>
                <view class="cellSub muted" v-else>空闲</view>
              </view>
            </view>
          </view>
        </scroll-view>
        <view class="empty" v-else>当前条件下暂无排班数据</view>
      </view>

      <view class="card">
        <view class="rowBetween sectionHeader">
          <view class="cardTitle">按实验室占用率</view>
          <view class="muted">当前 {{ modeText }} 范围</view>
        </view>
        <view class="utilList" v-if="labUtilRows.length > 0">
          <view class="utilItem" v-for="item in labUtilRows" :key="`util-${item.labName}`">
            <view class="rowBetween">
              <view class="utilName">{{ item.labName }}</view>
              <view class="utilValue">{{ item.bookedSlots }}/{{ item.capacitySlots }} · {{ item.utilPercent }}%</view>
            </view>
            <view class="utilTrack">
              <view class="utilFill" :class="item.utilTone" :style="{ width: `${item.barPercent}%` }"></view>
            </view>
            <view class="tiny muted">待审批 {{ item.pendingCount }} 条 · 已通过 {{ item.approvedCount }} 条</view>
          </view>
        </view>
        <view class="empty" v-else>暂无占用率数据</view>
      </view>

      <view class="card">
        <view class="rowBetween sectionHeader">
          <view class="cardTitle">冲突高发时段热力图</view>
          <view class="muted">统计维度：待审批 + 已通过</view>
        </view>
        <view class="legendRow">
          <view class="legendItem"><text class="legendDot level0"></text><text>低</text></view>
          <view class="legendItem"><text class="legendDot level2"></text><text>中</text></view>
          <view class="legendItem"><text class="legendDot level4"></text><text>高</text></view>
        </view>
        <scroll-view scroll-x class="heatmapScroll" v-if="heatmap.rows.length > 0 && heatmap.slots.length > 0">
          <view class="heatTable">
            <view class="heatRow heatHeader">
              <view class="heatCell dayName">星期\\时段</view>
              <view class="heatCell slotName" v-for="slot in heatmap.slots" :key="`slot-head-${slot}`">
                {{ shortSlot(slot) }}
              </view>
            </view>
            <view class="heatRow" v-for="row in heatmap.rows" :key="`heat-${row.weekday}`">
              <view class="heatCell dayName">{{ row.label }}</view>
              <view
                class="heatCell heatData"
                v-for="cell in row.cells"
                :key="`heat-${row.weekday}-${cell.slot}`"
                :class="heatTone(cell.count)"
              >
                <view class="heatMain">{{ cell.count }}</view>
                <view class="heatSub" v-if="cell.pending > 0">待{{ cell.pending }}</view>
              </view>
            </view>
          </view>
        </scroll-view>
        <view class="empty" v-else>暂无热力图数据</view>
      </view>

      <view class="card">
        <view class="rowBetween sectionHeader">
          <view>
            <view class="cardTitle">待审批预约集中面板</view>
            <view class="muted">按日期和实验室聚合展示</view>
          </view>
          <button class="btnPrimary miniBtn" size="mini" @click="goApprove">去审批</button>
        </view>

        <view class="summaryWrap" v-if="pendingByDateTop.length > 0">
          <view class="summaryTitle">按日期</view>
          <view class="summaryRow">
            <view class="summaryChip" v-for="item in pendingByDateTop" :key="`date-${item.key}`">
              {{ item.key }} · {{ item.count }}
            </view>
          </view>
        </view>

        <view class="summaryWrap" v-if="pendingByLabTop.length > 0">
          <view class="summaryTitle">按实验室</view>
          <view class="summaryRow">
            <view class="summaryChip" v-for="item in pendingByLabTop" :key="`lab-${item.key}`">
              {{ item.key }} · {{ item.count }}
            </view>
          </view>
        </view>

        <view class="pendingList" v-if="pendingPanelRows.length > 0">
          <view class="pendingItem" v-for="row in pendingPanelRows" :key="`pending-${row.id}`">
            <view class="rowBetween">
              <view class="pendingLab">{{ row.labName }}</view>
              <view class="statusTag warning">待审批</view>
            </view>
            <view class="pendingMeta">预约人：{{ row.user || "-" }}</view>
            <view class="pendingMeta">时间：{{ row.date }} {{ row.time }}</view>
            <view class="pendingMeta lineClamp" v-if="row.reason">用途：{{ row.reason }}</view>
            <view class="pendingActions">
              <button class="btnSecondary miniBtn" size="mini" @click="goApproveDetail(row.id)">详情</button>
              <button class="btnPrimary miniBtn" size="mini" @click="goApproveDetail(row.id)">审批</button>
            </view>
          </view>
        </view>
        <view class="empty" v-else>当前范围没有待审批预约</view>
      </view>
    </view>
  </view>
</template>

<script>
import { BASE_URL } from "@/common/api.js"

const VIEW_MODES = [
  { value: "day", label: "按天" },
  { value: "week", label: "按周" },
  { value: "month", label: "按月" }
]

const WEEKDAY_LABELS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

const FALLBACK_SLOTS = [
  "08:00-08:40",
  "08:45-09:35",
  "10:25-11:05",
  "11:10-11:50",
  "14:30-15:10",
  "15:15-15:55",
  "16:05-16:45",
  "16:50-17:30",
  "19:00-19:40",
  "19:45-20:25"
]

function toInt(value) {
  const n = Number(value)
  return Number.isFinite(n) ? Math.max(0, Math.round(n)) : 0
}

function pad2(n) {
  const num = Number(n)
  return num < 10 ? `0${num}` : `${num}`
}

function formatDate(dateObj) {
  if (!(dateObj instanceof Date)) return ""
  return `${dateObj.getFullYear()}-${pad2(dateObj.getMonth() + 1)}-${pad2(dateObj.getDate())}`
}

function todayText() {
  return formatDate(new Date())
}

function parseDate(text) {
  const src = String(text || "").trim()
  const m = src.match(/^(\d{4})-(\d{2})-(\d{2})$/)
  if (!m) return null
  const y = Number(m[1])
  const mo = Number(m[2])
  const d = Number(m[3])
  if (!Number.isFinite(y) || !Number.isFinite(mo) || !Number.isFinite(d)) return null
  const parsed = new Date(y, mo - 1, d)
  if (parsed.getFullYear() !== y || parsed.getMonth() !== mo - 1 || parsed.getDate() !== d) return null
  return parsed
}

function addDays(dateObj, days) {
  const base = new Date(dateObj.getFullYear(), dateObj.getMonth(), dateObj.getDate())
  base.setDate(base.getDate() + Number(days || 0))
  return base
}

function buildDateRange(anchorText, mode) {
  const anchor = parseDate(anchorText) || parseDate(todayText()) || new Date()
  let start = new Date(anchor.getFullYear(), anchor.getMonth(), anchor.getDate())
  let end = new Date(anchor.getFullYear(), anchor.getMonth(), anchor.getDate())

  if (mode === "week") {
    const weekOffset = (start.getDay() + 6) % 7
    start = addDays(start, -weekOffset)
    end = addDays(start, 6)
  } else if (mode === "month") {
    start = new Date(start.getFullYear(), start.getMonth(), 1)
    end = new Date(start.getFullYear(), start.getMonth() + 1, 0)
  }

  const dates = []
  let cursor = new Date(start.getFullYear(), start.getMonth(), start.getDate())
  let guard = 0
  while (cursor.getTime() <= end.getTime() && guard < 62) {
    dates.push(formatDate(cursor))
    cursor = addDays(cursor, 1)
    guard += 1
  }

  return {
    start: formatDate(start),
    end: formatDate(end),
    dates
  }
}

function normalizeSlot(slotText) {
  return String(slotText || "").replace(/\s+/g, "").trim()
}

function splitSlotText(text) {
  return String(text || "")
    .split(/[,\n，]/)
    .map((x) => normalizeSlot(x))
    .filter(Boolean)
}

function slotStartMinutes(slotText) {
  const slot = normalizeSlot(slotText)
  const m = slot.match(/^(\d{1,2}):(\d{2})/)
  if (!m) return 10 * 24 * 60
  const h = Number(m[1])
  const mm = Number(m[2])
  if (!Number.isFinite(h) || !Number.isFinite(mm)) return 10 * 24 * 60
  return h * 60 + mm
}

function sortSlots(list) {
  const unique = []
  const seen = new Set()
  ;(list || []).forEach((item) => {
    const slot = normalizeSlot(item)
    if (!slot || seen.has(slot)) return
    seen.add(slot)
    unique.push(slot)
  })
  unique.sort((a, b) => {
    const am = slotStartMinutes(a)
    const bm = slotStartMinutes(b)
    if (am !== bm) return am - bm
    return a.localeCompare(b)
  })
  return unique
}

function parseReservationSlots(rawTime) {
  return sortSlots(splitSlotText(rawTime))
}

function parseListPayload(payload) {
  if (Array.isArray(payload)) return payload
  if (payload && Array.isArray(payload.data)) return payload.data
  return []
}

function parseMetaPayload(payload) {
  return payload && payload.meta && typeof payload.meta === "object" ? payload.meta : {}
}

function createRulePayload(rawData) {
  const src = rawData || {}
  const data = src && src.data && typeof src.data === "object" ? src.data : src
  const slots = sortSlots(Array.isArray(data.slots) ? data.slots : [])
  const disabledDates = new Set(
    (Array.isArray(data.disabledDates) ? data.disabledDates : [])
      .map((x) => String(x || "").trim())
      .filter(Boolean)
  )
  const blackoutByDate = {}
  ;(Array.isArray(data.blackoutSlots) ? data.blackoutSlots : []).forEach((item) => {
    const dateText = String((item && item.date) || "").trim()
    if (!dateText) return
    const slotList = sortSlots(Array.isArray(item.slots) ? item.slots : splitSlotText(item.slots))
    if (slotList.length === 0) return
    if (!blackoutByDate[dateText]) blackoutByDate[dateText] = new Set()
    slotList.forEach((slot) => blackoutByDate[dateText].add(slot))
  })
  return {
    slots: slots.length > 0 ? slots : FALLBACK_SLOTS.slice(),
    disabledDates,
    blackoutByDate,
    minDate: String(data.minDate || ""),
    maxDate: String(data.maxDate || "")
  }
}

function createFallbackRule() {
  return {
    slots: FALLBACK_SLOTS.slice(),
    disabledDates: new Set(),
    blackoutByDate: {},
    minDate: "",
    maxDate: ""
  }
}

function toPercent(numerator, denominator) {
  const num = Number(numerator || 0)
  const den = Number(denominator || 0)
  if (!Number.isFinite(num) || !Number.isFinite(den) || den <= 0) return 0
  const pct = (num / den) * 100
  if (!Number.isFinite(pct)) return 0
  return Math.max(0, Math.round(pct))
}

function weekdayIndex(dateText) {
  const dt = parseDate(dateText)
  if (!dt) return 0
  return (dt.getDay() + 6) % 7
}

function sortByCountDesc(items) {
  const rows = (items || []).slice()
  rows.sort((a, b) => {
    const cntA = toInt(a.count)
    const cntB = toInt(b.count)
    if (cntA !== cntB) return cntB - cntA
    return String(a.key || "").localeCompare(String(b.key || ""))
  })
  return rows
}

export default {
  data() {
    return {
      loading: false,
      operator: "",
      viewModes: VIEW_MODES,
      viewMode: "week",
      anchorDate: todayText(),
      labFilterIndex: 0,
      labs: [],
      globalRule: createFallbackRule(),
      labRuleMap: {},
      rangeStart: "",
      rangeEnd: "",
      dateHeaders: [],
      reservationRows: [],
      pendingRows: [],
      matrixRows: [],
      labUtilRows: [],
      heatmap: {
        slots: [],
        rows: [],
        maxCount: 0
      },
      pendingByDateTop: [],
      pendingByLabTop: [],
      pendingPanelRows: [],
      slotBusyIndex: {},
      recommendMode: false,
      recommendDate: todayText(),
      recommendSlotOptions: FALLBACK_SLOTS.slice(),
      recommendSlot: "",
      recommendRows: []
    }
  },
  computed: {
    modeText() {
      const row = this.viewModes.find((x) => x.value === this.viewMode)
      return row ? row.label : "按周"
    },
    labPickerOptions() {
      const rows = [{ labName: "全部实验室" }]
      this.labs.forEach((lab) => {
        rows.push({ labName: String(lab.name || "") })
      })
      return rows
    },
    currentLabFilterLabel() {
      const row = this.labPickerOptions[this.labFilterIndex]
      return row ? row.labName : "全部实验室"
    },
    recommendSlotPickerValue() {
      const idx = this.recommendSlotOptions.indexOf(this.recommendSlot)
      return idx >= 0 ? idx : 0
    }
  },
  onShow() {
    const s = uni.getStorageSync("session")
    if (!s || s.role !== "admin") {
      uni.showToast({ title: "无权限", icon: "none" })
      uni.reLaunch({ url: "/pages/login/login" })
      return
    }
    this.operator = String(s.username || "")
    this.refreshBoard(true)
  },
  methods: {
    shortDate(dateText) {
      const text = String(dateText || "")
      if (!text) return "-"
      return text.length >= 10 ? text.slice(5) : text
    },
    weekdayText(dateText) {
      const idx = weekdayIndex(dateText)
      return WEEKDAY_LABELS[idx] || "-"
    },
    shortSlot(slot) {
      const text = String(slot || "")
      return text.length > 11 ? text.slice(0, 11) : text
    },
    setViewMode(mode) {
      if (!mode || mode === this.viewMode) return
      this.viewMode = mode
      this.refreshBoard(false)
    },
    onAnchorDateChange(e) {
      const nextDate = String((e && e.detail && e.detail.value) || "").trim()
      if (!nextDate) return
      this.anchorDate = nextDate
      this.recommendDate = nextDate
      this.refreshBoard(false)
    },
    onLabFilterChange(e) {
      const idx = Number(e && e.detail && e.detail.value)
      this.labFilterIndex = Number.isFinite(idx) ? Math.max(0, idx) : 0
      this.rebuildDerived()
    },
    onRecommendDateChange(e) {
      const nextDate = String((e && e.detail && e.detail.value) || "").trim()
      if (!nextDate) return
      this.recommendDate = nextDate
      this.rebuildRecommendations()
    },
    onRecommendSlotChange(e) {
      const idx = Number(e && e.detail && e.detail.value)
      if (!Number.isFinite(idx) || idx < 0 || idx >= this.recommendSlotOptions.length) return
      this.recommendSlot = this.recommendSlotOptions[idx] || ""
      this.rebuildRecommendations()
    },
    toggleRecommendMode() {
      this.recommendMode = !this.recommendMode
      if (this.recommendMode) {
        if (!this.recommendDate) this.recommendDate = this.anchorDate || todayText()
        if (!this.recommendSlot && this.recommendSlotOptions.length > 0) {
          this.recommendSlot = this.recommendSlotOptions[0]
        }
      }
      this.rebuildRecommendations()
    },
    getSelectedLabName() {
      if (this.labFilterIndex <= 0) return ""
      const row = this.labs[this.labFilterIndex - 1]
      return row ? String(row.name || "").trim() : ""
    },
    findLabMeta(labName) {
      const target = String(labName || "").trim()
      return this.labs.find((lab) => String(lab.name || "").trim() === target) || null
    },
    getRuleForLab(labName) {
      const key = String(labName || "").trim()
      if (key && this.labRuleMap[key]) return this.labRuleMap[key]
      return this.globalRule || createFallbackRule()
    },
    availableSlotsForDate(labName, dateText) {
      const rule = this.getRuleForLab(labName)
      if (!rule) return FALLBACK_SLOTS.slice()
      const dateKey = String(dateText || "").trim()
      if (dateKey && rule.disabledDates && rule.disabledDates.has(dateKey)) return []
      const slots = Array.isArray(rule.slots) && rule.slots.length > 0 ? rule.slots : FALLBACK_SLOTS
      const blackout = dateKey && rule.blackoutByDate ? rule.blackoutByDate[dateKey] : null
      if (!blackout || blackout.size <= 0) return slots.slice()
      return slots.filter((slot) => !blackout.has(slot))
    },
    async refreshBoard(reloadMeta) {
      if (this.loading) return
      this.loading = true
      try {
        if (reloadMeta) {
          await this.loadLabs()
          await this.loadGlobalRule()
          await this.loadLabRules()
        }
        const range = buildDateRange(this.anchorDate, this.viewMode)
        this.rangeStart = range.start
        this.rangeEnd = range.end
        this.dateHeaders = range.dates
        this.reservationRows = await this.loadReservationRows(range.start, range.end)
        this.rebuildDerived()
      } catch (e) {
        uni.showToast({ title: "数据加载失败", icon: "none" })
      } finally {
        this.loading = false
      }
    },
    async loadLabs() {
      const res = await uni.request({
        url: `${BASE_URL}/labs`,
        method: "GET"
      })
      const rows = parseListPayload(res && res.data)
      const normalized = []
      rows.forEach((item) => {
        const name = String((item && item.name) || "").trim()
        if (!name) return
        normalized.push({
          id: toInt(item.id),
          name,
          capacity: toInt(item.capacity)
        })
      })
      normalized.sort((a, b) => a.name.localeCompare(b.name))
      this.labs = normalized
      const maxIndex = this.labs.length
      if (this.labFilterIndex > maxIndex) this.labFilterIndex = 0
    },
    async loadGlobalRule() {
      try {
        const res = await uni.request({
          url: `${BASE_URL}/reservation-rules`,
          method: "GET"
        })
        const body = (res && res.data) || {}
        if (body.ok && body.data) {
          this.globalRule = createRulePayload(body.data)
          const slotOptions = sortSlots(this.globalRule.slots || FALLBACK_SLOTS)
          this.recommendSlotOptions = slotOptions.length > 0 ? slotOptions : FALLBACK_SLOTS.slice()
          if (!this.recommendSlot || !this.recommendSlotOptions.includes(this.recommendSlot)) {
            this.recommendSlot = this.recommendSlotOptions[0] || ""
          }
          if (!this.recommendDate) {
            this.recommendDate = this.globalRule.minDate || this.anchorDate || todayText()
          }
          return
        }
      } catch (e) {}
      this.globalRule = createFallbackRule()
      this.recommendSlotOptions = FALLBACK_SLOTS.slice()
      if (!this.recommendSlot) this.recommendSlot = this.recommendSlotOptions[0] || ""
    },
    async loadLabRules() {
      const map = {}
      if (!Array.isArray(this.labs) || this.labs.length === 0) {
        this.labRuleMap = map
        return
      }
      const requests = this.labs.map((lab) =>
        uni.request({
          url: `${BASE_URL}/reservation-rules?labName=${encodeURIComponent(lab.name)}`,
          method: "GET"
        })
      )
      const results = await Promise.allSettled(requests)
      results.forEach((result, idx) => {
        const lab = this.labs[idx]
        if (!lab || !lab.name) return
        if (result.status === "fulfilled") {
          const body = (result.value && result.value.data) || {}
          if (body.ok && body.data) {
            map[lab.name] = createRulePayload(body.data)
            return
          }
        }
        map[lab.name] = this.globalRule
      })
      this.labRuleMap = map
    },
    async loadReservationRows(dateFrom, dateTo) {
      const rows = []
      let page = 1
      const pageSize = 100
      let hasMore = true
      let guard = 0
      while (hasMore && guard < 80) {
        const qs = [
          `status=${encodeURIComponent("pending,approved")}`,
          `dateFrom=${encodeURIComponent(dateFrom)}`,
          `dateTo=${encodeURIComponent(dateTo)}`,
          `page=${page}`,
          `pageSize=${pageSize}`
        ].join("&")
        const res = await uni.request({
          url: `${BASE_URL}/reservations?${qs}`,
          method: "GET"
        })
        const payload = res && res.data
        if (Array.isArray(payload)) {
          rows.push(...payload)
          break
        }
        if (!payload || !payload.ok) {
          throw new Error((payload && payload.msg) || "failed")
        }
        const chunk = Array.isArray(payload.data) ? payload.data : []
        rows.push(...chunk)
        const meta = parseMetaPayload(payload)
        hasMore = !!meta.hasMore && chunk.length > 0
        page += 1
        guard += 1
      }
      return rows
    },
    rebuildDerived() {
      const selectedLabName = this.getSelectedLabName()
      const headerSet = new Set(this.dateHeaders || [])

      const labNameSet = new Set()
      this.labs.forEach((lab) => {
        const name = String(lab.name || "").trim()
        if (name) labNameSet.add(name)
      })
      ;(this.reservationRows || []).forEach((row) => {
        const name = String((row && row.labName) || "").trim()
        if (name) labNameSet.add(name)
      })

      let visibleLabNames = Array.from(labNameSet).filter(Boolean)
      visibleLabNames.sort((a, b) => a.localeCompare(b))
      if (selectedLabName) {
        visibleLabNames = visibleLabNames.filter((name) => name === selectedLabName)
      }
      const visibleSet = new Set(visibleLabNames)

      const dayLabMap = {}
      const slotBusyIndex = {}
      const heatCellMap = {}
      const pendingList = []
      const observedSlots = new Set(this.recommendSlotOptions || [])

      ;(this.reservationRows || []).forEach((raw) => {
        const status = String((raw && raw.status) || "").trim().toLowerCase()
        if (status !== "pending" && status !== "approved") return
        const labName = String((raw && raw.labName) || "").trim()
        const dateText = String((raw && raw.date) || "").trim()
        if (!labName || !dateText || !headerSet.has(dateText)) return
        if (visibleSet.size > 0 && !visibleSet.has(labName)) return

        const slots = parseReservationSlots(raw.time)
        if (slots.length === 0) return

        const mapKey = `${labName}@@${dateText}`
        if (!dayLabMap[mapKey]) {
          dayLabMap[mapKey] = {
            bookedSlots: 0,
            pendingCount: 0,
            approvedCount: 0,
            reservationCount: 0
          }
        }
        const bucket = dayLabMap[mapKey]
        bucket.bookedSlots += slots.length
        bucket.reservationCount += 1
        if (status === "pending") bucket.pendingCount += 1
        else bucket.approvedCount += 1

        const weekday = weekdayIndex(dateText)
        slots.forEach((slot) => {
          observedSlots.add(slot)
          const busyKey = `${dateText}@@${labName}@@${slot}`
          slotBusyIndex[busyKey] = toInt(slotBusyIndex[busyKey]) + 1
          const heatKey = `${weekday}@@${slot}`
          if (!heatCellMap[heatKey]) {
            heatCellMap[heatKey] = {
              count: 0,
              pending: 0
            }
          }
          heatCellMap[heatKey].count += 1
          if (status === "pending") heatCellMap[heatKey].pending += 1
        })

        if (status === "pending") {
          pendingList.push({
            id: toInt(raw.id),
            labName,
            user: String((raw && raw.user) || "").trim(),
            date: dateText,
            time: String((raw && raw.time) || "").trim(),
            reason: String((raw && raw.reason) || "").trim()
          })
        }
      })

      const matrixRows = []
      visibleLabNames.forEach((labName) => {
        const days = []
        let totalBookedSlots = 0
        let totalCapacitySlots = 0
        let pendingCount = 0
        let approvedCount = 0
        this.dateHeaders.forEach((dateText) => {
          const key = `${labName}@@${dateText}`
          const agg = dayLabMap[key] || {
            bookedSlots: 0,
            pendingCount: 0,
            approvedCount: 0,
            reservationCount: 0
          }
          const availableSlots = this.availableSlotsForDate(labName, dateText)
          const capacitySlots = toInt(availableSlots.length)
          const bookedSlots = toInt(agg.bookedSlots)
          const pending = toInt(agg.pendingCount)
          const approved = toInt(agg.approvedCount)
          const utilization = capacitySlots > 0 ? bookedSlots / capacitySlots : bookedSlots > 0 ? 1 : 0
          days.push({
            date: dateText,
            bookedSlots,
            capacitySlots,
            pendingCount: pending,
            approvedCount: approved,
            utilization
          })
          totalBookedSlots += bookedSlots
          totalCapacitySlots += capacitySlots
          pendingCount += pending
          approvedCount += approved
        })
        const utilPercent = toPercent(totalBookedSlots, totalCapacitySlots)
        matrixRows.push({
          labName,
          days,
          bookedSlots: totalBookedSlots,
          capacitySlots: totalCapacitySlots,
          pendingCount,
          approvedCount,
          utilPercent
        })
      })
      this.matrixRows = matrixRows

      const utilRows = matrixRows.map((row) => {
        const utilPercent = toPercent(row.bookedSlots, row.capacitySlots)
        let utilTone = "toneLow"
        if (utilPercent >= 100) utilTone = "toneOver"
        else if (utilPercent >= 75) utilTone = "toneHigh"
        else if (utilPercent >= 40) utilTone = "toneMid"
        return {
          labName: row.labName,
          bookedSlots: toInt(row.bookedSlots),
          capacitySlots: toInt(row.capacitySlots),
          pendingCount: toInt(row.pendingCount),
          approvedCount: toInt(row.approvedCount),
          utilPercent,
          utilTone,
          barPercent: Math.max(6, Math.min(100, utilPercent))
        }
      })
      utilRows.sort((a, b) => {
        if (a.utilPercent !== b.utilPercent) return b.utilPercent - a.utilPercent
        if (a.pendingCount !== b.pendingCount) return b.pendingCount - a.pendingCount
        return a.labName.localeCompare(b.labName)
      })
      this.labUtilRows = utilRows

      const heatSlots = sortSlots(Array.from(observedSlots))
      const heatRows = []
      let maxCount = 0
      WEEKDAY_LABELS.forEach((label, weekday) => {
        const cells = heatSlots.map((slot) => {
          const cell = heatCellMap[`${weekday}@@${slot}`] || { count: 0, pending: 0 }
          maxCount = Math.max(maxCount, toInt(cell.count))
          return {
            slot,
            count: toInt(cell.count),
            pending: toInt(cell.pending)
          }
        })
        heatRows.push({
          weekday,
          label,
          cells
        })
      })
      this.heatmap = {
        slots: heatSlots,
        rows: heatRows,
        maxCount
      }

      pendingList.sort((a, b) => {
        const dateCmp = String(a.date || "").localeCompare(String(b.date || ""))
        if (dateCmp !== 0) return dateCmp
        const aFirst = slotStartMinutes(parseReservationSlots(a.time)[0] || "")
        const bFirst = slotStartMinutes(parseReservationSlots(b.time)[0] || "")
        if (aFirst !== bFirst) return aFirst - bFirst
        return toInt(a.id) - toInt(b.id)
      })
      this.pendingRows = pendingList
      this.pendingPanelRows = pendingList.slice(0, 24)

      const pendingByDateMap = {}
      const pendingByLabMap = {}
      pendingList.forEach((row) => {
        const dateKey = String(row.date || "").trim()
        const labKey = String(row.labName || "").trim()
        if (dateKey) pendingByDateMap[dateKey] = toInt(pendingByDateMap[dateKey]) + 1
        if (labKey) pendingByLabMap[labKey] = toInt(pendingByLabMap[labKey]) + 1
      })
      this.pendingByDateTop = sortByCountDesc(
        Object.keys(pendingByDateMap).map((key) => ({ key, count: pendingByDateMap[key] }))
      ).slice(0, 6)
      this.pendingByLabTop = sortByCountDesc(
        Object.keys(pendingByLabMap).map((key) => ({ key, count: pendingByLabMap[key] }))
      ).slice(0, 6)

      this.slotBusyIndex = slotBusyIndex
      this.recommendSlotOptions = heatSlots.length > 0 ? heatSlots : FALLBACK_SLOTS.slice()
      if (!this.recommendSlot || !this.recommendSlotOptions.includes(this.recommendSlot)) {
        this.recommendSlot = this.recommendSlotOptions[0] || ""
      }
      if (!this.recommendDate) {
        this.recommendDate = this.anchorDate || todayText()
      }

      this.rebuildRecommendations()
    },
    rebuildRecommendations() {
      if (!this.recommendMode) {
        this.recommendRows = []
        return
      }
      const dateText = String(this.recommendDate || "").trim()
      const slotText = normalizeSlot(this.recommendSlot)
      if (!dateText || !slotText) {
        this.recommendRows = []
        return
      }
      const selectedLabName = this.getSelectedLabName()
      let candidateNames = this.matrixRows.map((row) => row.labName)
      if (selectedLabName) candidateNames = candidateNames.filter((x) => x === selectedLabName)

      const utilMap = {}
      this.labUtilRows.forEach((row) => {
        utilMap[row.labName] = row
      })

      const nextRows = []
      candidateNames.forEach((labName) => {
        const availableSlots = this.availableSlotsForDate(labName, dateText)
        if (availableSlots.length <= 0) return
        if (!availableSlots.includes(slotText)) return
        const busyKey = `${dateText}@@${labName}@@${slotText}`
        if (toInt(this.slotBusyIndex[busyKey]) > 0) return
        const util = utilMap[labName] || {
          bookedSlots: 0,
          capacitySlots: 0,
          pendingCount: 0
        }
        const labMeta = this.findLabMeta(labName)
        nextRows.push({
          labName,
          bookedSlots: toInt(util.bookedSlots),
          capacitySlots: toInt(util.capacitySlots),
          pendingCount: toInt(util.pendingCount),
          utilPercent: toPercent(util.bookedSlots, util.capacitySlots),
          capacity: labMeta ? toInt(labMeta.capacity) : 0
        })
      })

      nextRows.sort((a, b) => {
        if (a.utilPercent !== b.utilPercent) return a.utilPercent - b.utilPercent
        if (a.pendingCount !== b.pendingCount) return a.pendingCount - b.pendingCount
        if (a.capacity !== b.capacity) return b.capacity - a.capacity
        return a.labName.localeCompare(b.labName)
      })
      this.recommendRows = nextRows
    },
    cellTone(cell) {
      const booked = toInt(cell && cell.bookedSlots)
      const cap = toInt(cell && cell.capacitySlots)
      if (cap <= 0) return booked > 0 ? "toneOver" : "toneOff"
      const ratio = booked / cap
      if (ratio > 1) return "toneOver"
      if (ratio >= 0.75) return "toneHigh"
      if (ratio >= 0.4) return "toneMid"
      if (ratio > 0) return "toneLow"
      return "toneOff"
    },
    heatTone(count) {
      const max = toInt(this.heatmap && this.heatmap.maxCount)
      const value = toInt(count)
      if (value <= 0 || max <= 0) return "level0"
      const ratio = value / max
      if (ratio >= 0.85) return "level4"
      if (ratio >= 0.6) return "level3"
      if (ratio >= 0.35) return "level2"
      return "level1"
    },
    goApprove() {
      uni.navigateTo({ url: "/pages/admin/approve" })
    },
    goApproveDetail(id) {
      if (!id) return
      uni.navigateTo({ url: `/pages/admin/approve-detail?id=${id}` })
    },
    goLabCalendar(labName) {
      const name = encodeURIComponent(String(labName || ""))
      uni.navigateTo({ url: `/pages/labs/calendar?labName=${name}` })
    },
    goReserve(labName) {
      const name = encodeURIComponent(String(labName || ""))
      uni.navigateTo({ url: `/pages/reserve/reserve?labName=${name}` })
    }
  }
}
</script>

<style lang="scss">
.boardPage {
  padding-bottom: 20px;
}

.heroCard {
  border: 1px solid rgba(22, 119, 255, 0.2);
  background: linear-gradient(160deg, #ffffff 0%, #eef6ff 100%);
}

.heroTop {
  align-items: flex-start;
}

.heroMeta {
  margin-top: 4px;
}

.miniBtn {
  min-height: 30px;
  line-height: 30px;
  padding: 0 10px;
  border-radius: 9px;
  font-size: 12px;
}

.sectionHeader {
  align-items: center;
}

.chipRow {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.chip {
  min-width: 72px;
  padding: 7px 12px;
  border-radius: 999px;
  border: 1px solid #d4deee;
  background: #f8fbff;
  color: #334155;
  text-align: center;
  font-size: 12px;
}

.chipOn {
  border-color: #1677ff;
  color: #0f5bcc;
  background: #e8f1ff;
  box-shadow: 0 0 0 1px rgba(22, 119, 255, 0.12) inset;
}

.grid2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-top: 10px;
}

.pickerField {
  min-height: 36px;
  line-height: 36px;
  padding: 0 12px;
  border-radius: 10px;
  border: 1px solid #d8e2f0;
  background: #f8fbff;
  color: #334155;
  font-size: 13px;
}

.matrixCard {
  overflow: hidden;
}

.matrixScroll {
  width: 100%;
}

.matrixTable {
  min-width: 860px;
}

.matrixRow {
  display: flex;
  border-bottom: 1px solid #edf2fb;
}

.matrixHeader {
  background: #f4f8ff;
}

.matrixCell {
  min-height: 54px;
  padding: 8px;
  box-sizing: border-box;
  border-right: 1px solid #edf2fb;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 2px;
  font-size: 12px;
  color: #334155;
}

.stickyCol {
  width: 140px;
  position: sticky;
  left: 0;
  z-index: 2;
  background: #ffffff;
}

.matrixHeader .stickyCol {
  background: #f4f8ff;
}

.dayHead,
.dayCell {
  width: 96px;
  text-align: center;
  align-items: center;
}

.labCell {
  align-items: flex-start;
}

.cellMain {
  font-weight: 700;
  color: #0f172a;
}

.cellSub {
  font-size: 10px;
  color: #475569;
}

.toneOff {
  background: #f8fafc;
}

.toneLow {
  background: #eefbf2;
}

.toneMid {
  background: #fff9e8;
}

.toneHigh {
  background: #fff3e3;
}

.toneOver {
  background: #ffebee;
}

.utilList {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.utilItem {
  padding: 10px;
  border-radius: 10px;
  border: 1px solid #e3eaf4;
  background: #f9fbff;
}

.utilName {
  font-size: 14px;
  font-weight: 700;
  color: #1e293b;
}

.utilValue {
  font-size: 12px;
  color: #334155;
}

.utilTrack {
  margin-top: 8px;
  height: 8px;
  border-radius: 999px;
  background: #e6edf8;
  overflow: hidden;
}

.utilFill {
  height: 100%;
  border-radius: inherit;
}

.utilFill.toneLow {
  background: #16a34a;
}

.utilFill.toneMid {
  background: #d97706;
}

.utilFill.toneHigh {
  background: #ea580c;
}

.utilFill.toneOver {
  background: #dc2626;
}

.legendRow {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.legendItem {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #64748b;
}

.legendDot {
  width: 10px;
  height: 10px;
  border-radius: 3px;
  display: inline-block;
}

.heatmapScroll {
  width: 100%;
}

.heatTable {
  min-width: 920px;
}

.heatRow {
  display: flex;
}

.heatHeader {
  background: #f6f9ff;
}

.heatCell {
  min-height: 48px;
  border-right: 1px solid #e9eef7;
  border-bottom: 1px solid #e9eef7;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 1px;
  font-size: 11px;
  color: #334155;
  padding: 4px 2px;
  box-sizing: border-box;
}

.dayName {
  width: 88px;
  background: #f8fbff;
  font-weight: 700;
}

.slotName,
.heatData {
  width: 84px;
}

.heatMain {
  font-weight: 700;
}

.heatSub {
  font-size: 10px;
  color: #7c3aed;
}

.level0 {
  background: #f8fafc;
}

.level1 {
  background: #ecfdf3;
}

.level2 {
  background: #fff8e7;
}

.level3 {
  background: #ffeed9;
}

.level4 {
  background: #ffe4e6;
}

.summaryWrap {
  margin-bottom: 10px;
}

.summaryTitle {
  font-size: 12px;
  color: #64748b;
  margin-bottom: 6px;
}

.summaryRow {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.summaryChip {
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid #dbe4f2;
  background: #f7faff;
  font-size: 12px;
  color: #334155;
}

.pendingList,
.recommendList {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.pendingItem {
  border: 1px solid #e6edf8;
  border-radius: 12px;
  background: #f8fbff;
  padding: 10px;
}

.pendingLab {
  font-size: 14px;
  font-weight: 700;
  color: #1f2937;
}

.pendingMeta {
  font-size: 12px;
  color: #475569;
  margin-top: 4px;
}

.pendingActions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 8px;
}

.statusTag {
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  line-height: 18px;
}

.statusTag.warning {
  color: #92400e;
  background: #fef3c7;
}

.statusTag.success {
  color: #166534;
  background: #dcfce7;
}

.tiny {
  font-size: 10px;
}

.lineClampOne {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 640px) {
  .grid2 {
    grid-template-columns: 1fr;
  }
}
</style>

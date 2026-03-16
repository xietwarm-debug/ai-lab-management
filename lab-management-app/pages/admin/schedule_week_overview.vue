<template>
  <view class="container overviewPage">
    <view class="stack">
      <view class="card heroCard">
        <view class="title">当周课表总览</view>
        <view class="subtitle">按实验室查看周一到周五课程安排</view>
      </view>

      <view class="card">
        <view class="rowBetween">
          <view class="cardTitle">周范围</view>
          <view class="muted">{{ weekStartDate }} ~ {{ weekEndDate }}</view>
        </view>
        <view class="rowBetween mt8">
          <picker mode="date" :value="weekStartDate" @change="onPickDate">
            <view class="pickerLike">选择任意日期（自动定位到周一）</view>
          </picker>
        </view>
        <view class="chipRow">
          <view class="chip" @click="prevWeek">上一周</view>
          <view class="chip chipOn" @click="goCurrentWeek">本周</view>
          <view class="chip" @click="nextWeek">下一周</view>
          <view class="chip" @click="loadAll">刷新</view>
        </view>
      </view>

      <view class="card" v-if="loading">
        <view class="muted">加载中...</view>
      </view>

      <view class="card" v-else>
        <view class="rowBetween">
          <view class="cardTitle">课表网格</view>
          <view class="muted">实验室 x 周一到周五</view>
        </view>
        <view v-if="rows.length===0" class="empty">本周暂无排课</view>
        <scroll-view v-else class="tableWrap" scroll-x>
          <view class="table">
            <view class="tableRow headRow">
              <view class="cell labCell headCell">实验室</view>
              <view class="cell dayCell headCell" v-for="d in dayColumns" :key="d.weekDay">
                <view>{{ d.label }}</view>
                <view class="daySub">{{ d.mmdd }}</view>
              </view>
            </view>
            <view class="tableRow bodyRow" v-for="row in rows" :key="row.key">
              <view class="cell labCell labName">{{ row.labName || "-" }}</view>
              <view class="cell dayCell" v-for="d in dayColumns" :key="`${row.key}-${d.weekDay}`">
                <view v-if="!row.cells[d.weekDay] || row.cells[d.weekDay].length===0" class="cellEmpty">-</view>
                <view v-else class="courseList">
                  <view class="courseItem" v-for="item in row.cells[d.weekDay]" :key="item.key">
                    <view class="courseTitle">{{ item.periodText || "-" }} · {{ item.courseName || "-" }}</view>
                    <view class="courseMeta">{{ item.teacherName || "-" }} · {{ item.className || "-" }}</view>
                  </view>
                </view>
              </view>
            </view>
          </view>
        </scroll-view>
      </view>
    </view>
  </view>
</template>

<script>
import { adminGetDoorRemindersWeek, getApiListData, listLabs } from "@/common/api.js"

function ensureAdmin() {
  const s = uni.getStorageSync("session")
  return !!(s && s.role === "admin")
}

function todayText() {
  const d = new Date()
  const p = (n) => (n < 10 ? `0${n}` : `${n}`)
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

function parseDateText(text) {
  const raw = String(text || "").trim()
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(raw)
  if (!m) return null
  const y = Number(m[1])
  const mm = Number(m[2])
  const dd = Number(m[3])
  if (!y || !mm || !dd) return null
  return new Date(y, mm - 1, dd)
}

function formatDate(d) {
  if (!(d instanceof Date)) return ""
  const p = (n) => (n < 10 ? `0${n}` : `${n}`)
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

function addDays(dateText, delta) {
  const base = parseDateText(dateText) || new Date()
  base.setDate(base.getDate() + Number(delta || 0))
  return formatDate(base)
}

function mondayOf(dateText) {
  const d = parseDateText(dateText) || new Date()
  const day = d.getDay()
  const offset = day === 0 ? -6 : 1 - day
  d.setDate(d.getDate() + offset)
  return formatDate(d)
}

function dayColumnsFromMonday(mondayText) {
  const labels = ["周一", "周二", "周三", "周四", "周五"]
  const out = []
  for (let i = 0; i < 5; i += 1) {
    const date = addDays(mondayText, i)
    out.push({
      weekDay: i + 1,
      label: labels[i],
      date,
      mmdd: date ? date.slice(5) : ""
    })
  }
  return out
}

export default {
  data() {
    const monday = mondayOf(todayText())
    return {
      loading: false,
      weekStartDate: monday,
      weekEndDate: addDays(monday, 4),
      dayColumns: dayColumnsFromMonday(monday),
      rows: []
    }
  },
  onShow() {
    if (!ensureAdmin()) {
      uni.showToast({ title: "无权限", icon: "none" })
      uni.reLaunch({ url: "/pages/login/login" })
      return
    }
    this.loadAll()
  },
  methods: {
    buildRows(labs, reminderList) {
      const map = {}
      ;(Array.isArray(labs) ? labs : []).forEach((lab) => {
        const id = Number((lab || {}).id || 0)
        const name = String((lab || {}).name || "").trim()
        const key = id > 0 ? `id:${id}` : `name:${name}`
        if (!key) return
        map[key] = { key, labId: id, labName: name || `LAB-${id}`, cells: { 1: [], 2: [], 3: [], 4: [], 5: [] } }
      })
      ;(Array.isArray(reminderList) ? reminderList : []).forEach((item, idx) => {
        const weekDay = Number((item || {}).weekDay || 0)
        if (weekDay < 1 || weekDay > 5) return
        const id = Number((item || {}).labId || 0)
        const name = String((item || {}).labName || "").trim()
        const key = id > 0 ? `id:${id}` : `name:${name}`
        if (!map[key]) {
          map[key] = { key, labId: id, labName: name || `LAB-${id || "-"}`, cells: { 1: [], 2: [], 3: [], 4: [], 5: [] } }
        }
        map[key].cells[weekDay].push({
          key: `${Number((item || {}).id || 0)}-${idx}`,
          periodStart: Number((item || {}).periodStart || 0),
          periodEnd: Number((item || {}).periodEnd || 0),
          periodText: String((item || {}).periodText || "").trim(),
          courseName: String((item || {}).courseName || "").trim(),
          teacherName: String((item || {}).teacherName || "").trim(),
          className: String((item || {}).className || "").trim()
        })
      })
      Object.keys(map).forEach((k) => {
        for (let i = 1; i <= 5; i += 1) {
          map[k].cells[i].sort((a, b) => {
            const sa = Number(a.periodStart || 0)
            const sb = Number(b.periodStart || 0)
            if (sa !== sb) return sa - sb
            const ea = Number(a.periodEnd || 0)
            const eb = Number(b.periodEnd || 0)
            return ea - eb
          })
        }
      })
      return Object.values(map).sort((a, b) => String(a.labName || "").localeCompare(String(b.labName || ""), "zh-Hans-CN"))
    },
    async loadAll() {
      if (this.loading) return
      this.loading = true
      try {
        const monday = mondayOf(this.weekStartDate || todayText())
        const [weekRes, labsRes] = await Promise.all([adminGetDoorRemindersWeek(monday), listLabs({})])
        const weekPayload = (weekRes && weekRes.data) || {}
        const weekData = weekPayload.ok ? (weekPayload.data || {}) : {}
        const startDate = mondayOf(String(weekData.startDate || monday).trim() || monday)
        const list = Array.isArray(weekData.list) ? weekData.list : []
        const labs = getApiListData(labsRes && labsRes.data)
        this.weekStartDate = startDate
        this.weekEndDate = addDays(startDate, 4)
        this.dayColumns = dayColumnsFromMonday(startDate)
        this.rows = this.buildRows(labs, list)
      } catch (e) {
        this.rows = []
        uni.showToast({ title: "加载失败", icon: "none" })
      } finally {
        this.loading = false
      }
    },
    onPickDate(e) {
      this.weekStartDate = mondayOf((e && e.detail && e.detail.value) || todayText())
      this.loadAll()
    },
    prevWeek() {
      this.weekStartDate = addDays(this.weekStartDate, -7)
      this.loadAll()
    },
    nextWeek() {
      this.weekStartDate = addDays(this.weekStartDate, 7)
      this.loadAll()
    },
    goCurrentWeek() {
      this.weekStartDate = mondayOf(todayText())
      this.loadAll()
    }
  }
}
</script>

<style lang="scss">
.overviewPage {
  padding-bottom: 20px;
}

.heroCard {
  border: 1px solid rgba(22, 119, 255, 0.18);
  background: linear-gradient(160deg, #ffffff 0%, #f2f7ff 100%);
}

.mt8 {
  margin-top: 8px;
}

.pickerLike {
  min-height: 36px;
  border: 1px solid #d0d8e2;
  border-radius: 8px;
  padding: 8px 10px;
  box-sizing: border-box;
  font-size: 13px;
  color: #0f172a;
  background: #fff;
}

.chipRow {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.chipOn {
  border-color: #bfdbfe;
  background: #eaf3ff;
  color: #1d4ed8;
}

.tableWrap {
  margin-top: 8px;
  width: 100%;
  white-space: nowrap;
}

.table {
  min-width: 920px;
  border: 1px solid rgba(148, 163, 184, 0.3);
  border-radius: 10px;
  overflow: hidden;
}

.tableRow {
  display: grid;
  grid-template-columns: 130px repeat(5, minmax(0, 1fr));
}

.cell {
  border-right: 1px solid rgba(148, 163, 184, 0.24);
  border-bottom: 1px solid rgba(148, 163, 184, 0.24);
  padding: 8px;
  box-sizing: border-box;
  background: #fff;
}

.tableRow .cell:last-child {
  border-right: none;
}

.tableRow:last-child .cell {
  border-bottom: none;
}

.headCell {
  background: #f8fafc;
  font-weight: 700;
  color: #0f172a;
  font-size: 12px;
}

.daySub {
  margin-top: 2px;
  font-size: 11px;
  color: #64748b;
}

.labName {
  font-size: 12px;
  color: #0f172a;
  font-weight: 700;
}

.cellEmpty {
  font-size: 12px;
  color: #94a3b8;
}

.courseList {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.courseItem {
  border: 1px solid rgba(59, 130, 246, 0.22);
  background: #f8fbff;
  border-radius: 8px;
  padding: 6px;
}

.courseTitle {
  font-size: 12px;
  color: #0f172a;
  font-weight: 700;
}

.courseMeta {
  margin-top: 2px;
  font-size: 11px;
  color: #64748b;
}

.empty {
  margin-top: 8px;
  font-size: 12px;
  color: #94a3b8;
}
</style>

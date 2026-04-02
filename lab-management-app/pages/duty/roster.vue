<template>
  <view class="container dutyRosterPage">
    <view class="stack">
      <view class="card heroCard">
        <view class="rowBetween heroTop">
          <view>
            <view class="title">值班表</view>
            <view class="subtitle">查看本周值班安排，底部可直接联系应急联系人</view>
          </view>
          <button class="btnSecondary miniBtn" size="mini" :loading="loading" @click="loadAll">刷新</button>
        </view>
        <view class="heroMeta muted">当前账号：{{ operator || "-" }}</view>
        <view class="heroMeta muted">值班 {{ dutyRows.length }} 条 · 联系人 {{ contactRows.length }} 条</view>
      </view>

      <view class="card sectionCard">
        <view class="rowBetween sectionHeader">
          <view class="cardTitle">当日值班安排</view>
          <view class="muted">{{ weekLabel }}</view>
        </view>
        <view class="dateSelector">
          <view
            v-for="item in weekDateOptions"
            :key="item.date"
            class="dateChip"
            :class="{ dateChipOn: selectedDate === item.date }"
            @click="selectedDate = item.date"
          >
            <view class="dateChipWeek">{{ item.weekday }}</view>
            <view class="dateChipDay">{{ item.short }}</view>
          </view>
        </view>
        <view class="selectedDateBar">
          <view class="dayTitle">{{ selectedDateLabel }}</view>
          <view class="daySub muted">{{ selectedDutyRows.length }} 个时段</view>
        </view>
        <view v-if="selectedDutyRows.length === 0" class="empty">当天暂无值班安排</view>
        <view v-else class="slotList">
          <view class="slotCard" v-for="item in selectedDutyRows" :key="item.id || `${selectedDate}-${item.shiftName}`">
            <view class="rowBetween slotTop">
              <view class="slotName">{{ item.shiftName || "-" }}</view>
              <view class="statusTag" :class="dutyTone(item.status)">{{ dutyStatusText(item.status) }}</view>
            </view>
            <view class="slotLine">
              <text class="slotLabel">值班</text>
              <text class="slotValue">{{ item.assigneeName || "-" }}</text>
            </view>
            <view class="slotLine">
              <text class="slotLabel">电话</text>
              <text class="slotValue">{{ item.assigneePhone || "-" }}</text>
            </view>
            <view class="slotLine" v-if="item.backupName || item.backupPhone">
              <text class="slotLabel">备岗</text>
              <text class="slotValue">{{ item.backupName || "-" }} {{ item.backupPhone || "" }}</text>
            </view>
            <view class="slotNote" v-if="item.note">{{ item.note }}</view>
          </view>
        </view>
      </view>

      <view class="card sectionCard">
        <view class="rowBetween sectionHeader">
          <view class="cardTitle">应急联系人</view>
          <view class="muted">紧急情况可直接拨号</view>
        </view>
        <view v-if="contactRows.length === 0" class="empty">暂无应急联系人</view>
        <view v-else class="list">
          <view class="contactRow" v-for="item in contactRows" :key="item.id || `${item.name}-${item.phone}`">
            <view class="contactMain">
              <view class="contactTitle">{{ item.priorityNo || "-" }} · {{ item.name || "-" }}</view>
              <view class="contactMeta">{{ item.roleName || "应急联系人" }}</view>
              <view class="contactMeta">电话：{{ item.phone || "-" }}</view>
              <view class="contactMeta" v-if="item.description">{{ item.description }}</view>
            </view>
            <button class="btnPrimary miniBtn" size="mini" @click="callPhone(item.phone)">拨号</button>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { getDutyRoster, getEmergencyContacts } from "@/common/api.js"
import { HOME_PAGE_URL, normalizeRole, requireRole } from "@/common/session.js"

function pad(value) {
  const n = Number(value || 0)
  return n < 10 ? `0${n}` : `${n}`
}

function formatDate(date) {
  const value = new Date(date)
  return `${value.getFullYear()}-${pad(value.getMonth() + 1)}-${pad(value.getDate())}`
}

function getWeekStart(date = new Date()) {
  const value = new Date(date)
  value.setHours(0, 0, 0, 0)
  const day = value.getDay() || 7
  value.setDate(value.getDate() - day + 1)
  return value
}

export default {
  data() {
    return {
      operator: "",
      role: "",
      loading: false,
      dutyRows: [],
      contactRows: [],
      weekStart: getWeekStart(new Date()),
      selectedDate: ""
    }
  },
  computed: {
    weekEnd() {
      const value = new Date(this.weekStart)
      value.setDate(value.getDate() + 6)
      return value
    },
    weekLabel() {
      return `${formatDate(this.weekStart)} - ${formatDate(this.weekEnd)}`
    },
    weekDateOptions() {
      const labels = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"]
      return Array.from({ length: 7 }, (_, index) => {
        const value = new Date(this.weekStart)
        value.setDate(value.getDate() + index)
        const dateText = formatDate(value)
        return {
          date: dateText,
          weekday: labels[value.getDay()] || "",
          short: `${pad(value.getMonth() + 1)}/${pad(value.getDate())}`
        }
      })
    },
    selectedDateLabel() {
      const current = this.weekDateOptions.find((item) => item.date === this.selectedDate)
      return current ? `${current.date} ${current.weekday}` : "请选择日期"
    },
    selectedDutyRows() {
      const shiftOrder = { "早班": 1, "白班": 1, "中班": 2, "午班": 2, "晚班": 3, "夜班": 3 }
      return (Array.isArray(this.dutyRows) ? this.dutyRows : [])
        .filter((item) => String(item.dutyDate || "").trim() === this.selectedDate)
        .slice()
        .sort((a, b) => {
          const aShift = String((a && a.shiftName) || "")
          const bShift = String((b && b.shiftName) || "")
          return (shiftOrder[aShift] || 99) - (shiftOrder[bShift] || 99)
        })
    }
  },
  onShow() {
    const session = requireRole(["admin", "teacher", "student"], {
      message: "请先登录后查看值班表",
      fallbackUrl: HOME_PAGE_URL
    })
    if (!session) return
    this.operator = String(session.username || "").trim()
    this.role = normalizeRole(session.role)
    this.weekStart = getWeekStart(new Date())
    this.selectedDate = formatDate(new Date())
    this.loadAll()
  },
  async onPullDownRefresh() {
    try {
      await this.loadAll()
    } finally {
      uni.stopPullDownRefresh()
    }
  },
  methods: {
    dutyStatusText(status) {
      const map = { scheduled: "待值班", on_duty: "值班中", completed: "已完成", closed: "已关闭" }
      return map[String(status || "").trim()] || "待值班"
    },
    dutyTone(status) {
      if (status === "on_duty") return "status-info"
      if (status === "completed") return "status-success"
      if (status === "closed") return "status-muted"
      return "status-warn"
    },
    async loadAll() {
      this.loading = true
      try {
        const startDate = formatDate(this.weekStart)
        const end = new Date(this.weekStart)
        end.setDate(end.getDate() + 6)
        const endDate = formatDate(end)
        const [dutyRes, contactRes] = await Promise.all([
          getDutyRoster({ startDate, endDate }),
          getEmergencyContacts({ status: "active" })
        ])
        const dutyPayload = (dutyRes && dutyRes.data) || {}
        const contactPayload = (contactRes && contactRes.data) || {}
        this.dutyRows = Array.isArray(dutyPayload.data) ? dutyPayload.data : []
        this.contactRows = Array.isArray(contactPayload.data)
          ? [...contactPayload.data].sort((a, b) => Number(a.priorityNo || 0) - Number(b.priorityNo || 0))
          : []
        if (!this.weekDateOptions.some((item) => item.date === this.selectedDate)) {
          this.selectedDate = this.weekDateOptions.length ? this.weekDateOptions[0].date : ""
        }
      } catch (e) {
        uni.showToast({ title: "加载值班信息失败", icon: "none" })
      } finally {
        this.loading = false
      }
    },
    callPhone(phone) {
      const value = String(phone || "").trim()
      if (!value) {
        uni.showToast({ title: "暂无联系电话", icon: "none" })
        return
      }
      uni.makePhoneCall({ phoneNumber: value })
    }
  }
}
</script>

<style lang="scss">
.dutyRosterPage {
  padding-bottom: 24px;
}

.heroCard {
  border: 1px solid rgba(22, 119, 255, 0.16);
  background: linear-gradient(160deg, #ffffff 0%, #f5faff 100%);
}

.heroTop,
.sectionHeader,
.contactRow,
.slotTop {
  align-items: flex-start;
}

.miniBtn {
  min-height: 30px;
  line-height: 30px;
  padding: 0 10px;
  border-radius: 9px;
  font-size: 12px;
}

.heroMeta {
  margin-top: 6px;
}

.sectionCard {
  gap: 12px;
}

.dateSelector {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 4px;
}

.dateChip {
  flex-shrink: 0;
  min-width: 68px;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  background: #f8fafc;
  text-align: center;
}

.dateChipOn {
  border-color: #60a5fa;
  background: linear-gradient(180deg, #eff6ff, #ffffff);
  box-shadow: 0 6px 16px rgba(59, 130, 246, 0.12);
}

.dateChipWeek {
  font-size: 12px;
  color: #64748b;
}

.dateChipDay {
  margin-top: 4px;
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
}

.selectedDateBar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 4px;
}

.dayTitle {
  font-size: 15px;
  font-weight: 700;
  color: #1f2937;
}

.slotList {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.slotCard {
  border-radius: 12px;
  background: #ffffff;
  border: 1px solid #edf2f7;
  padding: 12px;
}

.slotName {
  font-size: 14px;
  font-weight: 700;
  color: #111827;
}

.slotLine,
.contactMeta {
  margin-top: 6px;
  font-size: 13px;
  color: #64748b;
}

.slotLabel {
  display: inline-block;
  width: 34px;
  color: #94a3b8;
}

.slotValue {
  color: #334155;
}

.slotNote {
  margin-top: 8px;
  font-size: 13px;
  line-height: 1.5;
  color: #64748b;
}

.contactRow {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid #eef2f7;
}

.contactRow:last-child {
  border-bottom: 0;
}

.contactMain {
  flex: 1;
  min-width: 0;
}

.contactTitle {
  font-size: 14px;
  font-weight: 700;
  color: #111827;
}
</style>

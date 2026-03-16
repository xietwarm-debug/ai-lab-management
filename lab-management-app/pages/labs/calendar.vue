<template>
  <view class="container calendarPage">
    <view class="stack">
      <view class="card heroCard">
        <view class="rowBetween heroTop">
          <view>
            <view class="title">实验室日历</view>
            <view class="subtitle">{{ labName || '未选择实验室' }}</view>
          </view>
          <button class="btnSecondary miniBtn" size="mini" @click="refreshCurrent">刷新</button>
        </view>
      </view>

      <view class="card dateCard">
        <view class="label">选择日期</view>
        <picker mode="date" :value="date" :start="rules.minDate" :end="rules.maxDate" @change="onDateChange">
          <view class="calendarBtn">点击打开日历</view>
        </picker>
        <view class="muted" v-if="date">已选日期：{{ date }}</view>
        <view class="muted">可预约范围：{{ rules.minDate || '-' }} 至 {{ rules.maxDate || '-' }}</view>
      </view>

      <view class="card loadingCard" v-if="loading">
        <view class="muted">正在加载该日期的预约...</view>
      </view>

      <view class="card" v-else>
        <view class="rowBetween">
          <view class="cardTitle">已预约时段</view>
          <view class="muted">已占用 {{ bookedSet.size }} 段</view>
        </view>

        <view class="legendRow">
          <view class="legendItem"><text class="legendDot free"></text><text>可用</text></view>
          <view class="legendItem"><text class="legendDot booked"></text><text>已预约</text></view>
        </view>

        <view class="sectionTitle">上午</view>
        <view class="slots">
          <view v-for="t in timeSlotsMorning" :key="t" class="slot" :class="{ booked: bookedSet.has(t) }">
            {{ t }}
            <text class="tag" v-if="bookedSet.has(t)">已预约</text>
          </view>
        </view>

        <view class="sectionTitle">下午</view>
        <view class="slots">
          <view v-for="t in timeSlotsAfternoon" :key="t" class="slot" :class="{ booked: bookedSet.has(t) }">
            {{ t }}
            <text class="tag" v-if="bookedSet.has(t)">已预约</text>
          </view>
        </view>

        <view class="empty miniEmpty" v-if="date && bookedSet.size === 0">当天暂无已审批预约</view>
      </view>

      <view class="card actionCard">
        <view class="rowBetween" style="gap: 8px;">
          <button class="btnPrimary actionBtn" @click="goReserve">去预约</button>
          <button class="btnGhost actionBtn" @click="goList">返回列表</button>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { BASE_URL } from "@/common/api.js"

function parseListPayload(payload) {
  if (Array.isArray(payload)) return payload
  if (payload && Array.isArray(payload.data)) return payload.data
  if (payload && payload.ok && Array.isArray(payload.data)) return payload.data
  return []
}

function todayText() {
  const d = new Date()
  const p = (n) => (n < 10 ? `0${n}` : `${n}`)
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

export default {
  data() {
    return {
      labName: "",
      date: "",
      loading: false,
      timeSlotsMorning: ["08:00-08:40", "08:45-09:35", "10:25-11:05", "11:10-11:50"],
      timeSlotsAfternoon: ["14:30-15:10", "15:15-15:55", "16:05-16:45", "16:50-17:30", "19:00-19:40", "19:45-20:25"],
      bookedSet: new Set(),
      rules: {
        minDate: "",
        maxDate: "",
        slots: []
      }
    }
  },
  onLoad(options) {
    if (options && options.labName) {
      this.labName = decodeURIComponent(options.labName)
    }
    this.fetchReservationRules()
  },
  methods: {
    fetchReservationRules() {
      const q = this.labName ? `?labName=${encodeURIComponent(this.labName)}` : ""
      uni.request({
        url: `${BASE_URL}/reservation-rules${q}`,
        method: "GET",
        success: (res) => {
          const payload = res.data || {}
          if (!payload.ok || !payload.data) {
            this.date = this.date || todayText()
            if (this.labName && this.date) this.fetchReservations()
            return
          }

          this.rules.minDate = payload.data.minDate || ""
          this.rules.maxDate = payload.data.maxDate || ""
          this.rules.slots = Array.isArray(payload.data.slots) ? payload.data.slots : []
          this.applyRuleSlots(this.rules.slots)
          this.date = this.date || this.rules.minDate || todayText()
          if (this.labName && this.date) this.fetchReservations()
        },
        fail: () => {
          this.date = this.date || todayText()
          if (this.labName && this.date) this.fetchReservations()
        }
      })
    },
    onDateChange(e) {
      this.date = e.detail.value
      this.fetchReservations()
    },
    refreshCurrent() {
      if (!this.date) {
        this.date = this.rules.minDate || todayText()
      }
      this.fetchReservations()
    },
    fetchReservations() {
      if (!this.labName || !this.date) {
        this.bookedSet = new Set()
        return
      }

      this.loading = true
      const qs = `?labName=${encodeURIComponent(this.labName)}&date=${encodeURIComponent(this.date)}&status=approved`
      uni.request({
        url: `${BASE_URL}/reservations${qs}`,
        method: "GET",
        success: (res) => {
          const list = parseListPayload(res.data)
          const times = []
          list.forEach((row) => {
            const slots = String(row.time || "")
              .split(",")
              .map((s) => s.trim())
              .filter(Boolean)
            times.push(...slots)
          })
          this.bookedSet = new Set(times)
        },
        fail: () => {
          this.bookedSet = new Set()
          uni.showToast({ title: "获取失败", icon: "none" })
        },
        complete: () => {
          this.loading = false
        }
      })
    },
    applyRuleSlots(slotList) {
      const list = Array.isArray(slotList) ? slotList : []
      if (list.length === 0) return
      const morning = []
      const afternoon = []
      list.forEach((slot) => {
        const text = String(slot || "").trim()
        const hour = Number((text.split("-")[0] || "0").split(":")[0] || 0)
        if (Number.isFinite(hour) && hour < 12) morning.push(text)
        else afternoon.push(text)
      })
      this.timeSlotsMorning = morning
      this.timeSlotsAfternoon = afternoon
    },
    goReserve() {
      if (!this.labName) {
        uni.showToast({ title: "请先选择实验室", icon: "none" })
        return
      }
      uni.navigateTo({ url: `/pages/reserve/reserve?labName=${encodeURIComponent(this.labName)}` })
    },
    goList() {
      const pages = getCurrentPages ? getCurrentPages() : []
      if (pages.length > 1) {
        uni.navigateBack()
        return
      }
      uni.navigateTo({ url: "/pages/labs/labs" })
    }
  }
}
</script>

<style lang="scss">
.calendarPage {
  padding-bottom: 20px;
}

.heroCard {
  border: 1px solid rgba(22, 119, 255, 0.18);
  background: linear-gradient(160deg, #ffffff 0%, #f2f7ff 100%);
}

.heroTop {
  align-items: flex-start;
}

.dateCard,
.actionCard {
  border: 1px solid rgba(148, 163, 184, 0.24);
}

.miniBtn {
  min-height: 30px;
  line-height: 30px;
  padding: 0 10px;
  font-size: 12px;
  border-radius: 9px;
}

.loadingCard {
  min-height: 70px;
  display: flex;
  align-items: center;
}

.legendRow {
  margin-top: 8px;
  display: flex;
  gap: 16px;
}

.legendItem {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #64748b;
}

.legendDot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}

.legendDot.free {
  background: #94a3b8;
}

.legendDot.booked {
  background: #dc2626;
}

.slots {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.slot {
  padding: 8px 10px;
  border-radius: 999px;
  border: 1px solid #dbe3ef;
  background: #f8fafc;
  font-size: 12px;
  color: #334155;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.slot.booked {
  border-color: #fecaca;
  background: #fff1f2;
  color: #b91c1c;
}

.tag {
  font-size: 10px;
}

.miniEmpty {
  margin-top: 10px;
}

.actionBtn {
  width: 48%;
}
</style>

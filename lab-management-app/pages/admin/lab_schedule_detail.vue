<template>
  <view class="container detailPage">
    <view class="stack">
      <view class="card heroCard">
        <view class="title">实验室课表详情</view>
        <view class="subtitle">按日/周查看实验室教学排课</view>
      </view>

      <view class="card">
        <view class="cardTitle">查询条件</view>
        <view class="label mt8">实验室</view>
        <picker :range="labs" range-key="name" :value="labIndex" @change="onLabChange">
          <view class="pickerLike">{{ currentLab ? currentLab.name : "请选择实验室" }}</view>
        </picker>
        <view class="rowBetween mt8">
          <view class="field">
            <view class="label">日期</view>
            <picker mode="date" :value="dateText" @change="onDateChange">
              <view class="pickerLike">{{ dateText }}</view>
            </picker>
          </view>
          <view class="field">
            <view class="label">视图</view>
            <view class="chipRow">
              <view class="chip" :class="{ chipOn: mode==='day' }" @click="setMode('day')">按天</view>
              <view class="chip" :class="{ chipOn: mode==='week' }" @click="setMode('week')">按周</view>
            </view>
          </view>
        </view>
        <view class="chipRow">
          <view class="chip chipOn" @click="loadSchedule">查询</view>
          <view class="chip" @click="goToday">今日提醒</view>
        </view>
      </view>

      <view class="card" v-if="loading">
        <view class="muted">加载中...</view>
      </view>

      <view class="card" v-else-if="mode==='day'">
        <view class="rowBetween">
          <view class="cardTitle">当天课表</view>
          <view class="muted">{{ dateText }}</view>
        </view>
        <view v-if="dayList.length===0" class="empty">当天无课程安排</view>
        <view class="list" v-else>
          <view class="rowItem" v-for="item in dayList" :key="item.id">
            <view class="rowTitle">{{ item.periodText || "-" }} · {{ item.courseName || "-" }}</view>
            <view class="rowMeta">{{ item.teacherName || "-" }} · {{ item.className || "-" }}</view>
            <view class="rowMeta">{{ item.startAt || "-" }} ~ {{ item.endAt || "-" }}</view>
          </view>
        </view>
      </view>

      <view class="card" v-else>
        <view class="rowBetween">
          <view class="cardTitle">本周课表</view>
          <view class="muted">{{ weekRangeText }}</view>
        </view>
        <view v-if="weekDays.length===0" class="empty">暂无数据</view>
        <view class="list" v-else>
          <view class="dayBlock" :class="{ dayClickable: day.list && day.list.length>0 }" v-for="day in weekDays" :key="day.date" @click="openDayDetail(day)">
            <view class="dayTitle">
              {{ day.date }} · {{ weekText(day.weekDay) }}
              <text class="dayHint" v-if="day.list && day.list.length>0">（点击查看当天）</text>
            </view>
            <view v-if="!day.list || day.list.length===0" class="rowMeta">无课程</view>
            <view class="rowItem" v-for="item in day.list" :key="item.id" v-else>
              <view class="rowTitle">{{ item.periodText || "-" }} · {{ item.courseName || "-" }}</view>
              <view class="rowMeta">{{ item.teacherName || "-" }} · {{ item.className || "-" }}</view>
            </view>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { getApiListData, listLabs, adminGetLabScheduleDay, adminGetLabScheduleWeek } from "@/common/api.js"

function todayText() {
  const d = new Date()
  const p = (n) => (n < 10 ? `0${n}` : `${n}`)
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

function ensureAdmin() {
  const s = uni.getStorageSync("session")
  return !!(s && s.role === "admin")
}

export default {
  data() {
    return {
      loading: false,
      labs: [],
      labId: 0,
      dateText: todayText(),
      mode: "week",
      dayList: [],
      weekDays: [],
      weekRangeText: ""
    }
  },
  computed: {
    currentLab() {
      return this.labs.find((x) => Number(x.id) === Number(this.labId)) || null
    },
    labIndex() {
      const idx = this.labs.findIndex((x) => Number(x.id) === Number(this.labId))
      return idx >= 0 ? idx : 0
    }
  },
  onLoad(options) {
    const lid = Number((options && options.labId) || 0)
    if (lid > 0) this.labId = lid
    if (options && options.date) this.dateText = String(options.date || "").trim() || this.dateText
    if (options && options.mode) {
      const m = String(options.mode || "").trim()
      if (m === "day" || m === "week") this.mode = m
    }
  },
  onShow() {
    if (!ensureAdmin()) {
      uni.showToast({ title: "无权限", icon: "none" })
      uni.reLaunch({ url: "/pages/login/login" })
      return
    }
    this.loadLabs()
  },
  methods: {
    weekText(day) {
      const map = ["", "周一", "周二", "周三", "周四", "周五", "周六", "周日"]
      return map[Number(day) || 0] || `周${day}`
    },
    onLabChange(e) {
      const idx = Number((e && e.detail && e.detail.value) || 0)
      const row = this.labs[idx] || null
      if (row) this.labId = Number(row.id || 0)
      this.loadSchedule()
    },
    onDateChange(e) {
      this.dateText = e.detail.value
      this.loadSchedule()
    },
    setMode(mode) {
      this.mode = mode
      this.loadSchedule()
    },
    async loadLabs() {
      this.loading = true
      try {
        const res = await listLabs({})
        this.labs = getApiListData(res && res.data)
        if (!this.labId && this.labs.length > 0) {
          this.labId = Number(this.labs[0].id || 0)
        }
        await this.loadSchedule()
      } catch (e) {
        uni.showToast({ title: "加载失败", icon: "none" })
      } finally {
        this.loading = false
      }
    },
    async loadSchedule() {
      if (!this.labId) return
      this.loading = true
      try {
        if (this.mode === "day") {
          const res = await adminGetLabScheduleDay(this.labId, this.dateText)
          const payload = (res && res.data) || {}
          if (!payload.ok || !payload.data) {
            uni.showToast({ title: payload.msg || "加载失败", icon: "none" })
            return
          }
          this.dayList = Array.isArray(payload.data.list) ? payload.data.list : []
          this.weekDays = []
          this.weekRangeText = payload.data.date || ""
          return
        }
        const res = await adminGetLabScheduleWeek(this.labId, this.dateText)
        const payload = (res && res.data) || {}
        if (!payload.ok || !payload.data) {
          uni.showToast({ title: payload.msg || "加载失败", icon: "none" })
          return
        }
        this.weekDays = Array.isArray(payload.data.days) ? payload.data.days : []
        this.dayList = []
        this.weekRangeText = `${payload.data.startDate || "-"} ~ ${payload.data.endDate || "-"}`
      } catch (e) {
        uni.showToast({ title: "加载失败", icon: "none" })
      } finally {
        this.loading = false
      }
    },
    openDayDetail(day) {
      if (!day || !day.date || !Array.isArray(day.list) || day.list.length <= 0) return
      if (!this.labId) return
      uni.navigateTo({
        url: `/pages/admin/lab_schedule_detail?labId=${encodeURIComponent(String(this.labId))}&date=${encodeURIComponent(String(day.date))}&mode=day`
      })
    },
    goToday() {
      uni.navigateTo({ url: "/pages/admin/door_reminders_today" })
    }
  }
}
</script>

<style lang="scss">
.detailPage {
  padding-bottom: 20px;
}

.heroCard {
  border: 1px solid rgba(22, 119, 255, 0.18);
  background: linear-gradient(160deg, #ffffff 0%, #f2f7ff 100%);
}

.mt8 {
  margin-top: 8px;
}

.field {
  flex: 1;
}

.label {
  font-size: 12px;
  color: #64748b;
  margin-bottom: 4px;
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
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.chipOn {
  border-color: #bfdbfe;
  background: #eaf3ff;
  color: #1d4ed8;
}

.list {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.rowItem {
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 10px;
  padding: 10px;
}

.rowTitle {
  font-size: 13px;
  color: #0f172a;
  font-weight: 700;
}

.rowMeta {
  margin-top: 4px;
  font-size: 12px;
  color: #64748b;
}

.dayBlock {
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 10px;
  padding: 10px;
}

.dayBlock.dayClickable {
  border-color: rgba(37, 99, 235, 0.35);
  background: #f8fbff;
}

.dayTitle {
  font-size: 13px;
  color: #0f172a;
  font-weight: 700;
}

.dayHint {
  font-size: 11px;
  color: #2563eb;
  font-weight: 500;
}

.empty {
  font-size: 12px;
  color: #94a3b8;
}
</style>

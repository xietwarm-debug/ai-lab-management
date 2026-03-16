<template>
  <view class="container reminderPage">
    <view class="stack">
      <view class="card heroCard">
        <view class="rowBetween heroTop">
          <view>
            <view class="title">今日开门提醒</view>
            <view class="subtitle">按时段提醒管理员人工开门</view>
          </view>
          <button class="btnSecondary miniBtn" size="mini" :loading="loading" @click="loadData">刷新</button>
        </view>
        <view class="heroMeta muted">日期：{{ dateText }}</view>
      </view>

      <view class="card">
        <view class="rowBetween">
          <view class="cardTitle">筛选日期</view>
        </view>
        <picker mode="date" :value="dateText" @change="onDateChange">
          <view class="pickerLike">{{ dateText }}</view>
        </picker>
        <view class="chipRow">
          <view class="chip chipOn">总 {{ groups.length }}</view>
          <view class="chip">待处理 {{ pendingCount }}</view>
          <view class="chip" @click="goLogs">查看记录</view>
        </view>
      </view>

      <view class="card" v-if="loading">
        <view class="muted">加载中...</view>
      </view>

      <view v-else-if="groups.length===0" class="card">
        <view class="empty">当天暂无提醒</view>
      </view>

      <view class="card rowItem" v-for="group in groups" :key="group.key" v-else>
        <view class="rowBetween">
          <view>
            <view class="rowTitle">{{ group.labName || "-" }} · {{ group.periodText || "-" }}</view>
            <view class="rowMeta">上课时间：{{ group.startAt || "-" }}</view>
          </view>
          <view class="statusTag" :class="tone(group.statusText)">{{ statusLabel(group.statusText) }}</view>
        </view>
        <view class="rowMeta">课程数：{{ group.items.length }}</view>
        <view class="courseList">
          <view class="courseItem" v-for="item in group.items" :key="item.id">
            {{ item.courseName || "-" }} · {{ item.teacherName || "-" }} · {{ item.className || "-" }}
          </view>
        </view>
        <view class="rowBetween actions">
          <button class="btnPrimary miniBtn" size="mini" :loading="actioningKey===group.key" :disabled="group.statusText!=='pending'" @click="confirmOpen(group)">已开门</button>
          <button class="btnSecondary miniBtn" size="mini" :loading="actioningKey===group.key" :disabled="group.statusText!=='pending'" @click="ignoreGroup(group)">忽略</button>
          <button class="btnSecondary miniBtn" size="mini" @click="goLab(group)">查看实验室课表</button>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import {
  adminGetDoorRemindersToday,
  adminConfirmDoorReminderOpen,
  adminIgnoreDoorReminder
} from "@/common/api.js"

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
      dateText: todayText(),
      loading: false,
      actioningKey: "",
      rows: []
    }
  },
  computed: {
    groups() {
      const map = {}
      this.rows.forEach((row) => {
        const key = `${row.occurrenceDate || ""}|${row.labId || 0}|${row.periodStart || 0}|${row.periodEnd || 0}`
        if (!map[key]) {
          map[key] = {
            key,
            labId: row.labId || 0,
            labName: row.labName || "",
            periodText: row.periodText || "",
            startAt: row.startAt || "",
            items: []
          }
        }
        map[key].items.push(row)
      })
      return Object.keys(map).map((k) => {
        const item = map[k]
        const statuses = item.items.map((x) => String(x.doorStatus || "pending"))
        let statusText = "pending"
        if (statuses.every((s) => s === "opened")) statusText = "opened"
        else if (statuses.every((s) => s === "ignored")) statusText = "ignored"
        else if (statuses.some((s) => s === "pending")) statusText = "pending"
        return { ...item, statusText }
      })
    },
    pendingCount() {
      return this.groups.filter((x) => x.statusText === "pending").length
    }
  },
  onShow() {
    if (!ensureAdmin()) {
      uni.showToast({ title: "无权限", icon: "none" })
      uni.reLaunch({ url: "/pages/login/login" })
      return
    }
    this.loadData()
  },
  methods: {
    onDateChange(e) {
      this.dateText = e.detail.value
      this.loadData()
    },
    tone(status) {
      if (status === "opened") return "success"
      if (status === "ignored") return "muted"
      return "warning"
    },
    statusLabel(status) {
      if (status === "opened") return "已开门"
      if (status === "ignored") return "已忽略"
      return "待处理"
    },
    async loadData() {
      if (this.loading) return
      this.loading = true
      try {
        const res = await adminGetDoorRemindersToday(this.dateText)
        const payload = (res && res.data) || {}
        if (!payload.ok || !payload.data) {
          uni.showToast({ title: payload.msg || "加载失败", icon: "none" })
          return
        }
        this.rows = Array.isArray(payload.data.list) ? payload.data.list : []
      } catch (e) {
        uni.showToast({ title: "加载失败", icon: "none" })
      } finally {
        this.loading = false
      }
    },
    async confirmOpen(group) {
      if (!group || !group.items || !group.items.length) return
      const first = group.items[0]
      this.actioningKey = group.key
      try {
        const res = await adminConfirmDoorReminderOpen(first.id, { note: "管理员手动确认已开门" })
        const payload = (res && res.data) || {}
        if (!payload.ok) {
          uni.showToast({ title: payload.msg || "操作失败", icon: "none" })
          return
        }
        uni.showToast({ title: "已标记开门", icon: "none" })
        this.loadData()
      } catch (e) {
        uni.showToast({ title: "操作失败", icon: "none" })
      } finally {
        this.actioningKey = ""
      }
    },
    async ignoreGroup(group) {
      if (!group || !group.items || !group.items.length) return
      const first = group.items[0]
      this.actioningKey = group.key
      try {
        const res = await adminIgnoreDoorReminder(first.id, { note: "管理员手动忽略" })
        const payload = (res && res.data) || {}
        if (!payload.ok) {
          uni.showToast({ title: payload.msg || "操作失败", icon: "none" })
          return
        }
        uni.showToast({ title: "已忽略", icon: "none" })
        this.loadData()
      } catch (e) {
        uni.showToast({ title: "操作失败", icon: "none" })
      } finally {
        this.actioningKey = ""
      }
    },
    goLogs() {
      uni.navigateTo({ url: "/pages/admin/door_reminder_logs" })
    },
    goLab(group) {
      if (!group || !group.labId) return
      uni.navigateTo({ url: `/pages/admin/lab_schedule_detail?labId=${encodeURIComponent(String(group.labId))}&date=${encodeURIComponent(this.dateText)}` })
    }
  }
}
</script>

<style lang="scss">
.reminderPage {
  padding-bottom: 20px;
}

.heroCard {
  border: 1px solid rgba(22, 119, 255, 0.18);
  background: linear-gradient(160deg, #ffffff 0%, #f2f7ff 100%);
}

.heroTop {
  align-items: flex-start;
}

.heroMeta {
  margin-top: 6px;
}

.miniBtn {
  min-height: 30px;
  line-height: 30px;
  padding: 0 10px;
  border-radius: 9px;
  font-size: 12px;
}

.pickerLike {
  margin-top: 8px;
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
  gap: 8px;
  flex-wrap: wrap;
}

.chipOn {
  border-color: #bfdbfe;
  background: #eaf3ff;
  color: #1d4ed8;
}

.empty {
  color: #94a3b8;
  font-size: 12px;
}

.rowItem {
  border: 1px solid rgba(148, 163, 184, 0.24);
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

.courseList {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.courseItem {
  font-size: 12px;
  color: #334155;
}

.actions {
  margin-top: 10px;
}
</style>

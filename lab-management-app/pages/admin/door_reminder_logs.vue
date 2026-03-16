<template>
  <view class="container logPage">
    <view class="stack">
      <view class="card heroCard">
        <view class="rowBetween">
          <view>
            <view class="title">提醒记录</view>
            <view class="subtitle">开门提醒处理历史</view>
          </view>
          <button class="btnSecondary miniBtn" size="mini" :loading="loading" @click="loadData">刷新</button>
        </view>
      </view>

      <view class="card">
        <view class="cardTitle">筛选条件</view>
        <view class="rowBetween mt8">
          <view class="field">
            <view class="label">开始日期</view>
            <picker mode="date" :value="query.startDate" @change="onStartDateChange">
              <view class="pickerLike">{{ query.startDate }}</view>
            </picker>
          </view>
          <view class="field">
            <view class="label">结束日期</view>
            <picker mode="date" :value="query.endDate" @change="onEndDateChange">
              <view class="pickerLike">{{ query.endDate }}</view>
            </picker>
          </view>
        </view>
        <view class="chipRow">
          <view class="chip" :class="{ chipOn: query.doorStatus==='' }" @click="setDoorStatus('')">全部</view>
          <view class="chip" :class="{ chipOn: query.doorStatus==='pending' }" @click="setDoorStatus('pending')">待处理</view>
          <view class="chip" :class="{ chipOn: query.doorStatus==='opened' }" @click="setDoorStatus('opened')">已开门</view>
          <view class="chip" :class="{ chipOn: query.doorStatus==='ignored' }" @click="setDoorStatus('ignored')">已忽略</view>
        </view>
        <view class="chipRow">
          <view class="chip chipOn" @click="loadData">查询</view>
          <view class="chip" @click="goToday">去今日提醒</view>
        </view>
      </view>

      <view class="card" v-if="loading">
        <view class="muted">加载中...</view>
      </view>

      <view class="card" v-else-if="rows.length===0">
        <view class="empty">暂无记录</view>
      </view>

      <view class="card rowItem" v-for="item in rows" :key="item.id" v-else>
        <view class="rowBetween">
          <view class="rowTitle">{{ item.occurrenceDate }} · {{ item.labName || "-" }}</view>
          <view class="statusTag" :class="tone(item.doorStatus)">{{ statusLabel(item.doorStatus) }}</view>
        </view>
        <view class="rowMeta">{{ item.periodText || "-" }} · {{ item.courseName || "-" }}</view>
        <view class="rowMeta">{{ item.teacherName || "-" }} · {{ item.className || "-" }}</view>
        <view class="rowMeta">处理人：{{ item.handledBy || "-" }} · 处理时间：{{ item.handledAt || "-" }}</view>
      </view>

      <view class="card rowBetween" v-if="meta.total > query.pageSize">
        <button class="btnSecondary miniBtn" size="mini" :disabled="query.page<=1" @click="prevPage">上一页</button>
        <view class="muted">第 {{ query.page }} 页 / 共 {{ totalPages }} 页</view>
        <button class="btnSecondary miniBtn" size="mini" :disabled="query.page>=totalPages" @click="nextPage">下一页</button>
      </view>
    </view>
  </view>
</template>

<script>
import { adminGetDoorReminderRecords } from "@/common/api.js"

function dateBefore(days) {
  const d = new Date(Date.now() - days * 24 * 60 * 60 * 1000)
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
      rows: [],
      meta: { total: 0, page: 1, pageSize: 30 },
      query: {
        startDate: dateBefore(30),
        endDate: dateBefore(0),
        doorStatus: "",
        page: 1,
        pageSize: 30
      }
    }
  },
  computed: {
    totalPages() {
      const total = Number(this.meta.total || 0)
      const size = Number(this.query.pageSize || 30)
      return Math.max(1, Math.ceil(total / size))
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
    onStartDateChange(e) {
      this.query.startDate = e.detail.value
    },
    onEndDateChange(e) {
      this.query.endDate = e.detail.value
    },
    setDoorStatus(val) {
      this.query.doorStatus = val
      this.query.page = 1
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
        const res = await adminGetDoorReminderRecords(this.query)
        const payload = (res && res.data) || {}
        if (!payload.ok) {
          uni.showToast({ title: payload.msg || "加载失败", icon: "none" })
          return
        }
        this.rows = Array.isArray(payload.data) ? payload.data : []
        this.meta = payload.meta || { total: 0, page: 1, pageSize: 30 }
      } catch (e) {
        uni.showToast({ title: "加载失败", icon: "none" })
      } finally {
        this.loading = false
      }
    },
    prevPage() {
      if (this.query.page <= 1) return
      this.query.page -= 1
      this.loadData()
    },
    nextPage() {
      if (this.query.page >= this.totalPages) return
      this.query.page += 1
      this.loadData()
    },
    goToday() {
      uni.navigateTo({ url: "/pages/admin/door_reminders_today" })
    }
  }
}
</script>

<style lang="scss">
.logPage {
  padding-bottom: 20px;
}

.heroCard {
  border: 1px solid rgba(22, 119, 255, 0.18);
  background: linear-gradient(160deg, #ffffff 0%, #f2f7ff 100%);
}

.miniBtn {
  min-height: 30px;
  line-height: 30px;
  padding: 0 10px;
  border-radius: 9px;
  font-size: 12px;
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

.empty {
  color: #94a3b8;
  font-size: 12px;
}
</style>

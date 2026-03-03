<template>
  <view class="container myPage">
    <view class="stack">
      <view class="card heroCard">
        <view class="rowBetween heroTop">
          <view>
            <view class="title">我的预约</view>
            <view class="subtitle">仅展示当前登录账号的预约记录</view>
          </view>
          <view class="statusTag info">账号 {{ user || '-' }}</view>
        </view>
        <view class="heroActions">
          <button class="btnSecondary miniBtn" size="mini" @click="openChangePassword">修改密码</button>
          <button class="btnSecondary miniBtn" size="mini" @click="goAgent">智能助手</button>
          <button class="btnSecondary miniBtn" size="mini" @click="queryMine">刷新</button>
          <button class="btnDanger miniBtn" size="mini" @click="logout">退出登录</button>
        </view>
      </view>

      <view class="card filterCard">
        <view class="rowBetween">
          <view class="cardTitle">状态筛选</view>
          <view class="muted">每页 {{ pageSize }} 条</view>
        </view>

        <view class="chipRow">
          <view
            v-for="item in statusOptions"
            :key="item.value"
            class="chip filterChip"
            :class="{ chipOn: statusFilter === item.value }"
            @click="setStatus(item.value)"
          >
            {{ item.label }}
          </view>
        </view>

        <view class="muted ruleText">
          可预约日期：{{ rules.minDate || '-' }} 至 {{ rules.maxDate || '-' }}
        </view>
      </view>

      <view class="card loadingCard" v-if="loading && list.length === 0">
        <view class="muted">正在加载预约记录...</view>
      </view>

      <view class="stack" v-else-if="list.length > 0">
        <view v-for="r in list" :key="r.id" class="card reserveItem">
          <view class="rowBetween">
            <view class="reserveName">{{ r.labName || '未知实验室' }}</view>
            <view class="statusTag" :class="statusTone(r.status)">{{ statusText(r.status) }}</view>
          </view>

          <view class="meta">时间：{{ r.date || '-' }} {{ r.time || '-' }}</view>
          <view class="meta" v-if="r.reason || r.purpose">用途：{{ r.reason || r.purpose }}</view>
          <view class="meta" v-if="r.status === 'rejected' && r.rejectReason">驳回原因：{{ r.rejectReason }}</view>
          <view class="meta" v-if="r.adminNote">管理员备注：{{ r.adminNote }}</view>
          <view class="meta muted">编号：{{ r.id }} · 提交：{{ r.createdAt || '-' }}</view>

          <view class="actions" v-if="r.status === 'pending' || r.status === 'approved'">
            <button size="mini" class="btnSecondary miniBtn" @click="openReschedule(r)">改期</button>
            <button size="mini" class="btnDanger miniBtn" @click="cancel(r)">取消预约</button>
          </view>
          <view class="actions" v-else-if="r.status === 'rejected' || r.status === 'cancelled'">
            <button size="mini" class="btnDanger miniBtn" @click="deleteRecord(r)">删除记录</button>
          </view>
        </view>

        <view class="card rowBetween pageCard">
          <view class="muted">已加载 {{ list.length }} / {{ total || 0 }}</view>
          <button
            size="mini"
            class="btnSecondary miniBtn"
            :disabled="!hasMore || loadingMore"
            @click="fetchMore"
          >
            {{ loadMoreText }}
          </button>
        </view>
      </view>

      <view class="emptyState" v-else>
        <view class="emptyIcon">约</view>
        <view class="emptyTitle">暂无预约记录</view>
        <view class="emptySub">去实验室列表选择时段，发起第一次预约</view>
      </view>
    </view>

    <view v-if="showReschedule" class="modalMask" @click="closeReschedule">
      <view class="modalCard stack" @click.stop>
        <view class="modalTitle">改期预约</view>

        <view class="label">日期</view>
        <picker
          mode="date"
          :value="rescheduleDate"
          :start="rules.minDate"
          :end="rules.maxDate"
          @change="onRescheduleDateChange"
        >
          <view class="calendarBtn">点击选择日期</view>
        </picker>
        <view class="muted">可预约日期：{{ rules.minDate || '-' }} 至 {{ rules.maxDate || '-' }}</view>

        <view class="label">时间段</view>
        <view class="sectionTitle">上午</view>
        <view class="slots">
          <view
            v-for="t in timeSlotsMorning"
            :key="t"
            class="slot"
            :class="{ selected: rescheduleTimes.includes(t) }"
            @click="toggleRescheduleTime(t)"
          >
            {{ t }}
          </view>
        </view>

        <view class="sectionTitle">下午</view>
        <view class="slots">
          <view
            v-for="t in timeSlotsAfternoon"
            :key="t"
            class="slot"
            :class="{ selected: rescheduleTimes.includes(t) }"
            @click="toggleRescheduleTime(t)"
          >
            {{ t }}
          </view>
        </view>

        <view class="modalActions">
          <button size="mini" class="btnSecondary miniBtn" @click="closeReschedule">取消</button>
          <button size="mini" class="btnPrimary miniBtn" @click="confirmReschedule">确定</button>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { BASE_URL } from "@/common/api.js"

export default {
  data() {
    return {
      user: "",
      list: [],
      loading: false,
      loadingMore: false,
      page: 1,
      pageSize: 20,
      total: 0,
      hasMore: false,
      statusFilter: "all",
      statusOptions: [
        { label: "全部", value: "all" },
        { label: "待审批", value: "pending" },
        { label: "已通过", value: "approved" },
        { label: "已驳回", value: "rejected" },
        { label: "已取消", value: "cancelled" }
      ],
      showReschedule: false,
      rescheduleTarget: null,
      rescheduleDate: "",
      rescheduleTimes: [],
      timeSlotsMorning: ["8:00-8:40", "8:45-9:35", "10:25-11:05", "11:10-11:50"],
      timeSlotsAfternoon: ["2:30-3:10", "3:15-3:55", "4:05-4:45", "4:50-5:30", "7:00-7:40", "7:45-8:25"],
      rules: {
        minDate: "",
        maxDate: "",
        minDaysAhead: 0,
        maxDaysAhead: 30,
        minTime: "08:00",
        maxTime: "22:00"
      }
    }
  },
  computed: {
    loadMoreText() {
      if (this.loadingMore) return "加载中..."
      if (this.hasMore) return "加载更多"
      return "已加载全部"
    }
  },
  onShow() {
    this.initUser()
    this.fetchReservationRules()
    this.queryMine()
  },
  onReachBottom() {
    this.fetchMore()
  },
  methods: {
    initUser() {
      const s = uni.getStorageSync("session")
      this.user = s && s.username ? s.username : ""
    },
    fetchReservationRules() {
      uni.request({
        url: `${BASE_URL}/reservation-rules`,
        method: "GET",
        success: (res) => {
          const payload = res.data || {}
          if (!payload.ok || !payload.data) return
          const data = payload.data
          this.rules.minDate = data.minDate || ""
          this.rules.maxDate = data.maxDate || ""
          this.rules.minDaysAhead = Number(data.minDaysAhead || 0)
          this.rules.maxDaysAhead = Number(data.maxDaysAhead || 30)
          this.rules.minTime = data.minTime || "08:00"
          this.rules.maxTime = data.maxTime || "22:00"
        }
      })
    },
    statusText(status) {
      if (status === "pending") return "待审批"
      if (status === "approved") return "已通过"
      if (status === "rejected") return "已驳回"
      if (status === "cancelled") return "已取消"
      return status || "-"
    },
    statusTone(status) {
      if (status === "approved") return "success"
      if (status === "pending") return "warning"
      if (status === "rejected" || status === "cancelled") return "danger"
      return "info"
    },
    setStatus(status) {
      if (this.statusFilter === status) return
      this.statusFilter = status
      this.queryMine()
    },
    buildQuery(page) {
      const parts = [
        `user=${encodeURIComponent(this.user)}`,
        `page=${page}`,
        `pageSize=${this.pageSize}`
      ]
      if (this.statusFilter !== "all") {
        parts.push(`status=${encodeURIComponent(this.statusFilter)}`)
      }
      return parts.join("&")
    },
    queryMine() {
      if (!this.user) {
        uni.showToast({ title: "请先登录", icon: "none" })
        uni.reLaunch({ url: "/pages/login/login" })
        return
      }
      this.page = 1
      this.total = 0
      this.hasMore = false
      this.list = []
      this.fetchMine(true)
    },
    fetchMine(reset = false) {
      if (reset) {
        if (this.loading) return
        this.loading = true
      } else {
        if (this.loading || this.loadingMore || !this.hasMore) return
        this.loadingMore = true
      }

      const reqPage = reset ? 1 : this.page
      uni.request({
        url: `${BASE_URL}/reservations?${this.buildQuery(reqPage)}`,
        method: "GET",
        success: (res) => {
          const payload = res.data
          if (Array.isArray(payload)) {
            this.list = payload
            this.total = payload.length
            this.hasMore = false
            this.page = 2
            return
          }

          if (!payload || !payload.ok) {
            if (reset) this.list = []
            uni.showToast({ title: (payload && payload.msg) || "查询失败", icon: "none" })
            return
          }

          const rows = Array.isArray(payload.data) ? payload.data : []
          const meta = payload.meta || {}
          if (reset) this.list = rows
          else this.list = this.list.concat(rows)
          this.total = Number(meta.total || this.list.length)
          this.hasMore = !!meta.hasMore
          this.page = reqPage + 1
        },
        fail: () => {
          if (reset) this.list = []
          uni.showToast({ title: "查询失败", icon: "none" })
        },
        complete: () => {
          this.loading = false
          this.loadingMore = false
        }
      })
    },
    fetchMore() {
      this.fetchMine(false)
    },
    goAgent() {
      uni.switchTab({ url: "/pages/agent/agent" })
    },
    logout() {
      const s = uni.getStorageSync("session") || {}
      uni.request({
        url: `${BASE_URL}/auth/logout`,
        method: "POST",
        header: { "Content-Type": "application/json" },
        data: { refreshToken: s.refreshToken || "" },
        complete: () => {
          uni.removeStorageSync("session")
          uni.reLaunch({ url: "/pages/login/login" })
        }
      })
    },
    openChangePassword() {
      uni.showModal({
        title: "输入旧密码",
        editable: true,
        placeholderText: "旧密码",
        success: (m1) => {
          if (!m1.confirm) return
          const oldPassword = (m1.content || "").trim()
          if (!oldPassword) {
            uni.showToast({ title: "请输入旧密码", icon: "none" })
            return
          }

          uni.showModal({
            title: "输入新密码",
            editable: true,
            placeholderText: "至少 6 位",
            success: (m2) => {
              if (!m2.confirm) return
              const newPassword = (m2.content || "").trim()
              if (newPassword.length < 6) {
                uni.showToast({ title: "新密码至少 6 位", icon: "none" })
                return
              }

              uni.request({
                url: `${BASE_URL}/auth/change-password`,
                method: "POST",
                header: { "Content-Type": "application/json" },
                data: { oldPassword, newPassword },
                success: (res) => {
                  if (!res.data || !res.data.ok) {
                    uni.showToast({ title: (res.data && res.data.msg) || "修改失败", icon: "none" })
                    return
                  }
                  uni.showModal({
                    title: "修改成功",
                    content: "请重新登录",
                    showCancel: false,
                    success: () => {
                      uni.removeStorageSync("session")
                      uni.reLaunch({ url: "/pages/login/login" })
                    }
                  })
                },
                fail: () => {
                  uni.showToast({ title: "请求失败", icon: "none" })
                }
              })
            }
          })
        }
      })
    },
    cancel(row) {
      uni.showModal({
        title: "确认取消",
        content: `取消 ${row.labName || "该实验室"} 的预约？`,
        success: (m) => {
          if (!m.confirm) return
          uni.request({
            url: `${BASE_URL}/reservations/${row.id}/cancel`,
            method: "POST",
            header: { "Content-Type": "application/json" },
            data: { user: this.user },
            success: (res) => {
              if (!res.data || !res.data.ok) {
                uni.showToast({ title: (res.data && res.data.msg) || "取消失败", icon: "none" })
                return
              }
              uni.showToast({ title: "已取消", icon: "success" })
              this.queryMine()
            },
            fail: () => {
              uni.showToast({ title: "请求失败", icon: "none" })
            }
          })
        }
      })
    },
    deleteRecord(row) {
      uni.showModal({
        title: "确认删除",
        content: `删除预约记录 #${row.id}？删除后不可恢复。`,
        confirmColor: "#ef4444",
        success: (m) => {
          if (!m.confirm) return
          uni.request({
            url: `${BASE_URL}/reservations/${row.id}/delete`,
            method: "POST",
            header: { "Content-Type": "application/json" },
            data: { user: this.user },
            success: (res) => {
              if (!res.data || !res.data.ok) {
                uni.showToast({ title: (res.data && res.data.msg) || "删除失败", icon: "none" })
                return
              }
              uni.showToast({ title: "已删除", icon: "success" })
              this.queryMine()
            },
            fail: () => {
              uni.showToast({ title: "请求失败", icon: "none" })
            }
          })
        }
      })
    },
    openReschedule(row) {
      this.rescheduleTarget = row
      this.rescheduleDate = row.date || ""
      this.rescheduleTimes = (row.time || "")
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean)
      this.showReschedule = true
    },
    closeReschedule() {
      this.showReschedule = false
      this.rescheduleTarget = null
    },
    onRescheduleDateChange(e) {
      this.rescheduleDate = e.detail.value
    },
    toggleRescheduleTime(time) {
      const idx = this.rescheduleTimes.indexOf(time)
      if (idx >= 0) this.rescheduleTimes.splice(idx, 1)
      else this.rescheduleTimes.push(time)
    },
    confirmReschedule() {
      if (!this.rescheduleTarget) return
      if (!this.rescheduleDate || this.rescheduleTimes.length === 0) {
        uni.showToast({ title: "请选择日期与时间段", icon: "none" })
        return
      }
      if (this.rules.minDate && this.rescheduleDate < this.rules.minDate) {
        uni.showToast({ title: "日期不在可预约范围", icon: "none" })
        return
      }
      if (this.rules.maxDate && this.rescheduleDate > this.rules.maxDate) {
        uni.showToast({ title: "日期不在可预约范围", icon: "none" })
        return
      }

      uni.showModal({
        title: "确认改期",
        content: `预约编号：${this.rescheduleTarget.id}\n新日期：${this.rescheduleDate}\n新时段：${this.rescheduleTimes.join(', ')}`,
        success: (m) => {
          if (!m.confirm) return
          uni.request({
            url: `${BASE_URL}/reservations/${this.rescheduleTarget.id}/reschedule`,
            method: "POST",
            header: { "Content-Type": "application/json" },
            data: {
              user: this.user,
              date: this.rescheduleDate,
              time: this.rescheduleTimes.join(",")
            },
            success: (res) => {
              if (!res.data || !res.data.ok) {
                uni.showToast({ title: (res.data && res.data.msg) || "改期失败", icon: "none" })
                return
              }
              uni.showModal({
                title: "改期成功",
                content: `预约 #${this.rescheduleTarget.id} 已更新，并重新进入待审批状态`,
                showCancel: false
              })
              this.showReschedule = false
              this.queryMine()
            },
            fail: () => {
              uni.showToast({ title: "请求失败", icon: "none" })
            }
          })
        }
      })
    }
  }
}
</script>

<style lang="scss">
.myPage {
  padding-bottom: 20px;
}

.heroCard {
  border: 1px solid rgba(22, 119, 255, 0.18);
  background: linear-gradient(160deg, #ffffff 0%, #f1f7ff 100%);
}

.heroTop {
  align-items: flex-start;
}

.heroActions {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.miniBtn {
  min-height: 30px;
  line-height: 30px;
  padding: 0 10px;
  font-size: 12px;
  border-radius: 9px;
}

.filterCard {
  border: 1px solid rgba(148, 163, 184, 0.24);
}

.chipRow {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.filterChip {
  transition: all 0.14s ease;
}

.chipOn {
  border-color: #bfdbfe;
  background: #eaf3ff;
  color: #1d4ed8;
}

.ruleText {
  margin-top: 8px;
}

.loadingCard {
  min-height: 70px;
  display: flex;
  align-items: center;
}

.reserveItem {
  border: 1px solid rgba(148, 163, 184, 0.24);
}

.reserveName {
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
}

.meta {
  margin-top: 6px;
  color: #64748b;
  font-size: 12px;
  line-height: 18px;
}

.actions {
  margin-top: 10px;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.pageCard {
  border: 1px solid rgba(148, 163, 184, 0.24);
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
}

.selected {
  border-color: #bfdbfe;
  background: #eaf3ff;
  color: #1d4ed8;
}
</style>

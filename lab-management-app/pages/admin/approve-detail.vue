<template>
  <view class="container">
    <view class="stack">
      <view>
        <view class="title">预约详情</view>
        <view class="subtitle">审批与备注</view>
      </view>

      <view class="card">
        <view class="rowBetween">
          <view class="name">{{ data.labName }}</view>
          <view class="status" :class="data.status">{{ statusText(data.status) }}</view>
        </view>
        <view class="meta">预约人: {{ data.user }}</view>
        <view class="meta">时间: {{ data.date }} {{ data.time }}</view>
        <view class="meta" v-if="data.reason">用途: {{ data.reason }}</view>
        <view class="meta" v-if="data.rejectReason">驳回原因: {{ data.rejectReason }}</view>
        <view class="meta" v-if="data.adminNote">管理员备注: {{ data.adminNote }}</view>
        <view class="meta muted">提交: {{ data.createdAt }}</view>
      </view>

      <view class="card actions">
        <button size="mini" class="btnPrimary" @click="approve" v-if="data.status==='pending'">通过</button>
        <button size="mini" class="btnGhost" @click="reject" v-if="data.status==='pending'">驳回</button>
        <button size="mini" class="btnGhost" @click="note">备注</button>
        <button size="mini" class="btnGhost" @click="openReschedule">改期</button>
        <button size="mini" class="btnGhost" @click="adminCancel">取消预约</button>
      </view>
    </view>

    <view v-if="showReschedule" class="modalMask" @click="closeReschedule">
      <view class="modalCard stack" @click.stop>
        <view class="modalTitle">改期</view>
        <view class="label">日期</view>
        <picker mode="date" :value="rescheduleDate" @change="e => rescheduleDate = e.detail.value">
          <view class="calendarBtn">点击选择日期</view>
        </picker>
        <view class="label">时间段</view>
        <view class="sectionTitle">上午</view>
        <view class="slots">
          <view
            v-for="t in timeSlotsMorning"
            :key="t"
            class="slot"
            :class="{ selected: rescheduleTimes.includes(t) }"
            @click="toggleRescheduleTime(t)"
          >{{ t }}</view>
        </view>
        <view class="sectionTitle">下午</view>
        <view class="slots">
          <view
            v-for="t in timeSlotsAfternoon"
            :key="t"
            class="slot"
            :class="{ selected: rescheduleTimes.includes(t) }"
            @click="toggleRescheduleTime(t)"
          >{{ t }}</view>
        </view>
        <view class="modalActions">
          <button size="mini" class="btnGhost" @click="closeReschedule">取消</button>
          <button size="mini" class="btnPrimary" @click="confirmReschedule">确定</button>
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
      id: "",
      data: {},
      showReschedule: false,
      rescheduleDate: "",
      rescheduleTimes: [],
      timeSlotsMorning: [
        "8:00-8:40",
        "8:45-9:35",
        "10:25-11:05",
        "11:10-11:50"
      ],
      timeSlotsAfternoon: [
        "2:30-3:10",
        "3:15-3:55",
        "4:05-4:45",
        "4:50-5:30"
      ]
    }
  },
  onLoad(options) {
    this.id = options.id || ""
  },
  onShow() {
    this.fetch()
  },
  methods: {
    statusText(s) {
      if (s === "pending") return "待审批"
      if (s === "approved") return "已通过"
      if (s === "rejected") return "已驳回"
      if (s === "cancelled") return "已取消"
      return s
    },
    fetch() {
      if (!this.id) return
      uni.request({
        url: `${BASE_URL}/reservations/${this.id}`,
        method: "GET",
        success: (res) => {
          if (!res.data || !res.data.ok) return
          this.data = res.data.data || {}
        }
      })
    },
    openReschedule() {
      this.rescheduleDate = this.data.date || ""
      this.rescheduleTimes = (this.data.time || "").split(",").map(s => s.trim()).filter(Boolean)
      this.showReschedule = true
    },
    closeReschedule() {
      this.showReschedule = false
    },
    toggleRescheduleTime(t) {
      const idx = this.rescheduleTimes.indexOf(t)
      if (idx >= 0) this.rescheduleTimes.splice(idx, 1)
      else this.rescheduleTimes.push(t)
    },
    confirmReschedule() {
      const s = uni.getStorageSync("session")
      const operator = s ? s.username : ""
      if (!this.rescheduleDate || this.rescheduleTimes.length === 0) {
        return uni.showToast({ title: "请选择日期与时间段", icon: "none" })
      }
      uni.request({
        url: `${BASE_URL}/reservations/${this.id}/admin-reschedule`,
        method: "POST",
        header: { "Content-Type": "application/json" },
        data: {
          operator,
          date: this.rescheduleDate,
          time: this.rescheduleTimes.join(",")
        },
        success: (res) => {
          if (!res.data || !res.data.ok) {
            return uni.showToast({ title: (res.data && res.data.msg) || "改期失败", icon: "none" })
          }
          uni.showToast({ title: "已改期", icon: "success" })
          this.showReschedule = false
          this.fetch()
        },
        fail: () => uni.showToast({ title: "请求失败", icon: "none" })
      })
    },
    adminCancel() {
      const s = uni.getStorageSync("session")
      const operator = s ? s.username : ""
      uni.showModal({
        title: "确认取消",
        content: "确认取消该预约？",
        success: (m) => {
          if (!m.confirm) return
          uni.request({
            url: `${BASE_URL}/reservations/${this.id}/admin-cancel`,
            method: "POST",
            header: { "Content-Type": "application/json" },
            data: { operator },
            success: (res) => {
              if (!res.data || !res.data.ok) {
                return uni.showToast({ title: (res.data && res.data.msg) || "取消失败", icon: "none" })
              }
              uni.showToast({ title: "已取消", icon: "success" })
              this.fetch()
            },
            fail: () => uni.showToast({ title: "请求失败", icon: "none" })
          })
        }
      })
    },
    approve() {
      uni.request({
        url: `${BASE_URL}/reservations/${this.id}/approve`,
        method: "POST",
        success: (res) => {
          if (!res.data.ok) return uni.showToast({ title: res.data.msg || "失败", icon: "none" })
          uni.showToast({ title: "已通过", icon: "success" })
          this.fetch()
        },
        fail: () => uni.showToast({ title: "请求失败", icon: "none" })
      })
    },
    reject() {
      uni.showModal({
        title: "驳回原因",
        editable: true,
        placeholderText: "可选: 填写原因",
        success: (m) => {
          if (!m.confirm) return
          uni.request({
            url: `${BASE_URL}/reservations/${this.id}/reject`,
            method: "POST",
            header: { "Content-Type": "application/json" },
            data: { rejectReason: m.content || "" },
            success: (res) => {
              if (!res.data.ok) return uni.showToast({ title: res.data.msg || "失败", icon: "none" })
              uni.showToast({ title: "已驳回", icon: "success" })
              this.fetch()
            },
            fail: () => uni.showToast({ title: "请求失败", icon: "none" })
          })
        }
      })
    },
    note() {
      const s = uni.getStorageSync("session")
      const operator = s ? s.username : ""
      uni.showModal({
        title: "管理员备注",
        editable: true,
        placeholderText: "填写备注",
        success: (m) => {
          if (!m.confirm) return
          const note = (m.content || "").trim()
          if (!note) return
          uni.request({
            url: `${BASE_URL}/reservations/${this.id}/note`,
            method: "POST",
            header: { "Content-Type": "application/json" },
            data: { operator, note },
            success: (res) => {
              if (!res.data.ok) return uni.showToast({ title: res.data.msg || "失败", icon: "none" })
              uni.showToast({ title: "已备注", icon: "success" })
              this.fetch()
            },
            fail: () => uni.showToast({ title: "请求失败", icon: "none" })
          })
        }
      })
    }
  }
}
</script>

<style>
.actions { display:flex; gap:10px; }
.status{ font-size:12px; padding:4px 8px; border-radius:999px; }
.pending{ background:#fff7e6; color:#8a5a00; }
.approved{ background:#e8fff0; color:#1f7a3a; }
.rejected{ background:#ffecec; color:#a11f1f; }
.cancelled{ background:#eef2f6; color:#64748b; }
.name { font-weight: 600; }
.meta { margin-top:6px; color:#64748b; font-size:12px; }
.modalMask{
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 999;
}
.modalCard{
  width: 82%;
  background: #fff;
  border-radius: 14px;
  padding: 12px;
  box-shadow: 0 12px 30px rgba(0,0,0,0.12);
}
.modalTitle{ font-weight: 600; }
.label { font-size: 12px; color: #6b7280; margin: 8px 0 6px; }
.calendarBtn {
  padding: 10px 12px;
  background: #f4f6f9;
  border-radius: 12px;
}
.sectionTitle { font-size: 12px; color: #6b7280; margin: 8px 0 6px; }
.slots { display: flex; flex-wrap: wrap; gap: 8px; }
.slot {
  padding: 8px 10px;
  background: #f2f2f2;
  border-radius: 999px;
  font-size: 12px;
}
.selected {
  background: #e6f0ff;
  color: #2b5fd9;
}
.modalActions{
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 12px;
}
</style>

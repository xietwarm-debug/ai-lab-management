<template>
  <view class="container attendancePage">
    <view class="stack">
      <view class="card heroCard">
        <view class="rowBetween">
          <view>
            <view class="title">课堂签到</view>
            <view class="subtitle">加入当前开放的考勤并提交签到码</view>
          </view>
          <button class="btnSecondary miniBtn" size="mini" :loading="loading" @click="loadData">刷新</button>
        </view>
      </view>

      <view class="emptyState" v-if="!loading && sessions.length === 0">
        <view class="emptyTitle">暂无开放的考勤</view>
        <view class="emptySub">老师发起的课堂考勤将会在此显示。</view>
      </view>

      <view class="card sessionCard" v-for="item in sessions" :key="item.id">
        <view class="rowBetween">
          <view class="sessionTitle">{{ item.courseName || "课堂考勤" }}</view>
          <view class="statusTag" :class="statusTone(item.myRecord && item.myRecord.status)">
            {{ statusText(item.myRecord && item.myRecord.status) }}
          </view>
        </view>
        <view class="meta">实验室: {{ item.labName || "未指定" }}</view>
        <view class="meta">开放时间: {{ item.startAt || "-" }} 至 {{ item.endAt || "-" }}</view>
        <view class="meta">防作弊策略: {{ antiCheatText(item) }}</view>
        <view class="meta" v-if="item.myRecord && item.myRecord.finalCheckinAt">
          上次签到: {{ item.myRecord.finalCheckinAt }}
        </view>
        <view class="meta warning" v-if="item.myRecord && item.myRecord.suspicionReason">
          风险提示: {{ item.myRecord.suspicionReason }}
        </view>

        <input
          class="inputBase fieldInput"
          v-model.trim="draftMap[item.id].attendanceCode"
          maxlength="16"
          placeholder="输入签到码"
        />
        <input
          class="inputBase fieldInput"
          v-model.trim="draftMap[item.id].seatCode"
          maxlength="32"
          :placeholder="item.requireSeatCode ? '输入座位号' : '座位号（选填）'"
        />
        <input
          v-if="item.recheckActive"
          class="inputBase fieldInput"
          v-model.trim="draftMap[item.id].recheckCode"
          maxlength="16"
          placeholder="输入二次核验码"
        />

        <view class="actions">
          <button class="btnPrimary miniBtn" size="mini" @click="submitCheckIn(item)">提交签到</button>
          <button v-if="item.recheckActive" class="btnSecondary miniBtn" size="mini" @click="submitRecheck(item)">
            确认二次核验
          </button>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import {
  listMyActiveAttendanceSessions,
  studentAttendanceCheckIn,
  studentAttendanceRecheck
} from "@/common/api.js"
import { ensureLocalDeviceProfile } from "@/common/device.js"
import { requireRole } from "@/common/session.js"

const TEACHER_ATTENDANCE_PAGE_URL = "/pages/teacher/attendance"

export default {
  data() {
    return {
      loading: false,
      sessions: [],
      draftMap: {}
    }
  },
  onShow() {
    const session = requireRole(["student"], {
      message: "仅限学生访问",
      fallbackUrl: TEACHER_ATTENDANCE_PAGE_URL
    })
    if (!session) return
    this.loadData()
  },
  methods: {
    ensureDraft(sessionId) {
      const key = String(sessionId || "")
      if (!this.draftMap[key]) {
        this.$set(this.draftMap, key, {
          attendanceCode: "",
          seatCode: "",
          recheckCode: ""
        })
      }
      return this.draftMap[key]
    },
    async loadData() {
      if (this.loading) return
      this.loading = true
      try {
        const res = await listMyActiveAttendanceSessions()
        const payload = (res && res.data) || {}
        if (!payload.ok) {
          uni.showToast({ title: payload.msg || "加载失败", icon: "none" })
          return
        }
        const rows = Array.isArray(payload.data) ? payload.data : []
        this.sessions = rows
        rows.forEach((item) => this.ensureDraft(item.id))
      } catch (e) {
        uni.showToast({ title: "加载失败", icon: "none" })
      } finally {
        this.loading = false
      }
    },
    antiCheatText(item) {
      const parts = []
      if (item && item.requireLocation) parts.push("地理位置")
      if (item && item.requireDeviceBinding) parts.push("设备绑定")
      if (item && item.requireSeatCode) parts.push("座位号")
      if (item && item.recheckActive) parts.push("二次核验")
      return parts.join(" / ") || "基础签到"
    },
    statusText(status) {
      if (status === "present") return "已签到"
      if (status === "suspected") return "疑似异常"
      if (status === "rejected") return "已驳回"
      return "待签到"
    },
    statusTone(status) {
      if (status === "present") return "success"
      if (status === "suspected") return "warning"
      if (status === "rejected") return "danger"
      return "info"
    },
    getLocationPayload() {
      return new Promise((resolve) => {
        uni.getLocation({
          type: "gcj02",
          success: (res) => resolve({ latitude: res.latitude, longitude: res.longitude }),
          fail: () => resolve({})
        })
      })
    },
    async buildCheckInPayload(item, draft) {
      const payload = {
        attendanceCode: draft.attendanceCode,
        seatCode: draft.seatCode
      }
      if (item && item.requireDeviceBinding) {
        const device = ensureLocalDeviceProfile()
        payload.deviceId = device.deviceId
        payload.deviceName = device.deviceName
        payload.networkName = device.platform
      }
      if (item && item.requireLocation) {
        Object.assign(payload, await this.getLocationPayload())
      }
      return payload
    },
    async submitCheckIn(item) {
      const draft = this.ensureDraft(item.id)
      try {
        const res = await studentAttendanceCheckIn(item.id, await this.buildCheckInPayload(item, draft))
        const payload = (res && res.data) || {}
        if (!payload.ok) {
          uni.showToast({ title: payload.msg || "签到失败", icon: "none" })
          return
        }
        uni.showToast({ title: "签到成功", icon: "success" })
        this.loadData()
      } catch (e) {
        uni.showToast({ title: "签到失败", icon: "none" })
      }
    },
    async submitRecheck(item) {
      const draft = this.ensureDraft(item.id)
      const payloadData = {
        recheckCode: draft.recheckCode,
        seatCode: draft.seatCode
      }
      if (item && item.requireDeviceBinding) {
        const device = ensureLocalDeviceProfile()
        payloadData.deviceId = device.deviceId
      }
      try {
        const res = await studentAttendanceRecheck(item.id, payloadData)
        const payload = (res && res.data) || {}
        if (!payload.ok) {
          uni.showToast({ title: payload.msg || "二次核验失败", icon: "none" })
          return
        }
        uni.showToast({ title: "核验成功", icon: "success" })
        this.loadData()
      } catch (e) {
        uni.showToast({ title: "核验失败", icon: "none" })
      }
    }
  }
}
</script>

<style lang="scss">
.attendancePage {
  padding-bottom: 24px;
}

.heroCard,
.sessionCard {
  border: 1px solid rgba(37, 99, 235, 0.14);
}

.sessionTitle {
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
}

.meta {
  margin-top: 6px;
  color: #64748b;
  font-size: 12px;
}

.meta.warning {
  color: #b42318;
}

.fieldInput {
  margin-top: 10px;
}

.actions {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.miniBtn {
  min-height: 30px;
  line-height: 30px;
  padding: 0 10px;
  border-radius: 9px;
  font-size: 12px;
}
</style>

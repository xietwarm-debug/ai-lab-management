<template>
  <view class="container attendancePage">
    <view class="stack">
      <view class="card heroCard">
        <view class="rowBetween">
          <view>
            <view class="title">Class Check-in</view>
            <view class="subtitle">Join open sessions and submit the current code</view>
          </view>
          <button class="btnSecondary miniBtn" size="mini" :loading="loading" @click="loadData">Refresh</button>
        </view>
      </view>

      <view class="emptyState" v-if="!loading && sessions.length === 0">
        <view class="emptyTitle">No open sessions</view>
        <view class="emptySub">Your teacher will publish open attendance sessions here.</view>
      </view>

      <view class="card sessionCard" v-for="item in sessions" :key="item.id">
        <view class="rowBetween">
          <view class="sessionTitle">{{ item.courseName || "Attendance session" }}</view>
          <view class="statusTag" :class="statusTone(item.myRecord && item.myRecord.status)">
            {{ statusText(item.myRecord && item.myRecord.status) }}
          </view>
        </view>
        <view class="meta">Lab: {{ item.labName || "Not assigned" }}</view>
        <view class="meta">Window: {{ item.startAt || "-" }} to {{ item.endAt || "-" }}</view>
        <view class="meta">Anti-cheat: {{ antiCheatText(item) }}</view>
        <view class="meta" v-if="item.myRecord && item.myRecord.finalCheckinAt">
          Last check-in: {{ item.myRecord.finalCheckinAt }}
        </view>
        <view class="meta warning" v-if="item.myRecord && item.myRecord.suspicionReason">
          Risk: {{ item.myRecord.suspicionReason }}
        </view>

        <input
          class="inputBase fieldInput"
          v-model.trim="draftMap[item.id].attendanceCode"
          maxlength="16"
          placeholder="Attendance code"
        />
        <input
          class="inputBase fieldInput"
          v-model.trim="draftMap[item.id].seatCode"
          maxlength="32"
          :placeholder="item.requireSeatCode ? 'Seat code' : 'Seat code (optional)'"
        />
        <input
          v-if="item.recheckActive"
          class="inputBase fieldInput"
          v-model.trim="draftMap[item.id].recheckCode"
          maxlength="16"
          placeholder="Recheck code"
        />

        <view class="actions">
          <button class="btnPrimary miniBtn" size="mini" @click="submitCheckIn(item)">Check in</button>
          <button v-if="item.recheckActive" class="btnSecondary miniBtn" size="mini" @click="submitRecheck(item)">
            Confirm recheck
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
      message: "Students only",
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
          uni.showToast({ title: payload.msg || "Load failed", icon: "none" })
          return
        }
        const rows = Array.isArray(payload.data) ? payload.data : []
        this.sessions = rows
        rows.forEach((item) => this.ensureDraft(item.id))
      } catch (e) {
        uni.showToast({ title: "Load failed", icon: "none" })
      } finally {
        this.loading = false
      }
    },
    antiCheatText(item) {
      const parts = []
      if (item && item.requireLocation) parts.push("Location")
      if (item && item.requireDeviceBinding) parts.push("Device binding")
      if (item && item.requireSeatCode) parts.push("Seat code")
      if (item && item.recheckActive) parts.push("Recheck")
      return parts.join(" / ") || "Basic"
    },
    statusText(status) {
      if (status === "present") return "Checked in"
      if (status === "suspected") return "Needs review"
      if (status === "rejected") return "Rejected"
      return "Pending"
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
          uni.showToast({ title: payload.msg || "Check-in failed", icon: "none" })
          return
        }
        uni.showToast({ title: "Check-in saved", icon: "success" })
        this.loadData()
      } catch (e) {
        uni.showToast({ title: "Check-in failed", icon: "none" })
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
          uni.showToast({ title: payload.msg || "Recheck failed", icon: "none" })
          return
        }
        uni.showToast({ title: "Recheck saved", icon: "success" })
        this.loadData()
      } catch (e) {
        uni.showToast({ title: "Recheck failed", icon: "none" })
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

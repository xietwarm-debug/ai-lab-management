<template>
  <view class="container teacherAttendancePage">
    <view class="stack">
      <view class="card heroCard">
        <view class="rowBetween">
          <view>
            <view class="title">考勤管理控制台</view>
            <view class="subtitle">创建考勤、刷新签到码、发起二次核验及管理签到记录</view>
          </view>
          <button class="btnSecondary miniBtn" size="mini" :loading="loading" @click="bootstrap">刷新</button>
        </view>
      </view>

      <view class="card formCard">
        <view class="cardTitle">发起课堂考勤</view>
        <picker mode="selector" :range="courseOptions" range-key="label" @change="onCourseChange">
          <view class="pickerField">{{ selectedCourseLabel }}</view>
        </picker>
        <picker mode="selector" :range="labOptions" range-key="label" @change="onLabChange">
          <view class="pickerField">{{ selectedLabLabel }}</view>
        </picker>
        <view class="grid2">
          <input class="inputBase" v-model.number="form.durationMinutes" type="number" placeholder="考勤时长 (分钟)" />
          <input class="inputBase" v-model.number="form.geoRadiusMeter" type="number" placeholder="地理围栏半径 (米)" />
        </view>
        <input class="inputBase" v-model.trim="form.seatCodePrefix" maxlength="16" placeholder="座位号前缀 (可选)" />
        <input class="inputBase" v-model.trim="form.allowedNetworkHint" maxlength="64" placeholder="网络提示 (可选)" />
        <textarea class="textareaBase" v-model.trim="form.note" placeholder="备注信息 (可选)" />
        <view class="toggleRow">
          <label><checkbox :checked="form.requireLocation" @click="form.requireLocation = !form.requireLocation" /> 地理位置效验</label>
          <label><checkbox :checked="form.requireDeviceBinding" @click="form.requireDeviceBinding = !form.requireDeviceBinding" /> 设备绑定防伪</label>
          <label><checkbox :checked="form.requireSeatCode" @click="form.requireSeatCode = !form.requireSeatCode" /> 座位号验证</label>
        </view>
        <view class="actions">
          <button class="btnPrimary miniBtn" size="mini" :loading="creating" @click="createSession">发起签到</button>
        </view>
      </view>

      <view class="card sessionCard" v-for="item in sessions" :key="item.id">
        <view class="rowBetween">
          <view class="sessionTitle">{{ item.courseName || "课堂考勤" }}</view>
          <view class="statusTag" :class="item.status === 'open' ? 'warning' : 'success'">
            {{ item.status === "open" ? "进行中" : "已结束" }}
          </view>
        </view>
        <view class="meta">实验室: {{ item.labName || "未分配" }}</view>
        <view class="meta">签到码: {{ item.attendanceCode || "-" }} | 核验码: {{ item.recheckCode || "-" }}</view>
        <view class="meta">时间窗口: {{ item.startAt || "-" }} 至 {{ item.endAt || "-" }}</view>
        <view class="meta">
          统计: 已到 {{ item.summary && item.summary.present || 0 }},
          疑似异常 {{ item.summary && item.summary.suspected || 0 }},
          待核验 {{ item.summary && item.summary.recheckPending || 0 }}
        </view>

        <view class="actions">
          <button class="btnSecondary miniBtn" size="mini" @click="refreshCode(item)">刷新签到码</button>
          <button class="btnGhost miniBtn" size="mini" @click="startRecheck(item)">抽查核验</button>
          <button class="btnSecondary miniBtn" size="mini" @click="toggleDetail(item)">
            {{ expandedId === item.id ? "收起详情" : "查看详情" }}
          </button>
          <button v-if="item.status === 'open'" class="btnDanger miniBtn" size="mini" @click="closeSession(item)">
            结束考勤
          </button>
        </view>

        <view class="detailBox" v-if="expandedId === item.id">
          <view class="muted" v-if="detailLoading">加载中...</view>
          <view class="emptyText muted" v-else-if="detailRecords.length === 0">暂无签到记录</view>
          <view class="recordList" v-else>
            <view class="recordItem" v-for="record in detailRecords" :key="record.id">
              <view class="rowBetween">
                <view class="recordTitle">{{ record.studentDisplayName || record.studentUserName || "-" }}</view>
                <view
                  class="statusTag"
                  :class="record.status === 'present' ? 'success' : record.status === 'suspected' ? 'warning' : 'danger'"
                >
                  {{ record.status === "present" ? "已到" : record.status === "suspected" ? "疑似异常" : "已驳回" }}
                </view>
              </view>
              <view class="meta">座位号: {{ record.seatCode || "-" }} | 位移偏差: {{ record.distanceMeter || "-" }} 米</view>
              <view class="meta">打卡时间: {{ record.finalCheckinAt || "-" }}</view>
              <view class="meta warning" v-if="record.suspicionReason">风险提示: {{ record.suspicionReason }}</view>
              <view class="actions">
                <button class="btnPrimary miniBtn" size="mini" @click="resolveRecord(record, 'present')">标为正常</button>
                <button class="btnSecondary miniBtn" size="mini" @click="resolveRecord(record, 'suspected')">保留异常</button>
                <button class="btnDanger miniBtn" size="mini" @click="resolveRecord(record, 'rejected')">驳回签到</button>
              </view>
            </view>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import {
  listLabs,
  teacherCloseAttendanceSession,
  teacherCreateAttendanceSession,
  teacherGetAttendanceSessionDetail,
  teacherListAttendanceSessions,
  teacherRefreshAttendanceCode,
  teacherResolveAttendanceRecord,
  teacherStartAttendanceRecheck,
  teacherListCourses
} from "@/common/api.js"
import { requireRole } from "@/common/session.js"

const STUDENT_ATTENDANCE_PAGE_URL = "/pages/student/attendance"

export default {
  data() {
    return {
      loading: false,
      creating: false,
      detailLoading: false,
      expandedId: 0,
      detailRecords: [],
      courses: [],
      labs: [],
      sessions: [],
      form: {
        courseId: 0,
        labId: 0,
        durationMinutes: 15,
        geoRadiusMeter: 150,
        seatCodePrefix: "",
        allowedNetworkHint: "",
        note: "",
        requireLocation: true,
        requireDeviceBinding: true,
        requireSeatCode: true
      }
    }
  },
  computed: {
    courseOptions() {
      const rows = Array.isArray(this.courses) ? this.courses : []
      return rows.map((item) => ({ label: item.name || `课程 #${item.id}`, value: Number(item.id || 0) }))
    },
    labOptions() {
      const rows = Array.isArray(this.labs) ? this.labs : []
      return [{ label: "无实验室", value: 0 }].concat(
        rows.map((item) => ({
          label: item.labName || item.name || `实验室 #${item.labId || item.id}`,
          value: Number(item.labId || item.id || 0)
        }))
      )
    },
    selectedCourseLabel() {
      const hit = this.courseOptions.find((item) => Number(item.value) === Number(this.form.courseId || 0))
      return hit ? hit.label : "选择课程"
    },
    selectedLabLabel() {
      const hit = this.labOptions.find((item) => Number(item.value) === Number(this.form.labId || 0))
      return hit ? hit.label : "未配置实验室"
    }
  },
  onLoad(options) {
    const courseId = Number((options && options.courseId) || 0)
    if (Number.isFinite(courseId) && courseId > 0) this.form.courseId = courseId
  },
  onShow() {
    const session = requireRole(["teacher", "admin"], {
      message: "仅限教师和管理员访问",
      fallbackUrl: STUDENT_ATTENDANCE_PAGE_URL
    })
    if (!session) return
    this.bootstrap()
  },
  methods: {
    async bootstrap() {
      if (this.loading) return
      this.loading = true
      try {
        const [courseRes, labRes, sessionRes] = await Promise.all([
          teacherListCourses(),
          listLabs(),
          teacherListAttendanceSessions()
        ])
        const coursePayload = (courseRes && courseRes.data) || {}
        const labPayload = (labRes && labRes.data) || {}
        const sessionPayload = (sessionRes && sessionRes.data) || {}
        this.courses = Array.isArray(coursePayload.data) ? coursePayload.data : []
        this.labs = Array.isArray(labPayload.data) ? labPayload.data : []
        this.sessions = Array.isArray(sessionPayload.data) ? sessionPayload.data : []
        if (!this.form.courseId && this.courses.length > 0) {
          this.form.courseId = Number(this.courses[0].id || 0)
        }
      } catch (e) {
        uni.showToast({ title: "加载失败", icon: "none" })
      } finally {
        this.loading = false
      }
    },
    onCourseChange(e) {
      const index = Number(e && e.detail && e.detail.value)
      const option = this.courseOptions[index]
      this.form.courseId = Number((option && option.value) || 0)
    },
    onLabChange(e) {
      const index = Number(e && e.detail && e.detail.value)
      const option = this.labOptions[index]
      this.form.labId = Number((option && option.value) || 0)
    },
    async buildSessionLocationPayload() {
      if (!this.form.requireLocation) return {}
      return new Promise((resolve) => {
        uni.getLocation({
          type: "gcj02",
          success: (res) => resolve({ geoLat: res.latitude, geoLng: res.longitude }),
          fail: () => resolve({})
        })
      })
    },
    async createSession() {
      if (!this.form.courseId) {
        uni.showToast({ title: "请选择一门课程", icon: "none" })
        return
      }
      this.creating = true
      try {
        const res = await teacherCreateAttendanceSession({
          ...this.form,
          ...(await this.buildSessionLocationPayload())
        })
        const payload = (res && res.data) || {}
        if (!payload.ok) {
          uni.showToast({ title: payload.msg || "发起失败", icon: "none" })
          return
        }
        uni.showToast({ title: "考勤已发起", icon: "success" })
        await this.bootstrap()
      } catch (e) {
        uni.showToast({ title: "发起操作失败", icon: "none" })
      } finally {
        this.creating = false
      }
    },
    async refreshCode(item) {
      const res = await teacherRefreshAttendanceCode(item.id)
      const payload = (res && res.data) || {}
      if (!payload.ok) {
        uni.showToast({ title: payload.msg || "刷新失败", icon: "none" })
        return
      }
      uni.showToast({ title: "签到码已刷新", icon: "success" })
      await this.bootstrap()
    },
    async startRecheck(item) {
      const res = await teacherStartAttendanceRecheck(item.id, { ratio: 0.3, windowSeconds: 60 })
      const payload = (res && res.data) || {}
      if (!payload.ok) {
        uni.showToast({ title: payload.msg || "抽查发起失败", icon: "none" })
        return
      }
      uni.showToast({ title: "已发起抽查核验", icon: "success" })
      await this.bootstrap()
    },
    async closeSession(item) {
      const res = await teacherCloseAttendanceSession(item.id)
      const payload = (res && res.data) || {}
      if (!payload.ok) {
        uni.showToast({ title: payload.msg || "结束考勤失败", icon: "none" })
        return
      }
      uni.showToast({ title: "该时段已结束", icon: "success" })
      this.expandedId = 0
      this.detailRecords = []
      await this.bootstrap()
    },
    async loadDetail(sessionId) {
      const res = await teacherGetAttendanceSessionDetail(sessionId)
      const payload = (res && res.data) || {}
      this.detailRecords = payload.ok && payload.data && Array.isArray(payload.data.records) ? payload.data.records : []
    },
    async toggleDetail(item) {
      if (this.expandedId === item.id) {
        this.expandedId = 0
        this.detailRecords = []
        return
      }
      this.expandedId = item.id
      this.detailLoading = true
      try {
        await this.loadDetail(item.id)
      } finally {
        this.detailLoading = false
      }
    },
    async resolveRecord(record, status) {
      const res = await teacherResolveAttendanceRecord(record.id, { status })
      const payload = (res && res.data) || {}
      if (!payload.ok) {
        uni.showToast({ title: payload.msg || "更新失败", icon: "none" })
        return
      }
      uni.showToast({ title: "状态已更新", icon: "success" })
      const expandedId = this.expandedId
      await this.bootstrap()
      if (!expandedId) return
      this.expandedId = expandedId
      this.detailLoading = true
      try {
        await this.loadDetail(expandedId)
      } finally {
        this.detailLoading = false
      }
    }
  }
}
</script>

<style lang="scss">
.teacherAttendancePage {
  padding-bottom: 24px;
}

.heroCard,
.formCard,
.sessionCard {
  border: 1px solid rgba(245, 158, 11, 0.2);
}

.grid2 {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  margin-top: 10px;
}

.pickerField,
.inputBase,
.textareaBase {
  margin-top: 10px;
}

.toggleRow {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  color: #475569;
  font-size: 13px;
}

.sessionTitle,
.recordTitle {
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
}

.meta,
.emptyText {
  margin-top: 6px;
  color: #64748b;
  font-size: 12px;
}

.meta.warning {
  color: #b42318;
}

.actions {
  margin-top: 12px;
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.detailBox {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(148, 163, 184, 0.16);
}

.recordList {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.recordItem {
  padding: 12px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(148, 163, 184, 0.16);
}

.miniBtn {
  min-height: 30px;
  line-height: 30px;
  padding: 0 10px;
  border-radius: 9px;
  font-size: 12px;
}
</style>

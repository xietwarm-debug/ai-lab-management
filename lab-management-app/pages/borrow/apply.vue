<template>
  <view class="container borrowApplyPage" :class="themeClass">
    <view class="stack">
      <view class="card heroCard">
        <view class="title">资产借用申请</view>
        <view class="subtitle">填写借用信息并提交审批</view>
      </view>

      <view class="card formCard">
        <view class="label">资产</view>
        <picker :range="equipments" range-key="displayName" :value="selectedIndex" @change="onEquipmentChange">
          <view class="valueBox">{{ selectedEquipmentText }}</view>
        </picker>

        <view class="label">申请人账号</view>
        <input class="inputBase" v-model="userName" disabled />

        <view class="label">申请人姓名</view>
        <input class="inputBase" v-model.trim="form.applicantName" placeholder="请输入申请人姓名" maxlength="64" />

        <view class="label">借用日期</view>
        <picker mode="date" :value="form.borrowDate" @change="onBorrowDateChange">
          <view class="calendarBtn">{{ form.borrowDate || "请选择借用日期" }}</view>
        </picker>

        <view class="label">借用时间</view>
        <picker mode="time" :value="form.borrowTime" @change="onBorrowTimeChange">
          <view class="calendarBtn">{{ form.borrowTime || "请选择借用时间" }}</view>
        </picker>

        <view class="label">归还日期</view>
        <picker mode="date" :value="form.returnDate" @change="onReturnDateChange">
          <view class="calendarBtn">{{ form.returnDate || "请选择归还日期" }}</view>
        </picker>

        <view class="label">归还时间</view>
        <picker mode="time" :value="form.returnTime" @change="onReturnTimeChange">
          <view class="calendarBtn">{{ form.returnTime || "请选择归还时间" }}</view>
        </picker>

        <view class="label">申请用途</view>
        <textarea class="textareaBase" v-model.trim="form.purpose" maxlength="255" placeholder="请输入申请用途" />
        <view class="muted">{{ (form.purpose || "").length }} / 255</view>

        <view v-if="isStudent">
          <view class="label">学号</view>
          <input class="inputBase" v-model.trim="form.studentNo" maxlength="64" placeholder="请输入学号" />
          <view class="label">班级</view>
          <input class="inputBase" v-model.trim="form.className" maxlength="64" placeholder="请输入班级" />
        </view>

        <view v-if="isTeacher">
          <view class="label">工号</view>
          <input class="inputBase" v-model.trim="form.jobNo" maxlength="64" placeholder="请输入工号" />
        </view>
      </view>

      <button class="btnPrimary submitBtn" :disabled="submitting || loading" @click="submit">
        {{ submitting ? "提交中..." : "提交申请" }}
      </button>
    </view>
  </view>
</template>

<script>
import { apiRequest, createBorrowRequest } from "@/common/api.js"
import { themePageMixin } from "@/common/theme.js"

function toDateTimeText(dateText, timeText) {
  const d = String(dateText || "").trim()
  const t = String(timeText || "").trim()
  if (!d || !t) return ""
  return `${d} ${t}`
}

function toMillis(text) {
  const raw = String(text || "").trim().replace(" ", "T")
  const val = Date.parse(raw)
  return Number.isFinite(val) ? val : 0
}

export default {
  mixins: [themePageMixin],
  data() {
    return {
      loading: false,
      submitting: false,
      userName: "",
      role: "",
      equipments: [],
      selectedIndex: 0,
      form: {
        equipmentId: 0,
        applicantName: "",
        borrowDate: "",
        borrowTime: "08:00",
        returnDate: "",
        returnTime: "17:00",
        purpose: "",
        studentNo: "",
        className: "",
        jobNo: ""
      }
    }
  },
  computed: {
    isStudent() {
      return this.role === "student"
    },
    isTeacher() {
      return this.role === "teacher"
    },
    selectedEquipment() {
      if (!Array.isArray(this.equipments) || this.equipments.length === 0) return null
      const idx = Math.max(0, Math.min(this.selectedIndex, this.equipments.length - 1))
      return this.equipments[idx] || null
    },
    selectedEquipmentText() {
      const item = this.selectedEquipment
      return item ? item.displayName : "请选择资产"
    }
  },
  onShow() {
    const session = uni.getStorageSync("session") || {}
    if (!session.username || !session.token) {
      uni.reLaunch({ url: "/pages/login/login" })
      return
    }
    this.userName = String(session.username || "").trim()
    this.role = String(session.role || "").trim().toLowerCase()
    this.bootstrap()
  },
  methods: {
    onEquipmentChange(e) {
      const idx = Number((e && e.detail && e.detail.value) || 0)
      this.selectedIndex = Number.isFinite(idx) ? idx : 0
      const item = this.selectedEquipment
      this.form.equipmentId = Number((item && item.id) || 0)
    },
    onBorrowDateChange(e) {
      this.form.borrowDate = (e && e.detail && e.detail.value) || ""
    },
    onBorrowTimeChange(e) {
      this.form.borrowTime = (e && e.detail && e.detail.value) || ""
    },
    onReturnDateChange(e) {
      this.form.returnDate = (e && e.detail && e.detail.value) || ""
    },
    onReturnTimeChange(e) {
      this.form.returnTime = (e && e.detail && e.detail.value) || ""
    },
    async bootstrap() {
      if (this.loading) return
      this.loading = true
      try {
        await Promise.all([this.fetchProfile(), this.fetchEquipments()])
      } finally {
        this.loading = false
      }
    },
    async fetchProfile() {
      try {
        const res = await apiRequest({ url: "/me/profile", method: "GET" })
        const payload = (res && res.data) || {}
        if (!payload.ok || !payload.data) return
        const profile = payload.data || {}
        this.form.applicantName = String(profile.nickname || this.userName || "").trim()
        this.form.studentNo = String(profile.studentNo || "").trim()
        this.form.className = String(profile.className || "").trim()
        this.form.jobNo = String(profile.jobNo || "").trim()
      } catch (e) {}
    },
    async fetchEquipments() {
      const res = await apiRequest({
        url: "/equipments?status=in_service&borrowable=1&page=1&pageSize=300",
        method: "GET"
      })
      const payload = (res && res.data) || {}
      if (!payload.ok) {
        this.equipments = []
        return
      }
      const rows = Array.isArray(payload.data) ? payload.data : []
      this.equipments = rows
        .filter((x) => !x.isBorrowed && String(x.status || "") !== "scrapped" && x.allowBorrow !== false)
        .map((x) => ({
          ...x,
          displayName: `${x.assetCode || "-"} · ${x.name || "-"} · ${x.labName || "-"}`
        }))
      this.selectedIndex = 0
      const first = this.selectedEquipment
      this.form.equipmentId = Number((first && first.id) || 0)
    },
    validate() {
      if (!this.form.equipmentId) {
        uni.showToast({ title: "请选择资产", icon: "none" })
        return false
      }
      if (!this.form.applicantName) {
        uni.showToast({ title: "请输入申请人姓名", icon: "none" })
        return false
      }
      const borrowStartAt = toDateTimeText(this.form.borrowDate, this.form.borrowTime)
      const expectedReturnAt = toDateTimeText(this.form.returnDate, this.form.returnTime)
      if (!borrowStartAt) {
        uni.showToast({ title: "请选择借用时间", icon: "none" })
        return false
      }
      if (!expectedReturnAt) {
        uni.showToast({ title: "请选择归还时间", icon: "none" })
        return false
      }
      const startMs = toMillis(borrowStartAt)
      const endMs = toMillis(expectedReturnAt)
      if (!startMs || !endMs || endMs <= startMs) {
        uni.showToast({ title: "归还时间需晚于借用时间", icon: "none" })
        return false
      }
      if (!this.form.purpose) {
        uni.showToast({ title: "请输入申请用途", icon: "none" })
        return false
      }
      if (this.isStudent) {
        if (!this.form.studentNo) {
          uni.showToast({ title: "学生需填写学号", icon: "none" })
          return false
        }
        if (!this.form.className) {
          uni.showToast({ title: "学生需填写班级", icon: "none" })
          return false
        }
      }
      if (this.isTeacher && !this.form.jobNo) {
        uni.showToast({ title: "教师需填写工号", icon: "none" })
        return false
      }
      return true
    },
    async submit() {
      if (this.submitting || !this.validate()) return
      this.submitting = true
      try {
        const payload = {
          equipmentId: Number(this.form.equipmentId || 0),
          applicantName: this.form.applicantName,
          borrowStartAt: toDateTimeText(this.form.borrowDate, this.form.borrowTime),
          expectedReturnAt: toDateTimeText(this.form.returnDate, this.form.returnTime),
          purpose: this.form.purpose,
          studentNo: this.form.studentNo,
          className: this.form.className,
          jobNo: this.form.jobNo
        }
        const res = await createBorrowRequest(payload)
        const body = (res && res.data) || {}
        if (!body.ok || !body.data) {
          uni.showToast({ title: body.msg || "提交失败", icon: "none" })
          return
        }
        const info = body.data || {}
        const riskText = info.riskFlag ? "\n注意：管理员将收到逾期历史提醒。" : ""
        uni.showModal({
          title: "提交成功",
          content: `申请编号：${info.id || "-"}\n状态：待审批${riskText}`,
          showCancel: false,
          success: () => {
            uni.redirectTo({ url: "/pages/my/borrowings?status=pending" })
          }
        })
      } catch (e) {
        uni.showToast({ title: "提交失败", icon: "none" })
      } finally {
        this.submitting = false
      }
    }
  }
}
</script>

<style lang="scss">
.borrowApplyPage {
  padding-bottom: 20px;
}

.heroCard {
  border: 1px solid var(--color-border-focus);
  background: var(--color-bg-soft);
}

.formCard {
  border: 1px solid var(--color-border-primary);
}

.valueBox {
  font-weight: 600;
  padding: 10px 12px;
  background: var(--color-bg-soft);
  border: 1px solid var(--color-border-primary);
  border-radius: 12px;
  color: var(--color-text-primary);
}

.submitBtn {
  width: 100%;
}
</style>

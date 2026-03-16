<template>
  <view class="container taskFormPage">
    <view class="stack">
      <view class="card heroCard">
        <view class="rowBetween heroTop">
          <view>
            <view class="title">新建实验任务</view>
            <view class="subtitle">{{ courseName || `课程 #${courseId || "-"}` }}</view>
          </view>
          <button class="btnSecondary miniBtn" size="mini" @click="goBack">返回</button>
        </view>
      </view>

      <view class="card loadingCard" v-if="loadingCourse">
        <view class="muted">正在加载课程信息...</view>
      </view>

      <view class="card formCard" v-else>
        <view class="label">任务模板（可选）</view>
        <view class="deadlineRow">
          <picker :range="templatePickerRange" range-key="label" :value="templatePickerIndex" @change="onTemplateChange">
            <view class="calendarBtn">{{ selectedTemplateLabel }}</view>
          </picker>
          <button class="btnGhost miniBtn" size="mini" :disabled="!selectedTemplateItem" @click="applyTemplate">套用模板</button>
        </view>
        <view class="muted" v-if="loadingTemplates">正在加载模板...</view>

        <view class="label">任务标题 *</view>
        <input class="inputBase" v-model.trim="form.title" maxlength="160" placeholder="例如：实验一：环境配置" />
        <view class="fieldError" v-if="errors.title">{{ errors.title }}</view>

        <view class="label">实验室（可选）</view>
        <view class="deadlineRow">
          <picker :range="labPickerRange" range-key="name" :value="labPickerIndex" @change="onLabChange">
            <view class="calendarBtn">{{ selectedLabName }}</view>
          </picker>
          <button class="btnGhost miniBtn" size="mini" @click="clearLab">清空</button>
        </view>
        <view class="muted" v-if="loadingLabs">正在加载实验室列表...</view>
        <view class="fieldError" v-if="errors.labId">{{ errors.labId }}</view>

        <view class="label">截止日期（可选）</view>
        <view class="deadlineRow">
          <picker mode="date" :value="form.deadlineDate" @change="onDeadlineDateChange">
            <view class="calendarBtn">{{ form.deadlineDate || "选择日期" }}</view>
          </picker>
          <picker mode="time" :value="form.deadlineTime" @change="onDeadlineTimeChange">
            <view class="calendarBtn">{{ form.deadlineTime || "选择时间" }}</view>
          </picker>
          <button class="btnGhost miniBtn" size="mini" @click="clearDeadline">清空</button>
        </view>
        <view class="fieldError" v-if="errors.deadline">{{ errors.deadline }}</view>

        <view class="label">任务说明</view>
        <textarea
          class="textareaBase"
          v-model.trim="form.description"
          maxlength="5000"
          placeholder="可选，补充任务要求、评分方式、提交规范"
        />
        <view class="fieldError" v-if="errors.description">{{ errors.description }}</view>

        <view class="actions">
          <button class="btnPrimary miniBtn" size="mini" :disabled="saving" @click="submit">
            {{ saving ? "提交中..." : "创建任务" }}
          </button>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { getApiListData, listCourseTasks, listLabs, teacherCreateCourseTask, teacherListTaskTemplates } from "@/common/api.js"

export default {
  data() {
    return {
      courseId: 0,
      courseName: "",
      loadingCourse: false,
      loadingLabs: false,
      loadingTemplates: false,
      saving: false,
      labOptions: [],
      templateTaskId: 0,
      templateOptions: [],
      form: {
        title: "",
        description: "",
        labId: null,
        deadlineDate: "",
        deadlineTime: ""
      },
      errors: {
        title: "",
        description: "",
        labId: "",
        deadline: ""
      }
    }
  },
  computed: {
    labPickerRange() {
      return [{ id: 0, name: "请选择实验室" }, ...(Array.isArray(this.labOptions) ? this.labOptions : [])]
    },
    labPickerIndex() {
      const currentId = Number(this.form.labId || 0)
      if (!currentId) return 0
      const idx = this.labPickerRange.findIndex((item) => Number(item.id || 0) === currentId)
      return idx >= 0 ? idx : 0
    },
    selectedLabName() {
      const option = this.labPickerRange[this.labPickerIndex] || {}
      return String(option.name || "请选择实验室")
    },
    templatePickerRange() {
      return [{ id: 0, label: "选择模板（可选）" }, ...(Array.isArray(this.templateOptions) ? this.templateOptions : [])]
    },
    templatePickerIndex() {
      const id = Number(this.templateTaskId || 0)
      if (!id) return 0
      const idx = this.templatePickerRange.findIndex((item) => Number(item.id || 0) === id)
      return idx >= 0 ? idx : 0
    },
    selectedTemplateLabel() {
      const option = this.templatePickerRange[this.templatePickerIndex] || {}
      return String(option.label || "选择模板（可选）")
    },
    selectedTemplateItem() {
      const id = Number(this.templateTaskId || 0)
      if (!id) return null
      return (this.templateOptions || []).find((item) => Number(item.id || 0) === id) || null
    }
  },
  onLoad(options) {
    const raw = Number(options && options.courseId)
    this.courseId = Number.isFinite(raw) && raw > 0 ? Math.floor(raw) : 0
  },
  onShow() {
    if (!this.ensureRole()) return
    this.fetchCourse()
    this.fetchLabs()
    this.fetchTemplates()
  },
  methods: {
    ensureRole() {
      const session = uni.getStorageSync("session") || {}
      const role = String(session.role || "").trim()
      const username = String(session.username || "").trim()
      if (!session.token || !username) {
        uni.showToast({ title: "请先登录", icon: "none" })
        uni.reLaunch({ url: "/pages/login/login" })
        return false
      }
      if (role !== "teacher" && role !== "admin") {
        uni.showToast({ title: "无权限", icon: "none" })
        uni.switchTab({ url: "/pages/index/index" })
        return false
      }
      if (!this.courseId) {
        uni.showToast({ title: "课程参数无效", icon: "none" })
        setTimeout(() => this.goBack(), 220)
        return false
      }
      return true
    },
    goBack() {
      const pages = typeof getCurrentPages === "function" ? getCurrentPages() || [] : []
      if (pages.length > 1) {
        uni.navigateBack()
      } else if (this.courseId) {
        uni.reLaunch({ url: `/pages/teacher/course_detail?courseId=${this.courseId}` })
      } else {
        uni.reLaunch({ url: "/pages/teacher/courses" })
      }
    },
    async fetchCourse() {
      if (!this.courseId || this.loadingCourse) return
      this.loadingCourse = true
      try {
        const res = await listCourseTasks(this.courseId)
        const payload = (res && res.data) || {}
        if (!payload.ok || !payload.data || !payload.data.course) {
          uni.showToast({ title: payload.msg || "课程不存在", icon: "none" })
          setTimeout(() => this.goBack(), 220)
          return
        }
        const course = payload.data.course || {}
        this.courseName = String(course.name || "")
      } catch (e) {
        uni.showToast({ title: "加载失败", icon: "none" })
      } finally {
        this.loadingCourse = false
      }
    },
    async fetchLabs() {
      if (this.loadingLabs) return
      this.loadingLabs = true
      try {
        const res = await listLabs({})
        const rows = getApiListData(res && res.data)
        this.labOptions = rows
          .map((item) => {
            const id = Number(item && item.id)
            const name = String((item && item.name) || "").trim()
            if (!Number.isFinite(id) || id <= 0 || !name) return null
            return { id: Math.floor(id), name }
          })
          .filter(Boolean)
      } catch (e) {
        this.labOptions = []
        uni.showToast({ title: "实验室列表加载失败", icon: "none" })
      } finally {
        this.loadingLabs = false
      }
    },
    async fetchTemplates() {
      if (this.loadingTemplates) return
      this.loadingTemplates = true
      try {
        const res = await teacherListTaskTemplates({ limit: 60 })
        const payload = (res && res.data) || {}
        if (!payload.ok) {
          this.templateOptions = []
          return
        }
        const rows = Array.isArray(payload.data) ? payload.data : []
        this.templateOptions = rows
          .map((item) => {
            const id = Number(item && item.id)
            const title = String((item && item.title) || "").trim()
            if (!Number.isFinite(id) || id <= 0 || !title) return null
            const courseName = String((item && item.courseName) || "").trim()
            return {
              id: Math.floor(id),
              title,
              description: String((item && item.description) || ""),
              labId: Number(item && item.labId) > 0 ? Number(item.labId) : null,
              deadline: String((item && item.deadline) || ""),
              label: `${title}${courseName ? `（${courseName}）` : ""}`
            }
          })
          .filter(Boolean)
      } catch (e) {
        this.templateOptions = []
      } finally {
        this.loadingTemplates = false
      }
    },
    onTemplateChange(e) {
      const idx = Number(e && e.detail && e.detail.value)
      if (!Number.isFinite(idx) || idx < 0 || idx >= this.templatePickerRange.length) return
      const option = this.templatePickerRange[idx] || {}
      this.templateTaskId = Number(option.id || 0)
    },
    applyTemplateDeadline(rawDeadline) {
      const raw = String(rawDeadline || "").trim()
      if (!raw) {
        this.form.deadlineDate = ""
        this.form.deadlineTime = ""
        return
      }
      const fixed = raw.replace("T", " ").replace("/", "-")
      const m = fixed.match(/^(\d{4}-\d{2}-\d{2})(?:\s+(\d{2}:\d{2}))?/)
      if (!m) {
        this.form.deadlineDate = ""
        this.form.deadlineTime = ""
        return
      }
      this.form.deadlineDate = m[1] || ""
      this.form.deadlineTime = m[2] || ""
    },
    applyTemplate() {
      const item = this.selectedTemplateItem
      if (!item) return
      this.form.title = String(item.title || "")
      this.form.description = String(item.description || "")
      this.form.labId = item.labId ? Number(item.labId) : null
      this.applyTemplateDeadline(item.deadline)
      this.clearErrors()
      uni.showToast({ title: "模板已套用", icon: "success" })
    },
    onLabChange(e) {
      const idx = Number(e && e.detail && e.detail.value)
      if (!Number.isFinite(idx) || idx < 0 || idx >= this.labPickerRange.length) return
      const option = this.labPickerRange[idx] || {}
      const id = Number(option.id || 0)
      this.form.labId = id > 0 ? Math.floor(id) : null
      this.errors.labId = ""
    },
    clearLab() {
      this.form.labId = null
      this.errors.labId = ""
    },
    onDeadlineDateChange(e) {
      const value = e && e.detail ? String(e.detail.value || "") : ""
      this.form.deadlineDate = value
    },
    onDeadlineTimeChange(e) {
      const value = e && e.detail ? String(e.detail.value || "") : ""
      this.form.deadlineTime = value
    },
    clearDeadline() {
      this.form.deadlineDate = ""
      this.form.deadlineTime = ""
      this.errors.deadline = ""
    },
    clearErrors() {
      this.errors = {
        title: "",
        description: "",
        labId: "",
        deadline: ""
      }
    },
    validate() {
      this.clearErrors()
      const title = String(this.form.title || "").trim()
      const description = String(this.form.description || "").trim()
      const labId = Number(this.form.labId || 0)
      const hasDate = !!String(this.form.deadlineDate || "").trim()
      const hasTime = !!String(this.form.deadlineTime || "").trim()
      let ok = true

      if (!title) {
        this.errors.title = "请输入任务标题"
        ok = false
      } else if (title.length > 160) {
        this.errors.title = "任务标题不能超过 160 字符"
        ok = false
      }
      if (description.length > 5000) {
        this.errors.description = "任务说明不能超过 5000 字符"
        ok = false
      }
      if (labId && (!Number.isFinite(labId) || labId <= 0)) {
        this.errors.labId = "请选择有效实验室"
        ok = false
      }
      if (hasDate !== hasTime) {
        this.errors.deadline = "截止时间需要同时选择日期和时间"
        ok = false
      }
      return ok
    },
    buildDeadline() {
      const date = String(this.form.deadlineDate || "").trim()
      const time = String(this.form.deadlineTime || "").trim()
      if (!date || !time) return ""
      const safeTime = /^\d{2}:\d{2}$/.test(time) ? `${time}:00` : time
      return `${date} ${safeTime}`
    },
    async submit() {
      if (this.saving || !this.validate()) return
      this.saving = true
      try {
        const payload = {
          title: String(this.form.title || "").trim(),
          description: String(this.form.description || "").trim(),
          labId: this.form.labId ? Number(this.form.labId) : null,
          deadline: this.buildDeadline()
        }
        const res = await teacherCreateCourseTask(this.courseId, payload)
        const body = (res && res.data) || {}
        if (!body.ok) {
          uni.showToast({ title: body.msg || "创建失败", icon: "none" })
          return
        }
        uni.showToast({ title: "创建成功", icon: "success" })
        setTimeout(() => {
          uni.navigateBack()
        }, 180)
      } catch (e) {
        uni.showToast({ title: "创建失败，请重试", icon: "none" })
      } finally {
        this.saving = false
      }
    }
  }
}
</script>

<style lang="scss">
.taskFormPage {
  padding-bottom: 24px;
}

.heroCard {
  border: 1px solid rgba(22, 119, 255, 0.18);
  background: linear-gradient(160deg, #ffffff 0%, #f2f7ff 100%);
}

.heroTop {
  align-items: flex-start;
}

.miniBtn {
  min-height: 30px;
  line-height: 30px;
  padding: 0 10px;
  border-radius: 9px;
  font-size: 12px;
}

.deadlineRow {
  margin-top: 8px;
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}

.actions {
  margin-top: 10px;
  display: flex;
  gap: 8px;
}
</style>

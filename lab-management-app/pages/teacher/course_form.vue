<template>
  <view class="container courseFormPage">
    <view class="stack">
      <view class="card heroCard">
        <view class="rowBetween heroTop">
          <view>
            <view class="title">{{ isCreate ? "新建课程" : "编辑课程" }}</view>
            <view class="subtitle">课程将用于组织实验任务</view>
          </view>
          <button class="btnSecondary miniBtn" size="mini" @click="goBack">返回</button>
        </view>
      </view>

      <view class="card loadingCard" v-if="loading">
        <view class="muted">正在加载课程信息...</view>
      </view>

      <view class="card formCard" v-else>
        <view class="label">课程名称 *</view>
        <input class="inputBase" v-model.trim="form.name" maxlength="120" placeholder="例如：软件工程实验" />
        <view class="fieldError" v-if="errors.name">{{ errors.name }}</view>

        <view class="label">班级 *</view>
        <input class="inputBase" v-model.trim="form.className" maxlength="64" placeholder="例如：计科23-1班" />
        <view class="fieldError" v-if="errors.className">{{ errors.className }}</view>

        <view class="label">课程状态 *</view>
        <view class="chipRow">
          <view class="chip statusChip" :class="{ chipOn: form.status === 'enabled' }" @click="setStatus('enabled')">
            启用
          </view>
          <view class="chip statusChip" :class="{ chipOn: form.status === 'disabled' }" @click="setStatus('disabled')">
            停用
          </view>
        </view>
        <view class="fieldError" v-if="errors.status">{{ errors.status }}</view>

        <view class="label">课程简介</view>
        <textarea
          class="textareaBase"
          v-model.trim="form.description"
          maxlength="2000"
          placeholder="可选，简要描述课程目标与安排"
        />
        <view class="fieldError" v-if="errors.description">{{ errors.description }}</view>

        <view class="actions">
          <button v-if="!isCreate" class="btnDanger miniBtn" size="mini" :disabled="saving || deleting" @click="removeCourse">
            {{ deleting ? "删除中..." : "删除课程" }}
          </button>
          <button class="btnPrimary miniBtn" size="mini" :disabled="saving || deleting" @click="submit">
            {{ saving ? "提交中..." : isCreate ? "创建课程" : "保存修改" }}
          </button>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { listCourseTasks, teacherCreateCourse, teacherDeleteCourse, teacherUpdateCourse } from "@/common/api.js"

export default {
  data() {
    return {
      id: 0,
      isCreate: true,
      loading: false,
      saving: false,
      deleting: false,
      form: {
        name: "",
        className: "",
        status: "enabled",
        description: ""
      },
      errors: {
        name: "",
        className: "",
        status: "",
        description: ""
      }
    }
  },
  onLoad(options) {
    const rawId = Number(options && options.id)
    if (Number.isFinite(rawId) && rawId > 0) {
      this.id = Math.floor(rawId)
      this.isCreate = false
    }
  },
  onShow() {
    if (!this.ensureRole()) return
    if (!this.isCreate) this.fetchDetail()
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
      return true
    },
    goBack() {
      const pages = typeof getCurrentPages === "function" ? getCurrentPages() || [] : []
      if (pages.length > 1) {
        uni.navigateBack()
      } else {
        uni.reLaunch({ url: "/pages/teacher/courses" })
      }
    },
    setStatus(status) {
      this.form.status = status
      this.errors.status = ""
    },
    clearErrors() {
      this.errors = {
        name: "",
        className: "",
        status: "",
        description: ""
      }
    },
    async fetchDetail() {
      if (!this.id || this.loading) return
      this.loading = true
      try {
        const res = await listCourseTasks(this.id)
        const payload = (res && res.data) || {}
        if (!payload.ok || !payload.data || !payload.data.course) {
          uni.showToast({ title: payload.msg || "课程不存在", icon: "none" })
          setTimeout(() => this.goBack(), 220)
          return
        }
        const course = payload.data.course || {}
        this.form.name = String(course.name || "")
        this.form.className = String(course.className || "")
        this.form.status = String(course.status || "enabled") === "disabled" ? "disabled" : "enabled"
        this.form.description = String(course.description || "")
      } catch (e) {
        uni.showToast({ title: "加载失败", icon: "none" })
      } finally {
        this.loading = false
      }
    },
    validate() {
      this.clearErrors()
      const name = String(this.form.name || "").trim()
      const className = String(this.form.className || "").trim()
      const status = String(this.form.status || "").trim()
      const description = String(this.form.description || "").trim()
      let ok = true

      if (!name) {
        this.errors.name = "请输入课程名称"
        ok = false
      } else if (name.length > 120) {
        this.errors.name = "课程名称不能超过 120 字符"
        ok = false
      }
      if (!className) {
        this.errors.className = "请输入班级"
        ok = false
      } else if (className.length > 64) {
        this.errors.className = "班级不能超过 64 字符"
        ok = false
      }
      if (status !== "enabled" && status !== "disabled") {
        this.errors.status = "请选择课程状态"
        ok = false
      }
      if (description.length > 2000) {
        this.errors.description = "课程简介不能超过 2000 字符"
        ok = false
      }
      return ok
    },
    async submit() {
      if (this.saving || !this.validate()) return
      this.saving = true
      const payload = {
        name: String(this.form.name || "").trim(),
        className: String(this.form.className || "").trim(),
        status: String(this.form.status || "").trim(),
        description: String(this.form.description || "").trim()
      }
      try {
        const res = this.isCreate
          ? await teacherCreateCourse(payload)
          : await teacherUpdateCourse(this.id, payload)
        const body = (res && res.data) || {}
        if (!body.ok) {
          uni.showToast({ title: body.msg || "提交失败", icon: "none" })
          return
        }

        if (this.isCreate) {
          const createdId = Number(body.data && body.data.id)
          if (createdId > 0) {
            uni.showToast({ title: "创建成功", icon: "success" })
            setTimeout(() => {
              uni.redirectTo({ url: `/pages/teacher/course_detail?courseId=${createdId}` })
            }, 180)
            return
          }
        }
        uni.showToast({ title: "保存成功", icon: "success" })
        setTimeout(() => this.goBack(), 180)
      } catch (e) {
        uni.showToast({ title: "提交失败，请重试", icon: "none" })
      } finally {
        this.saving = false
      }
    },
    removeCourse() {
      if (this.isCreate || !this.id || this.deleting) return
      uni.showModal({
        title: "确认删除",
        content: "删除后课程及其任务将不可见，确认继续？",
        success: async (m) => {
          if (!m.confirm) return
          this.deleting = true
          try {
            const res = await teacherDeleteCourse(this.id)
            const body = (res && res.data) || {}
            if (!body.ok) {
              uni.showToast({ title: body.msg || "删除失败", icon: "none" })
              return
            }
            uni.showToast({ title: "删除成功", icon: "success" })
            setTimeout(() => {
              uni.reLaunch({ url: "/pages/teacher/courses" })
            }, 180)
          } catch (e) {
            uni.showToast({ title: "删除失败，请重试", icon: "none" })
          } finally {
            this.deleting = false
          }
        }
      })
    }
  }
}
</script>

<style lang="scss">
.courseFormPage {
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

.chipRow {
  margin-top: 8px;
  display: flex;
  gap: 8px;
}

.statusChip {
  transition: all 0.14s ease;
}

.chipOn {
  border-color: #bfdbfe;
  background: #eaf3ff;
  color: #1d4ed8;
}

.actions {
  margin-top: 10px;
  display: flex;
  gap: 8px;
}
</style>

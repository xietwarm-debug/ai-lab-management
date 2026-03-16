<template>
  <view class="container courseStudentsPage">
    <view class="stack">
      <view class="card heroCard">
        <view class="rowBetween heroTop">
          <view>
            <view class="title">{{ course.name || "班级管理" }}</view>
            <view class="subtitle">课程 #{{ course.id || courseId || "-" }} · {{ course.className || "-" }}</view>
          </view>
          <view class="heroActions">
            <button class="btnSecondary miniBtn" size="mini" @click="fetchData">刷新</button>
            <button class="btnGhost miniBtn" size="mini" @click="goBack">返回</button>
          </view>
        </view>
        <view class="meta">课程码：{{ course.courseCode || "-" }}</view>
        <view class="meta">学生数：{{ students.length }}</view>
        <view class="meta">任务数：{{ tasks.length }}</view>
      </view>

      <view class="card loadingCard" v-if="loading && students.length === 0">
        <view class="muted">正在加载班级数据...</view>
      </view>

      <view class="card taskCard" v-if="tasks.length > 0">
        <view class="rowBetween">
          <view class="cardTitle">任务提交提醒</view>
          <button class="btnSecondary miniBtn" size="mini" :disabled="autoNotifying" @click="autoNotifyMissing(false)">
            {{ autoNotifying ? "催交中..." : "自动催交" }}
          </button>
        </view>
        <view class="meta muted" v-if="lastAutoNotifyText">{{ lastAutoNotifyText }}</view>
        <view class="stack taskStack">
          <view class="taskRow" v-for="task in tasks" :key="task.id">
            <view class="rowBetween">
              <view class="taskTitle">{{ task.title || `任务 #${task.id}` }}</view>
              <view class="meta">未交 {{ missingByTask(task.id) }}</view>
            </view>
            <view class="meta muted">截止：{{ task.deadline || "未设置" }}</view>
            <view class="actions">
              <button class="btnGhost miniBtn" size="mini" @click="goTaskFiles(task)">学生文件</button>
              <button
                class="btnPrimary miniBtn"
                size="mini"
                :disabled="notifyingTaskId === task.id"
                @click="notifyMissing(task)"
              >
                {{ notifyingTaskId === task.id ? "发送中..." : "提醒未提交" }}
              </button>
            </view>
          </view>
        </view>
      </view>

      <view class="stack" v-if="students.length > 0">
        <view class="card studentCard" v-for="student in students" :key="student.studentUserName">
          <view class="rowBetween">
            <view class="studentName">{{ studentLabel(student) }}</view>
            <view class="statusTag" :class="student.missingTaskCount > 0 ? 'warning' : 'success'">
              {{ student.submittedTaskCount || 0 }}/{{ student.totalTaskCount || 0 }}
            </view>
          </view>
          <view class="meta">账号：{{ student.studentUserName || "-" }}</view>
          <view class="meta">加入时间：{{ student.joinedAt || "-" }}</view>
          <view class="meta">未交任务：{{ student.missingTaskCount || 0 }}</view>

          <view class="taskStatusList" v-if="Array.isArray(student.taskStatusList) && student.taskStatusList.length > 0">
            <view class="taskStatusItem" v-for="item in student.taskStatusList" :key="`${student.studentUserName}-${item.taskId}`">
              <view class="taskStatusLabel">{{ taskTitle(item.taskId) }}</view>
              <view class="taskStatusValue" :class="item.submitted ? 'ok' : 'missing'">
                {{ item.submitted ? "已提交" : "未提交" }}
              </view>
            </view>
          </view>

          <view class="actions">
            <button
              class="btnDanger miniBtn"
              size="mini"
              :disabled="removingUserName === student.studentUserName"
              @click="removeStudent(student)"
            >
              {{ removingUserName === student.studentUserName ? "移除中..." : "移除学生" }}
            </button>
          </view>
        </view>
      </view>

      <view class="emptyState" v-else-if="!loading">
        <view class="emptyIcon">班</view>
        <view class="emptyTitle">暂无加入学生</view>
        <view class="emptySub">学生通过课程码加入后会显示在这里</view>
      </view>
    </view>
  </view>
</template>

<script>
import {
  teacherAutoNotifyMissingTasks,
  teacherListCourseStudents,
  teacherNotifyMissingTask,
  teacherRemoveCourseStudent
} from "@/common/api.js"

export default {
  data() {
    return {
      courseId: 0,
      loading: false,
      autoNotifying: false,
      notifyingTaskId: 0,
      removingUserName: "",
      lastAutoNotifyText: "",
      course: {},
      tasks: [],
      students: []
    }
  },
  onLoad(options) {
    const raw = Number(options && options.courseId)
    this.courseId = Number.isFinite(raw) && raw > 0 ? Math.floor(raw) : 0
  },
  onShow() {
    if (!this.ensureRole()) return
    this.fetchData(true)
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
        return
      }
      if (this.courseId) {
        uni.reLaunch({ url: `/pages/teacher/course_detail?courseId=${this.courseId}` })
        return
      }
      uni.reLaunch({ url: "/pages/teacher/courses" })
    },
    studentLabel(student) {
      const display = String((student && student.studentDisplayName) || "").trim()
      const userName = String((student && student.studentUserName) || "").trim()
      if (display && userName && display !== userName) return `${display}（${userName}）`
      return display || userName || "-"
    },
    taskTitle(taskId) {
      const id = Number(taskId || 0)
      const row = (Array.isArray(this.tasks) ? this.tasks : []).find((task) => Number(task.id || 0) === id)
      return (row && row.title) || `任务 #${id || "-"}`
    },
    missingByTask(taskId) {
      const id = Number(taskId || 0)
      if (!id) return 0
      return (Array.isArray(this.students) ? this.students : []).reduce((sum, student) => {
        const list = Array.isArray(student && student.taskStatusList) ? student.taskStatusList : []
        const state = list.find((item) => Number(item && item.taskId) === id)
        return state && state.submitted ? sum : sum + 1
      }, 0)
    },
    goTaskFiles(task) {
      if (!task || !task.id) return
      const title = encodeURIComponent(String(task.title || ""))
      uni.navigateTo({
        url: `/pages/teacher/task_student_files?taskId=${task.id}&courseId=${this.courseId}&taskTitle=${title}`
      })
    },
    autoNotifyKey() {
      return `teacher.auto_notify.course.${this.courseId || 0}`
    },
    shouldAutoNotifyNow() {
      const key = this.autoNotifyKey()
      const last = Number(uni.getStorageSync(key) || 0)
      const now = Date.now()
      return !last || now - last >= 15 * 60 * 1000
    },
    markAutoNotifyNow() {
      uni.setStorageSync(this.autoNotifyKey(), Date.now())
    },
    async autoNotifyMissing(silent = false) {
      if (!this.courseId || this.autoNotifying) return
      if (silent && !this.shouldAutoNotifyNow()) return
      this.autoNotifying = true
      try {
        const res = await teacherAutoNotifyMissingTasks(this.courseId)
        const payload = (res && res.data) || {}
        if (!payload.ok) {
          if (!silent) uni.showToast({ title: payload.msg || "自动催交失败", icon: "none" })
          return
        }
        const data = payload.data || {}
        const before = Number(data.beforeDeadlineCount || 0)
        const overdue = Number(data.overdueCount || 0)
        const total = Number(data.autoNotifiedCount || 0)
        this.lastAutoNotifyText = `最近自动催交：截止前 ${before} 条，逾期 ${overdue} 条`
        this.markAutoNotifyNow()
        if (!silent) {
          if (total > 0) uni.showToast({ title: `已自动催交 ${total} 条`, icon: "success" })
          else uni.showToast({ title: "当前无需自动催交", icon: "none" })
        }
      } catch (e) {
        if (!silent) uni.showToast({ title: "自动催交失败", icon: "none" })
      } finally {
        this.autoNotifying = false
      }
    },
    async fetchData(triggerAuto = false) {
      if (!this.courseId || this.loading) return
      this.loading = true
      try {
        const res = await teacherListCourseStudents(this.courseId)
        const payload = (res && res.data) || {}
        if (!payload.ok || !payload.data) {
          this.course = {}
          this.tasks = []
          this.students = []
          uni.showToast({ title: payload.msg || "加载失败", icon: "none" })
          return
        }
        this.course = payload.data.course || {}
        this.tasks = Array.isArray(payload.data.tasks) ? payload.data.tasks : []
        this.students = Array.isArray(payload.data.students) ? payload.data.students : []
        if (triggerAuto && this.tasks.length > 0) {
          this.autoNotifyMissing(true)
        }
      } catch (e) {
        this.course = {}
        this.tasks = []
        this.students = []
        uni.showToast({ title: "加载失败，请重试", icon: "none" })
      } finally {
        this.loading = false
      }
    },
    notifyMissing(task) {
      if (!task || !task.id || this.notifyingTaskId) return
      const missingCount = this.missingByTask(task.id)
      if (missingCount <= 0) {
        uni.showToast({ title: "全部已提交", icon: "none" })
        return
      }
      uni.showModal({
        title: "发送提醒",
        content: `将向 ${missingCount} 名未提交学生发送提醒，是否继续？`,
        success: async (m) => {
          if (!m.confirm) return
          this.notifyingTaskId = task.id
          try {
            const res = await teacherNotifyMissingTask(this.courseId, task.id)
            const payload = (res && res.data) || {}
            if (!payload.ok) {
              uni.showToast({ title: payload.msg || "发送失败", icon: "none" })
              return
            }
            const count = Number(payload.data && payload.data.notifiedCount)
            uni.showToast({ title: `已提醒 ${Number.isFinite(count) ? count : 0} 人`, icon: "success" })
          } catch (e) {
            uni.showToast({ title: "发送失败，请重试", icon: "none" })
          } finally {
            this.notifyingTaskId = 0
            this.fetchData()
          }
        }
      })
    },
    removeStudent(student) {
      const userName = String((student && student.studentUserName) || "").trim()
      if (!userName || this.removingUserName) return
      uni.showModal({
        title: "移除学生",
        content: `确认将 ${this.studentLabel(student)} 移出课程？`,
        success: async (m) => {
          if (!m.confirm) return
          this.removingUserName = userName
          try {
            const res = await teacherRemoveCourseStudent(this.courseId, userName)
            const payload = (res && res.data) || {}
            if (!payload.ok) {
              uni.showToast({ title: payload.msg || "移除失败", icon: "none" })
              return
            }
            uni.showToast({ title: "已移除", icon: "success" })
            this.fetchData()
          } catch (e) {
            uni.showToast({ title: "移除失败，请重试", icon: "none" })
          } finally {
            this.removingUserName = ""
          }
        }
      })
    }
  }
}
</script>

<style lang="scss">
.courseStudentsPage {
  padding-bottom: 24px;
}

.heroCard {
  border: 1px solid rgba(22, 119, 255, 0.18);
  background: linear-gradient(160deg, #ffffff 0%, #f2f7ff 100%);
}

.heroTop {
  align-items: flex-start;
}

.heroActions {
  display: flex;
  gap: 8px;
}

.miniBtn {
  min-height: 30px;
  line-height: 30px;
  padding: 0 10px;
  border-radius: 9px;
  font-size: 12px;
}

.meta {
  margin-top: 6px;
  font-size: 12px;
  color: #64748b;
}

.taskCard,
.studentCard {
  border: 1px solid rgba(148, 163, 184, 0.24);
}

.taskStack {
  margin-top: 10px;
}

.taskRow {
  border: 1px solid rgba(148, 163, 184, 0.25);
  border-radius: 10px;
  padding: 10px;
  background: #f8fafc;
}

.taskTitle {
  font-size: 13px;
  font-weight: 600;
  color: #0f172a;
}

.studentName {
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
}

.taskStatusList {
  margin-top: 10px;
  border-top: 1px dashed rgba(148, 163, 184, 0.32);
  padding-top: 8px;
}

.taskStatusItem {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 0;
  gap: 8px;
}

.taskStatusLabel {
  font-size: 12px;
  color: #475569;
}

.taskStatusValue {
  font-size: 12px;
  font-weight: 600;
}

.taskStatusValue.ok {
  color: #16a34a;
}

.taskStatusValue.missing {
  color: #dc2626;
}

.actions {
  margin-top: 10px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
</style>

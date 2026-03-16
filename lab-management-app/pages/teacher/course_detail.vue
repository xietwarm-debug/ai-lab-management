<template>
  <view class="container courseDetailPage">
    <view class="stack">
      <view class="card heroCard">
        <view class="rowBetween heroTop">
          <view>
            <view class="title">{{ course.name || "课程详情" }}</view>
            <view class="subtitle">课程编号 #{{ course.id || "-" }}</view>
          </view>
          <view class="heroActions">
            <button class="btnSecondary miniBtn" size="mini" @click="fetchData">刷新</button>
            <button v-if="canManage" class="btnPrimary miniBtn" size="mini" @click="goEditCourse">编辑课程</button>
          </view>
        </view>
        <view class="meta">状态：{{ statusText(course.status) }}</view>
        <view class="meta">教师：{{ course.teacherUserName || "-" }}</view>
        <view class="meta">班级：{{ course.className || "-" }}</view>
        <view class="meta">课程码：{{ course.courseCode || "-" }}</view>
        <view class="meta" v-if="course.description">简介：{{ course.description }}</view>
        <view class="meta muted">更新时间：{{ course.updatedAt || "-" }}</view>
      </view>

      <view class="card actionCard" v-if="canManage">
        <view class="rowBetween">
          <view class="cardTitle">实验任务</view>
          <view class="heroActions">
            <button class="btnGhost miniBtn" size="mini" @click="goCourseStudents">班级管理</button>
            <button class="btnSecondary miniBtn" size="mini" @click="goAttendance">课堂签到</button>
            <button class="btnPrimary miniBtn" size="mini" @click="goCreateTask">新建任务</button>
          </view>
        </view>
        <view class="planGrid">
          <input
            class="inputBase planInput"
            v-model.trim="planForm.preferredDate"
            maxlength="10"
            placeholder="AI推荐偏好日期：YYYY-MM-DD"
          />
          <input
            class="inputBase planInput"
            v-model.trim="planForm.preferredTime"
            maxlength="30"
            placeholder="AI推荐偏好时段：08:00-10:00"
          />
        </view>
        <input
          class="inputBase planInput"
          v-model.trim="planForm.noticeHint"
          maxlength="80"
          placeholder="通知补充提醒（可选）"
        />
      </view>

      <view class="card loadingCard" v-if="loading">
        <view class="muted">正在加载任务列表...</view>
      </view>

      <view class="stack" v-else-if="tasks.length > 0">
        <view class="card taskCard" v-for="item in tasks" :key="item.id">
          <view class="rowBetween">
            <view class="taskTitle">{{ item.title || "-" }}</view>
            <view class="statusTag" :class="taskTone(item.status)">{{ taskText(item.status) }}</view>
          </view>
          <view class="meta">任务编号：{{ item.id }}</view>
          <view class="meta">实验室 ID：{{ item.labId || "-" }}</view>
          <view class="meta">截止时间：{{ item.deadline || "未设置" }}</view>
          <view class="meta" v-if="item.description">说明：{{ item.description }}</view>
          <view class="meta muted">创建时间：{{ item.createdAt || "-" }}</view>
          <view class="actions" v-if="canManage">
            <button
              class="btnSecondary miniBtn"
              size="mini"
              :disabled="planningTaskId === item.id"
              @click="fetchTaskPlans(item)"
            >
              {{ planningTaskId === item.id ? "生成中..." : "AI预约推荐" }}
            </button>
            <button
              class="btnGhost miniBtn"
              size="mini"
              :disabled="noticeDraftingTaskId === item.id"
              @click="showTaskNoticeDraft(item)"
            >
              {{ noticeDraftingTaskId === item.id ? "生成中..." : "AI通知草稿" }}
            </button>
          </view>
          <view class="planBox" v-if="taskPlanLines(item.id).length > 0">
            <view class="meta strongMeta">AI 推荐方案</view>
            <view class="planLine" v-for="(line, idx) in taskPlanLines(item.id)" :key="`${item.id}-plan-${idx}`">
              {{ idx + 1 }}. {{ line }}
            </view>
          </view>
          <view class="fileSection">
            <view class="rowBetween">
              <view class="meta strongMeta">实验文件</view>
              <view class="rowBetween fileTools">
                <button class="btnGhost miniBtn" size="mini" @click="refreshTaskFiles(item)">刷新</button>
                <button class="btnGhost miniBtn" size="mini" @click="goStudentFiles(item)">学生文件</button>
                <button
                  v-if="canManage"
                  class="btnSecondary miniBtn"
                  size="mini"
                  :disabled="uploadingTaskId === item.id"
                  @click="chooseAndUploadTaskFile(item)"
                >
                  {{ uploadingTaskId === item.id ? "上传中..." : "上传文件" }}
                </button>
              </view>
            </view>
            <view class="meta muted" v-if="taskFileLoading(item.id)">正在加载文件...</view>
            <view class="stack fileList" v-else-if="taskFiles(item.id).length > 0">
              <view class="fileItem" v-for="f in taskFiles(item.id)" :key="f.id">
                <view class="fileName" @click="openTaskFile(f)">{{ f.fileName || `文件 #${f.id}` }}</view>
                <view class="meta muted">
                  大小：{{ formatFileSize(f.fileSize) }} · 上传者：{{ f.uploaderUserName || "-" }} · {{ f.createdAt || "-" }}
                </view>
                <view class="actions" v-if="canManage">
                  <button class="btnGhost miniBtn" size="mini" @click="copyTaskFileLink(f)">复制链接</button>
                  <button class="btnDanger miniBtn" size="mini" @click="deleteTaskFile(f)">删除文件</button>
                </view>
              </view>
            </view>
            <view class="meta muted" v-else>暂无实验文件</view>
          </view>
          <view class="actions" v-if="canManage">
            <button class="btnDanger miniBtn" size="mini" @click="deleteTask(item)">删除任务</button>
          </view>
        </view>
      </view>

      <view class="emptyState" v-else>
        <view class="emptyIcon">任</view>
        <view class="emptyTitle">暂无实验任务</view>
        <view class="emptySub">{{ canManage ? "可点击“新建任务”添加第一条任务" : "该课程暂未发布任务" }}</view>
      </view>
    </view>
  </view>
</template>

<script>
import {
  BASE_URL,
  listCourseTasks,
  listTaskFiles,
  teacherGetTaskNoticeDraft,
  teacherGetTaskReservePlans,
  teacherDeleteTask,
  teacherDeleteTaskFile,
  teacherUploadTaskFile
} from "@/common/api.js"

export default {
  data() {
    return {
      courseId: 0,
      loading: false,
      course: {},
      tasks: [],
      fileMap: {},
      fileLoadingMap: {},
      uploadingTaskId: 0,
      planningTaskId: 0,
      noticeDraftingTaskId: 0,
      taskPlanMap: {},
      planForm: {
        preferredDate: "",
        preferredTime: "",
        noticeAudience: "学生",
        noticeHint: ""
      },
      currentRole: "",
      currentUser: ""
    }
  },
  computed: {
    canManage() {
      const teacherName = String(this.course.teacherUserName || "").trim()
      return this.currentRole === "admin" || (teacherName && teacherName === this.currentUser)
    }
  },
  onLoad(options) {
    const raw = Number(options && options.courseId)
    this.courseId = Number.isFinite(raw) && raw > 0 ? Math.floor(raw) : 0
  },
  onShow() {
    if (!this.ensureLogin()) return
    this.fetchData()
  },
  methods: {
    ensureLogin() {
      const session = uni.getStorageSync("session") || {}
      const token = String(session.token || "").trim()
      const username = String(session.username || "").trim()
      if (!token || !username) {
        uni.showToast({ title: "请先登录", icon: "none" })
        uni.reLaunch({ url: "/pages/login/login" })
        return false
      }
      if (!this.courseId) {
        uni.showToast({ title: "课程参数无效", icon: "none" })
        setTimeout(() => uni.navigateBack(), 220)
        return false
      }
      this.currentRole = String(session.role || "").trim()
      this.currentUser = username
      return true
    },
    statusText(status) {
      if (status === "enabled") return "启用"
      if (status === "disabled") return "停用"
      return status || "-"
    },
    taskText(status) {
      if (status === "active") return "有效"
      if (status === "deleted") return "已删除"
      return status || "-"
    },
    taskTone(status) {
      if (status === "active") return "success"
      if (status === "deleted") return "danger"
      return "info"
    },
    async fetchData() {
      if (!this.courseId || this.loading) return
      this.loading = true
      try {
        const res = await listCourseTasks(this.courseId)
        const payload = (res && res.data) || {}
        if (!payload.ok || !payload.data) {
          uni.showToast({ title: payload.msg || "加载失败", icon: "none" })
          this.course = {}
          this.tasks = []
          return
        }
        this.course = payload.data.course || {}
        this.tasks = Array.isArray(payload.data.tasks) ? payload.data.tasks : []
        this.fileMap = {}
        this.fileLoadingMap = {}
        if (this.tasks.length > 0) {
          await Promise.all(this.tasks.map((task) => this.fetchTaskFiles(task.id, true)))
        }
      } catch (e) {
        this.course = {}
        this.tasks = []
        this.fileMap = {}
        this.fileLoadingMap = {}
        uni.showToast({ title: "加载失败，请重试", icon: "none" })
      } finally {
        this.loading = false
      }
    },
    parseUploadResponse(res) {
      if (res && res.data && typeof res.data === "object" && Object.prototype.hasOwnProperty.call(res.data, "ok")) {
        return res.data
      }
      if (res && typeof res.data === "string") {
        try {
          return JSON.parse(res.data)
        } catch (e) {
          return null
        }
      }
      if (res && typeof res === "object" && Object.prototype.hasOwnProperty.call(res, "ok")) {
        return res
      }
      return null
    },
    taskFiles(taskId) {
      const key = String(taskId || "")
      const rows = this.fileMap[key]
      return Array.isArray(rows) ? rows : []
    },
    taskFileLoading(taskId) {
      const key = String(taskId || "")
      return !!this.fileLoadingMap[key]
    },
    async fetchTaskFiles(taskId, silent = false) {
      const key = String(taskId || "")
      if (!key) return
      this.fileLoadingMap = { ...this.fileLoadingMap, [key]: true }
      try {
        const res = await listTaskFiles(taskId)
        const payload = (res && res.data) || {}
        if (!payload.ok) {
          this.fileMap = { ...this.fileMap, [key]: [] }
          if (!silent) uni.showToast({ title: payload.msg || "文件加载失败", icon: "none" })
          return
        }
        const rows = Array.isArray(payload.data) ? payload.data : []
        this.fileMap = { ...this.fileMap, [key]: rows }
      } catch (e) {
        this.fileMap = { ...this.fileMap, [key]: [] }
        if (!silent) uni.showToast({ title: "文件加载失败", icon: "none" })
      } finally {
        this.fileLoadingMap = { ...this.fileLoadingMap, [key]: false }
      }
    },
    refreshTaskFiles(task) {
      if (!task || !task.id) return
      this.fetchTaskFiles(task.id)
    },
    taskPlanLines(taskId) {
      const payload = this.taskPlanMap[String(taskId || "")] || {}
      const plans = Array.isArray(payload.plans) ? payload.plans : []
      return plans.map((item) => {
        const labText = String(item.labName || payload.labName || "").trim() || "未定实验室"
        const dateText = String(item.date || "").trim() || "未定日期"
        const timeText = String(item.timeText || item.time || "").trim() || "未定时段"
        const reason = String(item.reason || "").trim()
        return [labText, dateText, timeText, reason].filter(Boolean).join(" · ")
      })
    },
    formatFileSize(raw) {
      const size = Number(raw || 0)
      if (!Number.isFinite(size) || size <= 0) return "0 B"
      if (size < 1024) return `${Math.floor(size)} B`
      if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
      if (size < 1024 * 1024 * 1024) return `${(size / (1024 * 1024)).toFixed(1)} MB`
      return `${(size / (1024 * 1024 * 1024)).toFixed(1)} GB`
    },
    toFileUrl(rawUrl) {
      const url = String(rawUrl || "").trim()
      if (!url) return ""
      if (/^https?:\/\//i.test(url)) return url
      return `${BASE_URL}${url}`
    },
    openTaskFile(file) {
      const url = this.toFileUrl(file && file.fileUrl)
      if (!url) return
      if (typeof window !== "undefined" && typeof window.open === "function") {
        window.open(url, "_blank")
        return
      }
      uni.setClipboardData({ data: url })
    },
    copyTaskFileLink(file) {
      const url = this.toFileUrl(file && file.fileUrl)
      if (!url) return
      uni.setClipboardData({
        data: url,
        success: () => uni.showToast({ title: "链接已复制", icon: "success" })
      })
    },
    chooseAndUploadTaskFile(task) {
      if (!this.canManage || !task || !task.id || this.uploadingTaskId === task.id) return
      if (typeof uni.chooseFile !== "function") {
        uni.showToast({ title: "当前环境不支持文件选择", icon: "none" })
        return
      }
      uni.chooseFile({
        count: 1,
        success: async (pick) => {
          const first = Array.isArray(pick && pick.tempFiles) && pick.tempFiles.length > 0 ? pick.tempFiles[0] : {}
          const filePath =
            String(first.path || first.tempFilePath || "") ||
            String((pick && Array.isArray(pick.tempFilePaths) && pick.tempFilePaths[0]) || "")
          if (!filePath) {
            uni.showToast({ title: "未选择有效文件", icon: "none" })
            return
          }
          this.uploadingTaskId = task.id
          try {
            const up = await teacherUploadTaskFile(task.id, filePath)
            const payload = this.parseUploadResponse(up)
            if (!payload || !payload.ok) {
              uni.showToast({ title: (payload && payload.msg) || "上传失败", icon: "none" })
              return
            }
            uni.showToast({ title: "上传成功", icon: "success" })
            this.fetchTaskFiles(task.id, true)
          } catch (e) {
            uni.showToast({ title: "上传失败，请重试", icon: "none" })
          } finally {
            this.uploadingTaskId = 0
          }
        },
        fail: () => {
          uni.showToast({ title: "文件选择失败", icon: "none" })
        }
      })
    },
    deleteTaskFile(file) {
      if (!this.canManage || !file || !file.id) return
      uni.showModal({
        title: "确认删除",
        content: `确认删除文件「${file.fileName || file.id}」？`,
        success: async (m) => {
          if (!m.confirm) return
          try {
            const res = await teacherDeleteTaskFile(file.id)
            const payload = (res && res.data) || {}
            if (!payload.ok) {
              uni.showToast({ title: payload.msg || "删除失败", icon: "none" })
              return
            }
            uni.showToast({ title: "删除成功", icon: "success" })
            const taskId = Number((file && file.taskId) || 0)
            if (taskId > 0) {
              this.fetchTaskFiles(taskId, true)
            } else {
              this.fetchData()
            }
          } catch (e) {
            uni.showToast({ title: "删除失败，请重试", icon: "none" })
          }
        }
      })
    },
    goStudentFiles(task) {
      if (!task || !task.id) return
      const taskId = Number(task.id)
      if (!Number.isFinite(taskId) || taskId <= 0) return
      const title = encodeURIComponent(String(task.title || ""))
      uni.navigateTo({
        url: `/pages/teacher/task_student_files?taskId=${taskId}&courseId=${this.courseId}&taskTitle=${title}`
      })
    },
    async fetchTaskPlans(task) {
      if (!this.canManage || !task || !task.id || this.planningTaskId === task.id) return
      const preferredDate = String(this.planForm.preferredDate || "").trim()
      const preferredTime = String(this.planForm.preferredTime || "").trim()
      if (preferredDate && !/^\d{4}-\d{2}-\d{2}$/.test(preferredDate)) {
        uni.showToast({ title: "日期格式应为 YYYY-MM-DD", icon: "none" })
        return
      }
      this.planningTaskId = Number(task.id || 0)
      try {
        const res = await teacherGetTaskReservePlans(task.id, {
          preferredDate,
          preferredTime,
          days: 7,
          k: 3
        })
        const payload = (res && res.data) || {}
        if (!payload.ok || !payload.data) {
          uni.showToast({ title: payload.msg || "推荐生成失败", icon: "none" })
          return
        }
        const data = payload.data || {}
        this.taskPlanMap = {
          ...this.taskPlanMap,
          [String(task.id)]: {
            labName: String(data.labName || "").trim(),
            plans: Array.isArray(data.plans) ? data.plans : []
          }
        }
        uni.showToast({ title: "已生成 3 套候选方案", icon: "success" })
      } catch (e) {
        uni.showToast({ title: "推荐生成失败", icon: "none" })
      } finally {
        this.planningTaskId = 0
      }
    },
    async showTaskNoticeDraft(task) {
      if (!this.canManage || !task || !task.id || this.noticeDraftingTaskId === task.id) return
      this.noticeDraftingTaskId = Number(task.id || 0)
      try {
        const res = await teacherGetTaskNoticeDraft(task.id, {
          audience: String(this.planForm.noticeAudience || "学生").trim() || "学生",
          extraHint: String(this.planForm.noticeHint || "").trim()
        })
        const payload = (res && res.data) || {}
        if (!payload.ok || !payload.data) {
          uni.showToast({ title: payload.msg || "草稿生成失败", icon: "none" })
          return
        }
        const data = payload.data || {}
        const title = String(data.title || "").trim()
        const content = String(data.content || "").trim()
        uni.showModal({
          title: title || "AI通知草稿",
          content: content.slice(0, 260) + (content.length > 260 ? "\n..." : ""),
          confirmText: "复制草稿",
          cancelText: "关闭",
          success: (modalRes) => {
            if (!modalRes.confirm) return
            uni.setClipboardData({
              data: `${title}\n${content}`.trim(),
              success: () => uni.showToast({ title: "草稿已复制", icon: "success" })
            })
          }
        })
      } catch (e) {
        uni.showToast({ title: "草稿生成失败", icon: "none" })
      } finally {
        this.noticeDraftingTaskId = 0
      }
    },
    goEditCourse() {
      if (!this.canManage || !this.courseId) return
      uni.navigateTo({ url: `/pages/teacher/course_form?id=${this.courseId}` })
    },
    goCreateTask() {
      if (!this.canManage || !this.courseId) return
      uni.navigateTo({ url: `/pages/teacher/task_form?courseId=${this.courseId}` })
    },
    goCourseStudents() {
      if (!this.canManage || !this.courseId) return
      uni.navigateTo({ url: `/pages/teacher/course_students?courseId=${this.courseId}` })
    },
    goAttendance() {
      if (!this.canManage || !this.courseId) return
      uni.navigateTo({ url: `/pages/teacher/attendance?courseId=${this.courseId}` })
    },
    deleteTask(task) {
      if (!this.canManage || !task || !task.id) return
      uni.showModal({
        title: "确认删除",
        content: `确认删除任务「${task.title || task.id}」？`,
        success: async (m) => {
          if (!m.confirm) return
          try {
            const res = await teacherDeleteTask(task.id)
            const payload = (res && res.data) || {}
            if (!payload.ok) {
              uni.showToast({ title: payload.msg || "删除失败", icon: "none" })
              return
            }
            uni.showToast({ title: "删除成功", icon: "success" })
            this.fetchData()
          } catch (e) {
            uni.showToast({ title: "删除失败，请重试", icon: "none" })
          }
        }
      })
    }
  }
}
</script>

<style lang="scss">
.courseDetailPage {
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

.planGrid {
  margin-top: 10px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.planInput {
  margin-top: 8px;
}

.miniBtn {
  min-height: 30px;
  line-height: 30px;
  padding: 0 10px;
  border-radius: 9px;
  font-size: 12px;
}

.taskCard {
  border: 1px solid rgba(148, 163, 184, 0.24);
}

.taskTitle {
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
}

.meta {
  margin-top: 6px;
  font-size: 12px;
  color: #64748b;
}

.strongMeta {
  font-weight: 600;
  color: #334155;
}

.fileSection {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed rgba(148, 163, 184, 0.32);
}

.fileTools {
  gap: 8px;
}

.fileList {
  margin-top: 8px;
}

.planBox {
  margin-top: 10px;
  padding: 10px;
  border-radius: 12px;
  border: 1px solid rgba(59, 130, 246, 0.16);
  background: #f8fafc;
}

.planLine {
  margin-top: 6px;
  font-size: 12px;
  line-height: 18px;
  color: #475569;
}

.fileItem {
  padding: 8px 10px;
  border-radius: 10px;
  border: 1px solid rgba(148, 163, 184, 0.25);
  background: #f8fafc;
}

.fileName {
  font-size: 13px;
  color: #1d4ed8;
  word-break: break-all;
}

.actions {
  margin-top: 10px;
  display: flex;
  gap: 8px;
}
</style>

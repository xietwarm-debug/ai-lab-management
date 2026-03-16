<template>
  <view class="container taskStudentFilesPage">
    <view class="stack">
      <view class="card heroCard">
        <view class="rowBetween heroTop">
          <view>
            <view class="title">{{ pageTitle }}</view>
            <view class="subtitle">{{ taskTitle || `任务 #${taskId || "-"}` }}</view>
          </view>
          <view class="heroActions">
            <button
              v-if="isStudent"
              class="btnPrimary miniBtn"
              size="mini"
              :disabled="uploading"
              @click="chooseSubmissionFile"
            >
              {{ uploading ? "提交中..." : (pendingFileName ? "重新选择文件" : "选择文件") }}
            </button>
            <button class="btnSecondary miniBtn" size="mini" @click="fetchList">刷新</button>
            <button class="btnGhost miniBtn" size="mini" @click="goBack">返回</button>
          </view>
        </view>
        <view class="meta">任务编号：{{ taskId || "-" }}</view>
        <view class="meta">文件总数：{{ rows.length }}</view>
      </view>

      <view class="card submitCard" v-if="isStudent">
        <view class="rowBetween">
          <view class="title">提交作业</view>
          <view class="muted">文件或文本，至少一种</view>
        </view>
        <view class="meta" v-if="pendingFileName">已选文件：{{ pendingFileName }}</view>
        <view class="actions" v-if="pendingFileName">
          <button class="btnGhost miniBtn" size="mini" :disabled="uploading" @click="clearPendingFile">移除文件</button>
        </view>
        <textarea
          class="textareaBase submitTextArea"
          v-model.trim="textContent"
          maxlength="20000"
          placeholder="也可以直接输入作业内容；若选择文件，请清空文本后提交"
        />
        <view class="meta">文本长度：{{ textContent.length }} / 20000</view>
        <view class="meta muted">当前版本一次支持一种提交方式，提交新内容会覆盖旧提交。</view>
        <button class="btnPrimary submitBtn" :disabled="uploading" @click="submitStudentWork">
          {{ uploading ? "提交中..." : (rows.length > 0 ? "重新提交作业" : "提交作业") }}
        </button>
      </view>

      <view class="card loadingCard" v-if="loading && rows.length === 0">
        <view class="muted">正在加载文件...</view>
      </view>

      <view class="stack" v-else-if="rows.length > 0">
        <view class="card fileCard" v-for="item in rows" :key="item.id">
          <view class="fileName" @click="openFile(item)">{{ item.fileName || `文件 #${item.id}` }}</view>
          <view class="meta" v-if="canManage">学生：{{ studentText(item) }}</view>
          <view class="meta" v-else>提交人：我</view>
          <view class="meta">大小：{{ formatFileSize(item.fileSize) }}</view>
          <view class="meta" v-if="isTextSubmission(item)">提交方式：文本作业</view>
          <view class="meta muted">提交时间：{{ item.createdAt || "-" }}</view>
          <view class="actions">
            <button class="btnGhost miniBtn" size="mini" @click="copyLink(item)">复制链接</button>
            <button
              v-if="isStudent"
              class="btnDanger miniBtn"
              size="mini"
              :disabled="withdrawingId === item.id"
              @click="withdrawFile(item)"
            >
              {{ withdrawingId === item.id ? "撤回中..." : "撤回作业" }}
            </button>
            <button v-if="canManage" class="btnDanger miniBtn" size="mini" @click="deleteFile(item)">删除</button>
          </view>
        </view>
      </view>

      <view class="emptyState" v-else>
        <view class="emptyIcon">作业</view>
        <view class="emptyTitle">{{ isStudent ? "暂无作业提交" : "暂无学生提交" }}</view>
        <view class="emptySub">{{ isStudent ? "可选择文件，或直接输入文本后提交" : "学生提交作业后会展示在这里" }}</view>
      </view>
    </view>
  </view>
</template>

<script>
import {
  BASE_URL,
  listTaskStudentFiles,
  submitTaskStudentText,
  studentWithdrawTaskStudentFile,
  teacherDeleteTaskStudentFile,
  uploadTaskStudentFile
} from "@/common/api.js"

export default {
  data() {
    return {
      taskId: 0,
      courseId: 0,
      taskTitle: "",
      loading: false,
      uploading: false,
      withdrawingId: 0,
      pendingFilePath: "",
      pendingFileName: "",
      textContent: "",
      rows: [],
      currentRole: "",
      currentUser: ""
    }
  },
  computed: {
    canManage() {
      return this.currentRole === "teacher" || this.currentRole === "admin"
    },
    isStudent() {
      return this.currentRole === "student"
    },
    pageTitle() {
      return this.isStudent ? "我的作业" : "学生文件"
    }
  },
  onLoad(options) {
    const taskId = Number(options && options.taskId)
    const courseId = Number(options && options.courseId)
    this.taskId = Number.isFinite(taskId) && taskId > 0 ? Math.floor(taskId) : 0
    this.courseId = Number.isFinite(courseId) && courseId > 0 ? Math.floor(courseId) : 0
    this.taskTitle = decodeURIComponent(String((options && options.taskTitle) || ""))
  },
  onShow() {
    if (!this.ensureRole()) return
    this.fetchList()
  },
  methods: {
    ensureRole() {
      const session = uni.getStorageSync("session") || {}
      const token = String(session.token || "").trim()
      const username = String(session.username || "").trim()
      const role = String(session.role || "").trim()
      if (!token || !username) {
        uni.showToast({ title: "请先登录", icon: "none" })
        uni.reLaunch({ url: "/pages/login/login" })
        return false
      }
      if (role !== "teacher" && role !== "admin" && role !== "student") {
        uni.showToast({ title: "无权限", icon: "none" })
        uni.switchTab({ url: "/pages/index/index" })
        return false
      }
      if (!this.taskId) {
        uni.showToast({ title: "任务参数无效", icon: "none" })
        setTimeout(() => this.goBack(), 220)
        return false
      }
      this.currentRole = role
      this.currentUser = username
      return true
    },
    goBack() {
      const pages = typeof getCurrentPages === "function" ? getCurrentPages() || [] : []
      if (pages.length > 1) {
        uni.navigateBack()
        return
      }
      if (this.courseId > 0) {
        uni.reLaunch({ url: `/pages/teacher/course_detail?courseId=${this.courseId}` })
        return
      }
      uni.reLaunch({ url: "/pages/teacher/courses" })
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
    isTextSubmission(item) {
      const name = String((item && item.fileName) || "").trim()
      const mime = String((item && item.mimeType) || "").trim().toLowerCase()
      return mime.startsWith("text/plain") && name === "文本作业.txt"
    },
    studentText(item) {
      const display = String((item && item.studentDisplayName) || "").trim()
      const userName = String((item && item.studentUserName) || "").trim()
      if (display && userName && display !== userName) return `${display}（${userName}）`
      return display || userName || "-"
    },
    formatFileSize(raw) {
      const size = Number(raw || 0)
      if (!Number.isFinite(size) || size <= 0) return "0 B"
      if (size < 1024) return `${Math.floor(size)} B`
      if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
      if (size < 1024 * 1024 * 1024) return `${(size / (1024 * 1024)).toFixed(1)} MB`
      return `${(size / (1024 * 1024 * 1024)).toFixed(1)} GB`
    },
    toUrl(raw) {
      const url = String(raw || "").trim()
      if (!url) return ""
      if (/^https?:\/\//i.test(url)) return url
      return `${BASE_URL}${url}`
    },
    openFile(item) {
      const url = this.toUrl(item && item.fileUrl)
      if (!url) return
      if (typeof window !== "undefined" && typeof window.open === "function") {
        window.open(url, "_blank")
      } else {
        uni.setClipboardData({ data: url })
      }
    },
    copyLink(item) {
      const url = this.toUrl(item && item.fileUrl)
      if (!url) return
      uni.setClipboardData({
        data: url,
        success: () => uni.showToast({ title: "链接已复制", icon: "success" })
      })
    },
    async fetchList() {
      if (!this.taskId || this.loading) return
      this.loading = true
      try {
        const res = await listTaskStudentFiles(this.taskId)
        const payload = (res && res.data) || {}
        if (!payload.ok) {
          this.rows = []
          uni.showToast({ title: payload.msg || "加载失败", icon: "none" })
          return
        }
        this.rows = Array.isArray(payload.data) ? payload.data : []
      } catch (e) {
        this.rows = []
        uni.showToast({ title: "加载失败，请重试", icon: "none" })
      } finally {
        this.loading = false
      }
    },
    chooseSubmissionFile() {
      if (!this.isStudent || !this.taskId || this.uploading) return
      if (typeof uni.chooseFile !== "function") {
        uni.showToast({ title: "当前环境不支持文件选择", icon: "none" })
        return
      }
      uni.chooseFile({
        count: 1,
        success: (pick) => {
          const first = Array.isArray(pick && pick.tempFiles) && pick.tempFiles.length > 0 ? pick.tempFiles[0] : {}
          const filePath =
            String(first.path || first.tempFilePath || "") ||
            String((pick && Array.isArray(pick.tempFilePaths) && pick.tempFilePaths[0]) || "")
          if (!filePath) {
            uni.showToast({ title: "未选择有效文件", icon: "none" })
            return
          }
          const fileName =
            String(first.name || "") ||
            String(filePath.split(/[\\/]/).pop() || "")
          this.pendingFilePath = filePath
          this.pendingFileName = fileName
          if (this.textContent) {
            uni.showToast({ title: "已选择文件，请清空文本后提交", icon: "none" })
          }
        },
        fail: () => {
          uni.showToast({ title: "文件选择失败", icon: "none" })
        }
      })
    },
    clearPendingFile() {
      this.pendingFilePath = ""
      this.pendingFileName = ""
    },
    async submitStudentWork() {
      if (!this.isStudent || !this.taskId || this.uploading) return
      const hasFile = !!String(this.pendingFilePath || "").trim()
      const text = String(this.textContent || "").trim()
      const hasText = !!text
      if (!hasFile && !hasText) {
        uni.showToast({ title: "请先选择文件或输入文本内容", icon: "none" })
        return
      }
      if (hasFile && hasText) {
        uni.showToast({ title: "请在文件和文本中二选一提交", icon: "none" })
        return
      }
      this.uploading = true
      try {
        let payload = null
        if (hasFile) {
          const up = await uploadTaskStudentFile(this.taskId, this.pendingFilePath)
          payload = this.parseUploadResponse(up)
        } else {
          const res = await submitTaskStudentText(this.taskId, { textContent: text })
          payload = (res && res.data) || {}
        }
        if (!payload || !payload.ok) {
          uni.showToast({ title: (payload && payload.msg) || "提交失败", icon: "none" })
          return
        }
        const replacedCount = Number((payload.data && payload.data.replacedCount) || 0)
        uni.showToast({ title: replacedCount > 0 ? "已重提并覆盖旧提交" : "提交成功", icon: "success" })
        this.pendingFilePath = ""
        this.pendingFileName = ""
        this.textContent = ""
        this.fetchList()
      } catch (e) {
        uni.showToast({ title: "提交失败，请重试", icon: "none" })
      } finally {
        this.uploading = false
      }
    },
    withdrawFile(item) {
      if (!this.isStudent || !item || !item.id || this.withdrawingId) return
      uni.showModal({
        title: "确认撤回",
        content: `确认撤回「${item.fileName || item.id}」？`,
        success: async (m) => {
          if (!m.confirm) return
          this.withdrawingId = item.id
          try {
            const res = await studentWithdrawTaskStudentFile(item.id)
            const payload = (res && res.data) || {}
            if (!payload.ok) {
              uni.showToast({ title: payload.msg || "撤回失败", icon: "none" })
              return
            }
            uni.showToast({ title: "已撤回，可重新提交", icon: "success" })
            this.fetchList()
          } catch (e) {
            uni.showToast({ title: "撤回失败，请重试", icon: "none" })
          } finally {
            this.withdrawingId = 0
          }
        }
      })
    },
    deleteFile(item) {
      if (!this.canManage || !item || !item.id) return
      uni.showModal({
        title: "确认删除",
        content: `确认删除学生文件「${item.fileName || item.id}」？`,
        success: async (m) => {
          if (!m.confirm) return
          try {
            const res = await teacherDeleteTaskStudentFile(item.id)
            const payload = (res && res.data) || {}
            if (!payload.ok) {
              uni.showToast({ title: payload.msg || "删除失败", icon: "none" })
              return
            }
            uni.showToast({ title: "删除成功", icon: "success" })
            this.fetchList()
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
.taskStudentFilesPage {
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
  flex-wrap: wrap;
  justify-content: flex-end;
}

.miniBtn {
  min-height: 30px;
  line-height: 30px;
  padding: 0 10px;
  border-radius: 9px;
  font-size: 12px;
}

.fileCard {
  border: 1px solid rgba(148, 163, 184, 0.24);
}

.submitCard {
  border: 1px solid rgba(59, 130, 246, 0.18);
}

.fileName {
  font-size: 14px;
  color: #1d4ed8;
  word-break: break-all;
}

.meta {
  margin-top: 6px;
  font-size: 12px;
  color: #64748b;
}

.actions {
  margin-top: 10px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.submitTextArea {
  margin-top: 10px;
  min-height: 140px;
}

.submitBtn {
  width: 100%;
  margin-top: 12px;
}
</style>

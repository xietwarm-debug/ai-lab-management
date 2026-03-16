<template>
  <view class="container homeworkReviewPage">
    <view class="stack">
      <view class="card heroCard">
        <view class="rowBetween heroTop">
          <view>
            <view class="title">作业批改</view>
            <view class="subtitle">按课程任务批改学生作业并导出成绩</view>
          </view>
          <view class="heroActions">
            <button class="btnSecondary miniBtn" size="mini" :disabled="loading" @click="query(true)">刷新</button>
            <button class="btnGhost miniBtn" size="mini" :disabled="loading || rows.length === 0 || batchSuggesting" @click="batchAnalyzeCurrentPage">
              {{ batchSuggesting ? "AI分析中..." : "批量AI分析" }}
            </button>
            <button class="btnPrimary miniBtn" size="mini" :loading="exporting" @click="exportAll">导出成绩</button>
          </view>
        </view>
        <view class="meta">待批改：{{ summary.pending || 0 }} ｜ 已通过：{{ summary.approved || 0 }} ｜ 已驳回：{{ summary.rejected || 0 }}</view>
        <view class="meta">平均分：{{ summary.avgApprovedScore == null ? "-" : Number(summary.avgApprovedScore).toFixed(2) }}</view>
      </view>

      <view class="card filterCard">
        <view class="filterGrid">
          <picker mode="selector" :range="courseOptions" range-key="label" @change="onCourseChange">
            <view class="pickerLike">课程：{{ selectedCourseLabel }}</view>
          </picker>
          <picker mode="selector" :range="taskOptions" range-key="label" @change="onTaskChange">
            <view class="pickerLike">任务：{{ selectedTaskLabel }}</view>
          </picker>
        </view>
        <view class="chipRow">
          <view
            v-for="item in statusOptions"
            :key="item.value"
            class="chip statusChip"
            :class="{ chipOn: filters.reviewStatus === item.value }"
            @click="setReviewStatus(item.value)"
          >
            {{ item.label }}
          </view>
        </view>
        <view class="rowBetween searchRow">
          <input
            class="inputBase searchInput"
            v-model.trim="filters.keyword"
            maxlength="64"
            placeholder="搜索学生 / 文件 / 任务"
            @confirm="query(true)"
          />
          <button class="btnGhost miniBtn" size="mini" @click="query(true)">查询</button>
        </view>
      </view>

      <view class="card filterCard" v-if="batchSuggestionSummary && batchSuggestionSummary.total > 0">
        <view class="rowBetween">
          <view class="fileName">AI 共性问题汇总</view>
          <view class="meta">分析 {{ batchSuggestionSummary.total }} 份</view>
        </view>
        <view class="meta">
          建议通过 {{ batchSuggestionSummary.approvedCount || 0 }} 份 ｜ 建议驳回 {{ batchSuggestionSummary.rejectedCount || 0 }} 份 ｜ 平均建议分
          {{ batchSuggestionSummary.avgSuggestedScore == null ? "-" : Number(batchSuggestionSummary.avgSuggestedScore).toFixed(2) }}
        </view>
        <view class="aiReasonRow" v-for="item in batchTopIssues" :key="`${item.kind}-${item.text}`">
          {{ issueLabel(item.kind) }}：{{ item.text }}（{{ item.count }} 份）
        </view>
      </view>

      <view class="card loadingCard" v-if="loading && rows.length === 0">
        <view class="muted">正在加载作业提交...</view>
      </view>

      <view class="stack" v-else-if="rows.length > 0">
        <view class="card itemCard" v-for="item in rows" :key="item.id">
          <view class="rowBetween">
            <view class="fileName" @click="openFile(item)">{{ item.fileName || `提交 #${item.id}` }}</view>
            <view class="statusTag" :class="statusTone(item.reviewStatus)">{{ statusText(item.reviewStatus) }}</view>
          </view>
          <view class="meta">课程：{{ item.courseName || "-" }} ｜ 任务：{{ item.taskTitle || "-" }}</view>
          <view class="meta">学生：{{ studentText(item) }}</view>
          <view class="meta">提交时间：{{ item.createdAt || "-" }}</view>
          <view class="meta">当前分数：{{ item.reviewScore == null ? "-" : Number(item.reviewScore).toFixed(2) }}</view>
          <view class="meta" v-if="item.reviewNote">评语：{{ item.reviewNote }}</view>
          <view class="meta muted" v-if="item.reviewedAt">批改时间：{{ item.reviewedAt }}（{{ item.reviewedBy || "-" }}）</view>
          <view class="meta aiMeta" v-if="suggestionSummary(item.id)">{{ suggestionSummary(item.id) }}</view>
          <view class="aiReasonList" v-if="suggestionReasonLines(item.id).length > 0">
            <view class="aiReasonRow" v-for="(line, idx) in suggestionReasonLines(item.id)" :key="`${item.id}-${idx}`">{{ line }}</view>
          </view>
          <view class="editorCard">
            <input
              class="inputBase fieldInput"
              type="digit"
              maxlength="8"
              :value="draftScore(item.id)"
              placeholder="输入分数 0-100（通过必填）"
              @input="onDraftScoreInput(item.id, $event)"
            />
            <input
              class="inputBase fieldInput"
              maxlength="255"
              :value="draftNote(item.id)"
              placeholder="评语（可选，最多 255 字）"
              @input="onDraftNoteInput(item.id, $event)"
            />
            <view class="actions">
              <button class="btnGhost miniBtn" size="mini" @click="openWorkspace(item)">Rubric</button>
              <button class="btnGhost miniBtn" size="mini" :disabled="reviewingId === item.id || suggestingId === item.id" @click="applyAiSuggestion(item)">
                {{ suggestingId === item.id ? "AI分析中..." : "AI建议" }}
              </button>
              <button class="btnSecondary miniBtn" size="mini" :disabled="reviewingId === item.id || suggestingId === item.id" @click="applyAndSubmitAiSuggestion(item)">
                {{ reviewingId === item.id ? "提交中..." : "采纳并提交" }}
              </button>
              <button class="btnPrimary miniBtn" size="mini" :disabled="reviewingId === item.id" @click="submitReview(item, 'approved')">
                {{ reviewingId === item.id ? "提交中..." : "通过" }}
              </button>
              <button class="btnDanger miniBtn" size="mini" :disabled="reviewingId === item.id" @click="submitReview(item, 'rejected')">
                {{ reviewingId === item.id ? "提交中..." : "驳回" }}
              </button>
            </view>
          </view>
        </view>

        <view class="card rowBetween pageCard">
          <view class="muted">已加载 {{ rows.length }} / {{ total }}</view>
          <button class="btnSecondary miniBtn" size="mini" :disabled="!hasMore || loadingMore" @click="fetchMore">
            {{ loadingMore ? "加载中..." : hasMore ? "加载更多" : "没有更多了" }}
          </button>
        </view>
      </view>

      <view class="emptyState" v-else>
        <view class="emptyIcon">作业</view>
        <view class="emptyTitle">暂无可批改作业</view>
        <view class="emptySub">可切换筛选条件或等待学生提交后再批改</view>
      </view>
    </view>
  </view>
</template>

<script>
import {
  BASE_URL,
  listCourseTasks,
  teacherApplyAiReviewSuggestion,
  teacherBatchGetAiReviewSuggestions,
  teacherHomeworkReviewExportUrl,
  teacherGetAiReviewSuggestion,
  teacherListCourses,
  teacherListHomeworkReviews,
  teacherReviewTaskStudentFile
} from "@/common/api.js"

function toInt(v, fallback = 0) {
  const n = Number(v)
  return Number.isFinite(n) ? Math.floor(n) : fallback
}

function parseRowsPayload(raw) {
  const payload = raw || {}
  if (Array.isArray(payload)) return payload
  if (Array.isArray(payload.data)) return payload.data
  return []
}

export default {
  data() {
    return {
      loading: false,
      loadingMore: false,
      exporting: false,
      reviewingId: 0,
      suggestingId: 0,
      batchSuggesting: false,
      page: 1,
      pageSize: 20,
      total: 0,
      hasMore: false,
      rows: [],
      courses: [],
      tasks: [],
      summary: {
        pending: 0,
        approved: 0,
        rejected: 0,
        avgApprovedScore: null
      },
      coursesEmptyHintShown: false,
      filters: {
        courseId: 0,
        taskId: 0,
        reviewStatus: "all",
        keyword: ""
      },
      reviewDraftMap: {},
      aiSuggestionMap: {},
      batchSuggestionSummary: null,
      statusOptions: [
        { label: "全部", value: "all" },
        { label: "待批改", value: "pending" },
        { label: "已通过", value: "approved" },
        { label: "已驳回", value: "rejected" }
      ]
    }
  },
  computed: {
    courseOptions() {
      const rows = Array.isArray(this.courses) ? this.courses : []
      return [{ label: "全部课程", value: 0 }].concat(
        rows.map((x) => ({
          label: String((x && x.name) || `课程 #${(x && x.id) || "-"}`),
          value: toInt(x && x.id, 0)
        }))
      )
    },
    taskOptions() {
      const rows = Array.isArray(this.tasks) ? this.tasks : []
      return [{ label: "全部任务", value: 0 }].concat(
        rows.map((x) => ({
          label: String((x && x.title) || `任务 #${(x && x.id) || "-"}`),
          value: toInt(x && x.id, 0)
        }))
      )
    },
    selectedCourseLabel() {
      const hit = this.courseOptions.find((x) => Number(x.value || 0) === Number(this.filters.courseId || 0))
      return (hit && hit.label) || "全部课程"
    },
    selectedTaskLabel() {
      const hit = this.taskOptions.find((x) => Number(x.value || 0) === Number(this.filters.taskId || 0))
      return (hit && hit.label) || "全部任务"
    },
    batchTopIssues() {
      const summary = this.batchSuggestionSummary || {}
      const rows = []
        .concat(Array.isArray(summary.commonIssues) ? summary.commonIssues : [])
        .concat(Array.isArray(summary.commonSignals) ? summary.commonSignals : [])
        .concat(Array.isArray(summary.commonLimitations) ? summary.commonLimitations : [])
      return rows.slice(0, 6)
    }
  },
  onLoad(options) {
    const reviewStatus = String((options && options.reviewStatus) || "").trim().toLowerCase()
    if (reviewStatus && ["all", "pending", "approved", "rejected"].includes(reviewStatus)) {
      this.filters.reviewStatus = reviewStatus
    }
  },
  onShow() {
    if (!this.ensureTeacher()) return
    this.bootstrap()
  },
  methods: {
    ensureTeacher() {
      const session = uni.getStorageSync("session") || {}
      const token = String(session.token || "").trim()
      const username = String(session.username || "").trim()
      const role = String(session.role || "").trim().toLowerCase()
      if (!token || !username) {
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
    async bootstrap() {
      await this.fetchCourses()
      await this.query(true)
    },
    async fetchCourses() {
      try {
        const res = await teacherListCourses()
        const payload = (res && res.data) || {}
        if (payload && payload.ok === false) {
          this.courses = []
          this.tasks = []
          return
        }
        const rows = parseRowsPayload(payload)
        this.courses = Array.isArray(rows) ? rows : []
        if (this.courses.length === 0 && !this.coursesEmptyHintShown) {
          this.coursesEmptyHintShown = true
          uni.showToast({ title: "当前账号下暂无课程", icon: "none" })
        }
        const hasSelected = this.courses.some((x) => toInt(x && x.id, 0) === toInt(this.filters.courseId, 0))
        if (!hasSelected) {
          this.filters.courseId = this.courses.length > 0 ? toInt(this.courses[0] && this.courses[0].id, 0) : 0
        }
      } catch (e) {
        this.courses = []
        this.tasks = []
      }
      await this.fetchTasks(this.filters.courseId)
    },
    async fetchTasks(courseId) {
      const cid = toInt(courseId, 0)
      if (cid <= 0) {
        this.tasks = []
        this.filters.taskId = 0
        return
      }
      try {
        const res = await listCourseTasks(cid)
        const payload = (res && res.data) || {}
        if (!payload.ok || !payload.data) {
          this.tasks = []
          this.filters.taskId = 0
          return
        }
        this.tasks = Array.isArray(payload.data.tasks) ? payload.data.tasks : []
        const hasTask = this.tasks.some((x) => toInt(x && x.id, 0) === toInt(this.filters.taskId, 0))
        if (!hasTask) this.filters.taskId = 0
      } catch (e) {
        this.tasks = []
        this.filters.taskId = 0
      }
    },
    onCourseChange(e) {
      const idx = toInt(e && e.detail && e.detail.value, 0)
      const option = this.courseOptions[idx] || this.courseOptions[0]
      this.filters.courseId = toInt(option && option.value, 0)
      this.filters.taskId = 0
      this.fetchTasks(this.filters.courseId).then(() => this.query(true))
    },
    onTaskChange(e) {
      const idx = toInt(e && e.detail && e.detail.value, 0)
      const option = this.taskOptions[idx] || this.taskOptions[0]
      this.filters.taskId = toInt(option && option.value, 0)
      this.query(true)
    },
    setReviewStatus(status) {
      const next = String(status || "all")
      if (this.filters.reviewStatus === next) return
      this.filters.reviewStatus = next
      this.query(true)
    },
    buildParams(page) {
      const params = {
        page: toInt(page, 1),
        pageSize: this.pageSize
      }
      if (toInt(this.filters.courseId, 0) > 0) params.courseId = toInt(this.filters.courseId, 0)
      if (toInt(this.filters.taskId, 0) > 0) params.taskId = toInt(this.filters.taskId, 0)
      const reviewStatus = String(this.filters.reviewStatus || "").trim()
      if (reviewStatus && reviewStatus !== "all") params.reviewStatus = reviewStatus
      const keyword = String(this.filters.keyword || "").trim()
      if (keyword) params.keyword = keyword
      return params
    },
    buildExportParams() {
      const params = {}
      if (toInt(this.filters.courseId, 0) > 0) params.courseId = toInt(this.filters.courseId, 0)
      if (toInt(this.filters.taskId, 0) > 0) params.taskId = toInt(this.filters.taskId, 0)
      const reviewStatus = String(this.filters.reviewStatus || "").trim()
      if (reviewStatus && reviewStatus !== "all") params.reviewStatus = reviewStatus
      const keyword = String(this.filters.keyword || "").trim()
      if (keyword) params.keyword = keyword
      return params
    },
    async query(reset = true) {
      if (reset) {
        this.page = 1
        this.total = 0
        this.hasMore = false
        this.rows = []
        this.batchSuggestionSummary = null
      }
      await this.fetchList(reset)
    },
    async fetchList(reset = false) {
      if (reset) {
        if (this.loading) return
        this.loading = true
      } else {
        if (this.loading || this.loadingMore || !this.hasMore) return
        this.loadingMore = true
      }
      const reqPage = reset ? 1 : this.page
      try {
        const res = await teacherListHomeworkReviews(this.buildParams(reqPage))
        const payload = (res && res.data) || {}
        if (!payload.ok) {
          if (reset) this.rows = []
          uni.showToast({ title: payload.msg || "加载失败", icon: "none" })
          return
        }
        const list = Array.isArray(payload.data) ? payload.data : []
        const meta = payload.meta || {}
        this.summary = {
          pending: toInt(meta.summary && meta.summary.pending, 0),
          approved: toInt(meta.summary && meta.summary.approved, 0),
          rejected: toInt(meta.summary && meta.summary.rejected, 0),
          avgApprovedScore: meta.summary && meta.summary.avgApprovedScore != null ? Number(meta.summary.avgApprovedScore) : null
        }
        list.forEach((row) => this.seedDraft(row))
        if (reset) this.rows = list
        else this.rows = this.rows.concat(list)
        this.page = reqPage + 1
        this.total = toInt(meta.total, this.rows.length)
        this.hasMore = !!meta.hasMore
      } catch (e) {
        if (reset) this.rows = []
        uni.showToast({ title: "加载失败", icon: "none" })
      } finally {
        this.loading = false
        this.loadingMore = false
      }
    },
    fetchMore() {
      this.fetchList(false)
    },
    seedDraft(item) {
      const id = toInt(item && item.id, 0)
      if (id <= 0) return
      const key = String(id)
      const next = {
        score: item && item.reviewScore != null ? String(item.reviewScore) : "",
        note: String((item && item.reviewNote) || "")
      }
      this.reviewDraftMap = { ...this.reviewDraftMap, [key]: next }
    },
    draftScore(id) {
      const key = String(toInt(id, 0))
      const row = this.reviewDraftMap[key] || {}
      return String(row.score || "")
    },
    draftNote(id) {
      const key = String(toInt(id, 0))
      const row = this.reviewDraftMap[key] || {}
      return String(row.note || "")
    },
    suggestionSummary(id) {
      const key = String(toInt(id, 0))
      const row = this.aiSuggestionMap[key] || {}
      const suggestion = row && row.suggestion ? row.suggestion : {}
      return String(suggestion.summary || "").trim()
    },
    suggestionReasonLines(id) {
      const key = String(toInt(id, 0))
      const row = this.aiSuggestionMap[key] || {}
      const suggestion = row && row.suggestion ? row.suggestion : {}
      const metrics = suggestion && suggestion.metrics ? suggestion.metrics : {}
      const lines = []
      const metricParts = []
      if (metrics.fileSize != null && Number(metrics.fileSize) > 0) {
        metricParts.push(`文件 ${(Number(metrics.fileSize) / 1024).toFixed(1)} KB`)
      }
      if (metrics.charCount != null && Number(metrics.charCount) > 0) {
        metricParts.push(`可读正文 ${Number(metrics.charCount)} 字`)
      }
      if (metrics.delayHours != null && Number(metrics.delayHours) > 0) {
        metricParts.push(`迟交 ${Number(metrics.delayHours).toFixed(1)} 小时`)
      }
      if (metricParts.length > 0) lines.push(`依据：${metricParts.join("，")}`)
      ;["signals", "risks", "limitations"].forEach((field) => {
        const values = Array.isArray(suggestion[field]) ? suggestion[field] : []
        values.slice(0, 2).forEach((text) => {
          const label = this.issueLabel(field === "signals" ? "signal" : field === "risks" ? "risk" : "limitation")
          const clean = String(text || "").trim()
          if (clean) lines.push(`${label}：${clean}`)
        })
      })
      return lines.slice(0, 6)
    },
    issueLabel(kind) {
      const key = String(kind || "").trim()
      if (key === "signal") return "AI判断依据"
      if (key === "risk") return "AI关注点"
      if (key === "limitation") return "AI局限"
      return "AI提示"
    },
    onDraftScoreInput(id, e) {
      const key = String(toInt(id, 0))
      const oldRow = this.reviewDraftMap[key] || { score: "", note: "" }
      const value = String((e && e.detail && e.detail.value) || "")
      this.reviewDraftMap = { ...this.reviewDraftMap, [key]: { ...oldRow, score: value } }
    },
    onDraftNoteInput(id, e) {
      const key = String(toInt(id, 0))
      const oldRow = this.reviewDraftMap[key] || { score: "", note: "" }
      const value = String((e && e.detail && e.detail.value) || "")
      this.reviewDraftMap = { ...this.reviewDraftMap, [key]: { ...oldRow, note: value } }
    },
    applySuggestionDraft(id, suggestion) {
      const key = String(toInt(id, 0))
      const oldRow = this.reviewDraftMap[key] || { score: "", note: "" }
      this.reviewDraftMap = {
        ...this.reviewDraftMap,
        [key]: {
          ...oldRow,
          score: suggestion && suggestion.suggestedScore != null ? String(suggestion.suggestedScore) : oldRow.score,
          note: String((suggestion && suggestion.suggestedNote) || oldRow.note || "")
        }
      }
    },
    async fetchAiSuggestion(item, force = false) {
      const id = toInt(item && item.id, 0)
      if (id <= 0) return null
      const key = String(id)
      if (!force) {
        const cached = this.aiSuggestionMap[key]
        if (cached && cached.suggestion) return cached
      }
      if (this.suggestingId && this.suggestingId !== id) return null
      this.suggestingId = id
      try {
        const res = await teacherGetAiReviewSuggestion(id)
        const payload = (res && res.data) || {}
        const data = payload && payload.data ? payload.data : {}
        const suggestion = data && data.suggestion ? data.suggestion : {}
        if (!payload.ok || !suggestion) {
          uni.showToast({ title: payload.msg || "AI建议获取失败", icon: "none" })
          return null
        }
        this.aiSuggestionMap = { ...this.aiSuggestionMap, [key]: data }
        return data
      } catch (e) {
        uni.showToast({ title: "AI建议获取失败", icon: "none" })
        return null
      } finally {
        this.suggestingId = 0
      }
    },
    async applyAiSuggestion(item) {
      const id = toInt(item && item.id, 0)
      const data = await this.fetchAiSuggestion(item)
      const suggestion = data && data.suggestion ? data.suggestion : null
      if (!suggestion) return
      this.applySuggestionDraft(id, suggestion)
      uni.showToast({ title: "已填入AI建议", icon: "success" })
    },
    async applyAndSubmitAiSuggestion(item) {
      const id = toInt(item && item.id, 0)
      if (id <= 0 || this.reviewingId) return
      this.reviewingId = id
      try {
        const res = await teacherApplyAiReviewSuggestion(id)
        const payload = (res && res.data) || {}
        if (!payload.ok || !payload.data) {
          uni.showToast({ title: payload.msg || "AI执行失败", icon: "none" })
          return
        }
        uni.showToast({ title: "AI建议已执行", icon: "success" })
        await this.query(true)
      } catch (e) {
        uni.showToast({ title: "AI执行失败", icon: "none" })
      } finally {
        this.reviewingId = 0
      }
    },
    async batchAnalyzeCurrentPage() {
      const ids = (Array.isArray(this.rows) ? this.rows : []).map((item) => toInt(item && item.id, 0)).filter((id) => id > 0)
      if (ids.length === 0 || this.batchSuggesting) return
      this.batchSuggesting = true
      try {
        const res = await teacherBatchGetAiReviewSuggestions(ids)
        const payload = (res && res.data) || {}
        const data = payload && payload.data ? payload.data : {}
        const items = Array.isArray(data.items) ? data.items : []
        if (!payload.ok || items.length === 0) {
          uni.showToast({ title: payload.msg || "批量AI分析失败", icon: "none" })
          return
        }
        const nextMap = { ...this.aiSuggestionMap }
        items.forEach((row) => {
          const fileId = toInt(row && row.fileId, 0)
          if (fileId <= 0) return
          nextMap[String(fileId)] = row
          if (row && row.suggestion) {
            this.applySuggestionDraft(fileId, row.suggestion)
          }
        })
        this.aiSuggestionMap = nextMap
        this.batchSuggestionSummary = data.summary || null
        uni.showToast({ title: "已完成批量AI分析", icon: "success" })
      } catch (e) {
        uni.showToast({ title: "批量AI分析失败", icon: "none" })
      } finally {
        this.batchSuggesting = false
      }
    },
    statusText(status) {
      const s = String(status || "").trim()
      if (s === "approved") return "已通过"
      if (s === "rejected") return "已驳回"
      return "待批改"
    },
    statusTone(status) {
      const s = String(status || "").trim()
      if (s === "approved") return "success"
      if (s === "rejected") return "danger"
      return "warning"
    },
    studentText(item) {
      const display = String((item && item.studentDisplayName) || "").trim()
      const user = String((item && item.studentUserName) || "").trim()
      if (display && user && display !== user) return `${display}（${user}）`
      return display || user || "-"
    },
    toFileUrl(rawUrl) {
      const url = String(rawUrl || "").trim()
      if (!url) return ""
      if (/^https?:\/\//i.test(url)) return url
      return `${BASE_URL}${url}`
    },
    openFile(item) {
      const url = this.toFileUrl(item && item.fileUrl)
      if (!url) return
      if (typeof window !== "undefined" && typeof window.open === "function") {
        window.open(url, "_blank")
        return
      }
      uni.setClipboardData({ data: url })
    },
    openWorkspace(item) {
      const id = toInt(item && item.id, 0)
      if (id <= 0) return
      uni.navigateTo({ url: `/pages/teacher/review_workspace?fileId=${id}` })
    },
    async submitReview(item, reviewStatus) {
      const id = toInt(item && item.id, 0)
      if (id <= 0 || this.reviewingId) return
      const key = String(id)
      const draft = this.reviewDraftMap[key] || { score: "", note: "" }
      const note = String(draft.note || "").trim()
      if (note.length > 255) {
        uni.showToast({ title: "评语不能超过255字", icon: "none" })
        return
      }
      const scoreText = String(draft.score || "").trim()
      let scoreVal = null
      if (scoreText) {
        const parsed = Number(scoreText)
        if (!Number.isFinite(parsed) || parsed < 0 || parsed > 100) {
          uni.showToast({ title: "分数需在0-100之间", icon: "none" })
          return
        }
        scoreVal = Math.round(parsed * 100) / 100
      }
      if (reviewStatus === "approved" && scoreVal == null) {
        uni.showToast({ title: "通过时必须填写分数", icon: "none" })
        return
      }

      this.reviewingId = id
      try {
        const payload = { reviewStatus, reviewNote: note }
        if (scoreVal != null) payload.reviewScore = scoreVal
        const res = await teacherReviewTaskStudentFile(id, payload)
        const body = (res && res.data) || {}
        if (!body.ok || !body.data) {
          uni.showToast({ title: body.msg || "批改失败", icon: "none" })
          return
        }
        uni.showToast({ title: "批改成功", icon: "success" })
        await this.query(true)
      } catch (e) {
        uni.showToast({ title: "批改失败", icon: "none" })
      } finally {
        this.reviewingId = 0
      }
    },
    exportAll() {
      if (this.exporting) return
      this.exporting = true
      const url = teacherHomeworkReviewExportUrl(this.buildExportParams())
      uni.downloadFile({
        url,
        success: (res) => {
          if (Number(res && res.statusCode) !== 200) {
            uni.showToast({ title: "导出失败", icon: "none" })
            return
          }
          uni.openDocument({
            filePath: res.tempFilePath,
            fileType: "csv",
            fail: () => {
              uni.showToast({ title: "已导出，请在文件管理中查看", icon: "none" })
            }
          })
        },
        fail: () => uni.showToast({ title: "导出失败", icon: "none" }),
        complete: () => {
          this.exporting = false
        }
      })
    }
  }
}
</script>

<style lang="scss">
.homeworkReviewPage {
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

.aiMeta {
  color: #1d4ed8;
}

.aiReasonList {
  margin-top: 8px;
  padding: 8px 10px;
  border-radius: 10px;
  background: rgba(239, 246, 255, 0.9);
}

.aiReasonRow {
  margin-top: 4px;
  font-size: 12px;
  color: #475569;
  line-height: 1.5;
}

.aiReasonRow:first-child {
  margin-top: 0;
}

.filterCard {
  border: 1px solid rgba(148, 163, 184, 0.24);
}

.filterGrid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.pickerLike {
  border: 1px solid rgba(148, 163, 184, 0.32);
  border-radius: 10px;
  padding: 8px 10px;
  font-size: 12px;
  color: #334155;
  background: #fff;
}

.chipRow {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.chipOn {
  border-color: #bfdbfe;
  background: #eaf3ff;
  color: #1d4ed8;
}

.searchRow {
  margin-top: 10px;
  gap: 8px;
}

.searchInput {
  flex: 1;
}

.itemCard {
  border: 1px solid rgba(148, 163, 184, 0.24);
}

.fileName {
  font-size: 14px;
  color: #1d4ed8;
  font-weight: 600;
  word-break: break-all;
}

.editorCard {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed rgba(148, 163, 184, 0.32);
}

.fieldInput {
  margin-top: 8px;
}

.actions {
  margin-top: 10px;
  display: flex;
  gap: 8px;
}
</style>

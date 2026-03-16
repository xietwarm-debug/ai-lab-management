<template>
  <view class="container teacherCoursesPage">
    <view class="stack">
      <view class="card heroCard">
        <view class="rowBetween heroTop">
          <view>
            <view class="title">课程管理</view>
            <view class="subtitle">{{ canManage ? "管理课程与实验任务" : "加入课程并查看已选课程" }}</view>
          </view>
          <button v-if="canManage" class="btnPrimary miniBtn" size="mini" @click="goCreateCourse">新建课程</button>
        </view>
      </view>

      <view class="card filterCard">
        <view class="rowBetween">
          <view class="cardTitle">课程筛选</view>
          <view class="muted">共 {{ rows.length }} 项</view>
        </view>
        <view class="rowBetween searchFieldRow">
          <view class="muted">搜索字段</view>
          <picker :range="searchOptions" range-key="label" :value="searchFieldIndex" @change="onSearchFieldChange">
            <view class="chip">{{ currentSearchLabel }}</view>
          </picker>
        </view>
        <input class="inputBase" v-model.trim="searchText" :maxlength="searchMaxlength" :placeholder="searchPlaceholder" />
        <view class="actions">
          <button class="btnSecondary miniBtn" size="mini" @click="fetchList">搜索</button>
          <button class="btnGhost miniBtn" size="mini" @click="resetFilters">重置</button>
        </view>
      </view>

      <view class="card filterCard" v-if="!canManage">
        <view class="rowBetween">
          <view class="cardTitle">课程码加入</view>
          <view class="muted">6 位课程码</view>
        </view>
        <input class="inputBase" v-model.trim="joinCode" maxlength="6" placeholder="例如：123456" />
        <view class="actions">
          <button class="btnPrimary miniBtn" size="mini" @click="joinByCode">加入课程</button>
        </view>
      </view>

      <view class="card loadingCard" v-if="loading && rows.length === 0">
        <view class="muted">正在加载课程...</view>
      </view>

      <view class="stack" v-else-if="rows.length > 0">
        <view class="card courseCard" v-for="item in rows" :key="item.id">
          <view class="rowBetween">
            <view class="courseName">{{ item.name || "-" }}</view>
            <view class="statusTag" :class="statusTone(item.status)">{{ statusText(item.status) }}</view>
          </view>
          <view class="meta">教师：{{ item.teacherUserName || "-" }}</view>
          <view class="meta">班级：{{ item.className || "-" }}</view>
          <view class="meta">课程码：{{ item.courseCode || "-" }}</view>
          <view class="meta">任务数：{{ item.taskCount || 0 }}</view>
          <view class="meta" v-if="item.description">简介：{{ item.description }}</view>
          <view class="meta muted">更新时间：{{ item.updatedAt || "-" }}</view>
          <view class="actions">
            <button class="btnSecondary miniBtn" size="mini" @click="goDetail(item)">详情</button>
            <button v-if="canManage" class="btnGhost miniBtn" size="mini" @click="goEdit(item)">编辑</button>
            <button v-if="canManage" class="btnPrimary miniBtn" size="mini" @click="goCreateTask(item)">新建任务</button>
          </view>
        </view>
      </view>

      <view class="emptyState" v-else>
        <view class="emptyIcon">C</view>
        <view class="emptyTitle">暂无课程</view>
        <view class="emptySub">{{ canManage ? "先创建一个课程开始使用" : "请先加入课程" }}</view>
      </view>
    </view>
  </view>
</template>

<script>
import { joinCourseByCode, listCourses, teacherListCourses } from "@/common/api.js"
import { normalizeRole, requireRole } from "@/common/session.js"

export default {
  data() {
    return {
      loading: false,
      searchText: "",
      joinCode: "",
      searchField: "keyword",
      searchOptions: [
        { label: "课程名 / 简介", value: "keyword", maxlength: 80, placeholder: "搜索课程名称或课程简介" },
        { label: "班级", value: "className", maxlength: 64, placeholder: "搜索班级名称" }
      ],
      rows: [],
      role: "",
      username: ""
    }
  },
  computed: {
    canManage() {
      return this.role === "teacher" || this.role === "admin"
    },
    searchFieldIndex() {
      const idx = this.searchOptions.findIndex((item) => item.value === this.searchField)
      return idx >= 0 ? idx : 0
    },
    currentSearchLabel() {
      const option = this.searchOptions[this.searchFieldIndex] || {}
      return String(option.label || "课程名 / 简介")
    },
    searchPlaceholder() {
      const option = this.searchOptions[this.searchFieldIndex] || {}
      return String(option.placeholder || "请输入搜索关键词")
    },
    searchMaxlength() {
      const option = this.searchOptions[this.searchFieldIndex] || {}
      const val = Number(option.maxlength)
      return Number.isFinite(val) && val > 0 ? Math.floor(val) : 80
    }
  },
  onShow() {
    if (!this.ensureRole()) return
    this.fetchList()
  },
  onPullDownRefresh() {
    this.fetchList(true)
  },
  methods: {
    ensureRole() {
      const session = requireRole(["teacher", "admin", "student"], {
        message: "无权访问"
      })
      if (!session) return false
      this.role = normalizeRole(session.role)
      this.username = String(session.username || "").trim()
      return true
    },
    statusText(status) {
      if (status === "enabled") return "启用"
      if (status === "disabled") return "停用"
      return status || "-"
    },
    statusTone(status) {
      if (status === "enabled") return "success"
      if (status === "disabled") return "warning"
      return "info"
    },
    onSearchFieldChange(e) {
      const idx = Number(e && e.detail && e.detail.value)
      if (!Number.isFinite(idx) || idx < 0 || idx >= this.searchOptions.length) return
      const option = this.searchOptions[idx] || {}
      this.searchField = String(option.value || "keyword")
    },
    buildSearchParams() {
      const text = String(this.searchText || "").trim()
      if (!text) return {}
      if (this.searchField === "className") return { className: text }
      return { keyword: text }
    },
    async fetchList(stopRefresh = false) {
      if (this.loading) {
        if (stopRefresh) uni.stopPullDownRefresh()
        return
      }
      this.loading = true
      try {
        const params = this.buildSearchParams()
        const res = this.canManage ? await teacherListCourses(params) : await listCourses(params)
        const payload = (res && res.data) || {}
        if (!payload.ok) {
          this.rows = []
          uni.showToast({ title: payload.msg || "加载失败", icon: "none" })
          return
        }
        this.rows = Array.isArray(payload.data) ? payload.data : []
      } catch (e) {
        this.rows = []
        uni.showToast({ title: "加载失败", icon: "none" })
      } finally {
        this.loading = false
        if (stopRefresh) uni.stopPullDownRefresh()
      }
    },
    resetFilters() {
      this.searchText = ""
      this.searchField = "keyword"
      this.fetchList()
    },
    async joinByCode() {
      const code = String(this.joinCode || "").trim()
      if (!/^\d{6}$/.test(code)) {
        uni.showToast({ title: "请输入 6 位课程码", icon: "none" })
        return
      }
      try {
        const res = await joinCourseByCode({ courseCode: code })
        const payload = (res && res.data) || {}
        if (!payload.ok) {
          uni.showToast({ title: payload.msg || "加入失败", icon: "none" })
          return
        }
        this.joinCode = ""
        uni.showToast({ title: "加入成功", icon: "success" })
        this.fetchList()
      } catch (e) {
        uni.showToast({ title: "加入失败", icon: "none" })
      }
    },
    goCreateCourse() {
      if (!this.canManage) return
      uni.navigateTo({ url: "/pages/teacher/course_form" })
    },
    goEdit(item) {
      if (!this.canManage) return
      if (!item || !item.id) return
      uni.navigateTo({ url: `/pages/teacher/course_form?id=${item.id}` })
    },
    goDetail(item) {
      if (!item || !item.id) return
      uni.navigateTo({ url: `/pages/teacher/course_detail?courseId=${item.id}` })
    },
    goCreateTask(item) {
      if (!this.canManage) return
      if (!item || !item.id) return
      uni.navigateTo({ url: `/pages/teacher/task_form?courseId=${item.id}` })
    }
  }
}
</script>

<style lang="scss">
.teacherCoursesPage {
  padding-bottom: 24px;
}

.heroCard {
  border: 1px solid rgba(22, 119, 255, 0.18);
  background: linear-gradient(160deg, #ffffff 0%, #f2f7ff 100%);
}

.heroTop {
  align-items: flex-start;
}

.filterCard {
  border: 1px solid rgba(148, 163, 184, 0.22);
}

.searchFieldRow {
  margin-bottom: 8px;
}

.miniBtn {
  min-height: 30px;
  line-height: 30px;
  padding: 0 10px;
  border-radius: 9px;
  font-size: 12px;
}

.courseCard {
  border: 1px solid rgba(148, 163, 184, 0.24);
}

.courseName {
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
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
</style>

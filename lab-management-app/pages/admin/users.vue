<template>
  <view class="container usersPage">
    <view class="stack">
      <view class="card">
        <view v-if="activeQuickFilterMeta" class="filterNotice">
          <view class="titleSmall">{{ activeQuickFilterMeta.label }}</view>
          <view class="muted">{{ activeQuickFilterMeta.description }}</view>
          <view class="chipRow compactChipRow">
            <view class="chip" @click="applyQuickFilter('all')">查看全部用户</view>
          </view>
        </view>
        <view class="rowBetween">
          <view>
            <view class="title">用户治理中心</view>
            <view class="subtitle">账号创建、批量生成、批量导入、毕业停用与权限维护</view>
          </view>
          <button class="btnSecondary miniBtn" size="mini" :loading="loading" @click="refreshUserView(true)">刷新</button>
        </view>
        <view class="muted">当前操作人：{{ operator || "-" }} · 总账号数：{{ total }}</view>
      </view>

      <view class="card">
        <view class="cardTitle">治理概览</view>
        <view class="grid2">
          <view class="muted">毕业治理年份</view>
          <input class="inputBase" type="number" v-model.number="filters.graduateReferenceYear" @blur="handleGraduateReferenceYearChange" />
        </view>
        <view class="governanceGrid">
          <view
            v-for="item in governanceCards"
            :key="item.quickFilter"
            class="governanceCard"
            :class="{ governanceCardOn: filters.quickFilter === item.quickFilter }"
            @click="applyQuickFilter(item.quickFilter)"
          >
            <view class="muted">{{ item.label }}</view>
            <view class="titleSmall">{{ item.value }}</view>
          </view>
        </view>
      </view>

      <view class="card">
        <view class="cardTitle">高级筛选</view>
        <input class="inputBase" v-model.trim="filters.keyword" placeholder="账号 / 昵称 / 班级 / 手机号 / ID" />
        <view class="chipRow">
          <view v-for="item in roleOptions" :key="item.value" class="chip" :class="{ chipOn: filters.role === item.value }" @click="filters.role = item.value">{{ item.label }}</view>
        </view>
        <view class="grid2">
          <input class="inputBase" v-model.trim="filters.className" placeholder="班级，如：计科2301" />
          <input class="inputBase" type="number" v-model.number="filters.graduationYear" placeholder="毕业年份，可选" />
        </view>
        <view class="chipRow">
          <view v-for="item in activeOptions" :key="item.value" class="chip" :class="{ chipOn: filters.activeState === item.value }" @click="filters.activeState = item.value">{{ item.label }}</view>
        </view>
        <view class="chipRow">
          <view v-for="item in neverLoginOptions" :key="item.value" class="chip" :class="{ chipOn: filters.neverLoggedIn === item.value }" @click="filters.neverLoggedIn = item.value">{{ item.label }}</view>
        </view>
        <view class="chipRow">
          <view v-for="item in violationOptions" :key="item.value" class="chip" :class="{ chipOn: filters.hasViolation === item.value }" @click="filters.hasViolation = item.value">{{ item.label }}</view>
        </view>
        <view class="chipRow">
          <view v-for="item in loginDayOptions" :key="item.value" class="chip" :class="{ chipOn: filters.loginDays === item.value }" @click="filters.loginDays = item.value">{{ item.label }}</view>
        </view>
        <view class="muted sectionLabel">快捷筛选</view>
        <view class="chipRow">
          <view v-for="item in quickFilterOptions" :key="item.value" class="chip" :class="{ chipOn: filters.quickFilter === item.value }" @click="applyQuickFilter(item.value)">{{ item.label }}</view>
        </view>
        <view class="rowBetween">
          <button class="btnSecondary miniBtn" size="mini" @click="resetFilters">重置</button>
          <button class="btnPrimary miniBtn" size="mini" :loading="loading" @click="fetchUsers(true)">查询</button>
        </view>
      </view>

      <view class="card">
        <view class="cardTitle">新增用户</view>
        <view class="chipRow">
          <view
            v-for="item in editableRoleOptions"
            :key="`create-${item.value}`"
            class="chip"
            :class="{ chipOn: createForm.role === item.value }"
            @click="createForm.role = item.value"
          >
            {{ item.label }}
          </view>
        </view>
        <view class="grid2">
          <input class="inputBase" v-model.trim="createForm.username" placeholder="账号，学生建议填写学号" />
          <input class="inputBase" v-model.trim="createForm.password" password placeholder="密码，留空按规则生成" />
        </view>
        <view class="grid2">
          <input class="inputBase" v-model.trim="createForm.nickname" placeholder="昵称，可选" />
          <input class="inputBase" v-model.trim="createForm.phone" placeholder="手机号，可选" />
        </view>
        <view class="grid2" v-if="createForm.role === 'student'">
          <input class="inputBase" v-model.trim="createForm.className" placeholder="班级，如：计科2301" />
          <input class="inputBase" type="number" v-model.number="createForm.graduationYear" placeholder="毕业年份" />
        </view>
        <view class="muted sectionLabel" v-if="createForm.role === 'student'">学生留空密码时，系统会默认把学号作为初始密码。</view>
        <view class="muted sectionLabel" v-else>教师和管理员留空密码时，系统会使用默认初始密码。</view>
        <button class="btnPrimary miniBtn" size="mini" :loading="createLoading" @click="submitCreateUser">创建用户</button>
      </view>

      <view class="card">
        <view class="cardTitle">批量生成学生</view>
        <view class="grid2">
          <input class="inputBase" v-model.trim="batchGenerateForm.prefix" placeholder="学号前缀，如：202301" />
          <input class="inputBase" v-model.trim="batchGenerateForm.className" placeholder="班级，如：计科2301" />
        </view>
        <view class="grid3">
          <input class="inputBase" type="number" v-model.number="batchGenerateForm.startNo" placeholder="起始序号" />
          <input class="inputBase" type="number" v-model.number="batchGenerateForm.count" placeholder="人数" />
          <input class="inputBase" type="number" v-model.number="batchGenerateForm.numberWidth" placeholder="序号位数" />
        </view>
        <view class="grid2">
          <input class="inputBase" type="number" v-model.number="batchGenerateForm.graduationYear" placeholder="毕业年份" />
          <view class="chipRow compactChipRow">
            <view class="chip" :class="{ chipOn: batchGenerateForm.updateIfExists }" @click="batchGenerateForm.updateIfExists = !batchGenerateForm.updateIfExists">
              {{ batchGenerateForm.updateIfExists ? "已存在账号：覆盖" : "已存在账号：跳过" }}
            </view>
          </view>
        </view>
        <view class="rowBetween">
          <button class="btnSecondary miniBtn" size="mini" :loading="batchGeneratePreviewLoading" @click="previewBatchGenerate">预览账号</button>
          <button class="btnPrimary miniBtn" size="mini" :loading="batchGenerateLoading" @click="submitBatchGenerate">确认生成</button>
        </view>
        <view class="muted" v-if="batchGeneratePreviewText">{{ batchGeneratePreviewText }}</view>
        <view class="previewList" v-if="batchGeneratePreviewItems.length > 0">
          <view class="previewItem" v-for="item in batchGeneratePreviewItems" :key="item.username">
            <view class="titleSmall">{{ item.username }}</view>
            <view class="muted">初始密码：{{ item.password }} · {{ item.className }} · {{ item.graduationYear }}</view>
          </view>
        </view>
      </view>

      <view class="card">
        <view class="cardTitle">批量操作</view>
        <view class="chipRow">
          <view class="chip" @click="toggleSelectCurrentPage">{{ allCurrentPageSelected ? "取消全选本页" : "全选本页" }}</view>
          <view class="chip" @click="selectedIds = []">清空选择</view>
          <view class="muted">已选 {{ selectedIds.length }} 人</view>
        </view>

        <view class="muted sectionLabel">批量设置角色</view>
        <view class="chipRow">
          <view v-for="item in editableRoleOptions" :key="item.value" class="chip" :class="{ chipOn: batchRole === item.value }" @click="batchRole = item.value">{{ item.label }}</view>
        </view>
        <button class="btnPrimary miniBtn" size="mini" :loading="batchRoleLoading" :disabled="selectedIds.length <= 0 || !canManageRole" @click="batchSetRole">执行批量设角色</button>

        <view class="muted sectionLabel">毕业生批量停用</view>
        <view class="grid2">
          <input class="inputBase" type="number" v-model.number="graduateYear" placeholder="毕业年份" />
          <input class="inputBase" v-model.trim="graduateClassKeyword" placeholder="可选：班级关键字" />
        </view>
        <view class="chipRow">
          <view class="chip" :class="{ chipOn: graduateMode === 'eq' }" @click="graduateMode = 'eq'">仅该届</view>
          <view class="chip" :class="{ chipOn: graduateMode === 'lte' }" @click="graduateMode = 'lte'">该届及以前</view>
        </view>
        <view class="rowBetween">
          <button class="btnSecondary miniBtn" size="mini" :loading="graduatePreviewLoading" @click="previewGraduateDeactivate">预览命中</button>
          <button class="btnDanger miniBtn" size="mini" :loading="graduateApplyLoading" @click="applyGraduateDeactivate">批量停用</button>
        </view>
        <view class="muted" v-if="graduatePreviewText">{{ graduatePreviewText }}</view>

        <view class="muted sectionLabel">文本导入用户</view>
        <input class="inputBase" v-model.trim="importDefaultPassword" placeholder="默认密码，留空走系统默认密码" />
        <view class="chipRow">
          <view class="chip" :class="{ chipOn: importUpdateIfExists }" @click="importUpdateIfExists = !importUpdateIfExists">
            {{ importUpdateIfExists ? "已存在账号：覆盖" : "已存在账号：跳过" }}
          </view>
        </view>
        <textarea class="textareaBase importText" v-model.trim="importText" placeholder="每行：username,password,role,className,graduationYear,nickname,phone" />
        <button class="btnPrimary miniBtn" size="mini" :loading="importLoading" @click="submitImport">执行导入</button>
        <view class="muted" v-if="importResultText">{{ importResultText }}</view>
      </view>

      <view class="card" v-if="loading">
        <view class="muted">正在加载用户...</view>
      </view>

      <view class="stack" v-else-if="users.length > 0">
        <view class="card" v-for="u in users" :key="u.id">
          <view class="rowBetween">
            <view class="userHead">
              <view class="selectBox" :class="{ on: selectedIds.includes(Number(u.id)) }" @click="toggleSelect(u.id)">{{ selectedIds.includes(Number(u.id)) ? "√" : "" }}</view>
              <view>
                <view class="titleSmall">{{ u.username }}</view>
                <view class="muted">ID {{ u.id }} · 班级 {{ u.className || "-" }} · 毕业 {{ u.graduationYear || "-" }}</view>
                <view class="muted">最近登录 {{ u.lastLoginAt || "从未登录" }} · 违规 {{ u.violationCount || 0 }}</view>
              </view>
            </view>
            <view>
              <view class="chip">{{ roleText(u.role) }}</view>
              <view class="chip stateChip" :class="stateClass(u)">{{ stateText(u) }}</view>
            </view>
          </view>
          <view class="chipRow">
            <view v-for="item in editableRoleOptions" :key="`${u.id}-${item.value}`" class="chip" :class="{ chipOn: getDraftRole(u) === item.value }" @click="pickRole(u, item.value)">{{ item.label }}</view>
          </view>
          <view class="chipRow">
            <button class="btnPrimary miniBtn" size="mini" @click="goDetail(u)">详情</button>
            <button class="btnSecondary miniBtn" size="mini" :disabled="!canSaveRole(u)" @click="saveRole(u)">保存角色</button>
            <button class="btnSecondary miniBtn" size="mini" :disabled="!canEditUserRole(u)" @click="toggleFreeze(u)">{{ Number(u.isFrozen || 0) === 1 ? "解冻" : "冻结" }}</button>
            <button class="btnSecondary miniBtn" size="mini" :disabled="!canEditUserRole(u)" @click="resetPassword(u)">重置密码</button>
            <button class="btnDanger miniBtn" size="mini" :disabled="!canEditUserRole(u)" @click="deleteUser(u)">删除</button>
          </view>
        </view>

        <view class="card rowBetween" v-if="pageCount > 1">
          <button class="btnSecondary miniBtn" size="mini" :disabled="page <= 1 || loading" @click="prevPage">上一页</button>
          <view class="muted">第 {{ page }} / {{ pageCount }} 页</view>
          <button class="btnSecondary miniBtn" size="mini" :disabled="page >= pageCount || loading" @click="nextPage">下一页</button>
        </view>
      </view>

      <view class="emptyState" v-else>
        <view class="emptyTitle">没有匹配用户</view>
      </view>
    </view>
  </view>
</template>

<script>
import { BASE_URL } from "@/common/api.js"

function toInt(v, d = 0) {
  const n = Number(v)
  return Number.isFinite(n) ? Math.round(n) : d
}

function toQuery(params) {
  const out = []
  Object.keys(params || {}).forEach((k) => {
    const v = (params || {})[k]
    if (v === undefined || v === null || v === "") return
    out.push(`${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
  })
  return out.join("&")
}

export default {
  data() {
    return {
      users: [],
      operator: "",
      operatorId: 0,
      operatorRole: "",
      loading: false,
      createLoading: false,
      batchGenerateLoading: false,
      batchGeneratePreviewLoading: false,
      batchRoleLoading: false,
      graduatePreviewLoading: false,
      graduateApplyLoading: false,
      importLoading: false,
      filters: { keyword: "", role: "all", className: "", graduationYear: "", activeState: "all", graduateReferenceYear: new Date().getFullYear(), quickFilter: "all", neverLoggedIn: "all", hasViolation: "all", loginDays: "all" },
      roleOptions: [{ label: "全部角色", value: "all" }, { label: "管理员", value: "admin" }, { label: "教师", value: "teacher" }, { label: "学生", value: "student" }],
      activeOptions: [{ label: "全部状态", value: "all" }, { label: "正常", value: "active" }, { label: "停用", value: "inactive" }, { label: "冻结", value: "frozen" }],
      neverLoginOptions: [{ label: "全部登录状态", value: "all" }, { label: "从未登录", value: "yes" }, { label: "至少登录过", value: "no" }],
      violationOptions: [{ label: "全部违规", value: "all" }, { label: "有违规", value: "yes" }, { label: "无违规", value: "no" }],
      loginDayOptions: [{ label: "全部登录", value: "all" }, { label: "7 天内", value: "7" }, { label: "30 天内", value: "30" }, { label: "90 天内", value: "90" }],
      editableRoleOptions: [{ label: "学生", value: "student" }, { label: "教师", value: "teacher" }, { label: "管理员", value: "admin" }],
      quickFilterOptions: [
        { label: "全部用户", value: "all" },
        { label: "从未登录学生", value: "never-login-student" },
        { label: "已毕业未停用", value: "graduate-pending" },
        { label: "有违规未冻结", value: "violation-unfrozen" },
        { label: "学生缺少班级", value: "missing-class" },
        { label: "学生缺少毕业年份", value: "missing-graduation" }
      ],
      createForm: {
        role: "student",
        username: "",
        password: "",
        nickname: "",
        phone: "",
        className: "",
        graduationYear: new Date().getFullYear() + 4
      },
      batchGenerateForm: {
        prefix: "",
        className: "",
        startNo: 1,
        count: 40,
        numberWidth: 2,
        graduationYear: new Date().getFullYear() + 4,
        updateIfExists: false
      },
      batchGeneratePreviewText: "",
      batchGeneratePreviewItems: [],
      roleDraft: {},
      selectedIds: [],
      batchRole: "student",
      graduateYear: new Date().getFullYear(),
      graduateMode: "eq",
      graduateClassKeyword: "",
      graduatePreviewText: "",
      importDefaultPassword: "",
      importUpdateIfExists: true,
      importText: "",
      importResultText: "",
      governanceStats: {
        total: 0,
        adminCount: 0,
        teacherCount: 0,
        studentCount: 0,
        neverLoginStudentCount: 0,
        graduatePendingDeactivateCount: 0,
        violationUnfrozenCount: 0,
        missingClassNameCount: 0,
        missingGraduationYearCount: 0
      },
      page: 1,
      pageSize: 12,
      total: 0
    }
  },
  computed: {
    canManageRole() { return this.operatorRole === "admin" },
    pageCount() { return Math.max(1, Math.ceil(Math.max(0, this.total) / this.pageSize)) },
    allCurrentPageSelected() { return this.users.length > 0 && this.users.every((u) => this.selectedIds.includes(Number(u.id))) },
    activeQuickFilterMeta() {
      if (this.filters.quickFilter === "all") return null
      const descriptions = {
        "never-login-student": "仅查看从未登录过的学生账号，适合排查新建后未启用的账号。",
        "graduate-pending": `仅查看毕业年份小于等于 ${toInt(this.filters.graduateReferenceYear, new Date().getFullYear())} 且仍处于启用状态的学生账号。`,
        "violation-unfrozen": "仅查看已有违规记录但尚未冻结的账号，便于快速干预。",
        "missing-class": "仅查看班级信息为空的学生账号，用于治理历史脏数据。",
        "missing-graduation": "仅查看毕业年份缺失的学生账号，便于后续毕业停用治理。"
      }
      const target = (this.quickFilterOptions || []).find((item) => item.value === this.filters.quickFilter)
      if (!target) return null
      return Object.assign({}, target, { description: descriptions[this.filters.quickFilter] || "" })
    },
    governanceCards() {
      return [
        { label: "从未登录学生", value: toInt(this.governanceStats.neverLoginStudentCount, 0), quickFilter: "never-login-student" },
        { label: "已毕业未停用", value: toInt(this.governanceStats.graduatePendingDeactivateCount, 0), quickFilter: "graduate-pending" },
        { label: "有违规未冻结", value: toInt(this.governanceStats.violationUnfrozenCount, 0), quickFilter: "violation-unfrozen" },
        { label: "学生缺少班级", value: toInt(this.governanceStats.missingClassNameCount, 0), quickFilter: "missing-class" },
        { label: "学生缺少毕业年份", value: toInt(this.governanceStats.missingGraduationYearCount, 0), quickFilter: "missing-graduation" }
      ]
    }
  },
  onShow() {
    const s = uni.getStorageSync("session")
    if (!s || s.role !== "admin") return uni.reLaunch({ url: "/pages/login/login" })
    this.operator = s.username || ""
    this.operatorId = toInt(s.userId, 0)
    this.operatorRole = s.role || ""
    this.refreshUserView(true)
  },
  methods: {
    roleText(role) { return role === "admin" ? "管理员" : role === "teacher" ? "教师" : role === "student" ? "学生" : (role || "未知") },
    stateText(u) { return Number(u.isFrozen || 0) === 1 ? "冻结" : Number(u.isActive || 0) === 1 ? "正常" : "停用" },
    stateClass(u) { return Number(u.isFrozen || 0) === 1 ? "frozen" : Number(u.isActive || 0) === 1 ? "active" : "inactive" },
    resetFilters() {
      this.filters = { keyword: "", role: "all", className: "", graduationYear: "", activeState: "all", graduateReferenceYear: new Date().getFullYear(), quickFilter: "all", neverLoggedIn: "all", hasViolation: "all", loginDays: "all" }
      this.refreshUserView(true)
    },
    applyQuickFilter(value) {
      this.filters.quickFilter = value
      this.fetchUsers(true)
    },
    handleGraduateReferenceYearChange() {
      if (!toInt(this.filters.graduateReferenceYear, 0)) {
        this.filters.graduateReferenceYear = new Date().getFullYear()
      }
      this.fetchGovernanceStats()
      if (this.filters.quickFilter === "graduate-pending") {
        this.fetchUsers(true)
      }
    },
    fetchGovernanceStats() {
      uni.request({
        url: `${BASE_URL}/users/governance-stats?${toQuery({ graduateReferenceYear: toInt(this.filters.graduateReferenceYear, new Date().getFullYear()) })}`,
        method: "GET",
        success: (res) => {
          const payload = (res && res.data) || {}
          if (!payload || payload.ok === false) return
          this.governanceStats = Object.assign({}, this.governanceStats, payload.data || {})
        }
      })
    },
    refreshUserView(resetPage = false) {
      this.fetchUsers(resetPage)
      this.fetchGovernanceStats()
    },
    canEditUserRole(u) { return this.canManageRole && u && u.id && u.username !== "admin1" && Number(u.id) !== this.operatorId },
    getDraftRole(u) { return this.roleDraft[u.id] || u.role || "student" },
    pickRole(u, role) { if (this.canEditUserRole(u)) this.$set(this.roleDraft, u.id, role) },
    canSaveRole(u) { return this.canEditUserRole(u) && this.getDraftRole(u) !== u.role },
    buildQueryObj() {
      const p = { page: this.page, pageSize: this.pageSize }
      if (this.filters.keyword) p.keyword = this.filters.keyword
      if (this.filters.role !== "all") p.role = this.filters.role
      if (this.filters.className) p.className = this.filters.className
      if (toInt(this.filters.graduationYear, 0) > 0) p.graduationYear = toInt(this.filters.graduationYear, 0)
      if (this.filters.hasViolation === "yes") p.hasViolation = 1
      if (this.filters.hasViolation === "no") p.hasViolation = 0
      if (this.filters.neverLoggedIn === "yes") p.neverLoggedIn = 1
      if (this.filters.neverLoggedIn === "no") p.neverLoggedIn = 0
      if (this.filters.loginDays !== "all") p.loginDays = this.filters.loginDays
      if (this.filters.quickFilter === "never-login-student") {
        p.role = "student"
        p.neverLoggedIn = 1
      } else if (this.filters.quickFilter === "graduate-pending") {
        p.graduatePendingDeactivate = 1
        p.graduateReferenceYear = toInt(this.filters.graduateReferenceYear, new Date().getFullYear())
      } else if (this.filters.quickFilter === "violation-unfrozen") {
        p.violationUnfrozen = 1
      } else if (this.filters.quickFilter === "missing-class") {
        p.missingClassName = 1
      } else if (this.filters.quickFilter === "missing-graduation") {
        p.missingGraduationYear = 1
      }
      if (this.filters.activeState === "active") {
        p.isActive = 1
        p.isFrozen = 0
      } else if (this.filters.activeState === "inactive") {
        p.isActive = 0
      } else if (this.filters.activeState === "frozen") {
        p.isFrozen = 1
      }
      return p
    },
    fetchUsers(resetPage = false) {
      if (resetPage) this.page = 1
      this.loading = true
      const q = toQuery(this.buildQueryObj())
      uni.request({
        url: `${BASE_URL}/users${q ? `?${q}` : ""}`,
        method: "GET",
        success: (res) => {
          const data = (res && res.data) || {}
          if (!data || data.ok === false) return uni.showToast({ title: data.msg || "获取失败", icon: "none" })
          this.users = Array.isArray(data.data) ? data.data : []
          this.total = toInt(((data.meta || {}).total), this.users.length)
          this.page = Math.max(1, toInt(((data.meta || {}).page), this.page))
          const next = {}
          this.users.forEach((u) => { next[u.id] = this.roleDraft[u.id] || u.role || "student" })
          this.roleDraft = next
        },
        fail: () => uni.showToast({ title: "请求失败", icon: "none" }),
        complete: () => { this.loading = false }
      })
    },
    prevPage() { if (this.page > 1) { this.page -= 1; this.fetchUsers(false) } },
    nextPage() { if (this.page < this.pageCount) { this.page += 1; this.fetchUsers(false) } },
    goDetail(u) { uni.navigateTo({ url: `/pages/admin/user_detail?uid=${Number(u.id || 0)}` }) },
    saveRole(u) {
      if (!this.canSaveRole(u)) return
      uni.request({
        url: `${BASE_URL}/users/${u.id}/set-role`,
        method: "POST",
        header: { "Content-Type": "application/json" },
        data: { role: this.getDraftRole(u) },
        success: (res) => {
          if (!res.data || !res.data.ok) return uni.showToast({ title: (res.data && res.data.msg) || "失败", icon: "none" })
          this.refreshUserView(false)
        }
      })
    },
    toggleFreeze(u) {
      if (!this.canEditUserRole(u)) return
      const action = Number(u.isFrozen || 0) === 1 ? "unfreeze" : "freeze"
      uni.request({
        url: `${BASE_URL}/users/${u.id}/${action}`,
        method: "POST",
        header: { "Content-Type": "application/json" },
        data: {},
        success: (res) => {
          if (!res.data || !res.data.ok) return uni.showToast({ title: (res.data && res.data.msg) || "失败", icon: "none" })
          this.refreshUserView(false)
        }
      })
    },
    resetPassword(u) {
      if (!this.canEditUserRole(u)) return
      uni.request({
        url: `${BASE_URL}/users/${u.id}/reset-password`,
        method: "POST",
        header: { "Content-Type": "application/json" },
        data: {},
        success: (res) => {
          const payload = (res && res.data) || {}
          if (!payload.ok) return uni.showToast({ title: payload.msg || "失败", icon: "none" })
          const pwd = (((payload || {}).data || {}).temporaryPassword || "").trim()
          if (pwd) uni.showModal({ title: "重置成功", content: `临时密码：${pwd}`, showCancel: false })
        }
      })
    },
    deleteUser(u) {
      if (!this.canEditUserRole(u)) return
      uni.showModal({
        title: "删除用户",
        content: `确认删除用户 ${u.username} 吗？`,
        success: (modalRes) => {
          if (!modalRes.confirm) return
          uni.request({
            url: `${BASE_URL}/users/${u.id}/delete`,
            method: "POST",
            header: { "Content-Type": "application/json" },
            data: {},
            success: (res) => {
              if (!res.data || !res.data.ok) return uni.showToast({ title: (res.data && res.data.msg) || "失败", icon: "none" })
              this.refreshUserView(false)
            }
          })
        }
      })
    },
    toggleSelect(id) {
      const uid = Number(id)
      if (uid <= 0) return
      if (this.selectedIds.includes(uid)) this.selectedIds = this.selectedIds.filter((x) => Number(x) !== uid)
      else this.selectedIds = this.selectedIds.concat([uid])
    },
    toggleSelectCurrentPage() {
      const ids = this.users.map((u) => Number(u.id)).filter((x) => x > 0)
      if (this.allCurrentPageSelected) this.selectedIds = this.selectedIds.filter((id) => !ids.includes(Number(id)))
      else this.selectedIds = Array.from(new Set(this.selectedIds.concat(ids)))
    },
    batchSetRole() {
      if (!this.selectedIds.length) return uni.showToast({ title: "请先选择用户", icon: "none" })
      this.batchRoleLoading = true
      uni.request({
        url: `${BASE_URL}/users/batch-set-role`,
        method: "POST",
        header: { "Content-Type": "application/json" },
        data: { ids: this.selectedIds, role: this.batchRole },
        success: () => this.refreshUserView(false),
        complete: () => { this.batchRoleLoading = false }
      })
    },
    validateCreateForm() {
      if (!this.createForm.username) {
        uni.showToast({ title: "请填写账号", icon: "none" })
        return false
      }
      if (this.createForm.password && String(this.createForm.password).trim().length < 6) {
        uni.showToast({ title: "密码至少 6 位", icon: "none" })
        return false
      }
      if (this.createForm.role === "student") {
        if (!this.createForm.className) {
          uni.showToast({ title: "学生必须填写班级", icon: "none" })
          return false
        }
        if (!toInt(this.createForm.graduationYear, 0)) {
          uni.showToast({ title: "学生必须填写毕业年份", icon: "none" })
          return false
        }
      }
      return true
    },
    submitCreateUser() {
      if (!this.validateCreateForm()) return
      this.createLoading = true
      uni.request({
        url: `${BASE_URL}/users`,
        method: "POST",
        header: { "Content-Type": "application/json" },
        data: {
          username: this.createForm.username,
          role: this.createForm.role,
          password: this.createForm.password || "",
          nickname: this.createForm.nickname || "",
          phone: this.createForm.phone || "",
          className: this.createForm.role === "student" ? this.createForm.className || "" : "",
          graduationYear: this.createForm.role === "student" ? toInt(this.createForm.graduationYear, 0) : 0
        },
        success: (res) => {
          const payload = (res && res.data) || {}
          if (!payload.ok) return uni.showToast({ title: payload.msg || "创建失败", icon: "none" })
          const data = payload.data || {}
          this.refreshUserView(true)
          uni.showModal({
            title: "创建成功",
            content: `账号：${this.createForm.username}\n初始密码：${data.initialPassword || "系统默认密码"}`,
            showCancel: false
          })
          this.createForm = {
            role: "student",
            username: "",
            password: "",
            nickname: "",
            phone: "",
            className: "",
            graduationYear: new Date().getFullYear() + 4
          }
        },
        complete: () => { this.createLoading = false }
      })
    },
    validateBatchGenerateForm() {
      if (!this.batchGenerateForm.prefix) {
        uni.showToast({ title: "请填写学号前缀", icon: "none" })
        return false
      }
      if (!this.batchGenerateForm.className) {
        uni.showToast({ title: "请填写班级", icon: "none" })
        return false
      }
      if (toInt(this.batchGenerateForm.count, 0) <= 0) {
        uni.showToast({ title: "请填写生成人数", icon: "none" })
        return false
      }
      return true
    },
    batchGeneratePayload(dryRun) {
      return {
        prefix: this.batchGenerateForm.prefix || "",
        className: this.batchGenerateForm.className || "",
        startNo: toInt(this.batchGenerateForm.startNo, 1),
        count: toInt(this.batchGenerateForm.count, 0),
        numberWidth: toInt(this.batchGenerateForm.numberWidth, 2),
        graduationYear: toInt(this.batchGenerateForm.graduationYear, 0),
        updateIfExists: !!this.batchGenerateForm.updateIfExists,
        dryRun: !!dryRun
      }
    },
    previewBatchGenerate() {
      if (!this.validateBatchGenerateForm()) return
      this.batchGeneratePreviewLoading = true
      uni.request({
        url: `${BASE_URL}/users/batch-generate-students`,
        method: "POST",
        header: { "Content-Type": "application/json" },
        data: this.batchGeneratePayload(true),
        success: (res) => {
          const payload = (res && res.data) || {}
          if (!payload.ok) return uni.showToast({ title: payload.msg || "预览失败", icon: "none" })
          const data = payload.data || {}
          this.batchGeneratePreviewItems = Array.isArray(data.preview) ? data.preview.slice(0, 20) : []
          this.batchGeneratePreviewText = `预览共 ${toInt(data.count, 0)} 个账号，序号范围 ${toInt(data.startNo, 0)} - ${toInt(data.endNo, 0)}`
        },
        complete: () => { this.batchGeneratePreviewLoading = false }
      })
    },
    submitBatchGenerate() {
      if (!this.validateBatchGenerateForm()) return
      this.batchGenerateLoading = true
      uni.request({
        url: `${BASE_URL}/users/batch-generate-students`,
        method: "POST",
        header: { "Content-Type": "application/json" },
        data: this.batchGeneratePayload(false),
        success: (res) => {
          const payload = (res && res.data) || {}
          if (!payload.ok) return uni.showToast({ title: payload.msg || "生成失败", icon: "none" })
          const data = payload.data || {}
          this.batchGeneratePreviewText = `生成完成：新增 ${toInt(data.inserted, 0)}，更新 ${toInt(data.updated, 0)}，跳过 ${toInt(data.skipped, 0)}，失败 ${toInt(data.failed, 0)}`
          this.refreshUserView(true)
        },
        complete: () => { this.batchGenerateLoading = false }
      })
    },
    graduatePayload(dryRun) {
      return {
        graduationYear: toInt(this.graduateYear, 0),
        mode: this.graduateMode,
        classKeyword: this.graduateClassKeyword || "",
        dryRun: !!dryRun
      }
    },
    previewGraduateDeactivate() {
      this.graduatePreviewLoading = true
      uni.request({
        url: `${BASE_URL}/users/batch-deactivate-graduates`,
        method: "POST",
        header: { "Content-Type": "application/json" },
        data: this.graduatePayload(true),
        success: (res) => {
          const d = ((res || {}).data || {}).data || {}
          this.graduatePreviewText = `预览命中 ${toInt(d.matched, 0)} 人`
        },
        complete: () => { this.graduatePreviewLoading = false }
      })
    },
    applyGraduateDeactivate() {
      this.graduateApplyLoading = true
      uni.request({
        url: `${BASE_URL}/users/batch-deactivate-graduates`,
        method: "POST",
        header: { "Content-Type": "application/json" },
        data: this.graduatePayload(false),
        success: (res) => {
          const d = ((res || {}).data || {}).data || {}
          this.graduatePreviewText = `已停用 ${toInt(d.deactivated, 0)} 人`
          this.refreshUserView(false)
        },
        complete: () => { this.graduateApplyLoading = false }
      })
    },
    submitImport() {
      if (!this.importText) return uni.showToast({ title: "请先粘贴导入内容", icon: "none" })
      this.importLoading = true
      uni.request({
        url: `${BASE_URL}/users/import`,
        method: "POST",
        header: { "Content-Type": "application/json" },
        data: {
          text: this.importText,
          updateIfExists: !!this.importUpdateIfExists,
          defaultPassword: (this.importDefaultPassword || "").trim() || undefined
        },
        success: (res) => {
          const d = ((res || {}).data || {}).data || {}
          this.importResultText = `新增 ${toInt(d.inserted, 0)}，更新 ${toInt(d.updated, 0)}，失败 ${toInt(d.failed, 0)}`
          this.refreshUserView(false)
        },
        complete: () => { this.importLoading = false }
      })
    }
  }
}
</script>

<style lang="scss">
.usersPage { padding-bottom: 20px; }
.miniBtn { min-height: 30px; line-height: 30px; padding: 0 10px; font-size: 12px; border-radius: 9px; }
.chipRow { margin-top: 8px; display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
.compactChipRow { margin-top: 0; }
.chipOn { border-color: #bfdbfe; background: #eaf3ff; color: #1d4ed8; }
.grid2 { margin-top: 8px; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
.grid3 { margin-top: 8px; display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; }
.sectionLabel { margin-top: 12px; }
.governanceGrid { margin-top: 8px; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
.governanceCard { padding: 12px; border-radius: 12px; background: #f8fafc; border: 1px solid #e2e8f0; }
.governanceCardOn { border-color: #bfdbfe; background: #eaf3ff; }
.filterNotice { margin-top: 10px; padding: 12px; border-radius: 12px; background: #eff6ff; border: 1px solid #bfdbfe; }
.importText { margin-top: 8px; min-height: 96px; }
.userHead { display: flex; gap: 10px; }
.selectBox { width: 20px; height: 20px; line-height: 20px; border-radius: 6px; border: 1px solid #cbd5e1; text-align: center; color: transparent; }
.selectBox.on { background: #2563eb; border-color: #2563eb; color: #fff; }
.titleSmall { font-size: 14px; font-weight: 700; color: #0f172a; }
.stateChip { margin-top: 6px; }
.stateChip.active { background: #e8fff0; color: #1f7a3a; }
.stateChip.inactive { background: #fff4e8; color: #b45309; }
.stateChip.frozen { background: #ffeaea; color: #b42318; }
.previewList { margin-top: 8px; display: flex; flex-direction: column; gap: 8px; }
.previewItem { padding: 10px 12px; border-radius: 10px; background: #f8fafc; }
</style>

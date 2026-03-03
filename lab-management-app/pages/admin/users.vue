<template>
  <view class="container usersPage">
    <view class="stack">
      <view class="card heroCard">
        <view class="rowBetween heroTop">
          <view>
            <view class="title">用户管理</view>
            <view class="subtitle">仅 `admin1` 可升降级管理员权限</view>
          </view>
          <button class="btnSecondary miniBtn" size="mini" @click="fetchUsers">刷新</button>
        </view>

        <view class="heroMetaRow">
          <view class="heroMetaItem">当前操作人：{{ operator || '-' }}</view>
          <view class="heroMetaItem">权限：{{ canManageRole ? '可管理权限' : '仅查看' }}</view>
        </view>
      </view>

      <view class="metricGrid">
        <view class="card metricCard" v-for="item in metrics" :key="item.key">
          <view class="metricLabel">{{ item.label }}</view>
          <view class="metricValue">{{ item.value }}</view>
          <view class="metricHint">{{ item.hint }}</view>
        </view>
      </view>

      <view class="card filterCard">
        <view class="rowBetween">
          <view class="cardTitle">筛选条件</view>
          <view class="muted">匹配 {{ filteredUsers.length }} 人</view>
        </view>

        <input
          class="inputBase"
          v-model="keyword"
          placeholder="按用户名或 ID 搜索"
        />

        <view class="chipRow">
          <view
            v-for="item in roleOptions"
            :key="item.value"
            class="chip roleChip"
            :class="{ chipOn: roleFilter === item.value }"
            @click="setRoleFilter(item.value)"
          >
            {{ item.label }}
          </view>
          <view class="chip roleChip" @click="resetFilters">重置</view>
        </view>
      </view>

      <view class="card loadingCard" v-if="loading">
        <view class="muted">正在加载用户列表...</view>
      </view>

      <view class="stack" v-else-if="pagedUsers.length > 0">
        <view v-for="u in pagedUsers" :key="u.id" class="card userItem">
          <view class="rowBetween">
            <view>
              <view class="userName">{{ u.username }}</view>
              <view class="meta">ID: {{ u.id }}</view>
            </view>
            <view class="roleTag" :class="roleClass(u.role)">{{ roleText(u.role) }}</view>
          </view>

          <view class="actions">
            <button
              v-if="canPromote(u)"
              class="btnPrimary miniBtn"
              size="mini"
              :disabled="isActionBusy(u.id)"
              @click="promote(u)"
            >
              {{ isActionBusy(u.id) ? '处理中...' : '升为管理员' }}
            </button>

            <button
              v-if="canDemote(u)"
              class="btnGhost miniBtn"
              size="mini"
              :disabled="isActionBusy(u.id)"
              @click="demote(u)"
            >
              {{ isActionBusy(u.id) ? '处理中...' : '降为普通用户' }}
            </button>

            <view class="muted" v-if="!canPromote(u) && !canDemote(u)">当前角色无需操作</view>
          </view>
        </view>

        <view class="card pageCard rowBetween" v-if="pageCount > 1">
          <button class="btnSecondary miniBtn" size="mini" :disabled="currentPage <= 1" @click="prevPage">上一页</button>
          <view class="muted">第 {{ currentPage }} / {{ pageCount }} 页</view>
          <button class="btnSecondary miniBtn" size="mini" :disabled="currentPage >= pageCount" @click="nextPage">下一页</button>
        </view>
      </view>

      <view class="emptyState" v-else>
        <view class="emptyIcon">人</view>
        <view class="emptyTitle">没有匹配的用户</view>
        <view class="emptySub">可以尝试清空关键词或切换角色筛选</view>
      </view>
    </view>
  </view>
</template>

<script>
import { BASE_URL } from "@/common/api.js"

export default {
  data() {
    return {
      users: [],
      operator: "",
      loading: false,
      keyword: "",
      roleFilter: "all",
      roleOptions: [
        { label: "全部", value: "all" },
        { label: "管理员", value: "admin" },
        { label: "教师", value: "teacher" },
        { label: "学生", value: "student" }
      ],
      page: 1,
      pageSize: 8,
      actionLoadingId: 0
    }
  },
  computed: {
    canManageRole() {
      return this.operator === "admin1"
    },
    metrics() {
      const adminCount = this.users.filter((x) => x.role === "admin").length
      const teacherCount = this.users.filter((x) => x.role === "teacher").length
      const studentCount = this.users.filter((x) => x.role === "student").length
      return [
        { key: "total", label: "用户总数", value: this.users.length, hint: "全量账号" },
        { key: "admin", label: "管理员", value: adminCount, hint: "含超级管理员" },
        { key: "teacher", label: "教师", value: teacherCount, hint: "教学相关账号" },
        { key: "student", label: "学生", value: studentCount, hint: "普通用户" }
      ]
    },
    filteredUsers() {
      const q = this.keyword.trim().toLowerCase()
      return this.users.filter((u) => {
        const passRole = this.roleFilter === "all" ? true : u.role === this.roleFilter
        if (!passRole) return false
        if (!q) return true
        const name = String(u.username || "").toLowerCase()
        const id = String(u.id || "")
        return name.includes(q) || id.includes(q)
      })
    },
    pageCount() {
      const total = this.filteredUsers.length
      return Math.max(1, Math.ceil(total / this.pageSize))
    },
    currentPage() {
      return Math.min(Math.max(this.page, 1), this.pageCount)
    },
    pagedUsers() {
      const start = (this.currentPage - 1) * this.pageSize
      const end = start + this.pageSize
      return this.filteredUsers.slice(start, end)
    }
  },
  watch: {
    keyword() {
      this.page = 1
    },
    roleFilter() {
      this.page = 1
    }
  },
  onShow() {
    const s = uni.getStorageSync("session")
    if (!s || s.role !== "admin") {
      uni.showToast({ title: "无权限", icon: "none" })
      uni.reLaunch({ url: "/pages/login/login" })
      return
    }

    this.operator = s.username || ""
    this.fetchUsers()
  },
  methods: {
    roleText(role) {
      if (role === "admin") return "管理员"
      if (role === "teacher") return "教师"
      if (role === "student") return "学生"
      return role || "未知"
    },
    roleClass(role) {
      if (role === "admin") return "admin"
      if (role === "teacher") return "teacher"
      if (role === "student") return "student"
      return "default"
    },
    setRoleFilter(role) {
      this.roleFilter = role
    },
    resetFilters() {
      this.keyword = ""
      this.roleFilter = "all"
      this.page = 1
    },
    prevPage() {
      this.page = Math.max(1, this.currentPage - 1)
    },
    nextPage() {
      this.page = Math.min(this.pageCount, this.currentPage + 1)
    },
    isActionBusy(id) {
      return this.actionLoadingId === id
    },
    canPromote(u) {
      return this.canManageRole && u.role !== "admin"
    },
    canDemote(u) {
      return this.canManageRole && u.role === "admin" && u.username !== "admin1"
    },
    fetchUsers() {
      this.loading = true
      uni.request({
        url: `${BASE_URL}/users`,
        method: "GET",
        success: (res) => {
          this.users = Array.isArray(res.data) ? res.data : []
        },
        fail: () => {
          this.users = []
          uni.showToast({ title: "获取失败", icon: "none" })
        },
        complete: () => {
          this.loading = false
        }
      })
    },
    promote(u) {
      if (!this.canManageRole) {
        uni.showToast({ title: "仅 admin1 可操作", icon: "none" })
        return
      }
      uni.showModal({
        title: "确认升级",
        content: `将 ${u.username} 升级为管理员？`,
        success: (m) => {
          if (!m.confirm) return
          this.actionLoadingId = u.id
          uni.request({
            url: `${BASE_URL}/users/${u.id}/promote`,
            method: "POST",
            header: { "Content-Type": "application/json" },
            data: { operator: this.operator },
            success: (res) => {
              if (!res.data || !res.data.ok) {
                uni.showToast({ title: (res.data && res.data.msg) || "操作失败", icon: "none" })
                return
              }
              uni.showToast({ title: "已升级", icon: "success" })
              this.fetchUsers()
            },
            fail: () => {
              uni.showToast({ title: "请求失败", icon: "none" })
            },
            complete: () => {
              this.actionLoadingId = 0
            }
          })
        }
      })
    },
    demote(u) {
      if (!this.canManageRole) {
        uni.showToast({ title: "仅 admin1 可操作", icon: "none" })
        return
      }
      uni.showModal({
        title: "确认降级",
        content: `将 ${u.username} 降级为普通用户？`,
        success: (m) => {
          if (!m.confirm) return
          this.actionLoadingId = u.id
          uni.request({
            url: `${BASE_URL}/users/${u.id}/demote`,
            method: "POST",
            header: { "Content-Type": "application/json" },
            data: { operator: this.operator },
            success: (res) => {
              if (!res.data || !res.data.ok) {
                uni.showToast({ title: (res.data && res.data.msg) || "操作失败", icon: "none" })
                return
              }
              uni.showToast({ title: "已降级", icon: "success" })
              this.fetchUsers()
            },
            fail: () => {
              uni.showToast({ title: "请求失败", icon: "none" })
            },
            complete: () => {
              this.actionLoadingId = 0
            }
          })
        }
      })
    }
  }
}
</script>

<style lang="scss">
.usersPage {
  padding-bottom: 20px;
}

.heroCard {
  border: 1px solid rgba(22, 119, 255, 0.18);
  background: linear-gradient(160deg, #ffffff 0%, #f2f7ff 100%);
}

.heroTop {
  align-items: flex-start;
}

.heroMetaRow {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.heroMetaItem {
  height: 25px;
  line-height: 25px;
  border-radius: 999px;
  padding: 0 10px;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(148, 163, 184, 0.24);
  color: #334155;
  font-size: 11px;
}

.miniBtn {
  min-height: 30px;
  line-height: 30px;
  padding: 0 10px;
  font-size: 12px;
  border-radius: 9px;
}

.metricGrid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.metricCard {
  min-height: 92px;
}

.metricLabel {
  font-size: 12px;
  color: #64748b;
}

.metricValue {
  margin-top: 4px;
  font-size: 24px;
  line-height: 1.15;
  font-weight: 700;
  color: #0f172a;
}

.metricHint {
  margin-top: 4px;
  font-size: 11px;
  color: #94a3b8;
}

.filterCard {
  border: 1px solid rgba(148, 163, 184, 0.24);
}

.chipRow {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.roleChip {
  transition: all 0.14s ease;
}

.chipOn {
  border-color: #bfdbfe;
  background: #eaf3ff;
  color: #1d4ed8;
}

.loadingCard {
  min-height: 70px;
  display: flex;
  align-items: center;
}

.userItem {
  border: 1px solid rgba(148, 163, 184, 0.24);
}

.userName {
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
}

.meta {
  margin-top: 6px;
  color: #64748b;
  font-size: 12px;
}

.roleTag {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 999px;
  background: #eef2f6;
  color: #475569;
}

.roleTag.admin {
  background: #eaf3ff;
  color: #1d4ed8;
}

.roleTag.teacher {
  background: #e8fff0;
  color: #1f7a3a;
}

.roleTag.student {
  background: #fff7e6;
  color: #8a5a00;
}

.actions {
  margin-top: 10px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.pageCard {
  border: 1px solid rgba(148, 163, 184, 0.24);
}
</style>

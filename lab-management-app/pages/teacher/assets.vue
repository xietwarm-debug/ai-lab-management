<template>
  <view class="container assetPortalPage">
    <view class="stack">
      <view class="card heroCard">
        <view class="title">资产只读查询</view>
        <view class="subtitle">面向已授权教师开放，可查看资产编号、状态、所在实验室和到期提醒。</view>
      </view>

      <view class="card filterCard">
        <view class="label">关键词</view>
        <input
          class="inputBase"
          v-model.trim="keyword"
          placeholder="搜索资产编号、设备名、实验室"
          confirm-type="search"
          @confirm="doSearch"
        />

        <view class="label">状态</view>
        <view class="chipRow">
          <view
            v-for="item in statusOptions"
            :key="item.value"
            class="chip"
            :class="{ chipOn: status === item.value }"
            @click="setStatus(item.value)"
          >
            {{ item.label }}
          </view>
        </view>

        <view class="label">借用筛选</view>
        <view class="chipRow">
          <view
            v-for="item in borrowedOptions"
            :key="item.value"
            class="chip"
            :class="{ chipOn: borrowedFilter === item.value }"
            @click="setBorrowedFilter(item.value)"
          >
            {{ item.label }}
          </view>
        </view>

        <view class="label">到期筛选</view>
        <view class="chipRow">
          <view
            v-for="item in dueOptions"
            :key="item.value"
            class="chip"
            :class="{ chipOn: dueMode === item.value }"
            @click="setDueMode(item.value)"
          >
            {{ item.label }}
          </view>
        </view>

        <view class="actions">
          <button class="btnPrimary miniBtn" size="mini" @click="doSearch">查询</button>
          <button class="btnSecondary miniBtn" size="mini" @click="resetFilters">重置</button>
        </view>
      </view>

      <view class="card" v-if="!hasPermission">
        <view class="muted">当前账号未开通资产只读权限，请联系管理员授权。</view>
      </view>

      <view class="card" v-else-if="loading && rows.length === 0">
        <view class="muted">加载中...</view>
      </view>

      <view class="card emptyState" v-else-if="rows.length === 0">
        <view class="emptyTitle">暂无可显示的资产</view>
        <view class="muted">可以调整筛选条件后再试一次。</view>
      </view>

      <view class="stack" v-else>
        <view class="card itemCard" v-for="item in rows" :key="item.id">
          <view class="rowBetween">
            <view class="itemTitle">{{ item.name || "-" }}</view>
            <view class="statusTag" :class="statusTone(item.status)">{{ item.statusLabel || statusText(item.status) }}</view>
          </view>
          <view class="meta">资产编号：{{ item.assetCode || "-" }}</view>
          <view class="meta">实验室：{{ item.labName || "-" }}</view>
          <view class="meta">借用状态：{{ item.borrowStatusText || (item.isBorrowed ? "已借出" : "在库") }}</view>
          <view class="meta">借用权限：{{ item.allowBorrow ? "允许借用" : "禁止借用" }}</view>
          <view class="meta">下次维保：{{ item.nextMaintenanceAt || "-" }}</view>
          <view class="meta">质保到期：{{ item.warrantyUntil || "-" }}</view>
          <view class="meta" v-if="item.locationNote">定位备注：{{ item.locationNote }}</view>
        </view>
      </view>

      <view class="card pageCard rowBetween" v-if="rows.length > 0">
        <view class="muted">第 {{ page }} 页 / 共 {{ total }} 条</view>
        <view class="muted" v-if="loadingMore">加载更多中...</view>
        <view class="muted" v-else-if="!hasMore">没有更多了</view>
        <view class="muted" v-else>上拉加载更多</view>
      </view>
    </view>
  </view>
</template>

<script>
import { listAssetPortalEquipments } from "@/common/api.js"
import { HOME_PAGE_URL, requireRole } from "@/common/session.js"

const PERMISSION_ASSET_READ_BASIC = "asset.read_basic"

export default {
  data() {
    return {
      role: "",
      permissions: [],
      hasPermission: false,
      keyword: "",
      status: "",
      borrowedFilter: "",
      dueMode: "",
      rows: [],
      page: 1,
      pageSize: 20,
      total: 0,
      loading: false,
      loadingMore: false
    }
  },
  computed: {
    hasMore() {
      return this.rows.length < this.total
    },
    statusOptions() {
      return [
        { label: "全部", value: "" },
        { label: "在用", value: "in_service" },
        { label: "维修中", value: "repairing" },
        { label: "已报废", value: "scrapped" }
      ]
    },
    borrowedOptions() {
      return [
        { label: "全部", value: "" },
        { label: "已借出", value: "borrowed" },
        { label: "在库", value: "free" }
      ]
    },
    dueOptions() {
      return [
        { label: "不限", value: "" },
        { label: "30天内维保", value: "maintenance" },
        { label: "30天内质保", value: "warranty" }
      ]
    }
  },
  onShow() {
    if (!this.ensureAccess()) return
    this.fetchList(true)
  },
  onPullDownRefresh() {
    if (!this.ensureAccess(false)) {
      uni.stopPullDownRefresh()
      return
    }
    this.fetchList(true).finally(() => uni.stopPullDownRefresh())
  },
  onReachBottom() {
    if (!this.ensureAccess(false)) return
    this.fetchList(false)
  },
  methods: {
    ensureAccess(withToast = true) {
      const session = requireRole(["admin", "teacher"], {
        toast: withToast,
        message: "暂无权限访问",
        fallbackUrl: HOME_PAGE_URL
      })
      if (!session) return false
      this.role = String(session.role || "").trim()
      this.permissions = Array.isArray(session.permissions) ? session.permissions : []
      this.hasPermission = this.role === "admin" || this.permissions.includes(PERMISSION_ASSET_READ_BASIC)
      if (!this.hasPermission && withToast) {
        uni.showToast({ title: "请联系管理员开通资产只读权限", icon: "none" })
      }
      return this.hasPermission
    },
    buildParams(pageNo = 1) {
      const params = {
        page: pageNo,
        pageSize: this.pageSize,
        keyword: this.keyword,
        status: this.status
      }
      if (this.borrowedFilter === "borrowed") params.isBorrowed = 1
      if (this.borrowedFilter === "free") params.isBorrowed = 0
      if (this.dueMode === "maintenance") params.maintenanceDueDays = 30
      if (this.dueMode === "warranty") params.warrantyDueDays = 30
      return params
    },
    async fetchList(reset = true) {
      if (!this.hasPermission) return
      const targetPage = reset ? 1 : this.page + 1
      if (!reset && !this.hasMore) return
      if (reset) {
        this.loading = true
      } else {
        this.loadingMore = true
      }
      try {
        const res = await listAssetPortalEquipments(this.buildParams(targetPage))
        const payload = (res && res.data) || {}
        if (!payload || !payload.ok) {
          throw new Error((payload && payload.msg) || "获取资产失败")
        }
        const list = Array.isArray(payload.data) ? payload.data : []
        const meta = payload.meta && typeof payload.meta === "object" ? payload.meta : {}
        this.page = Number(meta.page || targetPage || 1)
        this.total = Number(meta.total || list.length || 0)
        this.rows = reset ? list : this.rows.concat(list)
      } catch (error) {
        if (reset) this.rows = []
        uni.showToast({ title: (error && error.message) || "获取资产失败", icon: "none" })
      } finally {
        this.loading = false
        this.loadingMore = false
      }
    },
    doSearch() {
      this.fetchList(true)
    },
    resetFilters() {
      this.keyword = ""
      this.status = ""
      this.borrowedFilter = ""
      this.dueMode = ""
      this.fetchList(true)
    },
    setStatus(value) {
      this.status = value
      this.fetchList(true)
    },
    setBorrowedFilter(value) {
      this.borrowedFilter = value
      this.fetchList(true)
    },
    setDueMode(value) {
      this.dueMode = value
      this.fetchList(true)
    },
    statusText(status) {
      const key = String(status || "").trim()
      if (key === "in_service") return "在用"
      if (key === "repairing") return "维修中"
      if (key === "scrapped") return "已报废"
      return key || "未知"
    },
    statusTone(status) {
      const key = String(status || "").trim()
      if (key === "repairing") return "warn"
      if (key === "scrapped") return "danger"
      return "ok"
    }
  }
}
</script>

<style lang="scss">
.assetPortalPage {
  padding-bottom: 20px;
}

.heroCard {
  border: 1px solid rgba(96, 165, 250, 0.22);
  background: linear-gradient(160deg, #f8fbff 0%, #eef6ff 100%);
}

.filterCard {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.label {
  font-size: 12px;
  color: #64748b;
}

.chipRow {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.chip {
  padding: 6px 12px;
  border-radius: 999px;
  background: #f8fafc;
  border: 1px solid rgba(148, 163, 184, 0.2);
  color: #475569;
  font-size: 12px;
}

.chipOn {
  color: #2563eb;
  background: #eff6ff;
  border-color: rgba(59, 130, 246, 0.28);
}

.itemCard {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.itemTitle {
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
}

.meta {
  font-size: 13px;
  color: #475569;
}

.statusTag {
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
}

.statusTag.ok {
  background: #ecfdf5;
  color: #047857;
}

.statusTag.warn {
  background: #fff7ed;
  color: #c2410c;
}

.statusTag.danger {
  background: #fef2f2;
  color: #b91c1c;
}

.emptyState {
  text-align: center;
}

.emptyTitle {
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
}
</style>

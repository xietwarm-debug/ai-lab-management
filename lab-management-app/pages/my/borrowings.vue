<template>
  <view class="container myBorrowPage">
    <view class="stack">
      <view class="card heroCard">
        <view class="rowBetween heroTop">
          <view>
            <view class="title">我的借用</view>
            <view class="subtitle">查看借用申请、审批和归还状态</view>
          </view>
          <button class="btnPrimary miniBtn" size="mini" @click="goApply">发起借用</button>
        </view>
      </view>

      <view class="card filterCard">
        <view class="chipRow">
          <view
            v-for="item in statusOptions"
            :key="item.value"
            class="chip statusChip"
            :class="{ chipOn: statusFilter === item.value }"
            @click="setStatus(item.value)"
          >
            {{ item.label }}
          </view>
        </view>
        <view class="rowBetween">
          <view class="muted">共 {{ total }} 条</view>
          <button class="btnSecondary miniBtn" size="mini" @click="queryMine">刷新</button>
        </view>
      </view>

      <view class="card loadingCard" v-if="loading && list.length === 0">
        <view class="muted">正在加载借用记录...</view>
      </view>

      <view class="stack" v-else-if="list.length > 0">
        <view
          v-for="row in list"
          :key="row.id"
          :id="`borrow-row-${row.id}`"
          class="card itemCard"
          :class="{ focusItem: isFocused(row) }"
        >
          <view class="rowBetween">
            <view class="itemName">{{ row.equipmentName || row.equipmentAssetCode || "-" }}</view>
            <view class="statusTag" :class="statusTone(row)">{{ statusText(row) }}</view>
          </view>
          <view class="meta">资产编号：{{ row.equipmentAssetCode || "-" }}</view>
          <view class="meta">实验室：{{ row.equipmentLabName || "-" }}</view>
          <view class="meta">借用时间：{{ row.borrowStartAt || "-" }}</view>
          <view class="meta">应还时间：{{ row.expectedReturnAt || "-" }}</view>
          <view class="meta" v-if="row.returnedAt">归还时间：{{ row.returnedAt }}</view>
          <view class="meta">用途：{{ row.purpose || "-" }}</view>
          <view class="meta" v-if="row.adminNote">管理员备注：{{ row.adminNote }}</view>
          <view class="meta" v-if="row.rejectReason">驳回原因：{{ row.rejectReason }}</view>
          <view class="meta warning" v-if="row.isOverdue">当前已逾期，请尽快联系管理员归还登记</view>

          <view class="meta" v-if="latestRenewText(row.id)">续借：{{ latestRenewText(row.id) }}</view>
          <view class="meta" v-if="compensationText(row.id)">赔偿：{{ compensationText(row.id) }}</view>
          <view class="actions" v-if="row.status === 'approved'">
            <button class="btnSecondary miniBtn" size="mini" @click="renew(row)">申请续借</button>
          </view>
          <view class="actions" v-if="row.status === 'pending'">
            <button class="btnDanger miniBtn" size="mini" @click="cancel(row)">取消申请</button>
          </view>
        </view>

        <view class="card rowBetween pageCard">
          <view class="muted">已加载 {{ list.length }} / {{ total }}</view>
          <button class="btnSecondary miniBtn" size="mini" :disabled="!hasMore || loadingMore" @click="fetchMore">
            {{ loadingMore ? "加载中..." : hasMore ? "加载更多" : "已加载全部" }}
          </button>
        </view>
      </view>

      <view class="emptyState" v-else>
        <view class="emptyIcon">借</view>
        <view class="emptyTitle">暂无借用记录</view>
        <view class="emptySub">可点击右上角发起第一条借用申请</view>
      </view>
    </view>
  </view>
</template>

<script>
import { cancelBorrowRequest, createBorrowRenewRequest, listBorrowCompensations, listBorrowRenewRequests, listBorrowRequests } from "@/common/api.js"

function toInt(v, fallback = 0) {
  const n = Number(v)
  return Number.isFinite(n) ? Math.round(n) : fallback
}

export default {
  data() {
    return {
      userName: "",
      list: [],
      loading: false,
      loadingMore: false,
      page: 1,
      pageSize: 20,
      total: 0,
      hasMore: false,
      statusFilter: "all",
      focusId: 0,
      renewRows: [],
      compensationRows: [],
      statusOptions: [
        { label: "全部", value: "all" },
        { label: "待审批", value: "pending" },
        { label: "已通过", value: "approved" },
        { label: "已逾期", value: "overdue" },
        { label: "已归还", value: "returned" },
        { label: "已驳回", value: "rejected" },
        { label: "已取消", value: "cancelled" }
      ]
    }
  },
  onLoad(options) {
    const opts = options || {}
    this.statusFilter = String(opts.status || "all").trim() || "all"
    this.focusId = toInt(opts.focusId, 0)
  },
  onShow() {
    const session = uni.getStorageSync("session") || {}
    if (!session.username || !session.token) {
      uni.reLaunch({ url: "/pages/login/login" })
      return
    }
    this.userName = String(session.username || "").trim()
    this.queryMine()
  },
  onReachBottom() {
    this.fetchMore()
  },
  methods: {
    isFocused(row) {
      return toInt(row && row.id, 0) === this.focusId
    },
    statusText(row) {
      const status = String((row && row.status) || "").trim()
      const isOverdue = !!(row && row.isOverdue)
      if (status === "pending") return "待审批"
      if (status === "approved" && isOverdue) return "已逾期"
      if (status === "approved") return "已通过"
      if (status === "returned") return "已归还"
      if (status === "rejected") return "已驳回"
      if (status === "cancelled") return "已取消"
      return status || "-"
    },
    statusTone(row) {
      const status = String((row && row.status) || "").trim()
      const isOverdue = !!(row && row.isOverdue)
      if (status === "pending") return "warning"
      if (status === "approved" && isOverdue) return "danger"
      if (status === "approved") return "success"
      if (status === "returned") return "success"
      if (status === "rejected" || status === "cancelled") return "danger"
      return "info"
    },
    setStatus(status) {
      if (this.statusFilter === status) return
      this.statusFilter = status
      this.queryMine()
    },
    goApply() {
      uni.navigateTo({ url: "/pages/borrow/apply" })
    },
    async queryMine() {
      this.page = 1
      this.total = 0
      this.hasMore = false
      this.list = []
      await this.fetchList(true)
      await this.loadExtras()
    },
    buildParams(page) {
      const params = {
        mine: 1,
        page,
        pageSize: this.pageSize
      }
      if (this.statusFilter !== "all") params.status = this.statusFilter
      return params
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
        const res = await listBorrowRequests(this.buildParams(reqPage))
        const payload = (res && res.data) || {}
        if (!payload.ok) {
          if (reset) this.list = []
          uni.showToast({ title: payload.msg || "加载失败", icon: "none" })
          return
        }
        const rows = Array.isArray(payload.data) ? payload.data : []
        const meta = payload.meta || {}
        if (reset) this.list = rows
        else this.list = this.list.concat(rows)
        this.page = reqPage + 1
        this.total = Number(meta.total || this.list.length)
        this.hasMore = !!meta.hasMore
        this.scrollToFocus()
      } catch (e) {
        if (reset) this.list = []
        uni.showToast({ title: "加载失败", icon: "none" })
      } finally {
        this.loading = false
        this.loadingMore = false
      }
    },
    fetchMore() {
      this.fetchList(false)
    },
    async loadExtras() {
      try {
        const [renewRes, compensationRes] = await Promise.all([
          listBorrowRenewRequests(),
          listBorrowCompensations()
        ])
        const renewPayload = (renewRes && renewRes.data) || {}
        const compensationPayload = (compensationRes && compensationRes.data) || {}
        this.renewRows = renewPayload.ok && Array.isArray(renewPayload.data) ? renewPayload.data : []
        this.compensationRows = compensationPayload.ok && Array.isArray(compensationPayload.data) ? compensationPayload.data : []
      } catch (e) {
        this.renewRows = []
        this.compensationRows = []
      }
    },
    latestRenewText(requestId) {
      const rows = Array.isArray(this.renewRows) ? this.renewRows.filter((item) => Number(item.requestId || 0) === Number(requestId || 0)) : []
      if (rows.length === 0) return ""
      const latest = rows[0] || {}
      return `${latest.status || "-"} / ${latest.requestedReturnAt || "-"}`
    },
    compensationText(requestId) {
      const rows = Array.isArray(this.compensationRows) ? this.compensationRows.filter((item) => Number(item.requestId || 0) === Number(requestId || 0)) : []
      if (rows.length === 0) return ""
      const latest = rows[0] || {}
      return `${latest.status || "-"} / ${latest.amount || 0} 元`
    },
    scrollToFocus() {
      if (!this.focusId) return
      this.$nextTick(() => {
        uni.pageScrollTo({
          selector: `#borrow-row-${this.focusId}`,
          duration: 180
        })
      })
    },
    renew(row) {
      const id = toInt(row && row.id, 0)
      if (id <= 0) return
      uni.showModal({
        title: "申请续借",
        editable: true,
        placeholderText: "请输入新的归还时间，格式 YYYY-MM-DD HH:mm:ss",
        success: async (m) => {
          if (!m.confirm) return
          const requestedReturnAt = String(m.content || "").trim()
          if (!requestedReturnAt) return
          const reasonRes = await new Promise((resolve) => {
            uni.showModal({
              title: "续借原因",
              editable: true,
              placeholderText: "请输入续借原因",
              success: (res) => resolve(res)
            })
          })
          if (!reasonRes || !reasonRes.confirm) return
          const res = await createBorrowRenewRequest(id, {
            requestedReturnAt,
            reason: String(reasonRes.content || "").trim()
          })
          const payload = (res && res.data) || {}
          if (!payload.ok) {
            uni.showToast({ title: payload.msg || "续借申请失败", icon: "none" })
            return
          }
          uni.showToast({ title: "续借申请已提交", icon: "success" })
          this.queryMine()
        }
      })
    },
    cancel(row) {
      const id = toInt(row && row.id, 0)
      if (id <= 0) return
      uni.showModal({
        title: "取消申请",
        content: `确认取消借用申请 #${id} 吗？`,
        success: async (m) => {
          if (!m.confirm) return
          const res = await cancelBorrowRequest(id)
          const payload = (res && res.data) || {}
          if (!payload.ok) {
            uni.showToast({ title: payload.msg || "取消失败", icon: "none" })
            return
          }
          uni.showToast({ title: "已取消", icon: "success" })
          this.queryMine()
        }
      })
    }
  }
}
</script>

<style lang="scss">
.myBorrowPage {
  padding-bottom: 20px;
}

.heroCard,
.filterCard,
.itemCard,
.pageCard {
  border: 1px solid rgba(148, 163, 184, 0.24);
}

.heroTop {
  align-items: flex-start;
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

.miniBtn {
  min-height: 30px;
  line-height: 30px;
  padding: 0 10px;
  font-size: 12px;
  border-radius: 9px;
}

.itemName {
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
}

.meta {
  margin-top: 6px;
  color: #64748b;
  font-size: 12px;
}

.meta.warning {
  color: #b42318;
}

.focusItem {
  border-color: #1d4ed8;
  box-shadow: 0 0 0 2px rgba(29, 78, 216, 0.14);
}

.actions {
  margin-top: 10px;
  display: flex;
  justify-content: flex-end;
}
</style>

<template>
  <view class="container borrowApprovalPage">
    <view class="stack">
      <view class="card heroCard">
        <view class="title">租借审批中心</view>
        <view class="subtitle">审批借用申请、发送提醒、登记归还</view>
      </view>

      <view class="card tabsCard">
        <view class="tabs">
          <view v-for="tab in statusOptions" :key="tab.value" class="tab" :class="{ on: statusFilter === tab.value }" @click="setStatus(tab.value)">
            {{ tab.label }}
          </view>
        </view>
      </view>

      <view class="card filterCard">
        <view class="searchGrid">
          <input class="inputBase" v-model.trim="search.userKeyword" placeholder="申请账号/姓名" />
          <input class="inputBase" v-model.trim="search.equipmentKeyword" placeholder="资产编号/设备名/实验室" />
        </view>
        <view class="chipRow">
          <view class="chip" :class="{ chipOn: riskOnly }" @click="riskOnly = !riskOnly">{{ riskOnly ? "仅看风险申请" : "包含全部申请" }}</view>
        </view>
        <view class="rowBetween">
          <button class="btnSecondary miniBtn" size="mini" @click="resetSearch">重置</button>
          <button class="btnPrimary miniBtn" size="mini" :loading="loading" @click="queryList">搜索</button>
        </view>
      </view>

      <view class="card filterCard">
        <view class="rowBetween">
          <view class="cardTitle">扫码归还</view>
          <button class="btnPrimary miniBtn" size="mini" @click="scanReturn">提交扫码归还</button>
        </view>
        <input class="inputBase" v-model.trim="scanToken" placeholder="输入设备二维码 / 条码 / 资产编号" />
      </view>

      <view class="card" v-if="renewRows.length > 0">
        <view class="rowBetween">
          <view class="cardTitle">待审批续借</view>
          <view class="muted">{{ renewRows.length }} 条</view>
        </view>
        <view class="renewList">
          <view class="renewItem" v-for="item in renewRows" :key="item.id">
            <view class="rowBetween">
              <view class="itemName">{{ item.equipmentName || item.equipmentAssetCode || "-" }}</view>
              <view class="statusTag warning">{{ item.status }}</view>
            </view>
            <view class="meta">申请人：{{ item.applicantUserName || "-" }}</view>
            <view class="meta">当前归还：{{ item.currentExpectedReturnAt || "-" }}</view>
            <view class="meta">申请续借到：{{ item.requestedReturnAt || "-" }}</view>
            <view class="meta">原因：{{ item.reason || "-" }}</view>
            <view class="actions">
              <button class="btnPrimary miniBtn" size="mini" @click="approveRenew(item)">通过续借</button>
              <button class="btnDanger miniBtn" size="mini" @click="rejectRenew(item)">驳回续借</button>
            </view>
          </view>
        </view>
      </view>

      <view class="card" v-if="loading && rows.length === 0">
        <view class="muted">正在加载借用申请...</view>
      </view>

      <view class="stack" v-else-if="rows.length > 0">
        <view
          v-for="row in rows"
          :key="row.id"
          :id="`borrow-approval-row-${row.id}`"
          class="card itemCard"
          :class="{ focusItem: isFocused(row) }"
        >
          <view class="rowBetween">
            <view class="itemName">{{ row.equipmentName || row.equipmentAssetCode || "-" }}</view>
            <view class="statusTag" :class="statusTone(row)">{{ statusText(row) }}</view>
          </view>

          <view class="meta">资产编号：{{ row.equipmentAssetCode || "-" }}</view>
          <view class="meta">实验室：{{ row.equipmentLabName || "-" }}</view>
          <view class="meta">申请账号：{{ row.applicantUserName || "-" }}（{{ roleText(row.applicantRole) }}）</view>
          <view class="meta">申请姓名：{{ row.applicantName || "-" }}</view>
          <view class="meta" v-if="row.applicantRole === 'student'">学号/班级：{{ row.applicantStudentNo || "-" }} / {{ row.applicantClassName || "-" }}</view>
          <view class="meta" v-if="row.applicantRole === 'teacher'">工号：{{ row.applicantJobNo || "-" }}</view>
          <view class="meta">借用时间：{{ row.borrowStartAt || "-" }}</view>
          <view class="meta">应还时间：{{ row.expectedReturnAt || "-" }}</view>
          <view class="meta" v-if="row.returnedAt">归还时间：{{ row.returnedAt }}</view>
          <view class="meta">用途：{{ row.purpose || "-" }}</view>
          <view class="meta" v-if="row.rejectReason">驳回原因：{{ row.rejectReason }}</view>
          <view class="meta" v-if="row.adminNote">管理员备注：{{ row.adminNote }}</view>
          <view class="meta warning" v-if="row.riskFlag">风险提醒：{{ row.riskReason || "该用户存在逾期借用历史" }}</view>
          <view class="meta warning" v-if="row.isOverdue">当前逾期未归还</view>

          <view class="actions">
            <button class="btnSecondary miniBtn" size="mini" @click="note(row)">备注</button>
            <button v-if="row.status === 'pending'" class="btnPrimary miniBtn" size="mini" @click="approve(row)">通过</button>
            <button v-if="row.status === 'pending'" class="btnDanger miniBtn" size="mini" @click="reject(row)">驳回</button>
            <button v-if="row.status === 'approved' || row.isOverdue" class="btnSecondary miniBtn" size="mini" @click="remind(row)">手动提醒</button>
            <button v-if="row.status === 'approved' || row.isOverdue" class="btnGhost miniBtn" size="mini" @click="aiRemind(row)">AI提醒</button>
            <button v-if="row.status === 'approved' || row.isOverdue" class="btnSecondary miniBtn" size="mini" @click="createCompensation(row)">赔偿登记</button>
            <button v-if="row.status === 'approved' || row.isOverdue" class="btnPrimary miniBtn" size="mini" @click="markReturned(row)">标记已归还</button>
          </view>
        </view>

        <view class="card rowBetween pageCard">
          <view class="muted">已加载 {{ rows.length }} / {{ total }}</view>
          <button class="btnSecondary miniBtn" size="mini" :disabled="!hasMore || loadingMore" @click="fetchMore">
            {{ loadingMore ? "加载中..." : hasMore ? "加载更多" : "已加载全部" }}
          </button>
        </view>
      </view>

      <view class="emptyState" v-else>
        <view class="emptyTitle">暂无借用申请</view>
      </view>
    </view>
  </view>
</template>

<script>
import {
  adminAiRemindBorrowRequest,
  adminApproveBorrowRequest,
  adminApproveBorrowRenewRequest,
  adminCreateBorrowCompensation,
  adminMarkBorrowReturned,
  adminNoteBorrowRequest,
  adminRejectBorrowRequest,
  adminRejectBorrowRenewRequest,
  adminRemindBorrowRequest,
  adminScanReturnBorrowRequest,
  listBorrowRenewRequests,
  listBorrowRequests
} from "@/common/api.js"

function toInt(v, fallback = 0) {
  const n = Number(v)
  return Number.isFinite(n) ? Math.round(n) : fallback
}

export default {
  data() {
    return {
      rows: [],
      loading: false,
      loadingMore: false,
      page: 1,
      pageSize: 20,
      total: 0,
      hasMore: false,
      statusFilter: "pending",
      riskOnly: false,
      focusId: 0,
      scanToken: "",
      renewRows: [],
      search: {
        userKeyword: "",
        equipmentKeyword: ""
      },
      statusOptions: [
        { label: "待审批", value: "pending" },
        { label: "已通过", value: "approved" },
        { label: "逾期未还", value: "overdue" },
        { label: "已归还", value: "returned" },
        { label: "已驳回", value: "rejected" },
        { label: "已取消", value: "cancelled" },
        { label: "全部", value: "all" }
      ]
    }
  },
  onLoad(options) {
    const opts = options || {}
    this.focusId = toInt(opts.focusId, 0)
    const status = String(opts.status || "").trim()
    if (status) this.statusFilter = status
  },
  onShow() {
    const session = uni.getStorageSync("session") || {}
    if (String(session.role || "") !== "admin") {
      uni.showToast({ title: "无权限", icon: "none" })
      uni.reLaunch({ url: "/pages/login/login" })
      return
    }
    this.queryList()
    this.loadRenewRows()
  },
  onReachBottom() {
    this.fetchMore()
  },
  methods: {
    roleText(role) {
      if (role === "student") return "学生"
      if (role === "teacher") return "教师"
      if (role === "admin") return "管理员"
      return role || "-"
    },
    isFocused(row) {
      return toInt(row && row.id, 0) === this.focusId
    },
    statusText(row) {
      const status = String((row && row.status) || "").trim()
      const overdue = !!(row && row.isOverdue)
      if (status === "pending") return "待审批"
      if (status === "approved" && overdue) return "逾期未还"
      if (status === "approved") return "已通过"
      if (status === "returned") return "已归还"
      if (status === "rejected") return "已驳回"
      if (status === "cancelled") return "已取消"
      return status || "-"
    },
    statusTone(row) {
      const status = String((row && row.status) || "").trim()
      const overdue = !!(row && row.isOverdue)
      if (status === "pending") return "warning"
      if (status === "approved" && overdue) return "danger"
      if (status === "approved" || status === "returned") return "success"
      if (status === "rejected" || status === "cancelled") return "danger"
      return "info"
    },
    setStatus(status) {
      if (this.statusFilter === status) return
      this.statusFilter = status
      this.queryList()
    },
    resetSearch() {
      this.search.userKeyword = ""
      this.search.equipmentKeyword = ""
      this.riskOnly = false
      this.queryList()
    },
    buildParams(page) {
      const params = {
        page,
        pageSize: this.pageSize
      }
      if (this.statusFilter !== "all") params.status = this.statusFilter
      if (this.search.userKeyword) params.userKeyword = this.search.userKeyword
      if (this.search.equipmentKeyword) params.equipmentKeyword = this.search.equipmentKeyword
      if (this.riskOnly) params.riskOnly = 1
      return params
    },
    async queryList() {
      this.page = 1
      this.total = 0
      this.hasMore = false
      this.rows = []
      await this.fetchList(true)
      await this.loadRenewRows()
    },
    async loadRenewRows() {
      try {
        const res = await listBorrowRenewRequests({ status: "pending" })
        const payload = (res && res.data) || {}
        this.renewRows = payload.ok && Array.isArray(payload.data) ? payload.data : []
      } catch (e) {
        this.renewRows = []
      }
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
          uni.showToast({ title: payload.msg || "加载失败", icon: "none" })
          return
        }
        const list = Array.isArray(payload.data) ? payload.data : []
        const meta = payload.meta || {}
        if (reset) this.rows = list
        else this.rows = this.rows.concat(list)
        this.page = reqPage + 1
        this.total = Number(meta.total || this.rows.length)
        this.hasMore = !!meta.hasMore
        this.scrollToFocus()
      } catch (e) {
        uni.showToast({ title: "加载失败", icon: "none" })
      } finally {
        this.loading = false
        this.loadingMore = false
      }
    },
    fetchMore() {
      this.fetchList(false)
    },
    scrollToFocus() {
      if (!this.focusId) return
      this.$nextTick(() => {
        uni.pageScrollTo({
          selector: `#borrow-approval-row-${this.focusId}`,
          duration: 180
        })
      })
    },
    async scanReturn() {
      const token = String(this.scanToken || "").trim()
      if (!token) {
        uni.showToast({ title: "请输入扫码内容", icon: "none" })
        return
      }
      const res = await adminScanReturnBorrowRequest({ token })
      const payload = (res && res.data) || {}
      if (!payload.ok) {
        uni.showToast({ title: payload.msg || "扫码归还失败", icon: "none" })
        return
      }
      uni.showToast({ title: "已扫码归还", icon: "success" })
      this.scanToken = ""
      this.queryList()
    },
    async approveRenew(row) {
      const res = await adminApproveBorrowRenewRequest(row.id)
      const payload = (res && res.data) || {}
      if (!payload.ok) {
        uni.showToast({ title: payload.msg || "续借审批失败", icon: "none" })
        return
      }
      uni.showToast({ title: "续借已通过", icon: "success" })
      this.queryList()
    },
    rejectRenew(row) {
      uni.showModal({
        title: "驳回续借",
        editable: true,
        placeholderText: "可选：填写驳回原因",
        success: async (m) => {
          if (!m.confirm) return
          const res = await adminRejectBorrowRenewRequest(row.id, { rejectReason: String(m.content || "").trim() })
          const payload = (res && res.data) || {}
          if (!payload.ok) {
            uni.showToast({ title: payload.msg || "续借驳回失败", icon: "none" })
            return
          }
          uni.showToast({ title: "已驳回续借", icon: "success" })
          this.queryList()
        }
      })
    },
    approve(row) {
      uni.showModal({
        title: "确认通过",
        content: `确认通过借用申请 #${row.id} 吗？`,
        success: async (m) => {
          if (!m.confirm) return
          const res = await adminApproveBorrowRequest(row.id)
          const payload = (res && res.data) || {}
          if (!payload.ok) {
            uni.showToast({ title: payload.msg || "操作失败", icon: "none" })
            return
          }
          uni.showToast({ title: "已通过", icon: "success" })
          this.queryList()
        }
      })
    },
    reject(row) {
      uni.showModal({
        title: "驳回原因",
        editable: true,
        placeholderText: "可选：填写驳回原因",
        success: async (m) => {
          if (!m.confirm) return
          const res = await adminRejectBorrowRequest(row.id, { rejectReason: String(m.content || "").trim() })
          const payload = (res && res.data) || {}
          if (!payload.ok) {
            uni.showToast({ title: payload.msg || "操作失败", icon: "none" })
            return
          }
          uni.showToast({ title: "已驳回", icon: "success" })
          this.queryList()
        }
      })
    },
    note(row) {
      uni.showModal({
        title: "管理员备注",
        editable: true,
        placeholderText: "请输入备注",
        success: async (m) => {
          if (!m.confirm) return
          const note = String(m.content || "").trim()
          if (!note) return
          const res = await adminNoteBorrowRequest(row.id, { note })
          const payload = (res && res.data) || {}
          if (!payload.ok) {
            uni.showToast({ title: payload.msg || "备注失败", icon: "none" })
            return
          }
          uni.showToast({ title: "已备注", icon: "success" })
          this.queryList()
        }
      })
    },
    remind(row) {
      uni.showModal({
        title: "手动提醒",
        editable: true,
        placeholderText: "可选：填写提醒内容",
        success: async (m) => {
          if (!m.confirm) return
          const message = String(m.content || "").trim()
          const res = await adminRemindBorrowRequest(row.id, { message })
          const payload = (res && res.data) || {}
          if (!payload.ok) {
            uni.showToast({ title: payload.msg || "提醒失败", icon: "none" })
            return
          }
          uni.showToast({ title: "提醒已发送", icon: "success" })
          this.queryList()
        }
      })
    },
    async aiRemind(row) {
      const res = await adminAiRemindBorrowRequest(row.id)
      const payload = (res && res.data) || {}
      if (!payload.ok) {
        uni.showToast({ title: payload.msg || "AI提醒失败", icon: "none" })
        return
      }
      uni.showToast({ title: "AI 提醒已发送", icon: "success" })
      this.queryList()
    },
    createCompensation(row) {
      uni.showModal({
        title: "赔偿金额",
        editable: true,
        placeholderText: "请输入金额，例如 200",
        success: async (m) => {
          if (!m.confirm) return
          const amount = Number(m.content || 0)
          if (!Number.isFinite(amount) || amount < 0) {
            uni.showToast({ title: "金额无效", icon: "none" })
            return
          }
          const res = await adminCreateBorrowCompensation(row.id, {
            amount,
            damageLevel: "normal",
            description: `借用设备 ${row.equipmentName || row.equipmentAssetCode || row.id} 赔偿登记`
          })
          const payload = (res && res.data) || {}
          if (!payload.ok) {
            uni.showToast({ title: payload.msg || "赔偿登记失败", icon: "none" })
            return
          }
          uni.showToast({ title: "赔偿单已创建", icon: "success" })
        }
      })
    },
    markReturned(row) {
      uni.showModal({
        title: "确认归还",
        content: `确认将申请 #${row.id} 标记为已归还吗？`,
        success: async (m) => {
          if (!m.confirm) return
          const res = await adminMarkBorrowReturned(row.id, {})
          const payload = (res && res.data) || {}
          if (!payload.ok) {
            uni.showToast({ title: payload.msg || "操作失败", icon: "none" })
            return
          }
          const late = !!(payload.data && payload.data.returnedLate)
          uni.showToast({ title: late ? "已归还（逾期）" : "已标记归还", icon: "success" })
          this.queryList()
        }
      })
    }
  }
}
</script>

<style lang="scss">
.borrowApprovalPage {
  padding-bottom: 20px;
}

.heroCard,
.tabsCard,
.filterCard,
.itemCard,
.pageCard {
  border: 1px solid rgba(148, 163, 184, 0.24);
}

.tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tab {
  padding: 6px 10px;
  border-radius: 999px;
  background: #eef2f6;
  font-size: 12px;
}

.tab.on {
  background: #e6f0ff;
  color: #1f4d8f;
}

.searchGrid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
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
  font-size: 12px;
  color: #64748b;
}

.meta.warning {
  color: #b42318;
}

.actions {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.focusItem {
  border-color: #1d4ed8;
  box-shadow: 0 0 0 2px rgba(29, 78, 216, 0.14);
}
</style>

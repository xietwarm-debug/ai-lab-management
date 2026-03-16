<template>
  <view class="container">
    <view class="stack">
      <view>
        <view class="title">预约审批</view>
        <view class="subtitle">筛选与处理预约</view>
      </view>

      <view class="tabs card">
        <view class="tab" :class="{on: filter==='all'}" @click="setFilter('all')">全部</view>
        <view class="tab" :class="{on: filter==='pending'}" @click="setFilter('pending')">待审批</view>
        <view class="tab" :class="{on: filter==='approved'}" @click="setFilter('approved')">已通过</view>
        <view class="tab" :class="{on: filter==='rejected'}" @click="setFilter('rejected')">已驳回</view>
        <view class="tab" :class="{on: filter==='cancelled'}" @click="setFilter('cancelled')">已取消</view>
        <button v-if="isAdmin" class="btnGhost" size="mini" @click="exportCsv">导出历史</button>
      </view>

      <view class="card filterCard">
        <view class="searchGrid">
          <input class="input" v-model.trim="search.labKeyword" placeholder="实验室名称" />
          <input class="input" v-model.trim="search.userKeyword" placeholder="预约用户" />
        </view>
        <view class="searchGrid">
          <picker mode="date" :value="search.dateFrom" @change="onDateFromChange">
            <view class="dateField">{{ search.dateFrom || "开始日期" }}</view>
          </picker>
          <picker mode="date" :value="search.dateTo" @change="onDateToChange">
            <view class="dateField">{{ search.dateTo || "结束日期" }}</view>
          </picker>
        </view>
        <view class="rowBetween">
          <button size="mini" class="btnGhost" @click="resetSearch">重置搜索</button>
          <button size="mini" class="btnPrimary" @click="fetchList">搜索</button>
        </view>
      </view>

      <view class="card batch" v-if="filter==='pending' && shown.length">
        <view class="rowBetween">
          <view class="muted">已选 {{ selectedIds.length }} 条</view>
          <view class="batchActions">
            <button size="mini" class="btnGhost" @click="toggleAll">{{ allSelected ? '取消全选' : '全选' }}</button>
            <button size="mini" class="btnPrimary" @click="batchApprove" :disabled="selectedIds.length===0">批量通过</button>
            <button v-if="isAdmin" size="mini" class="btnGhost" @click="batchCancel" :disabled="selectedIds.length===0">批量取消</button>
          </view>
        </view>
      </view>

      <view v-for="r in shown" :key="r.id" class="card item">
        <view class="rowBetween">
          <view class="left">
            <checkbox
              v-if="filter==='pending'"
              :checked="selectedIds.includes(r.id)"
              @click.stop="toggleSelect(r.id)"
            />
            <view class="name">{{ r.labName }}</view>
          </view>
          <view class="status" :class="r.status">{{ statusText(r.status) }}</view>
        </view>

        <view class="meta">预约人: {{ r.user }}</view>
        <view class="meta">时间: {{ r.date }} {{ r.time }}</view>
        <view class="meta" v-if="r.reason">用途: {{ r.reason }}</view>
        <view class="meta" v-if="r.status==='rejected' && r.rejectReason">驳回原因: {{ r.rejectReason }}</view>
        <view class="meta" v-if="r.adminNote">管理员备注: {{ r.adminNote }}</view>
        <view class="meta aiMeta" v-if="aiSuggestionSummary(r.id)">{{ aiSuggestionSummary(r.id) }}</view>

        <view class="actions">
          <button size="mini" class="btnGhost" @click="goDetail(r.id)">详情</button>
          <button v-if="r.status==='pending'" size="mini" class="btnGhost" :disabled="aiSuggestLoadingId === r.id" @click="showAiSuggestion(r)">
            {{ aiSuggestLoadingId === r.id ? "AI分析中..." : "AI建议" }}
          </button>
          <view class="spacer" />
          <button v-if="r.status==='pending'" size="mini" class="btnPrimary" @click="approve(r.id)">通过</button>
          <button v-if="r.status==='pending'" size="mini" class="btnGhost" @click="reject(r.id)">驳回</button>
          <button v-if="r.status==='pending' && isAdmin" size="mini" class="btnGhost" @click="note(r)">备注</button>
        </view>
      </view>

      <view class="empty" v-if="shown.length===0">暂无数据</view>
    </view>
  </view>
</template>

<script>
import { BASE_URL, getReservationAiSuggestion } from "@/common/api.js"

export default {
  data() {
    return {
      role: "",
      list: [],
      filter: "pending",
      aiSuggestLoadingId: 0,
      aiSuggestionMap: {},
      selectedIds: [],
      search: {
        labKeyword: "",
        userKeyword: "",
        dateFrom: "",
        dateTo: ""
      }
    }
  },
  onShow() {
    const s = uni.getStorageSync("session")
    const role = String((s && s.role) || "").trim()
    this.role = role
    if (!s || (role !== "admin" && role !== "teacher")) {
      uni.showToast({ title: "无权限", icon: "none" })
      uni.reLaunch({ url: "/pages/login/login" })
      return
    }
    this.fetchList()
  },
  computed: {
    isAdmin() {
      return this.role === "admin"
    },
    shown() {
      if (this.filter === "all") return this.list
      return this.list.filter(x => x.status === this.filter)
    },
    allSelected() {
      return this.shown.length > 0 && this.selectedIds.length === this.shown.length
    }
  },
  methods: {
    statusText(s) {
      if (s === "pending") return "待审批"
      if (s === "approved") return "已通过"
      if (s === "rejected") return "已驳回"
      if (s === "cancelled") return "已取消"
      return s
    },
    decisionText(decision) {
      if (decision === "approve") return "建议通过"
      if (decision === "reject") return "建议驳回"
      if (decision === "review") return "建议转人工复核"
      return decision || "-"
    },
    aiSuggestionSummary(id) {
      const row = this.aiSuggestionMap[String(id)] || {}
      const suggestion = row && row.suggestion ? row.suggestion : {}
      const summary = String(suggestion.summary || "").trim()
      if (summary) return `AI：${summary}`
      const decision = this.decisionText(String(suggestion.decision || "").trim())
      if (!decision || decision === "-") return ""
      return `AI：${decision}`
    },
    setFilter(f) {
      this.filter = f
      this.selectedIds = []
      this.fetchList()
    },
    onDateFromChange(e) {
      this.search.dateFrom = e.detail.value || ""
    },
    onDateToChange(e) {
      this.search.dateTo = e.detail.value || ""
    },
    resetSearch() {
      this.search.labKeyword = ""
      this.search.userKeyword = ""
      this.search.dateFrom = ""
      this.search.dateTo = ""
      this.fetchList()
    },
    buildQuery() {
      const q = []
      if (this.filter !== "all") q.push(`status=${encodeURIComponent(this.filter)}`)
      if (this.search.labKeyword) q.push(`labKeyword=${encodeURIComponent(this.search.labKeyword)}`)
      if (this.search.userKeyword) q.push(`userKeyword=${encodeURIComponent(this.search.userKeyword)}`)
      if (this.search.dateFrom) q.push(`dateFrom=${encodeURIComponent(this.search.dateFrom)}`)
      if (this.search.dateTo) q.push(`dateTo=${encodeURIComponent(this.search.dateTo)}`)
      return q.length ? `?${q.join("&")}` : ""
    },
    fetchList() {
      if (this.search.dateFrom && this.search.dateTo && this.search.dateFrom > this.search.dateTo) {
        uni.showToast({ title: "开始日期不能大于结束日期", icon: "none" })
        return
      }
      const qs = this.buildQuery()
      uni.request({
        url: `${BASE_URL}/reservations${qs}`,
        method: "GET",
        success: (res) => {
          const payload = res.data
          if (Array.isArray(payload)) {
            this.list = payload
            return
          }
          if (payload && payload.ok) {
            this.list = payload.data || []
            return
          }
          this.list = []
        },
        fail: () => uni.showToast({ title: "获取失败", icon: "none" })
      })
    },
    toggleSelect(id) {
      const idx = this.selectedIds.indexOf(id)
      if (idx >= 0) this.selectedIds.splice(idx, 1)
      else this.selectedIds.push(id)
    },
    toggleAll() {
      if (this.allSelected) this.selectedIds = []
      else this.selectedIds = this.shown.map(x => x.id)
    },
    batchApprove() {
      this.batchAction("approve")
    },
    batchCancel() {
      this.batchAction("cancel")
    },
    batchAction(action) {
      const actionText = action === "approve" ? "批量通过" : "批量取消"
      if (!this.selectedIds.length) return
      if (action === "cancel" && !this.isAdmin) {
        uni.showToast({ title: "仅管理员可批量取消", icon: "none" })
        return
      }
      uni.showModal({
        title: `确认${actionText}`,
        content: `将对 ${this.selectedIds.length} 条预约执行${actionText}，是否继续？`,
        success: (m) => {
          if (!m.confirm) return
          this.doBatchAction(action)
        }
      })
    },
    doBatchAction(action) {
      const s = uni.getStorageSync("session")
      const operator = s ? s.username : ""
      uni.request({
        url: `${BASE_URL}/reservations/batch`,
        method: "POST",
        header: { "Content-Type": "application/json" },
        data: { operator, action, ids: this.selectedIds },
        success: (res) => {
          if (!res.data || !res.data.ok) {
            return uni.showToast({ title: (res.data && res.data.msg) || "失败", icon: "none" })
          }
          const data = res.data.data || {}
          const lines = [
            `成功数量: ${data.count || 0}`
          ]
          if (action === "approve") {
            if (Array.isArray(data.conflictIds) && data.conflictIds.length) lines.push(`冲突: ${data.conflictIds.length}`)
            if (Array.isArray(data.invalidStatusIds) && data.invalidStatusIds.length) lines.push(`状态不符: ${data.invalidStatusIds.length}`)
            if (Array.isArray(data.invalidScheduleIds) && data.invalidScheduleIds.length) lines.push(`时间规则不符: ${data.invalidScheduleIds.length}`)
            if (Array.isArray(data.notFoundIds) && data.notFoundIds.length) lines.push(`不存在: ${data.notFoundIds.length}`)
            if (Array.isArray(data.busyIds) && data.busyIds.length) lines.push(`并发占用: ${data.busyIds.length}`)
            if (Array.isArray(data.forbiddenIds) && data.forbiddenIds.length) lines.push(`无审批权限: ${data.forbiddenIds.length}`)
          }
          uni.showModal({
            title: "批量操作结果",
            content: lines.join("\n"),
            showCancel: false
          })
          this.selectedIds = []
          this.fetchList()
        },
        fail: () => uni.showToast({ title: "请求失败", icon: "none" })
      })
    },
    async showAiSuggestion(row) {
      const id = row && row.id
      if (!id || this.aiSuggestLoadingId) return
      this.aiSuggestLoadingId = id
      try {
        const res = await getReservationAiSuggestion(id)
        const payload = (res && res.data) || {}
        const data = payload && payload.data ? payload.data : {}
        const suggestion = data && data.suggestion ? data.suggestion : {}
        if (!payload.ok || !suggestion) {
          uni.showToast({ title: payload.msg || "AI建议获取失败", icon: "none" })
          return
        }
        this.aiSuggestionMap = { ...this.aiSuggestionMap, [String(id)]: data }
        const reasons = Array.isArray(suggestion.reasons) ? suggestion.reasons : []
        const risks = Array.isArray(suggestion.risks) ? suggestion.risks : []
        const actions = Array.isArray(suggestion.nextActions) ? suggestion.nextActions : []
        const alternatives = Array.isArray(suggestion.alternatives) ? suggestion.alternatives : []
        const lines = [
          `建议：${this.decisionText(suggestion.decision)}`,
          `评分：${suggestion.score || 0}`,
          suggestion.summary || ""
        ]
        if (reasons.length) lines.push(`依据：${reasons.join("；")}`)
        if (risks.length) lines.push(`风险：${risks.join("；")}`)
        if (actions.length) lines.push(`建议动作：${actions.join("；")}`)
        if (alternatives.length) {
          const altLines = alternatives.map((item, idx) => `${idx + 1}. ${item.labName} ${item.date} ${item.time}`)
          lines.push(`替代方案：${altLines.join("；")}`)
        }
        uni.showModal({
          title: "AI审批建议",
          content: lines.filter(Boolean).join("\n"),
          showCancel: false
        })
      } catch (e) {
        uni.showToast({ title: "AI建议获取失败", icon: "none" })
      } finally {
        this.aiSuggestLoadingId = 0
      }
    },
    approve(id) {
      uni.showModal({
        title: "确认通过预约",
        content: `确认通过编号 ${id} 的预约申请？`,
        success: (m) => {
          if (!m.confirm) return
          uni.request({
            url: `${BASE_URL}/reservations/${id}/approve`,
            method: "POST",
            success: (res) => {
              if (!res.data.ok) return uni.showToast({ title: res.data.msg || "失败", icon: "none" })
              uni.showModal({
                title: "操作成功",
                content: `预约 #${id} 已通过`,
                showCancel: false
              })
              this.fetchList()
            },
            fail: () => uni.showToast({ title: "请求失败", icon: "none" })
          })
        }
      })
    },
    reject(id) {
      uni.showModal({
        title: "驳回原因",
        editable: true,
        placeholderText: "可选：填写原因",
        success: (m) => {
          if (!m.confirm) return
          uni.request({
            url: `${BASE_URL}/reservations/${id}/reject`,
            method: "POST",
            header: { "Content-Type": "application/json" },
            data: { rejectReason: m.content || "" },
            success: (res) => {
              if (!res.data.ok) return uni.showToast({ title: res.data.msg || "失败", icon: "none" })
              uni.showToast({ title: "已驳回", icon: "success" })
              this.fetchList()
            },
            fail: () => uni.showToast({ title: "请求失败", icon: "none" })
          })
        }
      })
    },
    note(r) {
      const s = uni.getStorageSync("session")
      const operator = s ? s.username : ""
      uni.showModal({
        title: "管理员备注",
        editable: true,
        placeholderText: "填写备注",
        success: (m) => {
          if (!m.confirm) return
          const note = (m.content || "").trim()
          if (!note) return
          uni.request({
            url: `${BASE_URL}/reservations/${r.id}/note`,
            method: "POST",
            header: { "Content-Type": "application/json" },
            data: { operator, note },
            success: (res) => {
              if (!res.data || !res.data.ok) {
                return uni.showToast({ title: (res.data && res.data.msg) || "失败", icon: "none" })
              }
              uni.showToast({ title: "已备注", icon: "success" })
              this.fetchList()
            },
            fail: () => uni.showToast({ title: "请求失败", icon: "none" })
          })
        }
      })
    },
    goDetail(id) {
      uni.navigateTo({ url: `/pages/admin/approve-detail?id=${id}` })
    },
    exportCsv() {
      if (this.search.dateFrom && this.search.dateTo && this.search.dateFrom > this.search.dateTo) {
        uni.showToast({ title: "开始日期不能大于结束日期", icon: "none" })
        return
      }
      const qs = this.buildQuery()
      uni.downloadFile({
        url: `${BASE_URL}/reservations/export${qs}`,
        success: (res) => {
          if (res.statusCode !== 200) {
            return uni.showToast({ title: "导出失败", icon: "none" })
          }
          uni.openDocument({
            filePath: res.tempFilePath,
            fileType: "csv"
          })
        },
        fail: () => uni.showToast({ title: "导出失败", icon: "none" })
      })
    }
  }
}
</script>

<style>
.tabs { display:flex; gap:8px; flex-wrap: wrap; }
.tab{
  padding:6px 10px; border-radius:999px; background:#eef2f6; font-size:12px;
}
.on{ background:#e6f0ff; color:#1f4d8f; }
.filterCard { border: 1px solid rgba(31, 77, 143, 0.06); }
.searchGrid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-bottom: 8px;
}
.searchGrid .input {
  background: #f4f6f9;
  border-radius: 12px;
  padding: 10px 12px;
}
.dateField {
  background: #f4f6f9;
  border-radius: 12px;
  padding: 10px 12px;
  color: #334155;
}
.batch { border: 1px solid rgba(31, 77, 143, 0.06); }
.batchActions { display:flex; gap:8px; }

.item { border: 1px solid rgba(31, 77, 143, 0.06); }
.left { display:flex; align-items:center; gap:8px; }
.name{ font-weight:600; }
.meta{ margin-top:6px; color:#64748b; font-size:12px; }
.aiMeta{ color:#1d4ed8; }

.status{ font-size:12px; padding:4px 8px; border-radius:999px; }
.pending{ background:#fff7e6; color:#8a5a00; }
.approved{ background:#e8fff0; color:#1f7a3a; }
.rejected{ background:#ffecec; color:#a11f1f; }
.cancelled{ background:#eef2f6; color:#64748b; }

.actions{ display:flex; gap:10px; margin-top:10px; }
.spacer{ flex: 1; }
.empty{ text-align:center; color:#999; margin-top:40px; }
</style>

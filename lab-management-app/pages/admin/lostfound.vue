<template>
  <view class="container">
    <view class="stack">
      <view>
        <view class="title">失物招领管理</view>
        <view class="subtitle">支持失物结案、拾到物品认领审核</view>
      </view>

      <view class="card filter">
        <view class="chips">
          <view class="chip" :class="{active: filterStatus==='all'}" @click="setStatus('all')">状态:全部</view>
          <view class="chip" :class="{active: filterStatus==='open'}" @click="setStatus('open')">状态:进行中</view>
          <view class="chip" :class="{active: filterStatus==='closed'}" @click="setStatus('closed')">状态:已解决</view>
        </view>
        <view class="chips" style="margin-top:8px;">
          <view class="chip" :class="{active: filterType==='all'}" @click="setType('all')">类型:全部</view>
          <view class="chip" :class="{active: filterType==='lost'}" @click="setType('lost')">类型:失物</view>
          <view class="chip" :class="{active: filterType==='found'}" @click="setType('found')">类型:拾到</view>
        </view>
        <view class="chips" style="margin-top:8px;">
          <view class="chip" :class="{active: filterClaim==='all'}" @click="setClaim('all')">认领:全部</view>
          <view class="chip" :class="{active: filterClaim==='pending'}" @click="setClaim('pending')">认领:待审</view>
          <view class="chip" :class="{active: filterClaim==='approved'}" @click="setClaim('approved')">认领:通过</view>
          <view class="chip" :class="{active: filterClaim==='rejected'}" @click="setClaim('rejected')">认领:驳回</view>
        </view>
        <view class="searchGrid">
          <input class="input" v-model="search.studentId" placeholder="学号(结案)" />
          <input class="input" v-model="search.studentName" placeholder="姓名(结案)" />
          <input class="input" v-model="search.studentClass" placeholder="班级(结案)" />
          <button class="btnGhost" size="mini" @click="fetchList">搜索</button>
        </view>
      </view>

      <view v-for="i in list" :key="i.id" class="card item">
        <view class="rowBetween">
          <view class="name">{{ i.title }}</view>
          <view class="tag" :class="i.type">{{ i.type === 'lost' ? '丢失' : '拾到' }}</view>
        </view>
        <view class="meta">地点: {{ i.location || '-' }}</view>
        <image v-if="i.imageUrl" :src="imgSrc(i.imageUrl)" class="thumb" mode="aspectFill" />
        <view class="meta" v-if="i.description">描述: {{ i.description }}</view>
        <view class="meta">联系方式: {{ i.contact || '-' }}</view>
        <view class="meta muted">发布者: {{ i.owner || '-' }} · {{ i.createdAt }}</view>

        <view class="claimBox" v-if="i.type === 'found' && i.claimApplyStatus">
          <view class="meta">认领状态: {{ claimStatusText(i.claimApplyStatus) }}</view>
          <view class="meta" v-if="i.claimApplyUser">申请人账号: {{ i.claimApplyUser }}</view>
          <view class="meta" v-if="i.claimApplyStudentId || i.claimApplyName || i.claimApplyClass">
            申请信息: {{ i.claimApplyStudentId || "-" }} · {{ i.claimApplyName || "-" }} · {{ i.claimApplyClass || "-" }}
          </view>
          <view class="meta" v-if="i.claimApplyReason">申请说明: {{ i.claimApplyReason }}</view>
          <view class="meta" v-if="i.claimReviewedBy">审核人: {{ i.claimReviewedBy }} · {{ i.claimReviewedAt || "-" }}</view>
          <view class="meta" v-if="i.claimReviewNote">审核备注: {{ i.claimReviewNote }}</view>
        </view>

        <view class="actions">
          <view class="status" :class="i.status">{{ i.status === 'open' ? '进行中' : '已解决' }}</view>
          <view class="rowBetween" style="gap:8px;">
            <button
              v-if="i.type==='found' && i.claimApplyStatus==='pending'"
              class="btnPrimary"
              size="mini"
              @click="approveClaim(i)"
            >通过认领</button>
            <button
              v-if="i.type==='found' && i.claimApplyStatus==='pending'"
              class="btnGhost"
              size="mini"
              @click="rejectClaim(i)"
            >驳回认领</button>
            <button
              v-if="i.status === 'open' && !(i.type==='found' && i.claimApplyStatus==='pending')"
              class="btnGhost"
              size="mini"
              @click="closeItem(i)"
            >标记已解决</button>
          </view>
        </view>
        <view class="meta" v-if="i.status === 'closed' && (i.claimStudentId || i.claimName || i.claimClass)">
          结案认领: {{ i.claimStudentId || "-" }} · {{ i.claimName || "-" }} · {{ i.claimClass || "-" }}
        </view>
      </view>

      <view class="empty" v-if="list.length===0">暂无记录</view>
    </view>
  </view>
</template>

<script>
import { BASE_URL } from "@/common/api.js"

export default {
  data() {
    return {
      list: [],
      filterStatus: "all",
      filterType: "all",
      filterClaim: "all",
      operator: "",
      search: {
        studentId: "",
        studentName: "",
        studentClass: ""
      }
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
    this.fetchList()
  },
  methods: {
    claimStatusText(s) {
      if (s === "pending") return "待审核"
      if (s === "approved") return "已通过"
      if (s === "rejected") return "已驳回"
      return "无"
    },
    setStatus(v) {
      this.filterStatus = v
      this.fetchList()
    },
    setType(v) {
      this.filterType = v
      this.fetchList()
    },
    setClaim(v) {
      this.filterClaim = v
      this.fetchList()
    },
    fetchList() {
      const q = []
      if (this.filterStatus !== "all") q.push(`status=${encodeURIComponent(this.filterStatus)}`)
      if (this.filterType !== "all") q.push(`type=${encodeURIComponent(this.filterType)}`)
      if (this.filterClaim !== "all") q.push(`claimApplyStatus=${encodeURIComponent(this.filterClaim)}`)
      if (this.search.studentId.trim()) q.push(`studentId=${encodeURIComponent(this.search.studentId.trim())}`)
      if (this.search.studentName.trim()) q.push(`studentName=${encodeURIComponent(this.search.studentName.trim())}`)
      if (this.search.studentClass.trim()) q.push(`studentClass=${encodeURIComponent(this.search.studentClass.trim())}`)
      const qs = q.length ? `?${q.join("&")}` : ""
      uni.request({
        url: `${BASE_URL}/lostfound${qs}`,
        method: "GET",
        success: (res) => { this.list = res.data || [] },
        fail: () => uni.showToast({ title: "获取失败", icon: "none" })
      })
    },
    approveClaim(i) {
      uni.showModal({
        title: "确认通过认领",
        editable: true,
        placeholderText: "可选：审核备注",
        content: `确认通过《${i.title}》的认领申请？`,
        success: (m) => {
          if (!m.confirm) return
          uni.request({
            url: `${BASE_URL}/lostfound/${i.id}/claim-review`,
            method: "POST",
            header: { "Content-Type": "application/json" },
            data: { action: "approve", note: m.content || "" },
            success: (res) => {
              if (!res.data || !res.data.ok) {
                return uni.showToast({ title: (res.data && res.data.msg) || "失败", icon: "none" })
              }
              uni.showToast({ title: "已通过", icon: "success" })
              this.fetchList()
            },
            fail: () => uni.showToast({ title: "请求失败", icon: "none" })
          })
        }
      })
    },
    rejectClaim(i) {
      uni.showModal({
        title: "驳回认领申请",
        editable: true,
        placeholderText: "请填写驳回原因",
        success: (m) => {
          if (!m.confirm) return
          const note = (m.content || "").trim()
          if (!note) {
            uni.showToast({ title: "请填写驳回原因", icon: "none" })
            return
          }
          uni.request({
            url: `${BASE_URL}/lostfound/${i.id}/claim-review`,
            method: "POST",
            header: { "Content-Type": "application/json" },
            data: { action: "reject", note },
            success: (res) => {
              if (!res.data || !res.data.ok) {
                return uni.showToast({ title: (res.data && res.data.msg) || "失败", icon: "none" })
              }
              uni.showToast({ title: "已驳回", icon: "success" })
              this.fetchList()
            },
            fail: () => uni.showToast({ title: "请求失败", icon: "none" })
          })
        }
      })
    },
    closeItem(i) {
      uni.showModal({
        title: "确认",
        editable: true,
        placeholderText: "学号,姓名,班级",
        content: `将 "${i.title}" 标记为已解决？请填写学号,姓名,班级`,
        success: (m) => {
          if (!m.confirm) return
          const parts = (m.content || "").split(",").map(s => s.trim()).filter(Boolean)
          if (parts.length < 3) {
            uni.showToast({ title: "请填写学号,姓名,班级", icon: "none" })
            return
          }
          const [claimStudentId, claimName, claimClass] = parts
          uni.request({
            url: `${BASE_URL}/lostfound/${i.id}/status`,
            method: "POST",
            header: { "Content-Type": "application/json" },
            data: { operator: this.operator, status: "closed", claimStudentId, claimName, claimClass },
            success: (res) => {
              if (!res.data || !res.data.ok) {
                return uni.showToast({ title: (res.data && res.data.msg) || "失败", icon: "none" })
              }
              uni.showToast({ title: "已更新", icon: "success" })
              this.fetchList()
            },
            fail: () => uni.showToast({ title: "请求失败", icon: "none" })
          })
        }
      })
    },
    imgSrc(url) {
      if (!url) return ""
      if (url.startsWith("http")) return url
      return `${BASE_URL}${url}`
    }
  }
}
</script>

<style>
.chips { display:flex; gap:8px; flex-wrap: wrap; }
.chip.active { background: #e6f0ff; color: #1f4d8f; }
.searchGrid {
  margin-top: 10px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.searchGrid .input {
  background: #f4f6f9;
  border-radius: 12px;
  padding: 10px 12px;
}
.item { border: 1px solid rgba(31, 77, 143, 0.06); }
.name { font-weight: 600; }
.meta { margin-top: 6px; color:#64748b; font-size:12px; }
.thumb {
  width: 100%;
  height: 140px;
  border-radius: 12px;
  margin-top: 8px;
}
.tag { font-size:12px; padding:4px 8px; border-radius:999px; background:#eef2f6; }
.tag.lost { background:#fff7e6; color:#8a5a00; }
.tag.found { background:#e8fff0; color:#1f7a3a; }
.claimBox {
  margin-top: 8px;
  padding: 8px;
  border-radius: 10px;
  background: #f8fafc;
  border: 1px solid rgba(148, 163, 184, 0.35);
}
.actions { display:flex; justify-content:space-between; align-items:center; margin-top: 8px; }
.status { font-size:12px; color:#7a8593; }
.open { color:#b45309; }
.closed { color:#1f7a3a; }
.empty { text-align:center; color:#999; margin-top:40px; }
</style>

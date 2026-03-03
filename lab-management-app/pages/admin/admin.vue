<template>
  <view class="container adminPage">
    <view class="stack">
      <view class="card heroCard">
        <view class="rowBetween heroTop">
          <view>
            <view class="title">管理工作台</view>
            <view class="subtitle">移动端管理员首页</view>
          </view>
          <view class="heroActions">
            <button class="btnSecondary miniBtn" size="mini" @click="refreshAll">刷新</button>
            <button class="btnDanger miniBtn" size="mini" @click="logout">退出</button>
          </view>
        </view>
        <view class="heroMeta muted">当前账号：{{ operator || "-" }}</view>
        <view class="heroMeta muted">最近更新：{{ lastUpdated || "-" }}</view>
      </view>

      <view class="metricGrid">
        <view class="card metricCard" v-for="item in statCards" :key="item.key">
          <view class="metricIcon" :class="'tone-' + item.tone">{{ item.icon }}</view>
          <view class="metricBody">
            <view class="metricLabel">{{ item.title }}</view>
            <view class="metricValue">{{ item.value }}</view>
            <view class="metricSub">{{ item.sub }}</view>
          </view>
        </view>
      </view>

      <view class="card">
        <view class="rowBetween sectionHeader">
          <view class="cardTitle">快捷入口</view>
          <view class="muted">常用管理功能</view>
        </view>
        <view class="entryGrid">
          <view class="entryItem" v-for="item in quickEntries" :key="item.key" @click="openEntry(item.key)">
            <view class="entryIcon">{{ item.icon }}</view>
            <view class="entryName">{{ item.name }}</view>
            <view class="entryDesc">{{ item.desc }}</view>
            <view class="entryBadge" v-if="item.badge > 0">{{ item.badge }}</view>
          </view>
        </view>
      </view>

      <view class="card">
        <view class="rowBetween sectionHeader">
          <view class="cardTitle">公告发布</view>
          <view class="muted">发布后会出现在用户动态</view>
        </view>
        <input
          class="inputBase"
          v-model.trim="announcementTitle"
          maxlength="120"
          placeholder="请输入公告标题"
        />
        <textarea
          class="textareaBase announcementArea"
          v-model.trim="announcementContent"
          maxlength="5000"
          placeholder="请输入公告内容"
        />
        <view class="rowBetween announcementActions">
          <view class="muted">标题必填，内容必填</view>
          <button class="btnPrimary miniBtn" size="mini" :loading="publishing" @click="publishAnnouncement">
            发布公告
          </button>
        </view>
      </view>

      <view class="card">
        <view class="rowBetween sectionHeader">
          <view>
            <view class="cardTitle">待审批预约</view>
            <view class="muted">展示最近 6 条</view>
          </view>
          <button class="btnPrimary miniBtn" size="mini" @click="goApprove">全部审批</button>
        </view>

        <view class="empty" v-if="loadingPreview">加载中...</view>

        <view class="emptyState" v-else-if="pendingRows.length === 0">
          <view class="emptyIcon">📭</view>
          <view class="emptyTitle">当前没有待审批预约</view>
          <view class="emptySub">可点击刷新，或稍后再查看</view>
        </view>

        <view class="pendingList" v-else>
          <view class="pendingItem" v-for="row in pendingRows" :key="row.id">
            <view class="rowBetween">
              <view class="pendingLab">{{ row.labName || row.lab || "未知实验室" }}</view>
              <view class="statusTag" :class="statusTone(row.status)">
                {{ statusText(row.status) }}
              </view>
            </view>
            <view class="pendingMeta">预约人：{{ row.user || row.username || "-" }}</view>
            <view class="pendingMeta">时段：{{ row.date || "-" }} {{ row.time || row.slot || "-" }}</view>
            <view class="pendingMeta lineClamp" v-if="row.purpose">用途：{{ row.purpose }}</view>
            <view class="pendingActions">
              <button class="btnSecondary miniBtn" size="mini" @click="goApproveDetail(row.id)">详情</button>
              <button class="btnPrimary miniBtn" size="mini" @click="goApproveDetail(row.id)">审批</button>
            </view>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { BASE_URL } from "@/common/api.js"

function nowText() {
  const d = new Date()
  const p = (n) => (n < 10 ? `0${n}` : `${n}`)
  return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`
}

function parseListPayload(payload) {
  if (Array.isArray(payload)) return payload
  if (payload && Array.isArray(payload.data)) return payload.data
  if (payload && payload.ok && Array.isArray(payload.data)) return payload.data
  return []
}

export default {
  data() {
    return {
      operator: "",
      pendingCount: 0,
      lostOpenCount: 0,
      claimPendingCount: 0,
      userCount: 0,
      pendingRows: [],
      loadingPreview: false,
      lastUpdated: "",
      timer: null,
      refreshing: false,
      announcementTitle: "",
      announcementContent: "",
      publishing: false
    }
  },
  computed: {
    totalTodo() {
      return this.pendingCount + this.lostOpenCount + this.claimPendingCount
    },
    statCards() {
      return [
        {
          key: "todo",
          title: "待处理总数",
          value: this.totalTodo,
          sub: "预约 + 失物 + 认领",
          icon: "总",
          tone: "blue"
        },
        {
          key: "pending",
          title: "预约待审批",
          value: this.pendingCount,
          sub: "需要尽快处理",
          icon: "约",
          tone: "amber"
        },
        {
          key: "claim",
          title: "认领待审核",
          value: this.claimPendingCount,
          sub: "found 认领申请",
          icon: "领",
          tone: "green"
        },
        {
          key: "users",
          title: "系统用户数",
          value: this.userCount,
          sub: "可登录账号总数",
          icon: "人",
          tone: "violet"
        }
      ]
    },
    quickEntries() {
      return [
        {
          key: "approve",
          icon: "审",
          name: "预约审批",
          desc: "审核预约",
          badge: this.pendingCount
        },
        {
          key: "labs",
          icon: "室",
          name: "实验室",
          desc: "管理实验室",
          badge: 0
        },
        {
          key: "lostfound",
          icon: "物",
          name: "失物招领",
          desc: "审核认领",
          badge: this.lostOpenCount + this.claimPendingCount
        },
        {
          key: "users",
          icon: "户",
          name: "用户管理",
          desc: "账号权限",
          badge: 0
        },
        {
          key: "audit",
          icon: "记",
          name: "审计日志",
          desc: "操作记录",
          badge: 0
        }
      ]
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
    this.refreshAll()
    this.startTimer()
  },
  onHide() {
    this.stopTimer()
  },
  onUnload() {
    this.stopTimer()
  },
  methods: {
    statusText(status) {
      if (status === "pending") return "待审批"
      if (status === "approved") return "已通过"
      if (status === "rejected") return "已驳回"
      if (status === "cancelled") return "已取消"
      return status || "-"
    },
    statusTone(status) {
      if (status === "approved") return "success"
      if (status === "rejected" || status === "cancelled") return "danger"
      if (status === "pending") return "warning"
      return "info"
    },
    startTimer() {
      this.stopTimer()
      this.timer = setInterval(() => {
        this.refreshAll()
      }, 30000)
    },
    stopTimer() {
      if (!this.timer) return
      clearInterval(this.timer)
      this.timer = null
    },
    async refreshAll() {
      if (this.refreshing) return
      this.refreshing = true
      this.loadingPreview = true

      try {
        const [pendingRes, lostRes, claimRes, usersRes, previewRes] = await Promise.all([
          uni.request({
            url: `${BASE_URL}/reservations?status=pending`,
            method: "GET"
          }),
          uni.request({
            url: `${BASE_URL}/lostfound?status=open`,
            method: "GET"
          }),
          uni.request({
            url: `${BASE_URL}/lostfound?type=found&status=open&claimApplyStatus=pending`,
            method: "GET"
          }),
          uni.request({
            url: `${BASE_URL}/users`,
            method: "GET"
          }),
          uni.request({
            url: `${BASE_URL}/reservations?status=pending&page=1&pageSize=6`,
            method: "GET"
          })
        ])

        const pendingList = parseListPayload(pendingRes && pendingRes.data)
        const lostList = parseListPayload(lostRes && lostRes.data)
        const claimList = parseListPayload(claimRes && claimRes.data)
        const usersList = parseListPayload(usersRes && usersRes.data)
        const previewList = parseListPayload(previewRes && previewRes.data)

        this.pendingCount = pendingList.length
        this.lostOpenCount = lostList.length
        this.claimPendingCount = claimList.length
        this.userCount = usersList.length
        this.pendingRows = previewList.slice(0, 6)
        this.lastUpdated = nowText()
      } catch (e) {
        this.pendingCount = 0
        this.lostOpenCount = 0
        this.claimPendingCount = 0
        this.userCount = 0
        this.pendingRows = []
      } finally {
        this.loadingPreview = false
        this.refreshing = false
      }
    },
    openEntry(key) {
      if (key === "approve") return this.goApprove()
      if (key === "labs") return this.goLabs()
      if (key === "lostfound") return this.goLostFound()
      if (key === "users") return this.goUsers()
      if (key === "audit") return this.goAudit()
    },
    goApproveDetail(id) {
      if (!id) return
      uni.navigateTo({ url: `/pages/admin/approve-detail?id=${id}` })
    },
    goApprove() {
      uni.navigateTo({ url: "/pages/admin/approve" })
    },
    goLabs() {
      uni.navigateTo({ url: "/pages/admin/labs" })
    },
    goUsers() {
      uni.navigateTo({ url: "/pages/admin/users" })
    },
    goAudit() {
      uni.navigateTo({ url: "/pages/admin/audit" })
    },
    goLostFound() {
      uni.navigateTo({ url: "/pages/admin/lostfound" })
    },
    async publishAnnouncement() {
      const title = String(this.announcementTitle || "").trim()
      const content = String(this.announcementContent || "").trim()
      if (!title) {
        uni.showToast({ title: "请输入公告标题", icon: "none" })
        return
      }
      if (!content) {
        uni.showToast({ title: "请输入公告内容", icon: "none" })
        return
      }
      if (this.publishing) return
      this.publishing = true
      try {
        const res = await uni.request({
          url: `${BASE_URL}/announcements`,
          method: "POST",
          header: { "Content-Type": "application/json" },
          data: { title, content }
        })
        const payload = (res && res.data) || {}
        if (!payload.ok) {
          uni.showToast({ title: payload.msg || "发布失败", icon: "none" })
          return
        }
        this.announcementTitle = ""
        this.announcementContent = ""
        uni.showToast({ title: "公告已发布", icon: "success" })
      } catch (e) {
        uni.showToast({ title: "发布失败，请稍后重试", icon: "none" })
      } finally {
        this.publishing = false
      }
    },
    logout() {
      const s = uni.getStorageSync("session") || {}
      uni.request({
        url: `${BASE_URL}/auth/logout`,
        method: "POST",
        header: { "Content-Type": "application/json" },
        data: { refreshToken: s.refreshToken || "" },
        complete: () => {
          uni.removeStorageSync("session")
          uni.reLaunch({ url: "/pages/login/login" })
        }
      })
    }
  }
}
</script>

<style lang="scss">
.adminPage {
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
  align-items: center;
}

.miniBtn {
  min-height: 30px;
  line-height: 30px;
  padding: 0 10px;
  border-radius: 9px;
  font-size: 12px;
}

.heroMeta {
  margin-top: 6px;
}

.announcementArea {
  margin-top: 8px;
  min-height: 96px;
}

.announcementActions {
  margin-top: 10px;
  align-items: center;
}

.sectionHeader {
  align-items: flex-start;
}

.metricGrid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.metricCard {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 86px;
}

.metricIcon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 14px;
  font-weight: 700;
}

.metricIcon.tone-blue {
  color: #1d4ed8;
  background: #eaf3ff;
}

.metricIcon.tone-amber {
  color: #b45309;
  background: #fff4dd;
}

.metricIcon.tone-green {
  color: #15803d;
  background: #eafaf0;
}

.metricIcon.tone-violet {
  color: #6d28d9;
  background: #f3ebff;
}

.metricBody {
  min-width: 0;
}

.metricLabel {
  font-size: 12px;
  color: #64748b;
}

.metricValue {
  margin-top: 2px;
  font-size: 22px;
  line-height: 1.12;
  font-weight: 700;
  color: #0f172a;
}

.metricSub {
  margin-top: 2px;
  font-size: 11px;
  color: #94a3b8;
}

.entryGrid {
  margin-top: 8px;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.entryItem {
  position: relative;
  border: 1px solid rgba(148, 163, 184, 0.25);
  border-radius: 12px;
  background: #fff;
  padding: 10px 8px;
  text-align: center;
  transition: transform 0.14s ease, box-shadow 0.14s ease;
}

.entryItem:active {
  transform: scale(0.98);
  box-shadow: 0 3px 12px rgba(15, 23, 42, 0.08);
}

.entryIcon {
  width: 28px;
  height: 28px;
  margin: 0 auto;
  border-radius: 8px;
  background: #eff6ff;
  color: #1d4ed8;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
}

.entryName {
  margin-top: 6px;
  font-size: 12px;
  font-weight: 600;
  color: #0f172a;
}

.entryDesc {
  margin-top: 2px;
  font-size: 10px;
  color: #94a3b8;
}

.entryBadge {
  position: absolute;
  top: 6px;
  right: 6px;
  min-width: 18px;
  height: 18px;
  line-height: 18px;
  border-radius: 999px;
  background: #ef4444;
  color: #fff;
  text-align: center;
  font-size: 10px;
  padding: 0 5px;
  box-sizing: border-box;
}

.pendingList {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.pendingItem {
  border: 1px solid rgba(148, 163, 184, 0.28);
  border-radius: 12px;
  background: #fff;
  padding: 10px;
}

.pendingLab {
  font-size: 14px;
  line-height: 20px;
  font-weight: 700;
  color: #0f172a;
}

.pendingMeta {
  margin-top: 6px;
  font-size: 12px;
  color: #64748b;
  line-height: 18px;
}

.lineClamp {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.pendingActions {
  margin-top: 10px;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>

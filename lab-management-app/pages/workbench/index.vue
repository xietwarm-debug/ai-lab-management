<template>
  <view class="container adminPage">
    <view class="stack">
      <view class="card heroCard" v-if="isAdmin">
        <view class="rowBetween heroTop">
          <view>
            <view class="title">管理工作台</view>
            <view class="subtitle">管理员功能大厅</view>
          </view>
          <view class="heroActions">
            <button class="btnSecondary miniBtn" size="mini" @click="refreshCurrentHall">刷新</button>
          </view>
        </view>
        <view class="heroMeta muted">当前账号：{{ operator || "-" }}</view>
        <view class="heroMeta muted">最近更新：{{ lastUpdated || "-" }}</view>
      </view>

      <view class="card heroCard teacherHeroCard" v-else-if="isTeacher">
        <view class="rowBetween heroTop">
          <view>
            <view class="title">教师工作台</view>
            <view class="subtitle">教师功能大厅</view>
          </view>
          <view class="heroActions">
            <button class="btnSecondary miniBtn" size="mini" @click="refreshCurrentHall">刷新</button>
          </view>
        </view>
        <view class="heroMeta muted">当前账号：{{ operator || "-" }}</view>
        <view class="heroMeta muted">当前身份：{{ roleText }}</view>
        <view class="heroMeta muted">最近更新：{{ lastUpdated || "-" }}</view>
      </view>

      <view class="card heroCard studentHeroCard" v-else>
        <view class="rowBetween heroTop">
          <view>
            <view class="title">学生工作台</view>
            <view class="subtitle">学生功能大厅</view>
          </view>
          <view class="heroActions">
            <button class="btnSecondary miniBtn" size="mini" @click="refreshCurrentHall">刷新</button>
          </view>
        </view>
        <view class="heroMeta muted">当前账号：{{ operator || "-" }}</view>
        <view class="heroMeta muted">当前身份：{{ roleText }}</view>
        <view class="heroMeta muted">最近更新：{{ lastUpdated || "-" }}</view>
      </view>

      <view class="metricGrid">
        <view class="card metricCard" v-for="item in activeStatCards" :key="item.key">
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
          <view class="cardTitle">{{ hallTitle }}</view>
          <view class="muted">{{ hallSubtitle }}</view>
        </view>
        <view class="entryGroups">
          <view class="entryGroup" v-for="group in activeEntryGroups" :key="group.key">
            <view class="rowBetween groupHead">
              <view class="groupTitle">{{ group.name }}</view>
              <view class="rowBetween groupMeta">
                <view class="muted">{{ group.desc }}</view>
                <view class="groupBadge" v-if="group.badge > 0">{{ group.badge }}</view>
              </view>
            </view>
            <view class="entryGrid">
              <view class="entryItem" v-for="item in group.items" :key="item.key" @click="handleEntryTap(item.key)">
                <view class="entryIcon">{{ item.icon }}</view>
                <view class="entryName">{{ item.name }}</view>
                <view class="entryDesc">{{ item.desc }}</view>
                <view :class="['entryBadge', entryBadgeClass(item)]" v-if="item.badge > 0">{{ item.badge }}</view>
              </view>
            </view>
          </view>
        </view>
      </view>

    </view>
  </view>
</template>

<script>
import { getWorkbenchOverview } from "@/common/api.js"
import { applyNotificationTabBadge } from "@/common/notifications.js"
import { HOME_PAGE_URL, normalizeRole, requireRole } from "@/common/session.js"

function nowText() {
  const d = new Date()
  const p = (n) => (n < 10 ? `0${n}` : `${n}`)
  return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`
}

export default {
  data() {
    return {
      operator: "",
      role: "",
      pendingCount: 0,
      borrowPendingCount: 0,
      borrowOverdueCount: 0,
      lostOpenCount: 0,
      claimPendingCount: 0,
      repairPendingCount: 0,
      adminUnreadCount: 0,
      userCount: 0,
      lastUpdated: "",
      timer: null,
      refreshing: false,
      studentReservationCount: 0,
      studentPendingReservationCount: 0,
      studentBorrowPendingCount: 0,
      studentRepairCount: 0,
      studentRepairActiveCount: 0,
      studentUnreadCount: 0,
      teacherPendingReviewCount: 0,
      studentRefreshing: false
    }
  },
  computed: {
    isAdmin() {
      return this.role === "admin"
    },
    isTeacher() {
      return this.role === "teacher"
    },
    roleText() {
      if (this.role === "admin") return "管理员"
      if (this.role === "teacher") return "教师"
      if (this.role === "student") return "学生"
      return "访客"
    },
    hallTitle() {
      if (this.isAdmin) return "功能大厅"
      if (this.isTeacher) return "教师功能大厅"
      return "学生功能大厅"
    },
    hallSubtitle() {
      if (this.isAdmin) return "管理员全部可操作模块"
      if (this.isTeacher) return "仅展示教师常用入口"
      return "仅展示学生常用入口"
    },
    activeStatCards() {
      if (this.isAdmin) return this.statCards
      if (this.isTeacher) return this.teacherStatCards
      return this.studentStatCards
    },
    activeEntryGroups() {
      if (this.isAdmin) return this.entryGroups
      if (this.isTeacher) return this.teacherEntryGroups
      return this.studentEntryGroups
    },
    totalTodo() {
      return this.pendingCount + this.borrowPendingCount + this.borrowOverdueCount + this.repairPendingCount + this.claimPendingCount
    },
    statCards() {
      return [
        {
          key: "todo",
          title: "待处理总数",
          value: this.totalTodo,
          sub: "预约 + 借用 + 报修 + 认领",
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
          key: "borrow",
          title: "借用待处理",
          value: this.borrowPendingCount + this.borrowOverdueCount,
          sub: `待审批 ${this.borrowPendingCount} · 逾期 ${this.borrowOverdueCount}`,
          icon: "借",
          tone: "green"
        },
        {
          key: "claim",
          title: "认领待审核",
          value: this.claimPendingCount,
          sub: "found 认领申请",
          icon: "领",
          tone: "violet"
        },
        {
          key: "users",
          title: "系统用户数",
          value: this.userCount,
          sub: "可登录账号总数",
          icon: "人",
          tone: "blue"
        }
      ]
    },
    studentStatCards() {
      return [
        {
          key: "studentReservations",
          title: "我的预约总数",
          value: this.studentReservationCount,
          sub: "包含历史预约记录",
          icon: "约",
          tone: "blue"
        },
        {
          key: "studentPendingReservations",
          title: "待审批预约",
          value: this.studentPendingReservationCount,
          sub: "等待管理员处理",
          icon: "待",
          tone: "amber"
        },
        {
          key: "studentRepairActive",
          title: "处理中工单",
          value: this.studentRepairActiveCount,
          sub: `我的工单共 ${this.studentRepairCount} 条`,
          icon: "修",
          tone: "green"
        },
        {
          key: "studentUnreadNotifications",
          title: "通知未读",
          value: this.studentUnreadCount,
          sub: "建议优先查看",
          icon: "讯",
          tone: "violet"
        }
      ]
    },
    teacherStatCards() {
      return [
        {
          key: "teacherReservations",
          title: "我的预约总数",
          value: this.studentReservationCount,
          sub: "用于教学安排",
          icon: "课",
          tone: "blue"
        },
        {
          key: "teacherPendingReservations",
          title: "待审批预约",
          value: this.studentPendingReservationCount,
          sub: "等待管理员处理",
          icon: "待",
          tone: "amber"
        },
        {
          key: "teacherRepairActive",
          title: "处理中工单",
          value: this.studentRepairActiveCount,
          sub: `我的工单共 ${this.studentRepairCount} 条`,
          icon: "修",
          tone: "green"
        },
        {
          key: "teacherUnreadNotifications",
          title: "通知未读",
          value: this.studentUnreadCount,
          sub: "建议优先查看",
          icon: "讯",
          tone: "violet"
        }
      ]
    },
    quickEntries() {
      return [
        {
          key: "announcementEditor",
          icon: "告",
          name: "发布公告",
          desc: "编辑与定时",
          badge: 0
        },
        {
          key: "announcementList",
          icon: "管",
          name: "公告管理",
          desc: "置顶与删除",
          badge: 0
        },
        {
          key: "approve",
          icon: "审",
          name: "预约审批",
          desc: "审核预约",
          badge: this.pendingCount
        },
        {
          key: "borrowApproval",
          icon: "借",
          name: "租借审批中心",
          desc: "审批与归还管理",
          badge: this.borrowPendingCount + this.borrowOverdueCount
        },
        {
          key: "todoCenter",
          icon: "待",
          name: "待办中心",
          desc: "卡片化消息工作台",
          badge: this.totalTodo
        },
        {
          key: "labs",
          icon: "室",
          name: "实验室列表",
          desc: "管理员实验室列表",
          badge: 0
        },
        {
          key: "equipments",
          icon: "资",
          name: "资产管理",
          desc: "设备台账",
          badge: 0
        },
        {
          key: "repairOrders",
          icon: "单",
          name: "工单流转",
          desc: "报修处理",
          badge: this.repairPendingCount
        },
        {
          key: "lostfound",
          icon: "物",
          name: "失物招领",
          desc: "审核认领",
          badge: this.lostOpenCount + this.claimPendingCount
        },
        {
          key: "roomMap",
          icon: "图",
          name: "机房布局",
          desc: "先选实验室",
          badge: 0
        },
        {
          key: "users",
          icon: "户",
          name: "用户管理",
          desc: "账号权限",
          badge: 0
        },
        {
          key: "notifications",
          icon: "通",
          name: "通知中心",
          desc: "未读提醒",
          badge: this.adminUnreadCount,
          badgeType: "unread"
        },
        {
          key: "scheduleManage",
          icon: "课",
          name: "课表管理",
          desc: "导入与开门提醒",
          badge: 0
        },
        {
          key: "dutyEmergency",
          icon: "应",
          name: "值班应急",
          desc: "值班、事故与联系人",
          badge: 0
        },
        {
          key: "audit",
          icon: "记",
          name: "审计日志",
          desc: "操作记录",
          badge: 0
        },
        {
          key: "stats",
          icon: "数",
          name: "数据看板",
          desc: "运营统计",
          badge: 0
        },
        {
          key: "reportCenter",
          icon: "报",
          name: "报表中心",
          desc: "统一报表导出",
          badge: 0
        },
        {
          key: "reservationBoard",
          icon: "排",
          name: "预约排班",
          desc: "占用与冲突",
          badge: this.pendingCount
        },
        {
          key: "reservationRules",
          icon: "规",
          name: "预约规则",
          desc: "配置预约策略",
          badge: 0
        }
      ]
    },
    studentQuickEntries() {
      return [
        {
          key: "courses",
          icon: "课",
          name: "课程管理",
          desc: "课程码加入与任务查看",
          badge: 0
        },
        {
          key: "labs",
          icon: "室",
          name: "实验室列表",
          desc: "查看可用实验室",
          badge: 0
        },
        {
          key: "reserve",
          icon: "约",
          name: "我要预约",
          desc: "提交新的预约申请",
          badge: 0
        },
        {
          key: "myReservations",
          icon: "单",
          name: "我的预约",
          desc: "查询进度与状态",
          badge: this.studentPendingReservationCount
        },
        {
          key: "myBorrowings",
          icon: "借",
          name: "我的借用",
          desc: "资产借用与归还状态",
          badge: this.studentBorrowPendingCount
        },
        {
          key: "myRepairOrders",
          icon: "修",
          name: "我的工单",
          desc: "查看报修处理进度",
          badge: this.studentRepairActiveCount
        },
        {
          key: "notifications",
          icon: "讯",
          name: "通知中心",
          desc: "预约和系统消息",
          badge: this.studentUnreadCount,
          badgeType: "unread"
        },
        {
          key: "dutyRoster",
          icon: "值",
          name: "值班表",
          desc: "查看本周值班与应急联系人",
          badge: 0
        },
        {
          key: "lostfoundUser",
          icon: "物",
          name: "失物招领",
          desc: "发布或认领失物",
          badge: 0
        },
        {
          key: "agent",
          icon: "AI",
          name: "AI 助手",
          desc: "快速问答与辅助",
          badge: 0
        },
        {
          key: "profile",
          icon: "我",
          name: "个人资料",
          desc: "编辑头像和昵称",
          badge: 0
        },
        {
          key: "settings",
          icon: "设",
          name: "账号设置",
          desc: "密码和偏好设置",
          badge: 0
        }
      ]
    },
    teacherQuickEntries() {
      return [
        {
          key: "teacherAssets",
          icon: "资",
          name: "资产查询",
          desc: "只读查看资产台账",
          badge: 0
        },
        {
          key: "courses",
          icon: "\u8bfe",
          name: "\u8bfe\u7a0b\u7ba1\u7406",
          desc: "\u5b9e\u9a8c\u8bfe\u7a0b\u4e0e\u4efb\u52a1",
          badge: 0
        },
        {
          key: "homeworkReview",
          icon: "改",
          name: "作业批改",
          desc: "评分、通过与驳回",
          badge: 0
        },
        {
          key: "homeworkPending",
          icon: "待",
          name: "待批改",
          desc: "待处理作业提交",
          badge: this.teacherPendingReviewCount
        },
        {
          key: "labs",
          icon: "室",
          name: "实验室列表",
          desc: "查询开放实验室",
          badge: 0
        },
        {
          key: "reserve",
          icon: "约",
          name: "发起预约",
          desc: "提交教学预约申请",
          badge: 0
        },
        {
          key: "myReservations",
          icon: "课",
          name: "我的预约",
          desc: "查看预约审批进度",
          badge: this.studentPendingReservationCount
        },
        {
          key: "myBorrowings",
          icon: "借",
          name: "我的借用",
          desc: "资产借用与归还状态",
          badge: this.studentBorrowPendingCount
        },
        {
          key: "myRepairOrders",
          icon: "修",
          name: "我的工单",
          desc: "跟踪课堂设备报修",
          badge: this.studentRepairActiveCount
        },
        {
          key: "notifications",
          icon: "讯",
          name: "通知中心",
          desc: "预约与系统提醒",
          badge: this.studentUnreadCount,
          badgeType: "unread"
        },
        {
          key: "dutyRoster",
          icon: "值",
          name: "值班表",
          desc: "查看值班安排与应急联系人",
          badge: 0
        },
        {
          key: "lostfoundUser",
          icon: "物",
          name: "失物招领",
          desc: "查看与认领信息",
          badge: 0
        },
        {
          key: "agent",
          icon: "AI",
          name: "AI 助手",
          desc: "快速问答与辅助",
          badge: 0
        },
        {
          key: "profile",
          icon: "我",
          name: "个人资料",
          desc: "编辑头像和昵称",
          badge: 0
        },
        {
          key: "settings",
          icon: "设",
          name: "账号设置",
          desc: "密码和偏好设置",
          badge: 0
        }
      ]
    },
    entryGroups() {
      const byKey = {}
      this.quickEntries.forEach((item) => {
        byKey[item.key] = item
      })

      const buildGroup = (key, name, desc, itemKeys) => {
        const items = itemKeys.map((itemKey) => byKey[itemKey]).filter(Boolean)
        const badge = items.reduce((sum, item) => sum + Number(item.badge || 0), 0)
        return { key, name, desc, items, badge }
      }

      return [
        buildGroup("approval", "审批类", "预约、借用、工单、认领处理", ["todoCenter", "approve", "borrowApproval", "reservationBoard", "repairOrders", "lostfound"]),
        buildGroup("assets", "资产类", "实验室、布局与设备", ["labs", "roomMap", "equipments"]),
        buildGroup("content", "内容类", "公告、通知与课表运营", ["announcementEditor", "announcementList", "notifications", "scheduleManage"]),
        buildGroup("system", "系统类", "账号、审计、规则和值班应急", ["users", "audit", "stats", "reportCenter", "reservationRules", "dutyEmergency"])
      ]
    },
    studentEntryGroups() {
      const byKey = {}
      this.studentQuickEntries.forEach((item) => {
        byKey[item.key] = item
      })

      const buildGroup = (key, name, desc, itemKeys) => {
        const items = itemKeys.map((itemKey) => byKey[itemKey]).filter(Boolean)
        const badge = items.reduce((sum, item) => sum + Number(item.badge || 0), 0)
        return { key, name, desc, items, badge }
      }

      return [
        buildGroup("studentReserve", "预约学习", "实验室查询与预约申请", ["courses", "labs", "reserve", "myReservations"]),
        buildGroup("studentService", "消息服务", "通知、借用、报修和值班联系", ["notifications", "dutyRoster", "myBorrowings", "myRepairOrders", "lostfoundUser"]),
        buildGroup("studentAccount", "个人中心", "助手、资料与账号设置", ["agent", "profile", "settings"])
      ]
    },
    teacherEntryGroups() {
      const byKey = {}
      this.teacherQuickEntries.forEach((item) => {
        byKey[item.key] = item
      })

      const buildGroup = (key, name, desc, itemKeys) => {
        const items = itemKeys.map((itemKey) => byKey[itemKey]).filter(Boolean)
        const badge = items.reduce((sum, item) => sum + Number(item.badge || 0), 0)
        return { key, name, desc, items, badge }
      }

      return [
        buildGroup("teacherReserve", "\u6559\u5b66\u9884\u7ea6", "\u5b9e\u9a8c\u5ba4\u9884\u7ea6\u4e0e\u8fdb\u5ea6\u67e5\u770b", ["teacherAssets", "labs", "reserve", "myReservations"]),
        buildGroup("teacherService", "\u8bfe\u5802\u670d\u52a1", "\u5b9e\u9a8c\u8bfe\u7a0b\u4e0e\u4efb\u52a1", ["courses", "homeworkReview"]),
        buildGroup(
          "teacherWorkbench",
          "\u6559\u5e08\u5de5\u4f5c\u53f0",
          "\u5f85\u6279\u6539\u3001\u6d88\u606f\u3001\u503c\u73ed\u8054\u7cfb\u3001\u501f\u7528\u3001\u5de5\u5355\u4e0e\u8d26\u53f7\u7ba1\u7406",
          ["homeworkPending", "notifications", "dutyRoster", "myBorrowings", "myRepairOrders", "lostfoundUser", "agent", "profile", "settings"]
        )
      ]
    }
  },
  onShow() {
    const session = requireRole(["admin", "teacher", "student"], {
      message: "无权限访问",
      fallbackUrl: HOME_PAGE_URL
    })
    if (!session) return
    const s = {
      ...session,
      role: normalizeRole(session.role)
    }
    if (!s || !s.username || !s.token) {
      uni.showToast({ title: "请先登录", icon: "none" })
      uni.reLaunch({ url: "/pages/login/login" })
      return
    }
    this.operator = s.username || ""
    this.role = String(s.role || "").trim()

    if (this.isAdmin) {
      this.startTimer()
    } else {
      this.stopTimer()
    }
    this.fetchOverview()
  },
  async onPullDownRefresh() {
    try {
      await this.refreshCurrentHall()
    } finally {
      uni.stopPullDownRefresh()
    }
  },
  onHide() {
    this.stopTimer()
  },
  onUnload() {
    this.stopTimer()
  },
  methods: {
    refreshCurrentHall() {
      return this.fetchOverview()
    },
    startTimer() {
      this.stopTimer()
      if (!this.isAdmin) return
      this.timer = setInterval(() => {
        if (!this.isAdmin) return
        this.fetchOverview()
      }, 30000)
    },
    stopTimer() {
      if (!this.timer) return
      clearInterval(this.timer)
      this.timer = null
    },
    resetOverviewMetrics() {
      this.pendingCount = 0
      this.borrowPendingCount = 0
      this.borrowOverdueCount = 0
      this.lostOpenCount = 0
      this.claimPendingCount = 0
      this.repairPendingCount = 0
      this.adminUnreadCount = 0
      this.userCount = 0
      this.studentReservationCount = 0
      this.studentPendingReservationCount = 0
      this.studentBorrowPendingCount = 0
      this.studentRepairCount = 0
      this.studentRepairActiveCount = 0
      this.studentUnreadCount = 0
      this.teacherPendingReviewCount = 0
      this.lastUpdated = ""
    },
    applyOverviewMetrics(metrics = {}, role = "") {
      const data = metrics && typeof metrics === "object" ? metrics : {}
      const nextRole = String(role || this.role || "").trim()
      this.pendingCount = Number(data.pendingCount || 0)
      this.borrowPendingCount = Number(data.borrowPendingCount || 0)
      this.borrowOverdueCount = Number(data.borrowOverdueCount || 0)
      this.lostOpenCount = Number(data.lostOpenCount || 0)
      this.claimPendingCount = Number(data.claimPendingCount || 0)
      this.repairPendingCount = Number(data.repairPendingCount || 0)
      this.adminUnreadCount = Number(data.adminUnreadCount || 0)
      this.userCount = Number(data.userCount || 0)
      this.studentReservationCount = Number(data.studentReservationCount || 0)
      this.studentPendingReservationCount = Number(data.studentPendingReservationCount || 0)
      this.studentBorrowPendingCount = Number(data.studentBorrowPendingCount || 0)
      this.studentRepairCount = Number(data.studentRepairCount || 0)
      this.studentRepairActiveCount = Number(data.studentRepairActiveCount || 0)
      this.studentUnreadCount = Number(data.studentUnreadCount || 0)
      this.teacherPendingReviewCount = nextRole === "teacher" ? Number(data.teacherPendingReviewCount || 0) : 0
    },
    async fetchOverview() {
      if (this.refreshing || this.studentRefreshing) return
      this.refreshing = true
      this.studentRefreshing = true
      try {
        const res = await getWorkbenchOverview()
        const payload = (res && res.data) || {}
        if (!payload.ok || !payload.data) {
          this.resetOverviewMetrics()
          uni.showToast({ title: payload.msg || "Load failed", icon: "none" })
          applyNotificationTabBadge(0)
          return
        }
        const overview = payload.data || {}
        const nextRole = normalizeRole(overview.role || this.role)
        if (nextRole) {
          this.role = nextRole
        }
        this.applyOverviewMetrics(overview.metrics || {}, this.role)
        this.lastUpdated = String(overview.lastUpdated || nowText())
        const unreadCount = this.isAdmin ? Number(this.adminUnreadCount || 0) : Number(this.studentUnreadCount || 0)
        applyNotificationTabBadge(unreadCount)
      } catch (e) {
        this.resetOverviewMetrics()
        applyNotificationTabBadge(0)
      } finally {
        this.refreshing = false
        this.studentRefreshing = false
      }
    },
    entryBadgeClass(item) {
      return item && item.badgeType === "unread" ? "is-unread" : "is-todo"
    },
    handleEntryTap(key) {
      if (this.isAdmin) return this.openEntry(key)
      if (this.isTeacher) return this.openTeacherEntry(key)
      return this.openStudentEntry(key)
    },
    openEntry(key) {
      if (key === "announcementEditor") return this.goAnnouncementEditor()
      if (key === "announcementList") return this.goAnnouncementList()
      if (key === "todoCenter") return this.goTodoCenter()
      if (key === "approve") return this.goApprove()
      if (key === "borrowApproval") return this.goBorrowApproval()
      if (key === "labs") return this.goLabs()
      if (key === "equipments") return this.goEquipments()
      if (key === "repairOrders") return this.goRepairOrders()
      if (key === "lostfound") return this.goLostFound()
      if (key === "roomMap") return this.goRoomMap()
      if (key === "users") return this.goUsers()
      if (key === "notifications") return this.goNotifications()
      if (key === "scheduleManage") return this.goScheduleManage()
      if (key === "dutyEmergency") return this.goDutyEmergency()
      if (key === "audit") return this.goAudit()
      if (key === "stats") return this.goStats()
      if (key === "reportCenter") return this.goReportCenter()
      if (key === "reservationBoard") return this.goReservationBoard()
      if (key === "reservationRules") return this.goReservationRules()
    },
    openStudentEntry(key) {
      if (key === "courses") return this.goTeacherCourses()
      if (key === "labs") return this.goLabsList()
      if (key === "reserve") return this.goReserve()
      if (key === "myReservations") return this.goMyReservations()
      if (key === "myBorrowings") return this.goMyBorrowings()
      if (key === "approve") return this.goApprove()
      if (key === "myRepairOrders") return this.goMyRepairOrders()
      if (key === "notifications") return this.goNotifications()
      if (key === "dutyRoster") return this.goDutyRoster()
      if (key === "lostfoundUser") return this.goLostFoundUser()
      if (key === "agent") return this.goAgent()
      if (key === "profile") return this.goProfile()
      if (key === "settings") return this.goSettings()
    },
    openTeacherEntry(key) {
      if (key === "teacherAssets") return this.goTeacherAssets()
      if (key === "courses") return this.goTeacherCourses()
      if (key === "homeworkReview") return this.goHomeworkReview()
      if (key === "homeworkPending") return this.goHomeworkPending()
      if (key === "labs") return this.goLabsList()
      if (key === "reserve") return this.goReserve()
      if (key === "myReservations") return this.goMyReservations()
      if (key === "myBorrowings") return this.goMyBorrowings()
      if (key === "myRepairOrders") return this.goMyRepairOrders()
      if (key === "notifications") return this.goNotifications()
      if (key === "dutyRoster") return this.goDutyRoster()
      if (key === "lostfoundUser") return this.goLostFoundUser()
      if (key === "agent") return this.goAgent()
      if (key === "profile") return this.goProfile()
      if (key === "settings") return this.goSettings()
    },
    goAnnouncementEditor() {
      uni.navigateTo({ url: "/pages/admin/announcements?tab=editor" })
    },
    goAnnouncementList() {
      uni.navigateTo({ url: "/pages/admin/announcements?tab=list" })
    },
    goApprove() {
      uni.navigateTo({ url: "/pages/admin/approve" })
    },
    goBorrowApproval() {
      uni.navigateTo({ url: "/pages/admin/borrow_approval" })
    },
    goLabs() {
      uni.navigateTo({ url: "/pages/admin/labs" })
    },
    goEquipments() {
      uni.navigateTo({ url: "/pages/admin/equipments" })
    },
    goRepairOrders() {
      uni.navigateTo({ url: "/pages/admin/repair_orders" })
    },
    goRoomMap() {
      uni.showToast({ title: "请先进入实验室管理选择机房", icon: "none" })
      uni.navigateTo({ url: "/pages/admin/labs" })
    },
    goTodoCenter() {
      uni.navigateTo({ url: "/pages/admin/todo_center" })
    },
    goUsers() {
      uni.navigateTo({ url: "/pages/admin/users" })
    },
    goAudit() {
      uni.navigateTo({ url: "/pages/admin/audit" })
    },
    goStats() {
      uni.navigateTo({ url: "/pages/admin/stats" })
    },
    goReportCenter() {
      uni.navigateTo({ url: "/pages/admin/report_center" })
    },
    goReservationBoard() {
      uni.navigateTo({ url: "/pages/admin/reservation_board" })
    },
    goReservationRules() {
      uni.navigateTo({ url: "/pages/admin/reservation_rules" })
    },
    goTeacherCourses() {
      uni.navigateTo({ url: "/pages/teacher/courses" })
    },
    goTeacherAssets() {
      uni.navigateTo({ url: "/pages/teacher/assets" })
    },
    goHomeworkReview() {
      uni.navigateTo({ url: "/pages/teacher/homework_review" })
    },
    goHomeworkPending() {
      uni.navigateTo({ url: "/pages/teacher/homework_review?reviewStatus=pending" })
    },
    goLabsList() {
      uni.navigateTo({ url: "/pages/labs/labs" })
    },
    goReserve() {
      uni.navigateTo({ url: "/pages/reserve/reserve" })
    },
    goMyReservations() {
      uni.navigateTo({ url: "/pages/my/reservations" })
    },
    goMyBorrowings() {
      uni.navigateTo({ url: "/pages/my/borrowings" })
    },
    goMyRepairOrders() {
      uni.navigateTo({ url: "/pages/my/repair_orders" })
    },
    goLostFoundUser() {
      uni.navigateTo({ url: "/pages/lostfound/list" })
    },
    goAgent() {
      uni.switchTab({ url: "/pages/agent/agent" })
    },
    goProfile() {
      uni.navigateTo({ url: "/pages/my/profile" })
    },
    goSettings() {
      uni.navigateTo({ url: "/pages/settings/settings" })
    },
    goNotifications() {
      uni.navigateTo({ url: "/pages/notifications/list" })
    },
    goScheduleManage() {
      uni.navigateTo({ url: "/pages/admin/schedule_manage" })
    },
    goDutyEmergency() {
      uni.navigateTo({ url: "/pages/admin/duty_emergency" })
    },
    goDutyRoster() {
      uni.navigateTo({ url: "/pages/duty/roster" })
    },
    goLostFound() {
      uni.navigateTo({ url: "/pages/admin/lostfound" })
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

.studentHeroCard {
  border-color: rgba(22, 163, 74, 0.2);
  background: linear-gradient(160deg, #ffffff 0%, #eefbf4 100%);
}

.teacherHeroCard {
  border-color: rgba(245, 158, 11, 0.26);
  background: linear-gradient(160deg, #ffffff 0%, #fffaef 100%);
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

.entryGroups {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.entryGroup {
  border: 1px solid rgba(148, 163, 184, 0.25);
  border-radius: 12px;
  background: #f8fbff;
  padding: 10px;
}

.groupHead {
  align-items: center;
}

.groupTitle {
  font-size: 13px;
  line-height: 19px;
  font-weight: 700;
  color: #0f172a;
}

.groupMeta {
  gap: 8px;
  align-items: center;
}

.groupBadge {
  min-width: 18px;
  height: 18px;
  line-height: 18px;
  border-radius: 999px;
  background: #e2e8f0;
  color: #334155;
  text-align: center;
  font-size: 10px;
  padding: 0 5px;
  box-sizing: border-box;
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
  text-align: center;
  font-size: 10px;
  padding: 0 5px;
  box-sizing: border-box;
}

.entryBadge.is-unread {
  background: #ef4444;
  color: #fff;
}

.entryBadge.is-todo {
  background: #fef3c7;
  color: #92400e;
}

</style>

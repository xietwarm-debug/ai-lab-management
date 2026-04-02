<template>
  <view class="container portalPage" :class="themeClass">
    <view class="stack">
      <view class="card heroCard">
        <view class="heroBadge">AIlab</view>
        <view class="title">{{ isAdmin ? "管理员首页" : "高校实验室智能管理系统" }}</view>
        <view class="subtitle">{{ isAdmin ? "后台功能已拆分到独立页面，可在下方快捷入口直达" : "预约、审批、通知、失物招领一体化平台" }}</view>
        <view class="heroMetaRow">
          <view class="heroMetaItem">当前账号：{{ username || "未登录" }}</view>
          <view class="heroMetaItem">身份：{{ roleText }}</view>
        </view>
      </view>

      <view class="card adminBoard" v-if="isAdmin">
        <view class="rowBetween boardHead">
          <view>
            <view class="cardTitle">关键数据看板</view>
            <view class="feedMore">管理员专属实验室运营概览</view>
          </view>
          <button class="btnSecondary miniBtn" size="mini" :loading="adminPanelLoading" @click="loadAdminOverview">
            刷新
          </button>
        </view>

        <view class="boardTop">
          <view class="boardStat">
            <view class="boardLabel">实验室总数</view>
            <view class="boardValue">{{ adminMetrics.labsTotal }}</view>
          </view>
          <view class="boardStat">
            <view class="boardLabel">空闲实验室</view>
            <view class="boardValue">{{ adminMetrics.labsFree }}</view>
          </view>
          <view class="boardStat">
            <view class="boardLabel">系统用户</view>
            <view class="boardValue">{{ adminMetrics.userTotal }}</view>
          </view>
        </view>

        <view class="boardBars">
          <view class="boardBarRow" v-for="item in adminKpiItems" :key="item.key">
            <view class="rowBetween">
              <view class="boardBarLabel">{{ item.label }}</view>
              <view class="boardBarValue">{{ item.value }}</view>
            </view>
            <view class="boardTrack">
              <view class="boardFill" :class="'tone-' + item.tone" :style="{ width: item.percent + '%' }"></view>
            </view>
          </view>
        </view>
      </view>

      <view class="card feedCard" v-if="!isAdmin" @click="goFeed">
        <view class="rowBetween feedHead">
          <view class="cardTitle">动态</view>
          <view class="feedMore">查看更多</view>
        </view>

        <view v-if="feedLoading" class="feedEmpty">加载中...</view>
        <view v-else-if="previewFeed.length === 0" class="feedEmpty">暂无动态</view>
        <view v-else class="feedPreviewList">
          <view class="feedPreviewItem" v-for="item in previewFeed" :key="item.id">
            <view class="feedPreviewTitle">{{ item.title }}</view>
            <view class="feedPreviewMeta">{{ item.type }} · {{ item.time }}</view>
          </view>
        </view>
      </view>

      <view class="card">
        <view class="rowBetween">
          <view>
            <view class="cardTitle">快捷入口</view>
            <view class="feedMore">最多 {{ maxShortcuts }} 个</view>
          </view>
          <button class="btnSecondary miniBtn" size="mini" @click="toggleShortcutEdit">
            {{ editingShortcuts ? "完成" : "自定义" }}
          </button>
        </view>

        <view class="entryGrid" v-if="entries.length > 0 || editingShortcuts">
          <view class="entryCard" v-for="item in entries" :key="item.key" @click="handleEntryTap(item.key)">
            <view class="entryIcon" :class="'tone-' + item.tone">{{ item.icon }}</view>
            <view class="entryName">{{ item.name }}</view>
            <view class="entryDesc">{{ item.desc }}</view>
            <view class="entryRemove" v-if="editingShortcuts" @click.stop="removeShortcut(item.key)">删</view>
          </view>
          <view class="entryCard entryAddCard" v-if="editingShortcuts && canAddShortcut" @click="openShortcutPicker">
            <view class="entryAddIcon">+</view>
            <view class="entryName">添加</view>
            <view class="entryDesc">选择功能</view>
          </view>
        </view>
        <view class="feedEmpty" v-else>暂无快捷入口</view>
        <view class="feedMore entryEditHint" v-if="editingShortcuts">
          已选 {{ entries.length }} / {{ maxShortcuts }}
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { getWorkbenchOverview } from "@/common/api.js"
import { fetchAnnouncementRows } from "@/common/announcements.js"
import { themePageMixin } from "@/common/theme.js"

const MAX_SHORTCUTS = 6
const PERMISSION_ASSET_READ_BASIC = "asset.read_basic"
const DEFAULT_SHORTCUT_KEYS = {
  admin: ["admin_approve", "admin_labs", "admin_equipments", "admin_lostfound", "admin_users", "notifications"],
  teacher: ["courses", "teacher_assets", "labs", "reserve", "agent", "my"],
  student: ["courses", "labs", "reserve", "agent", "notifications", "my"],
  guest: ["labs", "reserve", "agent", "notifications", "lostfound", "my"]
}

export default {
  mixins: [themePageMixin],
  data() {
    return {
      username: "",
      role: "",
      permissions: [],
      feedList: [],
      feedLoading: false,
      adminPanelLoading: false,
      adminMetrics: {
        labsTotal: 0,
        labsFree: 0,
        userTotal: 0,
        pendingReservations: 0,
        repairPending: 0,
        lostOpen: 0,
        claimPending: 0
      },
      maxShortcuts: MAX_SHORTCUTS,
      editingShortcuts: false,
      shortcutKeys: []
    }
  },
  computed: {
    isAdmin() {
      return this.role === "admin"
    },
    teacherHasAssetReadPermission() {
      return this.role === "teacher" && Array.isArray(this.permissions) && this.permissions.includes(PERMISSION_ASSET_READ_BASIC)
    },
    roleText() {
      if (this.role === "admin") return "管理员"
      if (this.role === "teacher") return "教师"
      if (this.role === "student") return "学生"
      return "访客"
    },
    previewFeed() {
      return this.feedList.slice(0, 2)
    },
    adminKpiItems() {
      const rows = [
        { key: "pendingReservations", label: "待审批预约", value: this.adminMetrics.pendingReservations, tone: "violet" },
        { key: "repairPending", label: "待处理报修", value: this.adminMetrics.repairPending, tone: "amber" },
        { key: "lostOpen", label: "处理中失物", value: this.adminMetrics.lostOpen, tone: "indigo" },
        { key: "claimPending", label: "待审核认领", value: this.adminMetrics.claimPending, tone: "green" }
      ]
      const maxValue = Math.max(...rows.map((item) => Number(item.value || 0)), 1)
      return rows.map((item) => {
        const raw = Number(item.value || 0)
        const percent = raw <= 0 ? 0 : Math.max(12, Math.round((raw / maxValue) * 100))
        return { ...item, percent }
      })
    },
    allEntries() {
      if (this.role === "admin") {
        return [
          { key: "admin_approve", icon: "审", name: "预约审批", desc: "处理待审", tone: "violet" },
          { key: "admin_labs", icon: "室", name: "实验室管理", desc: "新增编辑", tone: "blue" },
          { key: "admin_equipments", icon: "资", name: "资产管理", desc: "设备台账", tone: "green" },
          { key: "admin_lostfound", icon: "失", name: "失物管理", desc: "认领审核", tone: "slate" },
          { key: "admin_users", icon: "户", name: "用户管理", desc: "权限维护", tone: "amber" },
          { key: "notifications", icon: "通", name: "通知中心", desc: "报修提醒", tone: "violet" },
          { key: "admin_audit", icon: "记", name: "审计日志", desc: "操作追踪", tone: "indigo" },
          { key: "admin_stats", icon: "数", name: "后台数据", desc: "统计看板", tone: "green" },
          { key: "agent", icon: "AI", name: "AI助手", desc: "智能问答", tone: "indigo" },
          { key: "my", icon: "我", name: "我的", desc: "账号设置", tone: "amber" }
        ]
      }
      if (this.role === "teacher") {
        return [
          { key: "teacher_assets", icon: "资", name: "资产查询", desc: "只读查看资产", tone: "green" },
          { key: "courses", icon: "课", name: "课程管理", desc: "课程与任务", tone: "violet" },
          { key: "labs", icon: "室", name: "实验室", desc: "查看状态", tone: "blue" },
          { key: "reserve", icon: "约", name: "预约", desc: "提交申请", tone: "green" },
          { key: "agent", icon: "AI", name: "助手", desc: "快速问答", tone: "indigo" },
          { key: "notifications", icon: "通", name: "通知", desc: "消息提醒", tone: "violet" },
          { key: "lostfound", icon: "失", name: "失物招领", desc: "发布认领", tone: "slate" },
          { key: "my", icon: "我", name: "我的", desc: "个人中心", tone: "amber" }
        ]
      }
      return [
        { key: "courses", icon: "课", name: "课程管理", desc: "课程码加入", tone: "violet" },
        { key: "labs", icon: "室", name: "实验室", desc: "查看状态", tone: "blue" },
        { key: "reserve", icon: "约", name: "预约", desc: "提交申请", tone: "green" },
        { key: "agent", icon: "AI", name: "助手", desc: "快速预约", tone: "indigo" },
        { key: "notifications", icon: "通", name: "通知", desc: "消息提醒", tone: "violet" },
        { key: "lostfound", icon: "失", name: "失物招领", desc: "发布认领", tone: "slate" },
        { key: "my", icon: "我", name: "我的", desc: "个人中心", tone: "amber" }
      ]
    },
    entries() {
      const dict = {}
      this.allEntries.forEach((item) => {
        dict[item.key] = item
      })
      return this.shortcutKeys.map((key) => dict[key]).filter(Boolean)
    },
    canAddShortcut() {
      return this.entries.length < this.maxShortcuts
    }
  },
  onShow() {
    const session = uni.getStorageSync("session") || {}
    this.username = session.username || ""
    this.role = session.role || ""
    this.permissions = Array.isArray(session.permissions) ? session.permissions : []
    this.loadShortcutPrefs()
    if (this.isAdmin) {
      this.feedList = []
      this.loadAdminOverview()
      return
    }
    this.loadFeedPreview()
  },
  methods: {
    async loadAdminOverview() {
      if (!this.isAdmin || this.adminPanelLoading) return
      this.adminPanelLoading = true
      try {
        const res = await getWorkbenchOverview()
        const payload = (res && res.data) || {}
        const overview = payload && payload.ok && payload.data ? payload.data : {}
        const metrics = overview && typeof overview.metrics === "object" ? overview.metrics : {}
        this.adminMetrics = {
          labsTotal: Number(metrics.labCount || 0),
          labsFree: Number(metrics.labFreeCount || 0),
          userTotal: Number(metrics.userCount || 0),
          pendingReservations: Number(metrics.pendingCount || 0),
          repairPending: Number(metrics.repairPendingCount || 0),
          lostOpen: Number(metrics.lostOpenCount || 0),
          claimPending: Number(metrics.claimPendingCount || 0)
        }
      } catch (e) {
        this.adminMetrics = {
          labsTotal: 0,
          labsFree: 0,
          userTotal: 0,
          pendingReservations: 0,
          repairPending: 0,
          lostOpen: 0,
          claimPending: 0
        }
      } finally {
        this.adminPanelLoading = false
      }
    },
    getShortcutStorageKey() {
      const username = String(this.username || "guest")
      const role = String(this.role || "guest")
      return `home.shortcuts.${username}.${role}`
    },
    normalizeShortcutKeys(inputKeys) {
      const validKeys = new Set(this.allEntries.map((item) => item.key))
      const result = []
      const source = Array.isArray(inputKeys) ? inputKeys : []
      source.forEach((rawKey) => {
        const key = String(rawKey || "")
        if (!key || !validKeys.has(key)) return
        if (result.includes(key)) return
        result.push(key)
      })
      return result.slice(0, this.maxShortcuts)
    },
    getDefaultShortcutKeys() {
      const role = this.role || "guest"
      const defaults = DEFAULT_SHORTCUT_KEYS[role] || DEFAULT_SHORTCUT_KEYS.guest
      return this.normalizeShortcutKeys(defaults)
    },
    saveShortcutPrefs() {
      const normalized = this.normalizeShortcutKeys(this.shortcutKeys)
      this.shortcutKeys = normalized
      try {
        uni.setStorageSync(this.getShortcutStorageKey(), normalized)
      } catch (e) {}
    },
    loadShortcutPrefs() {
      let storedKeys = []
      try {
        const raw = uni.getStorageSync(this.getShortcutStorageKey())
        if (Array.isArray(raw)) {
          storedKeys = raw
        } else if (typeof raw === "string" && raw) {
          const parsed = JSON.parse(raw)
          if (Array.isArray(parsed)) storedKeys = parsed
        }
      } catch (e) {}

      const normalizedStored = this.normalizeShortcutKeys(storedKeys)
      const defaultKeys = this.getDefaultShortcutKeys()
      let finalKeys = normalizedStored.length > 0 ? normalizedStored : defaultKeys
      if (this.role === "teacher" && !finalKeys.includes("courses")) {
        finalKeys = ["courses", ...finalKeys.filter((key) => key !== "courses")]
      }
      if (this.role === "teacher" && !finalKeys.includes("teacher_assets")) {
        finalKeys = ["courses", "teacher_assets", ...finalKeys.filter((key) => key !== "courses" && key !== "teacher_assets")].slice(0, this.maxShortcuts)
      }
      this.shortcutKeys = this.normalizeShortcutKeys(finalKeys)
      this.editingShortcuts = false
      this.saveShortcutPrefs()
    },
    toggleShortcutEdit() {
      this.editingShortcuts = !this.editingShortcuts
    },
    handleEntryTap(key) {
      if (!key) return
      if (this.editingShortcuts) return
      this.openEntry(key)
    },
    addShortcut(key) {
      if (!key || this.shortcutKeys.includes(key)) return
      if (this.shortcutKeys.length >= this.maxShortcuts) {
        uni.showToast({ title: `最多添加${this.maxShortcuts}个`, icon: "none" })
        return
      }
      this.shortcutKeys = [...this.shortcutKeys, key]
      this.saveShortcutPrefs()
    },
    removeShortcut(key) {
      this.shortcutKeys = this.shortcutKeys.filter((itemKey) => itemKey !== key)
      this.saveShortcutPrefs()
    },
    openShortcutPicker() {
      if (!this.canAddShortcut) {
        uni.showToast({ title: `最多添加${this.maxShortcuts}个`, icon: "none" })
        return
      }
      const selected = new Set(this.shortcutKeys)
      const options = this.allEntries.filter((item) => !selected.has(item.key))
      if (options.length === 0) {
        uni.showToast({ title: "没有可添加入口", icon: "none" })
        return
      }
      uni.showActionSheet({
        itemList: options.map((item) => `${item.name}（${item.desc}）`),
        success: (res) => {
          const picked = options[Number(res.tapIndex || 0)]
          if (!picked) return
          this.addShortcut(picked.key)
        }
      })
    },
    async loadFeedPreview() {
      if (this.feedLoading) return
      this.feedLoading = true
      try {
        const result = await fetchAnnouncementRows({ limit: 5, retries: 1, maxAgeMs: 5 * 60 * 1000 })
        const rows = Array.isArray(result && result.rows) ? result.rows : []
        this.feedList = rows.map((row) => ({
          id: `announcement-${row.id}`,
          type: "系统公告",
          title: row.title || "未命名公告",
          time: row.createdAt || "-"
        }))
      } catch (e) {
        this.feedList = []
      } finally {
        this.feedLoading = false
      }
    },
    openEntry(key) {
      if (key === "admin_approve") return this.goApprove()
      if (key === "admin_labs") return this.goAdminLabs()
      if (key === "admin_equipments") return this.goAdminEquipments()
      if (key === "admin_lostfound") return this.goAdminLostFound()
      if (key === "admin_users") return this.goAdminUsers()
      if (key === "admin_audit") return this.goAdminAudit()
      if (key === "admin_stats") return this.goAdminStats()
      if (key === "courses") return this.goTeacherCourses()
      if (key === "teacher_assets") return this.goTeacherAssets()
      if (key === "labs") return this.goLabs()
      if (key === "reserve") return this.goReserve()
      if (key === "agent") return this.goAgent()
      if (key === "notifications") return this.goNotifications()
      if (key === "lostfound") return this.goLostFound()
      if (key === "my") return this.goMy()
    },
    goApprove() {
      uni.navigateTo({ url: "/pages/admin/approve" })
    },
    goAdminLabs() {
      uni.navigateTo({ url: "/pages/admin/labs" })
    },
    goAdminEquipments() {
      uni.navigateTo({ url: "/pages/admin/equipments" })
    },
    goAdminLostFound() {
      uni.navigateTo({ url: "/pages/admin/lostfound" })
    },
    goAdminUsers() {
      uni.navigateTo({ url: "/pages/admin/users" })
    },
    goAdminAudit() {
      uni.navigateTo({ url: "/pages/admin/audit" })
    },
    goAdminStats() {
      uni.navigateTo({ url: "/pages/admin/stats" })
    },
    goTeacherCourses() {
      uni.navigateTo({ url: "/pages/teacher/courses" })
    },
    goTeacherAssets() {
      uni.navigateTo({ url: "/pages/teacher/assets" })
    },
    goLabs() {
      uni.navigateTo({ url: "/pages/labs/labs" })
    },
    goReserve() {
      uni.navigateTo({ url: "/pages/reserve/reserve" })
    },
    goAgent() {
      uni.switchTab({ url: "/pages/agent/agent" })
    },
    goFeed() {
      uni.navigateTo({ url: "/pages/feed/feed" })
    },
    goNotifications() {
      uni.navigateTo({ url: "/pages/notifications/list" })
    },
    goLostFound() {
      uni.navigateTo({ url: "/pages/lostfound/list" })
    },
    goMy() {
      uni.switchTab({ url: "/pages/my/my" })
    }
  }
}
</script>

<style lang="scss">
.portalPage {
  padding-bottom: 20px;
}

.heroCard {
  border: 1px solid var(--color-border-focus);
  background: var(--color-bg-soft);
}

.heroBadge {
  width: fit-content;
  height: 22px;
  line-height: 22px;
  border-radius: 999px;
  padding: 0 10px;
  font-size: 11px;
  font-weight: 600;
  color: var(--info);
  background: var(--color-info-soft);
  border: 1px solid var(--color-border-primary);
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
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-primary);
  color: var(--color-text-secondary);
  font-size: 11px;
}

.adminBoard {
  border: 1px solid var(--color-border-primary);
  background: linear-gradient(160deg, var(--color-bg-card) 0%, var(--color-bg-soft) 100%);
}

.boardHead {
  align-items: flex-start;
}

.boardTop {
  margin-top: 10px;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.boardStat {
  border: 1px solid var(--color-border-primary);
  border-radius: 10px;
  background: var(--color-bg-card);
  padding: 8px;
}

.boardLabel {
  font-size: 11px;
  color: var(--color-text-muted);
}

.boardValue {
  margin-top: 4px;
  font-size: 19px;
  line-height: 1.2;
  font-weight: 700;
  color: var(--color-text-primary);
}

.boardBars {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.boardBarLabel {
  font-size: 12px;
  color: var(--color-text-secondary);
}

.boardBarValue {
  font-size: 12px;
  color: var(--color-text-primary);
  font-weight: 700;
}

.boardTrack {
  margin-top: 4px;
  width: 100%;
  height: 8px;
  border-radius: 999px;
  background: var(--color-bg-soft);
  overflow: hidden;
}

.boardFill {
  height: 100%;
  border-radius: 999px;
}

.boardFill.tone-violet {
  background: #6366f1;
}

.boardFill.tone-amber {
  background: #f59e0b;
}

.boardFill.tone-indigo {
  background: #3b82f6;
}

.boardFill.tone-green {
  background: #16a34a;
}

.feedCard {
  border: 1px solid var(--color-border-primary);
}

.feedHead {
  align-items: center;
}

.feedMore {
  font-size: 12px;
  color: var(--color-text-muted);
}

.miniBtn {
  min-height: 30px;
  line-height: 30px;
  padding: 0 10px;
  border-radius: 9px;
  font-size: 12px;
}

.entryEditHint {
  margin-top: 8px;
}

.feedEmpty {
  margin-top: 10px;
  font-size: 12px;
  color: var(--color-text-muted);
}

.feedPreviewList {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.feedPreviewItem {
  border: 1px solid var(--color-border-primary);
  border-radius: 10px;
  padding: 8px;
  background: var(--color-bg-card);
}

.feedPreviewTitle {
  font-size: 13px;
  line-height: 18px;
  color: var(--color-text-primary);
  font-weight: 600;
}

.feedPreviewMeta {
  margin-top: 4px;
  font-size: 11px;
  line-height: 16px;
  color: var(--color-text-muted);
}

.entryGrid {
  margin-top: 10px;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.entryCard {
  position: relative;
  border: 1px solid var(--color-border-primary);
  border-radius: 10px;
  background: var(--color-bg-card);
  padding: 8px;
  transition: transform 0.14s ease, box-shadow 0.14s ease;
}

.entryCard:active {
  transform: scale(0.985);
  box-shadow: var(--shadow-sm);
}

.entryIcon {
  width: 24px;
  height: 24px;
  border-radius: 7px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
}

.entryIcon.tone-blue {
  color: var(--info);
  background: var(--color-info-soft);
}

.entryIcon.tone-green {
  color: var(--success);
  background: var(--color-success-soft);
}

.entryIcon.tone-amber {
  color: var(--warning);
  background: var(--color-warning-soft);
}

.entryIcon.tone-indigo {
  color: var(--info);
  background: var(--color-info-soft);
}

.entryIcon.tone-violet {
  color: var(--info);
  background: var(--color-info-soft);
}

.entryIcon.tone-slate {
  color: var(--color-text-secondary);
  background: var(--color-bg-soft);
}

.entryName {
  margin-top: 6px;
  font-size: 12px;
  line-height: 16px;
  font-weight: 700;
  color: var(--color-text-primary);
}

.entryDesc {
  margin-top: 2px;
  font-size: 10px;
  line-height: 14px;
  color: var(--color-text-muted);
}

.entryRemove {
  position: absolute;
  top: 4px;
  left: 4px;
  min-width: 16px;
  height: 16px;
  line-height: 16px;
  border-radius: 999px;
  background: #fee2e2;
  color: #b91c1c;
  text-align: center;
  font-size: 10px;
  padding: 0 4px;
  box-sizing: border-box;
}

.entryAddCard {
  border-style: dashed;
  background: var(--color-bg-soft);
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
}

.entryAddIcon {
  width: 24px;
  height: 24px;
  border-radius: 7px;
  border: 1px dashed var(--color-border-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-secondary);
  font-size: 14px;
}
</style>

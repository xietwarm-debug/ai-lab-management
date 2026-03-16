<template>
  <view class="container schedulePage">
    <view class="stack">
      <view class="card heroCard">
        <view class="rowBetween heroTop">
          <view>
            <view class="title">课表管理</view>
            <view class="subtitle">学期课表导入、启用与开门提醒</view>
          </view>
          <view class="heroActions">
            <button class="btnPrimary miniBtn" size="mini" @click="goImport">导入课表</button>
            <button class="btnSecondary miniBtn" size="mini" @click="loadAll">刷新</button>
          </view>
        </view>
        <view class="heroMeta muted">当前启用模板：{{ activeTemplate ? activeTemplate.termName || ("模板#" + activeTemplate.id) : "未启用" }}</view>
        <view class="heroMeta muted">今日待开门：{{ pendingCount }}</view>
      </view>

      <view class="metricGrid">
        <view class="card metricCard">
          <view class="metricLabel">模板总数</view>
          <view class="metricValue">{{ templates.length }}</view>
        </view>
        <view class="card metricCard">
          <view class="metricLabel">今日提醒总数</view>
          <view class="metricValue">{{ todayList.length }}</view>
        </view>
        <view class="card metricCard">
          <view class="metricLabel">待处理</view>
          <view class="metricValue warning">{{ pendingCount }}</view>
        </view>
      </view>

      <view class="card">
        <view class="rowBetween">
          <view class="cardTitle">快捷入口</view>
        </view>
        <view class="chipRow">
          <view class="chip chipOn" @click="goToday">今日开门提醒</view>
          <view class="chip" @click="goLogs">提醒记录</view>
          <view class="chip" @click="goWeekOverview">当周课表总览</view>
        </view>
      </view>

      <view class="card">
        <view class="rowBetween">
          <view class="cardTitle">课表模板</view>
          <view class="muted">共 {{ templates.length }} 条</view>
        </view>
        <view v-if="templates.length === 0" class="empty">暂无模板，先导入课表</view>
        <view v-else class="list">
          <view class="rowItem" v-for="item in templates" :key="item.id">
            <view>
              <view class="rowTitle">{{ item.termName || ("模板#" + item.id) }}</view>
              <view class="rowMeta">开学：{{ item.semesterStartDate || "-" }} · 周数：{{ item.semesterWeeks || "-" }} · 明细：{{ item.itemCount || 0 }}</view>
              <view class="rowMeta">状态：{{ item.status === "active" ? "启用中" : item.status || "-" }} · 提前提醒：{{ item.reminderLeadMinutes || 20 }} 分钟</view>
            </view>
            <view class="rowActions">
              <button v-if="item.status !== 'active'" class="btnSecondary miniBtn" size="mini" :loading="activatingId===item.id" @click="activate(item)">设为启用</button>
              <view v-else class="statusTag success">当前启用</view>
              <button class="btnSecondary miniBtn" size="mini" @click="editTemplate(item)">编辑</button>
              <button class="btnDanger miniBtn" size="mini" :loading="deletingId===item.id" @click="deleteTemplate(item)">删除</button>
            </view>
          </view>
        </view>
      </view>

      <view class="card">
        <view class="rowBetween">
          <view class="cardTitle">实验室课表详情</view>
          <view class="muted">点击查看本周安排</view>
        </view>
        <view v-if="labs.length===0" class="empty">暂无实验室数据</view>
        <view v-else class="chipRow">
          <view class="chip" v-for="lab in labs" :key="lab.id" @click="goLabDetail(lab.id)">
            {{ lab.name || ("LAB-" + lab.id) }}
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import {
  adminListScheduleTemplates,
  adminActivateScheduleTemplate,
  adminDeleteScheduleTemplate,
  adminGetDoorRemindersToday,
  getApiListData,
  listLabs
} from "@/common/api.js"

function ensureAdmin() {
  const s = uni.getStorageSync("session")
  return !!(s && s.role === "admin")
}

export default {
  data() {
    return {
      templates: [],
      labs: [],
      todayList: [],
      loading: false,
      activatingId: 0,
      deletingId: 0
    }
  },
  computed: {
    activeTemplate() {
      return this.templates.find((x) => x && x.status === "active") || null
    },
    pendingCount() {
      return this.todayList.filter((x) => String((x || {}).doorStatus || "") === "pending").length
    }
  },
  onShow() {
    if (!ensureAdmin()) {
      uni.showToast({ title: "无权限", icon: "none" })
      uni.reLaunch({ url: "/pages/login/login" })
      return
    }
    this.loadAll()
  },
  methods: {
    async loadAll() {
      if (this.loading) return
      this.loading = true
      try {
        const [tplRes, todayRes, labsRes] = await Promise.all([
          adminListScheduleTemplates(),
          adminGetDoorRemindersToday(""),
          listLabs({})
        ])
        const tplPayload = (tplRes && tplRes.data) || {}
        this.templates = tplPayload.ok && Array.isArray(tplPayload.data) ? tplPayload.data : []
        const todayPayload = (todayRes && todayRes.data) || {}
        this.todayList = todayPayload.ok && todayPayload.data && Array.isArray(todayPayload.data.list) ? todayPayload.data.list : []
        this.labs = getApiListData(labsRes && labsRes.data)
      } catch (e) {
        uni.showToast({ title: "加载失败", icon: "none" })
      } finally {
        this.loading = false
      }
    },
    async activate(item) {
      if (!item || !item.id || this.activatingId) return
      this.activatingId = item.id
      try {
        const res = await adminActivateScheduleTemplate(item.id)
        const payload = (res && res.data) || {}
        if (!payload.ok) {
          uni.showToast({ title: payload.msg || "启用失败", icon: "none" })
          return
        }
        uni.showToast({ title: "已启用", icon: "none" })
        this.loadAll()
      } catch (e) {
        uni.showToast({ title: "启用失败", icon: "none" })
      } finally {
        this.activatingId = 0
      }
    },
    deleteTemplate(item) {
      if (!item || !item.id || this.deletingId) return
      uni.showModal({
        title: "删除课表模板",
        content: `确定删除“${item.termName || ("模板#" + item.id)}”？\n将同时删除该模板下的课表明细与开门提醒记录。`,
        success: async (m) => {
          if (!m.confirm) return
          this.deletingId = item.id
          try {
            const res = await adminDeleteScheduleTemplate(item.id)
            const payload = (res && res.data) || {}
            if (!payload.ok) {
              uni.showToast({ title: payload.msg || "删除失败", icon: "none" })
              return
            }
            const data = payload.data || {}
            const activated = Number(data.fallbackActivatedTemplateId || 0)
            if (activated > 0) {
              uni.showToast({ title: `已删除，自动启用模板#${activated}`, icon: "none" })
            } else {
              uni.showToast({ title: "模板已删除", icon: "none" })
            }
            this.loadAll()
          } catch (e) {
            uni.showToast({ title: "删除失败", icon: "none" })
          } finally {
            this.deletingId = 0
          }
        }
      })
    },
    goImport() {
      uni.navigateTo({ url: "/pages/admin/schedule_import" })
    },
    editTemplate(item) {
      if (!item || !item.id) return
      uni.navigateTo({ url: `/pages/admin/schedule_import?templateId=${encodeURIComponent(String(item.id))}` })
    },
    goToday() {
      uni.navigateTo({ url: "/pages/admin/door_reminders_today" })
    },
    goLogs() {
      uni.navigateTo({ url: "/pages/admin/door_reminder_logs" })
    },
    goWeekOverview() {
      uni.navigateTo({ url: "/pages/admin/schedule_week_overview" })
    },
    goLabDetail(labId) {
      if (!labId) return
      uni.navigateTo({ url: `/pages/admin/lab_schedule_detail?labId=${encodeURIComponent(String(labId))}` })
    }
  }
}
</script>

<style lang="scss">
.schedulePage {
  padding-bottom: 20px;
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
}

.heroMeta {
  margin-top: 6px;
}

.miniBtn {
  min-height: 30px;
  line-height: 30px;
  padding: 0 10px;
  border-radius: 9px;
  font-size: 12px;
}

.metricGrid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.metricCard {
  min-height: 84px;
}

.metricLabel {
  font-size: 12px;
  color: #64748b;
}

.metricValue {
  margin-top: 4px;
  font-size: 23px;
  font-weight: 700;
  color: #0f172a;
}

.metricValue.warning {
  color: #b45309;
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

.list {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.rowItem {
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 10px;
  padding: 10px;
  display: flex;
  justify-content: space-between;
  gap: 10px;
}

.rowActions {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
}

.rowTitle {
  font-size: 13px;
  color: #0f172a;
  font-weight: 700;
}

.rowMeta {
  margin-top: 4px;
  font-size: 12px;
  color: #64748b;
}

.empty {
  margin-top: 8px;
  font-size: 12px;
  color: #94a3b8;
}
</style>

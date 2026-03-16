<template>
  <view class="container todoPage">
    <view class="stack">
      <view class="card heroCard">
        <view class="rowBetween heroTop">
          <view>
            <view class="title">管理员待办中心</view>
            <view class="subtitle">卡片化工作台：审批、工单、告警、认领、课程任务、公告计划</view>
          </view>
          <button class="btnSecondary miniBtn" size="mini" :loading="loading" @click="fetchTodos">刷新</button>
        </view>
        <view class="heroMeta muted">更新时间：{{ generatedAt || "-" }}</view>
      </view>

      <view class="card briefCard">
        <view class="rowBetween sectionHead">
          <view>
            <view class="cardTitle">AI 日报</view>
            <view class="muted tiny">{{ dailyBrief.generatedAt || "-" }}</view>
          </view>
          <button class="btnSecondary miniBtn" size="mini" :loading="briefLoading" @click="fetchAiBrief">刷新摘要</button>
        </view>
        <view class="muted" v-if="briefLoading && !dailyBrief.summaryText">正在生成今日摘要...</view>
        <view class="briefSummary" v-else>{{ dailyBrief.summaryText || "暂无摘要" }}</view>
        <view class="briefList" v-if="dailyBrief.highlights.length > 0">
          <view class="briefItem" v-for="(item, idx) in dailyBrief.highlights" :key="'brief-' + idx">{{ item }}</view>
        </view>
        <view class="chipRow" v-if="dailyBrief.focusActions.length > 0">
          <view class="chip" v-for="(item, idx) in dailyBrief.focusActions" :key="'focus-' + idx" @click="item.jumpUrl && uni.navigateTo({ url: item.jumpUrl })">
            {{ item.title }}
          </view>
        </view>
      </view>

      <view class="metricGrid">
        <view class="card metricCard">
          <view class="metricLabel">待办总量</view>
          <view class="metricValue">{{ summary.total }}</view>
        </view>
        <view class="card metricCard">
          <view class="metricLabel">超时总量</view>
          <view class="metricValue danger">{{ summary.timeoutTotal }}</view>
        </view>
        <view class="card metricCard">
          <view class="metricLabel">高优先级</view>
          <view class="metricValue warning">{{ summary.highPriorityTotal }}</view>
        </view>
      </view>

      <view class="card">
        <view class="cardTitle">排序与显示</view>
        <view class="chipRow">
          <view
            v-for="item in sortByOptions"
            :key="item.value"
            class="chip"
            :class="{ chipOn: sortBy === item.value }"
            @click="setSortBy(item.value)"
          >
            {{ item.label }}
          </view>
        </view>
        <view class="chipRow">
          <view
            v-for="item in sortOrderOptions"
            :key="item.value"
            class="chip"
            :class="{ chipOn: sortOrder === item.value }"
            @click="setSortOrder(item.value)"
          >
            {{ item.label }}
          </view>
          <view class="chip" :class="{ chipOn: showDone }" @click="toggleShowDone">
            {{ showDone ? "隐藏已标记完成" : "显示已标记完成" }}
          </view>
        </view>
      </view>

      <view class="card" v-if="loading">
        <view class="muted">正在加载待办...</view>
      </view>

      <view class="card todoCard" v-for="card in displayCards" :key="card.key" v-else>
        <view class="rowBetween sectionHead">
          <view>
            <view class="cardTitle">{{ card.title }}</view>
            <view class="muted">{{ card.description }}</view>
            <view class="muted tiny">总量 {{ card.total }} · 超时 {{ card.timeoutCount }} · 显示 {{ card.visibleCount }}</view>
          </view>
          <view class="rowBetween topActions">
            <button class="btnSecondary miniBtn" size="mini" @click="jumpCard(card)">一键跳转</button>
            <button class="btnPrimary miniBtn" size="mini" :loading="isCardProcessing(card.key)" @click="processCard(card)">
              一键批量处理
            </button>
          </view>
        </view>

        <view class="chipRow">
          <view class="chip" @click="toggleSelectAll(card)">{{ isCardAllSelected(card) ? "取消全选" : "全选当前卡片" }}</view>
          <view class="chip" @click="clearSelection(card.key)">清空选择</view>
          <view class="chip" @click="markTimeoutBatch(card, true)">超时标记</view>
          <view class="chip" @click="markTimeoutBatch(card, false)">取消超时</view>
          <view class="chip" @click="markDoneBatch(card, true)">标记完成</view>
          <view class="chip" @click="markDoneBatch(card, false)">取消完成</view>
          <view class="muted">已选 {{ selectedCount(card.key) }}</view>
        </view>

        <view class="itemList" v-if="card.items.length > 0">
          <view class="itemRow" v-for="item in card.items" :key="item.id">
            <view class="rowBetween">
              <view class="itemHead">
                <view class="selectBox" :class="{ on: isSelected(card.key, item.entityId) }" @click="toggleSelect(card.key, item.entityId)">
                  {{ isSelected(card.key, item.entityId) ? "✓" : "" }}
                </view>
                <view>
                  <view class="itemTitle">{{ item.title }}</view>
                  <view class="itemSub">{{ item.subtitle || "-" }}</view>
                </view>
              </view>
              <view class="tagWrap">
                <view class="priorityTag" :class="priorityTone(item.effectivePriority)">{{ item.priorityLevel }}</view>
                <view class="timeoutTag" v-if="item.effectiveTimeout">超时</view>
                <view class="doneTag" v-if="item.manualDone">已完成</view>
              </view>
            </view>
            <view class="itemMeta">创建：{{ item.createdAt || "-" }}<text v-if="item.deadlineAt"> · 截止：{{ item.deadlineAt }}</text></view>
            <view class="itemMeta" v-if="item.detail">{{ item.detail }}</view>
            <view class="rowBetween itemActions">
              <button class="btnSecondary miniBtn" size="mini" @click="jumpItem(item)">跳转</button>
              <view class="rowBetween">
                <button class="btnSecondary miniBtn" size="mini" @click="toggleTimeout(item)">{{ item.manualTimeout ? "取消超时标记" : "超时标记" }}</button>
                <button class="btnSecondary miniBtn" size="mini" @click="toggleDone(item)">{{ item.manualDone ? "取消完成" : "标记完成" }}</button>
                <button class="btnPrimary miniBtn" size="mini" :loading="isItemProcessing(item.id)" @click="processSingle(item)">处理</button>
              </view>
            </view>
          </view>
        </view>
        <view class="empty" v-else>当前卡片暂无待办</view>
      </view>
    </view>
  </view>
</template>

<script>
import { BASE_URL, adminGetAiDailyBrief } from "@/common/api.js"

function toInt(value, fallback = 0) {
  const n = Number(value)
  return Number.isFinite(n) ? Math.round(n) : fallback
}

function nowTimeText() {
  const d = new Date()
  const p = (n) => (n < 10 ? `0${n}` : `${n}`)
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`
}

function toDateNum(value) {
  const text = String(value || "").trim().replace(" ", "T")
  const t = Date.parse(text)
  return Number.isFinite(t) ? t : 0
}

function safeArray(value) {
  return Array.isArray(value) ? value : []
}

function newMarkState() {
  return { timeout: {}, done: {} }
}

function newDailyBrief() {
  return {
    generatedAt: "",
    summaryText: "",
    riskLevel: "low",
    highlights: [],
    focusActions: []
  }
}

export default {
  data() {
    return {
      loading: false,
      briefLoading: false,
      generatedAt: "",
      dailyBrief: newDailyBrief(),
      sortBy: "priority",
      sortOrder: "desc",
      showDone: false,
      cards: [],
      summary: { total: 0, timeoutTotal: 0, highPriorityTotal: 0 },
      selectedMap: {},
      markState: newMarkState(),
      processingCardMap: {},
      processingItemMap: {},
      userName: "",
      sortByOptions: [
        { label: "按优先级", value: "priority" },
        { label: "按截止时间", value: "deadline" },
        { label: "按创建时间", value: "createdAt" }
      ],
      sortOrderOptions: [
        { label: "降序", value: "desc" },
        { label: "升序", value: "asc" }
      ]
    }
  },
  computed: {
    displayCards() {
      return safeArray(this.cards).map((card) => {
        const key = String((card || {}).key || "")
        const rows = this.enrichItems((card || {}).items || [])
        const visible = this.showDone ? rows : rows.filter((x) => !x.manualDone)
        const sorted = this.sortItems(visible)
        return {
          ...card,
          key,
          items: sorted,
          visibleCount: sorted.length
        }
      })
    }
  },
  onShow() {
    const s = uni.getStorageSync("session")
    if (!s || s.role !== "admin") {
      uni.showToast({ title: "无权限", icon: "none" })
      uni.reLaunch({ url: "/pages/login/login" })
      return
    }
    this.userName = String(s.username || "").trim()
    this.loadMarks()
    this.fetchTodos()
    this.fetchAiBrief()
  },
  methods: {
    markKey(item) {
      const category = String((item || {}).category || "")
      const entityId = toInt((item || {}).entityId, 0)
      return `${category}:${entityId}`
    },
    marksStorageKey() {
      return `admin_todo_marks_${this.userName || "default"}`
    },
    loadMarks() {
      try {
        const raw = uni.getStorageSync(this.marksStorageKey())
        if (!raw || typeof raw !== "object") {
          this.markState = newMarkState()
          return
        }
        this.markState = {
          timeout: typeof raw.timeout === "object" && raw.timeout ? raw.timeout : {},
          done: typeof raw.done === "object" && raw.done ? raw.done : {}
        }
      } catch (e) {
        this.markState = newMarkState()
      }
    },
    saveMarks() {
      uni.setStorageSync(this.marksStorageKey(), this.markState)
    },
    setSortBy(value) {
      if (this.sortBy === value) return
      this.sortBy = value
      this.fetchTodos()
    },
    setSortOrder(value) {
      if (this.sortOrder === value) return
      this.sortOrder = value
      this.fetchTodos()
    },
    toggleShowDone() {
      this.showDone = !this.showDone
    },
    isCardProcessing(key) {
      return !!this.processingCardMap[String(key || "")]
    },
    isItemProcessing(itemId) {
      return !!this.processingItemMap[String(itemId || "")]
    },
    enrichItems(items) {
      return safeArray(items).map((item) => {
        const markKey = this.markKey(item)
        const manualTimeout = !!this.markState.timeout[markKey]
        const manualDone = !!this.markState.done[markKey]
        const basePriority = toInt(item.priorityScore, 0)
        const effectivePriority = basePriority + (manualTimeout ? 8 : 0) - (manualDone ? 20 : 0)
        const effectiveTimeout = !!item.timeout || manualTimeout
        return {
          ...item,
          manualTimeout,
          manualDone,
          effectivePriority,
          effectiveTimeout
        }
      })
    },
    sortItems(items) {
      const rows = safeArray(items).slice()
      const by = this.sortBy
      const order = this.sortOrder
      if (by === "priority") {
        rows.sort((a, b) => {
          const pa = toInt(a.effectivePriority, 0)
          const pb = toInt(b.effectivePriority, 0)
          if (pa !== pb) return order === "asc" ? pa - pb : pb - pa
          const da = toDateNum(a.deadlineAt || a.createdAt)
          const db = toDateNum(b.deadlineAt || b.createdAt)
          return da - db
        })
        return rows
      }
      if (by === "deadline") {
        rows.sort((a, b) => {
          const da = toDateNum(a.deadlineAt || a.createdAt)
          const db = toDateNum(b.deadlineAt || b.createdAt)
          return order === "asc" ? da - db : db - da
        })
        return rows
      }
      rows.sort((a, b) => {
        const da = toDateNum(a.createdAt)
        const db = toDateNum(b.createdAt)
        return order === "asc" ? da - db : db - da
      })
      return rows
    },
    priorityTone(score) {
      const n = toInt(score, 0)
      if (n >= 90) return "p0"
      if (n >= 75) return "p1"
      if (n >= 60) return "p2"
      return "p3"
    },
    async fetchAiBrief() {
      if (this.briefLoading) return
      this.briefLoading = true
      try {
        const res = await adminGetAiDailyBrief()
        const payload = (res && res.data) || {}
        if (!payload.ok || !payload.data) {
          this.dailyBrief = newDailyBrief()
          return
        }
        this.dailyBrief = {
          ...newDailyBrief(),
          ...(payload.data || {}),
          highlights: safeArray((payload.data || {}).highlights),
          focusActions: safeArray((payload.data || {}).focusActions)
        }
      } catch (e) {
        this.dailyBrief = newDailyBrief()
      } finally {
        this.briefLoading = false
      }
    },
    async fetchTodos() {
      if (this.loading) return
      this.loading = true
      try {
        const query = `sortBy=${encodeURIComponent(this.sortBy)}&sortOrder=${encodeURIComponent(this.sortOrder)}&limitPerCard=60`
        const res = await uni.request({
          url: `${BASE_URL}/admin/todo-center?${query}`,
          method: "GET"
        })
        const payload = (res && res.data) || {}
        if (!payload.ok || !payload.data) {
          uni.showToast({ title: payload.msg || "加载失败", icon: "none" })
          return
        }
        this.cards = safeArray(payload.data.cards)
        this.summary = payload.data.summary || { total: 0, timeoutTotal: 0, highPriorityTotal: 0 }
        this.generatedAt = String(payload.data.generatedAt || "")
        this.cleanSelection()
      } catch (e) {
        uni.showToast({ title: "加载失败", icon: "none" })
      } finally {
        this.loading = false
      }
    },
    cleanSelection() {
      const next = {}
      this.displayCards.forEach((card) => {
        const key = String(card.key || "")
        const valid = new Set(safeArray(card.items).map((x) => toInt(x.entityId, 0)))
        const selected = safeArray(this.selectedMap[key]).map((x) => toInt(x, 0)).filter((x) => valid.has(x))
        next[key] = selected
      })
      this.selectedMap = next
    },
    selectedCount(cardKey) {
      const key = String(cardKey || "")
      return safeArray(this.selectedMap[key]).length
    },
    isSelected(cardKey, entityId) {
      const key = String(cardKey || "")
      const id = toInt(entityId, 0)
      return safeArray(this.selectedMap[key]).includes(id)
    },
    toggleSelect(cardKey, entityId) {
      const key = String(cardKey || "")
      const id = toInt(entityId, 0)
      const list = safeArray(this.selectedMap[key]).slice()
      const idx = list.indexOf(id)
      if (idx >= 0) list.splice(idx, 1)
      else list.push(id)
      this.$set(this.selectedMap, key, list)
    },
    clearSelection(cardKey) {
      const key = String(cardKey || "")
      this.$set(this.selectedMap, key, [])
    },
    isCardAllSelected(card) {
      const key = String((card || {}).key || "")
      const ids = safeArray((card || {}).items).map((x) => toInt(x.entityId, 0)).filter((x) => x > 0)
      if (!ids.length) return false
      const selected = new Set(safeArray(this.selectedMap[key]).map((x) => toInt(x, 0)))
      return ids.every((id) => selected.has(id))
    },
    toggleSelectAll(card) {
      const key = String((card || {}).key || "")
      const ids = safeArray((card || {}).items).map((x) => toInt(x.entityId, 0)).filter((x) => x > 0)
      if (!ids.length) return
      if (this.isCardAllSelected(card)) {
        this.$set(this.selectedMap, key, [])
        return
      }
      this.$set(this.selectedMap, key, ids)
    },
    resolveTargets(card) {
      const key = String((card || {}).key || "")
      const rows = safeArray((card || {}).items)
      const selected = new Set(safeArray(this.selectedMap[key]).map((x) => toInt(x, 0)))
      const useSelected = selected.size > 0
      return rows.filter((x) => {
        const id = toInt(x.entityId, 0)
        if (id <= 0) return false
        if (!useSelected) return true
        return selected.has(id)
      })
    },
    toggleTimeout(item) {
      const key = this.markKey(item)
      if (this.markState.timeout[key]) delete this.markState.timeout[key]
      else this.$set(this.markState.timeout, key, true)
      this.markState = { ...this.markState, timeout: { ...this.markState.timeout } }
      this.saveMarks()
    },
    toggleDone(item) {
      const key = this.markKey(item)
      if (this.markState.done[key]) delete this.markState.done[key]
      else this.$set(this.markState.done, key, true)
      this.markState = { ...this.markState, done: { ...this.markState.done } }
      this.saveMarks()
    },
    markTimeoutBatch(card, flag) {
      const targets = this.resolveTargets(card)
      if (!targets.length) {
        uni.showToast({ title: "没有可操作项", icon: "none" })
        return
      }
      targets.forEach((item) => {
        const key = this.markKey(item)
        if (flag) this.$set(this.markState.timeout, key, true)
        else delete this.markState.timeout[key]
      })
      this.markState = { ...this.markState, timeout: { ...this.markState.timeout } }
      this.saveMarks()
      uni.showToast({ title: flag ? "已标记超时" : "已取消超时", icon: "none" })
    },
    markDoneBatch(card, flag) {
      const targets = this.resolveTargets(card)
      if (!targets.length) {
        uni.showToast({ title: "没有可操作项", icon: "none" })
        return
      }
      targets.forEach((item) => {
        const key = this.markKey(item)
        if (flag) this.$set(this.markState.done, key, true)
        else delete this.markState.done[key]
      })
      this.markState = { ...this.markState, done: { ...this.markState.done } }
      this.saveMarks()
      uni.showToast({ title: flag ? "已标记完成" : "已取消完成", icon: "none" })
    },
    jumpCard(card) {
      const url = String((card || {}).jumpUrl || "").trim()
      if (!url) return
      uni.navigateTo({ url })
    },
    jumpItem(item) {
      const url = String((item || {}).jumpUrl || "").trim()
      if (!url) return
      uni.navigateTo({ url })
    },
    markProcessedDone(items) {
      safeArray(items).forEach((item) => {
        const key = this.markKey(item)
        this.$set(this.markState.done, key, true)
      })
      this.markState = { ...this.markState, done: { ...this.markState.done } }
      this.saveMarks()
    },
    async processSingle(item) {
      const card = this.displayCards.find((x) => safeArray(x.items).some((it) => it.id === item.id))
      if (!card) return
      this.$set(this.processingItemMap, String(item.id), true)
      try {
        const result = await this.processItems(card.key, [item])
        if (safeArray(result.processedEntityIds).includes(toInt(item.entityId, 0))) {
          this.markProcessedDone([item])
        }
        uni.showToast({ title: result.failed > 0 ? `成功${result.success} 失败${result.failed}` : "处理成功", icon: "none" })
        this.fetchTodos()
      } finally {
        this.$delete(this.processingItemMap, String(item.id))
      }
    },
    async processCard(card) {
      const key = String((card || {}).key || "")
      const targets = this.resolveTargets(card)
      if (!targets.length) {
        uni.showToast({ title: "没有可处理项", icon: "none" })
        return
      }
      uni.showModal({
        title: "确认批量处理",
        content: `将处理 ${targets.length} 条待办，是否继续？`,
        success: async (m) => {
          if (!m.confirm) return
          this.$set(this.processingCardMap, key, true)
          try {
            const result = await this.processItems(key, targets)
            const processedSet = new Set(safeArray(result.processedEntityIds).map((x) => toInt(x, 0)))
            if (processedSet.size > 0) {
              const processedRows = targets.filter((x) => processedSet.has(toInt(x.entityId, 0)))
              this.markProcessedDone(processedRows)
            }
            uni.showModal({
              title: "批量处理结果",
              content: `成功 ${result.success} 条，失败 ${result.failed} 条`,
              showCancel: false
            })
            this.clearSelection(key)
            this.fetchTodos()
          } finally {
            this.$delete(this.processingCardMap, key)
          }
        }
      })
    },
    async processItems(category, items) {
      const key = String(category || "")
      const rows = safeArray(items)
      if (!rows.length) return { success: 0, failed: 0, processedEntityIds: [] }

      if (key === "alarm_high_risk") {
        this.markProcessedDone(rows)
        return { success: rows.length, failed: 0, processedEntityIds: rows.map((x) => toInt(x.entityId, 0)).filter((x) => x > 0) }
      }

      if (key === "reservation_pending") {
        const ids = rows.map((x) => toInt(x.entityId, 0)).filter((x) => x > 0)
        if (!ids.length) return { success: 0, failed: 0, processedEntityIds: [] }
        const res = await uni.request({
          url: `${BASE_URL}/reservations/batch`,
          method: "POST",
          header: { "Content-Type": "application/json" },
          data: {
            operator: this.userName || "",
            action: "approve",
            ids
          }
        })
        const payload = (res && res.data) || {}
        if (!payload.ok) {
          return { success: 0, failed: ids.length, processedEntityIds: [] }
        }
        const count = toInt(((payload.data || {}).count), 0)
        const approvedIds = safeArray((payload.data || {}).approvedIds).map((x) => toInt(x, 0)).filter((x) => x > 0)
        return { success: count, failed: Math.max(0, ids.length - count), processedEntityIds: approvedIds }
      }

      if (key === "repair_pending") {
        let success = 0
        let failed = 0
        const processedEntityIds = []
        for (const item of rows) {
          const id = toInt(item.entityId, 0)
          if (id <= 0) continue
          try {
            const res = await uni.request({
              url: `${BASE_URL}/repair-orders/${id}/status`,
              method: "POST",
              header: { "Content-Type": "application/json" },
              data: { status: "accepted" }
            })
            const payload = (res && res.data) || {}
            if (payload.ok) {
              success += 1
              processedEntityIds.push(id)
            }
            else failed += 1
          } catch (e) {
            failed += 1
          }
        }
        return { success, failed, processedEntityIds }
      }

      if (key === "claim_pending") {
        let success = 0
        let failed = 0
        const processedEntityIds = []
        for (const item of rows) {
          const id = toInt(item.entityId, 0)
          if (id <= 0) continue
          try {
            const res = await uni.request({
              url: `${BASE_URL}/lostfound/${id}/claim-review`,
              method: "POST",
              header: { "Content-Type": "application/json" },
              data: { action: "approve", note: "todo center batch approve" }
            })
            const payload = (res && res.data) || {}
            if (payload.ok) {
              success += 1
              processedEntityIds.push(id)
            }
            else failed += 1
          } catch (e) {
            failed += 1
          }
        }
        return { success, failed, processedEntityIds }
      }

      if (key === "course_task_due") {
        let success = 0
        let failed = 0
        const processedEntityIds = []
        for (const item of rows) {
          const courseId = toInt(item.courseId, 0)
          const taskId = toInt(item.taskId, 0)
          if (courseId <= 0 || taskId <= 0) continue
          try {
            const res = await uni.request({
              url: `${BASE_URL}/teacher/courses/${courseId}/tasks/${taskId}/notify-missing`,
              method: "POST",
              header: { "Content-Type": "application/json" },
              data: {}
            })
            const payload = (res && res.data) || {}
            if (payload.ok) {
              success += 1
              processedEntityIds.push(taskId)
            }
            else failed += 1
          } catch (e) {
            failed += 1
          }
        }
        return { success, failed, processedEntityIds }
      }

      if (key === "announcement_today_scheduled") {
        const nowText = nowTimeText()
        let success = 0
        let failed = 0
        const processedEntityIds = []
        for (const item of rows) {
          const id = toInt(item.entityId, 0)
          if (id <= 0) continue
          try {
            const res = await uni.request({
              url: `${BASE_URL}/announcements/${id}`,
              method: "PUT",
              header: { "Content-Type": "application/json" },
              data: { publishAt: nowText }
            })
            const payload = (res && res.data) || {}
            if (payload.ok) {
              success += 1
              processedEntityIds.push(id)
            }
            else failed += 1
          } catch (e) {
            failed += 1
          }
        }
        return { success, failed, processedEntityIds }
      }

      return { success: 0, failed: rows.length, processedEntityIds: [] }
    }
  }
}
</script>

<style lang="scss">
.todoPage {
  padding-bottom: 20px;
}

.heroCard {
  border: 1px solid rgba(22, 119, 255, 0.18);
  background: linear-gradient(160deg, #ffffff 0%, #f2f7ff 100%);
}

.heroTop {
  align-items: flex-start;
}

.heroMeta {
  margin-top: 8px;
}

.briefCard {
  border: 1px solid rgba(29, 78, 216, 0.14);
  background: linear-gradient(160deg, #ffffff 0%, #f5f9ff 100%);
}

.briefSummary {
  margin-top: 8px;
  font-size: 13px;
  line-height: 20px;
  color: #0f172a;
}

.briefList {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.briefItem {
  font-size: 12px;
  line-height: 18px;
  color: #475569;
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
  font-size: 24px;
  font-weight: 700;
  color: #0f172a;
}

.metricValue.warning {
  color: #b45309;
}

.metricValue.danger {
  color: #b42318;
}

.chipRow {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
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

.todoCard {
  border: 1px solid rgba(148, 163, 184, 0.24);
}

.sectionHead {
  align-items: flex-start;
}

.topActions {
  gap: 8px;
}

.itemList {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.itemRow {
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 10px;
  padding: 10px;
}

.itemHead {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.selectBox {
  width: 20px;
  height: 20px;
  border-radius: 6px;
  border: 1px solid #cbd5e1;
  text-align: center;
  line-height: 20px;
  color: transparent;
  font-size: 12px;
}

.selectBox.on {
  border-color: #2563eb;
  background: #2563eb;
  color: #fff;
}

.itemTitle {
  font-size: 13px;
  color: #0f172a;
  font-weight: 700;
}

.itemSub {
  margin-top: 4px;
  font-size: 12px;
  color: #64748b;
}

.itemMeta {
  margin-top: 6px;
  font-size: 12px;
  color: #475569;
}

.itemActions {
  margin-top: 8px;
}

.tagWrap {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
}

.priorityTag,
.timeoutTag,
.doneTag {
  font-size: 11px;
  border-radius: 999px;
  padding: 2px 8px;
}

.priorityTag.p0 {
  background: #ffe7e7;
  color: #b42318;
}

.priorityTag.p1 {
  background: #fff2e6;
  color: #b45309;
}

.priorityTag.p2 {
  background: #eaf3ff;
  color: #1d4ed8;
}

.priorityTag.p3 {
  background: #eef2f6;
  color: #475569;
}

.timeoutTag {
  background: #ffeaea;
  color: #b42318;
}

.doneTag {
  background: #e8fff0;
  color: #1f7a3a;
}

.tiny {
  margin-top: 4px;
}
</style>

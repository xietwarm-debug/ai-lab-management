<template>
  <view class="container knowledgePage">
    <view class="stack">
      <view class="card heroCard">
        <view class="rowBetween heroTop">
          <view>
            <view class="title">知识库管理</view>
            <view class="subtitle">录入实验室制度、设备说明和安全规范，供 AI 助手检索回答</view>
          </view>
          <button class="btnSecondary miniBtn" size="mini" :disabled="loading" @click="reload">刷新</button>
        </view>
      </view>

      <view class="card formCard">
        <view class="rowBetween">
          <view class="cardTitle">{{ editingId ? "编辑文档" : "新增文档" }}</view>
          <button v-if="editingId" class="btnGhost miniBtn" size="mini" @click="resetForm">取消编辑</button>
        </view>

        <view class="label">标题</view>
        <input class="inputBase" v-model.trim="form.title" maxlength="200" placeholder="例如：实验室安全操作规范" />

        <view class="formGrid">
          <view>
            <view class="label">分类</view>
            <picker mode="selector" :range="categoryOptions" range-key="label" @change="onCategoryChange">
              <view class="pickerLike">{{ currentCategoryLabel }}</view>
            </picker>
          </view>
          <view>
            <view class="label">适用角色</view>
            <picker mode="selector" :range="scopeOptions" range-key="label" @change="onScopeChange">
              <view class="pickerLike">{{ currentScopeLabel }}</view>
            </picker>
          </view>
        </view>

        <view class="formGrid">
          <view>
            <view class="label">状态</view>
            <picker mode="selector" :range="statusOptions" range-key="label" @change="onStatusChange">
              <view class="pickerLike">{{ currentStatusLabel }}</view>
            </picker>
          </view>
          <view>
            <view class="label">来源链接（可选）</view>
            <input class="inputBase" v-model.trim="form.sourceUrl" maxlength="500" placeholder="https://..." />
          </view>
        </view>

        <view class="label">正文</view>
        <textarea class="textareaBase bigTextarea" v-model="form.content" maxlength="200000" placeholder="粘贴制度、说明书、SOP 或实验指导内容" />
        <view class="muted">{{ form.content.length }} / 200000</view>

        <view class="actions">
          <button class="btnPrimary actionBtn" :loading="saving" @click="submitForm">{{ editingId ? "保存并重建索引" : "创建并建索引" }}</button>
          <button class="btnSecondary actionBtn" @click="fillDemo">填入示例</button>
        </view>
      </view>

      <view class="card formCard">
        <view class="rowBetween">
          <view class="cardTitle">知识问答自测</view>
          <button class="btnGhost miniBtn" size="mini" :loading="asking" @click="runKnowledgeAsk">测试检索</button>
        </view>
        <input class="inputBase" v-model.trim="question" maxlength="120" placeholder="例如：实验室预约最多提前几天？" @confirm="runKnowledgeAsk" />
        <view class="answerBox" v-if="answerText">
          <view class="answerText">{{ answerText }}</view>
          <view class="sourceItem" v-for="item in answerSources" :key="`source-${item.documentId}-${item.chunkNo}`">
            {{ item.title || "-" }}
          </view>
        </view>
      </view>

      <view class="card formCard">
        <view class="rowBetween">
          <view class="cardTitle">知识文档列表</view>
          <view class="muted">共 {{ rows.length }} 条</view>
        </view>
        <view class="chipRow">
          <view
            v-for="item in filterStatusOptions"
            :key="item.value"
            class="chip statusChip"
            :class="{ chipOn: filters.status === item.value }"
            @click="setStatusFilter(item.value)"
          >
            {{ item.label }}
          </view>
        </view>
        <input class="inputBase" v-model.trim="filters.keyword" maxlength="60" placeholder="搜索标题 / 摘要 / 关键词" @confirm="fetchRows" />

        <view class="docList" v-if="rows.length > 0">
          <view class="docItem" v-for="item in rows" :key="item.id">
            <view class="rowBetween">
              <view class="docTitle">{{ item.title || "-" }}</view>
              <view class="statusTag" :class="statusTone(item.status)">{{ statusLabel(item.status) }}</view>
            </view>
            <view class="meta">{{ item.category || "-" }} · {{ item.scopeRole || "-" }} · 分块 {{ item.chunkCount || 0 }}</view>
            <view class="meta" v-if="item.summary">{{ item.summary }}</view>
            <view class="meta muted">更新时间：{{ item.updatedAt || "-" }}</view>
            <view class="actions">
              <button class="btnGhost miniBtn" size="mini" @click="editRow(item)">编辑</button>
              <button class="btnSecondary miniBtn" size="mini" :loading="busyId === item.id && busyAction === 'reindex'" @click="reindexRow(item)">重建索引</button>
              <button
                class="btnSecondary miniBtn"
                size="mini"
                :loading="busyId === item.id && busyAction === 'status'"
                @click="toggleStatus(item)"
              >
                {{ item.status === "active" ? "停用" : "启用" }}
              </button>
            </view>
          </view>
        </view>
        <view class="empty" v-else>暂无知识文档</view>
      </view>
    </view>
  </view>
</template>

<script>
import {
  adminCreateKnowledgeDocument,
  adminListKnowledgeDocuments,
  adminReindexKnowledgeDocument,
  adminUpdateKnowledgeDocument,
  adminUpdateKnowledgeDocumentStatus,
  askKnowledgeBase
} from "@/common/api.js"

const CATEGORY_OPTIONS = [
  { label: "规则制度", value: "rule" },
  { label: "设备说明", value: "manual" },
  { label: "安全规范", value: "safety" },
  { label: "课程文档", value: "course" },
  { label: "报修知识", value: "repair" },
  { label: "常见问题", value: "faq" },
  { label: "其他", value: "other" }
]

const SCOPE_OPTIONS = [
  { label: "全员可见", value: "all" },
  { label: "仅学生", value: "student" },
  { label: "仅教师", value: "teacher" },
  { label: "仅管理员", value: "admin" }
]

const STATUS_OPTIONS = [
  { label: "草稿", value: "draft" },
  { label: "启用", value: "active" },
  { label: "停用", value: "disabled" }
]

export default {
  data() {
    return {
      loading: false,
      saving: false,
      asking: false,
      busyId: 0,
      busyAction: "",
      editingId: 0,
      question: "实验室预约最多提前几天？",
      answerText: "",
      answerSources: [],
      rows: [],
      filters: {
        status: "",
        keyword: ""
      },
      form: {
        title: "",
        category: "rule",
        scopeRole: "all",
        status: "active",
        sourceUrl: "",
        content: ""
      },
      categoryOptions: CATEGORY_OPTIONS,
      scopeOptions: SCOPE_OPTIONS,
      statusOptions: STATUS_OPTIONS,
      filterStatusOptions: [
        { label: "全部", value: "" },
        { label: "启用", value: "active" },
        { label: "草稿", value: "draft" },
        { label: "停用", value: "disabled" }
      ]
    }
  },
  computed: {
    currentCategoryLabel() {
      const hit = this.categoryOptions.find((item) => item.value === this.form.category)
      return (hit && hit.label) || "规则制度"
    },
    currentScopeLabel() {
      const hit = this.scopeOptions.find((item) => item.value === this.form.scopeRole)
      return (hit && hit.label) || "全员可见"
    },
    currentStatusLabel() {
      const hit = this.statusOptions.find((item) => item.value === this.form.status)
      return (hit && hit.label) || "草稿"
    }
  },
  onShow() {
    if (!this.ensureAdmin()) return
    this.fetchRows()
  },
  methods: {
    ensureAdmin() {
      const session = uni.getStorageSync("session") || {}
      if (session.role !== "admin") {
        uni.showToast({ title: "无权限", icon: "none" })
        uni.reLaunch({ url: "/pages/login/login" })
        return false
      }
      return true
    },
    statusTone(status) {
      if (status === "active") return "success"
      if (status === "disabled") return "danger"
      return "warning"
    },
    statusLabel(status) {
      const hit = this.statusOptions.find((item) => item.value === status)
      return (hit && hit.label) || "草稿"
    },
    onCategoryChange(e) {
      const idx = Number((e && e.detail && e.detail.value) || 0)
      const item = this.categoryOptions[idx]
      if (item) this.form.category = item.value
    },
    onScopeChange(e) {
      const idx = Number((e && e.detail && e.detail.value) || 0)
      const item = this.scopeOptions[idx]
      if (item) this.form.scopeRole = item.value
    },
    onStatusChange(e) {
      const idx = Number((e && e.detail && e.detail.value) || 0)
      const item = this.statusOptions[idx]
      if (item) this.form.status = item.value
    },
    setStatusFilter(value) {
      this.filters.status = value
      this.fetchRows()
    },
    resetForm() {
      this.editingId = 0
      this.form = {
        title: "",
        category: "rule",
        scopeRole: "all",
        status: "active",
        sourceUrl: "",
        content: ""
      }
    },
    fillDemo() {
      this.form.title = "实验室预约管理规定"
      this.form.category = "rule"
      this.form.scopeRole = "all"
      this.form.status = "active"
      this.form.content =
        "实验室预约开放时间为每日 08:00 至 22:00。\n\n学生可提前 7 天提交预约申请，超过 7 天的申请不予受理。\n\n高峰时段预约需管理员审批。若因教学任务冲突，课程任务优先。"
    },
    editRow(item) {
      this.editingId = Number(item.id || 0)
      this.form = {
        title: String(item.title || ""),
        category: String(item.category || "rule"),
        scopeRole: String(item.scopeRole || "all"),
        status: String(item.status || "draft"),
        sourceUrl: String(item.sourceUrl || ""),
        content: ""
      }
      uni.showToast({ title: "已载入基础信息，请补充或粘贴正文后保存", icon: "none" })
    },
    async fetchRows() {
      if (this.loading) return
      this.loading = true
      try {
        const res = await adminListKnowledgeDocuments(this.filters)
        const payload = (res && res.data) || {}
        this.rows = payload.ok && Array.isArray(payload.data) ? payload.data : []
      } catch (e) {
        this.rows = []
      } finally {
        this.loading = false
      }
    },
    reload() {
      this.fetchRows()
    },
    async submitForm() {
      if (this.saving) return
      if (!String(this.form.title || "").trim()) {
        uni.showToast({ title: "请填写标题", icon: "none" })
        return
      }
      if (!String(this.form.content || "").trim()) {
        uni.showToast({ title: "请填写正文", icon: "none" })
        return
      }
      this.saving = true
      try {
        const payload = { ...this.form }
        const res = this.editingId
          ? await adminUpdateKnowledgeDocument(this.editingId, payload)
          : await adminCreateKnowledgeDocument(payload)
        const body = (res && res.data) || {}
        if (!body.ok) {
          uni.showToast({ title: body.msg || "保存失败", icon: "none" })
          return
        }
        uni.showToast({ title: this.editingId ? "已更新" : "已创建", icon: "success" })
        this.resetForm()
        this.fetchRows()
      } catch (e) {
        uni.showToast({ title: "保存失败", icon: "none" })
      } finally {
        this.saving = false
      }
    },
    async reindexRow(item) {
      this.busyId = Number(item.id || 0)
      this.busyAction = "reindex"
      try {
        const res = await adminReindexKnowledgeDocument(item.id)
        const payload = (res && res.data) || {}
        uni.showToast({ title: payload.ok ? "索引已重建" : payload.msg || "重建失败", icon: payload.ok ? "success" : "none" })
        if (payload.ok) this.fetchRows()
      } catch (e) {
        uni.showToast({ title: "重建失败", icon: "none" })
      } finally {
        this.busyId = 0
        this.busyAction = ""
      }
    },
    async toggleStatus(item) {
      const nextStatus = item.status === "active" ? "disabled" : "active"
      this.busyId = Number(item.id || 0)
      this.busyAction = "status"
      try {
        const res = await adminUpdateKnowledgeDocumentStatus(item.id, nextStatus)
        const payload = (res && res.data) || {}
        uni.showToast({ title: payload.ok ? "状态已更新" : payload.msg || "更新失败", icon: payload.ok ? "success" : "none" })
        if (payload.ok) this.fetchRows()
      } catch (e) {
        uni.showToast({ title: "更新失败", icon: "none" })
      } finally {
        this.busyId = 0
        this.busyAction = ""
      }
    },
    async runKnowledgeAsk() {
      if (this.asking) return
      const question = String(this.question || "").trim()
      if (!question) {
        uni.showToast({ title: "请输入问题", icon: "none" })
        return
      }
      this.asking = true
      try {
        const res = await askKnowledgeBase({ question })
        const payload = (res && res.data) || {}
        const data = payload.data || {}
        if (!payload.ok || !data.matched) {
          this.answerText = "当前知识库没有命中相关内容。"
          this.answerSources = []
          return
        }
        this.answerText = String(data.answer || "").trim()
        this.answerSources = Array.isArray(data.sources) ? data.sources : []
      } catch (e) {
        this.answerText = "知识问答失败"
        this.answerSources = []
      } finally {
        this.asking = false
      }
    }
  }
}
</script>

<style lang="scss">
.knowledgePage {
  padding-bottom: 24px;
}

.heroCard {
  border: 1px solid rgba(22, 119, 255, 0.16);
  background: linear-gradient(160deg, #ffffff 0%, #eef6ff 100%);
}

.heroTop {
  align-items: flex-start;
}

.miniBtn {
  min-height: 30px;
  line-height: 30px;
  padding: 0 10px;
  border-radius: 9px;
  font-size: 12px;
}

.formGrid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.bigTextarea {
  min-height: 220px;
}

.answerBox {
  margin-top: 10px;
  padding: 12px;
  border-radius: 12px;
  background: #f8fafc;
}

.answerText {
  font-size: 13px;
  line-height: 22px;
  color: #0f172a;
}

.sourceItem {
  margin-top: 8px;
  font-size: 12px;
  line-height: 18px;
  color: #475569;
}

.docList {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.docItem {
  padding: 14px;
  border-radius: 14px;
  background: #f8fafc;
}

.docTitle {
  flex: 1;
  margin-right: 10px;
  font-size: 15px;
  font-weight: 600;
  color: #0f172a;
}

@media (max-width: 640px) {
  .formGrid {
    grid-template-columns: 1fr;
  }
}
</style>

<template>
  <view class="container feedbackPage" :class="themeClass">
    <view class="stack">
      <view class="card">
        <view class="title">在线反馈</view>
        <view class="subtitle">提交问题、建议或需求，系统会记录你的反馈</view>
      </view>

      <view class="card">
        <view class="fieldLabel">反馈类型</view>
        <picker class="pickerField" :range="typeLabels" @change="onTypeChange">
          <view class="pickerText">{{ selectedTypeLabel }}</view>
        </picker>

        <view class="fieldLabel">反馈内容</view>
        <textarea
          class="textareaBase contentArea"
          maxlength="2000"
          v-model.trim="content"
          placeholder="请描述你遇到的问题或建议（至少 5 个字）"
        />

        <view class="fieldLabel">联系方式（可选）</view>
        <input class="inputBase" v-model.trim="contact" maxlength="120" placeholder="手机号 / 邮箱 / 微信号" />

        <button class="btnPrimary submitBtn" :loading="submitting" @click="submitFeedback">提交反馈</button>
      </view>

      <view class="card">
        <view class="rowBetween">
          <view class="cardTitle">最近提交</view>
          <view class="muted">仅展示当前账号</view>
        </view>
        <view class="empty" v-if="historyRows.length === 0">暂无反馈记录</view>
        <view class="historyList" v-else>
          <view class="historyItem" v-for="item in historyRows" :key="item.id">
            <view class="rowBetween">
              <view class="typeTag">{{ item.typeLabel }}</view>
              <view class="muted">{{ item.createdAt }}</view>
            </view>
            <view class="historyContent">{{ item.content }}</view>
            <view class="muted" v-if="item.contact">联系方式：{{ item.contact }}</view>
            <view class="muted">状态：{{ item.online ? "已提交" : "离线暂存" }}</view>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { submitUserFeedback } from "@/common/api.js"
import { themePageMixin } from "@/common/theme.js"

const FEEDBACK_HISTORY_KEY = "user_feedback_history_v1"

function nowText() {
  const d = new Date()
  const p = (n) => (n < 10 ? `0${n}` : `${n}`)
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`
}

export default {
  mixins: [themePageMixin],
  data() {
    return {
      account: "",
      role: "",
      submitting: false,
      content: "",
      contact: "",
      selectedTypeIndex: 0,
      typeOptions: [
        { label: "问题反馈", value: "issue" },
        { label: "功能建议", value: "suggestion" },
        { label: "使用咨询", value: "consult" },
        { label: "其他", value: "other" }
      ],
      historyRows: []
    }
  },
  computed: {
    typeLabels() {
      return this.typeOptions.map((x) => x.label)
    },
    selectedType() {
      return this.typeOptions[this.selectedTypeIndex] || this.typeOptions[0]
    },
    selectedTypeLabel() {
      return (this.selectedType && this.selectedType.label) || "问题反馈"
    }
  },
  onShow() {
    const session = uni.getStorageSync("session") || {}
    if (!session.username || !session.token) {
      uni.reLaunch({ url: "/pages/login/login" })
      return
    }
    this.account = String(session.username || "").trim()
    this.role = String(session.role || "").trim().toLowerCase()
    this.loadHistory()
  },
  methods: {
    onTypeChange(e) {
      const idx = Number((e && e.detail && e.detail.value) || 0)
      if (Number.isFinite(idx) && idx >= 0 && idx < this.typeOptions.length) this.selectedTypeIndex = idx
    },
    readAllHistory() {
      const rows = uni.getStorageSync(FEEDBACK_HISTORY_KEY)
      return Array.isArray(rows) ? rows : []
    },
    loadHistory() {
      const rows = this.readAllHistory().filter((x) => String((x && x.account) || "") === this.account)
      this.historyRows = rows.slice(0, 10)
    },
    prependHistory(item) {
      const oldRows = this.readAllHistory()
      const rows = [item].concat(oldRows).slice(0, 200)
      uni.setStorageSync(FEEDBACK_HISTORY_KEY, rows)
      this.loadHistory()
    },
    async submitFeedback() {
      const text = String(this.content || "").trim()
      if (text.length < 5) {
        uni.showToast({ title: "反馈内容至少 5 个字", icon: "none" })
        return
      }
      if (this.submitting) return
      this.submitting = true
      const now = nowText()
      const type = this.selectedType
      try {
        const res = await submitUserFeedback({
          type: String((type && type.value) || "issue"),
          content: text,
          contact: String(this.contact || "").trim(),
          source: "my_help_feedback"
        })
        const payload = (res && res.data) || {}
        if (Number(res && res.statusCode) === 200 && payload.ok) {
          const createdAt = String(((payload.data || {}).createdAt) || now)
          this.prependHistory({
            id: String(((payload.data || {}).id) || `${Date.now()}`),
            account: this.account,
            role: this.role,
            typeLabel: type.label,
            content: text,
            contact: String(this.contact || "").trim(),
            createdAt,
            online: true
          })
          this.content = ""
          this.contact = ""
          uni.showToast({ title: "反馈已提交", icon: "success" })
          return
        }
        throw new Error(String(payload.msg || "submit failed"))
      } catch (e) {
        this.prependHistory({
          id: `${Date.now()}`,
          account: this.account,
          role: this.role,
          typeLabel: type.label,
          content: text,
          contact: String(this.contact || "").trim(),
          createdAt: now,
          online: false
        })
        this.content = ""
        this.contact = ""
        uni.showToast({ title: "网络异常，已暂存", icon: "none" })
      } finally {
        this.submitting = false
      }
    }
  }
}
</script>

<style lang="scss">
.feedbackPage {
  padding-bottom: 24px;
}

.fieldLabel {
  margin-top: 10px;
  font-size: 13px;
  line-height: 20px;
  color: var(--color-text-muted);
}

.pickerField {
  margin-top: 6px;
  min-height: 40px;
  border: 1px solid var(--color-border-primary);
  border-radius: 10px;
  padding: 10px 12px;
  box-sizing: border-box;
  background: var(--color-bg-card);
}

.pickerText {
  font-size: 14px;
  line-height: 20px;
  color: var(--color-text-primary);
}

.contentArea {
  margin-top: 6px;
  min-height: 120px;
}

.submitBtn {
  margin-top: 14px;
}

.historyList {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.historyItem {
  border: 1px solid var(--color-border-primary);
  border-radius: 10px;
  padding: 10px;
  background: var(--color-bg-card);
}

.typeTag {
  font-size: 12px;
  line-height: 18px;
  color: var(--brand);
}

.historyContent {
  margin-top: 6px;
  font-size: 13px;
  line-height: 20px;
  color: var(--color-text-primary);
  word-break: break-all;
}
</style>

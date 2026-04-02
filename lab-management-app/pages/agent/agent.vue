<template>
  <view class="agentPage" :class="themeClass">
    <view class="pageInner">
      <view class="headerSection">
        <view class="titleBar">
          <view class="titleLeft">
            <image class="titleAvatar" src="/static/ningning.png" mode="aspectFill"></image>
            <view class="titleName">&#23425;&#23425;</view>
          </view>
          <view class="menuButton" @click="openHeaderMenu">
            <view class="menuDots"></view>
          </view>
        </view>
      </view>

      <view class="chatCard" :style="chatCardStyle">
        <scroll-view
          class="chatScroll"
          scroll-y
          :scroll-into-view="scrollAnchorId"
          :scroll-with-animation="true"
          @scroll="onChatScroll"
        >
          <view class="defaultDialog" :class="{ withMessages: messages.length > 0 }">
            <view class="defaultCircle">
              <image class="defaultGif" src="/static/1.gif" mode="aspectFill"></image>
            </view>
            <view class="defaultText">
              我可以帮你处理预约、改期、取消、报修、查进度和规则解释；如果账号已开通资产只读权限，也可以直接查设备状态、借用情况和到期提醒。你可以直接说需求，也可以点下面的快捷入口。
            </view>
          </view>
          <view v-if="messages.length > 0" class="bubbleList">
            <view
              class="bubbleRow"
              v-for="(item, idx) in messages"
              :id="item.domId"
              :key="item.domId || `${item.role}-${idx}`"
              :class="{ user: item.role === 'user', assistant: item.role !== 'user' }"
            >
              <view
                class="bubble"
                :class="{ userBubble: item.role === 'user', assistantBubble: item.role !== 'user' }"
                @longpress="onMessageLongPress(idx)"
              >
                <view class="bubbleText">{{ item.text }}</view>
                <view v-if="item.role !== 'user' && item.sources.length > 0" class="sourcePanel">
                  <view class="sourceHeader">联网来源</view>
                  <view
                    v-for="(source, sourceIdx) in item.sources"
                    :key="`${item.domId}-source-${sourceIdx}`"
                    class="sourceItem"
                    @click="openSourceLink(source)"
                  >
                    <view class="sourceIndex">{{ sourceIdx + 1 }}</view>
                    <view class="sourceBody">
                      <view class="sourceTitle">{{ source.title || source.url || `来源 ${sourceIdx + 1}` }}</view>
                      <view class="sourceMeta">
                        {{ sourceHost(source.url) }}
                        <text v-if="source.publishedDate"> · {{ source.publishedDate }}</text>
                      </view>
                    </view>
                  </view>
                </view>
                <view v-if="item.meta" class="bubbleMeta" :class="{ bubbleWarn: item.tone === 'warn' }">
                  {{ item.meta }}
                </view>
                <view v-if="item.role !== 'user' && item.helper" class="bubbleActions">
                  <view class="bubbleActionButton" @click.stop="openHelperPanel(item.helper)">补充信息</view>
                </view>
              </view>
            </view>
          </view>
          <view id="chat-bottom-anchor"></view>
        </scroll-view>
      </view>

      <view v-if="showBackToBottom" class="backToBottomWrap" :style="backToBottomWrapStyle">
        <view class="backToBottomButton" @click="onBackToBottom">回到底部</view>
      </view>

      <view class="inputSection">
        <scroll-view class="quickActions" scroll-x enable-flex>
          <view class="quickActionsInner">
            <view
              v-for="item in quickActions"
              :key="item.text"
              class="quickActionChip"
              @click="sendText(item.text)"
            >
              {{ item.label }}
            </view>
          </view>
        </scroll-view>
        <view class="inputRow">
          <view class="inputWrap" :class="{ focused: inputFocused }">
            <input
              class="inputBox"
              v-model.trim="inputText"
              placeholder="请输入预约、报修需求，或直接让我联网搜索"
              confirm-type="send"
              @confirm="sendText()"
              @focus="onInputFocus"
              @blur="onInputBlur"
            />
            <view class="voiceIconBtn" :class="{ recording }" @click="toggleVoiceRecord">
              <view class="voiceIcon"></view>
            </view>
          </view>
          <view class="secondaryButton buttonBase searchTriggerButton" @click="sendWebSearch">
            联网搜
          </view>
          <view class="primaryButton buttonBase sendButton" @click="sendText()">
            发送
          </view>
        </view>

        <view v-if="recording" class="hintText">正在录音，点击麦克风结束并发送</view>
      </view>

      <view v-if="helperVisible" class="helperOverlay" @click="closeHelperPanel">
        <view class="helperSheet" @click.stop>
          <view class="helperHandle"></view>
          <view class="helperHeader">
            <view>
              <view class="helperTitle">{{ helperPanelTitle }}</view>
              <view class="helperDesc">直接点选后发送给宁宁，继续完成当前处理。</view>
            </view>
            <view class="helperClose" @click="closeHelperPanel">收起</view>
          </view>

          <view v-if="activeHelperMissingSlots.length > 0" class="helperSection">
            <view class="helperLabel">当前还缺</view>
            <view class="helperTagRow">
              <view v-for="slot in activeHelperMissingSlots" :key="slot" class="helperTag">{{ helperSlotLabel(slot) }}</view>
            </view>
          </view>

          <view v-if="activeHelperQuestions.length > 0" class="helperSection">
            <view class="helperLabel">助手提示</view>
            <view v-for="item in activeHelperQuestions" :key="item.key || item.question" class="helperTip">
              {{ item.question }}
            </view>
          </view>

          <view v-if="activeHelperPlans.length > 0" class="helperSection">
            <view class="helperLabel">可选方案</view>
            <view
              v-for="plan in activeHelperPlans"
              :key="plan.planId"
              class="helperPlanCard"
              :class="{ active: helperForm.selectedPlanId === plan.planId }"
              @click="selectHelperPlan(plan)"
            >
              <view class="helperPlanTop">
                <text class="helperPlanId">{{ plan.planId }}</text>
                <text class="helperPlanLab">{{ plan.labName || "-" }}</text>
              </view>
              <view class="helperPlanMeta">{{ plan.date || "-" }} {{ plan.time || "-" }}</view>
              <view v-if="plan.reason" class="helperPlanMeta">{{ plan.reason }}</view>
            </view>
          </view>

          <view v-if="shouldShowHelperField('labName')" class="helperSection">
            <view class="helperLabel">实验室</view>
            <view class="helperChipRow">
              <view
                v-for="lab in helperLabOptions"
                :key="lab.id || lab.name"
                class="helperChip"
                :class="{ active: helperForm.labName === lab.name }"
                @click="helperForm.labName = lab.name"
              >
                {{ lab.name }}
              </view>
            </view>
          </view>

          <view v-if="shouldShowHelperField('date')" class="helperSection">
            <view class="helperLabel">日期</view>
            <view class="helperChipRow">
              <view
                v-for="item in helperDateOptions"
                :key="item.value"
                class="helperChip"
                :class="{ active: helperForm.date === item.value }"
                @click="helperForm.date = item.value"
              >
                {{ item.label }}
              </view>
            </view>
          </view>

          <view v-if="shouldShowHelperField('time')" class="helperSection">
            <view class="helperLabel">时间段</view>
            <view class="helperChipRow">
              <view
                v-for="item in helperTimeOptions"
                :key="item.value"
                class="helperChip"
                :class="{ active: helperForm.time === item.value }"
                @click="helperForm.time = item.value"
              >
                {{ item.label }}
              </view>
            </view>
          </view>

          <view v-if="shouldShowHelperField('reason')" class="helperSection">
            <view class="helperLabel">用途</view>
            <textarea class="helperTextarea" v-model.trim="helperForm.reason" placeholder="例如：课程实验、上机考试"></textarea>
          </view>

          <view v-if="shouldShowHelperField('description')" class="helperSection">
            <view class="helperLabel">故障描述</view>
            <textarea class="helperTextarea" v-model.trim="helperForm.description" placeholder="例如：无法开机、蓝屏、断网"></textarea>
          </view>

          <view v-if="shouldShowHelperField('location')" class="helperSection">
            <view class="helperLabel">报修位置</view>
            <input class="helperInput" v-model.trim="helperForm.location" placeholder="例如：A203 物联网实验室" />
          </view>

          <view v-if="shouldShowHelperField('equipmentHint')" class="helperSection">
            <view class="helperLabel">设备编号</view>
            <input class="helperInput" v-model.trim="helperForm.equipmentHint" placeholder="例如：A203-HOST-001" />
          </view>

          <view class="helperFooter">
            <view class="helperSecondaryButton" @click="closeHelperPanel">稍后再说</view>
            <view class="helperPrimaryButton" :class="{ disabled: !canSubmitHelperForm }" @click="submitHelperPanel">发送补充信息</view>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { BASE_URL, listLabs } from "@/common/api.js"
import { themePageMixin } from "@/common/theme.js"

function profileStorageKey(account) {
  return `user_profile_${account}`
}

const HELPER_TIME_OPTIONS = [
  { value: "08:00-08:40", label: "第1节 08:00-08:40" },
  { value: "08:45-09:35", label: "第2节 08:45-09:35" },
  { value: "10:25-11:05", label: "第3节 10:25-11:05" },
  { value: "11:10-11:50", label: "第4节 11:10-11:50" },
  { value: "14:30-15:10", label: "第5节 14:30-15:10" },
  { value: "15:15-15:55", label: "第6节 15:15-15:55" },
  { value: "16:05-16:45", label: "第7节 16:05-16:45" },
  { value: "16:50-17:30", label: "第8节 16:50-17:30" },
  { value: "19:00-19:40", label: "第9节 19:00-19:40" },
  { value: "19:45-20:25", label: "第10节 19:45-20:25" }
]

function buildHelperDateOptions() {
  const labels = ["今天", "明天", "后天"]
  const items = []
  for (let i = 0; i < 7; i += 1) {
    const date = new Date()
    date.setDate(date.getDate() + i)
    const value = date.toISOString().slice(0, 10)
    const month = date.getMonth() + 1
    const day = date.getDate()
    const weekday = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"][date.getDay()]
    const prefix = labels[i] || ""
    const label = prefix ? `${prefix} ${month}/${day} ${weekday}` : `${month}/${day} ${weekday}`
    items.push({ value, label })
  }
  return items
}

function normalizeHelperSlotKey(rawKey = "") {
  const compact = String(rawKey || "")
    .trim()
    .replace(/[\s_-]+/g, "")
    .toLowerCase()
  if (!compact) return ""
  if (["lab", "labname", "labid", "room", "classroom"].includes(compact)) return "labName"
  if (["date", "day"].includes(compact)) return "date"
  if (["time", "slot", "timeslot", "period"].includes(compact)) return "time"
  if (["reason", "purpose"].includes(compact)) return "reason"
  if (["description", "desc", "issue", "fault"].includes(compact)) return "description"
  if (["location", "place"].includes(compact)) return "location"
  if (["equipmenthint", "equipmentcode", "assetcode", "devicecode", "equipment"].includes(compact)) return "equipmentHint"
  if (["selectedplanid", "plan", "planid"].includes(compact)) return "selectedPlanId"
  return String(rawKey || "").trim()
}

function inferHelperMissingSlotsFromText(text = "") {
  const raw = String(text || "").trim()
  if (!raw) return []
  const slots = []
  if (/(实验室|机房|教室|lab)/i.test(raw)) slots.push("labName")
  if (/(日期|哪天|时间日期|yyyy-mm-dd)/i.test(raw)) slots.push("date")
  if (/(时间段|时段|几节|08:00|time)/i.test(raw)) slots.push("time")
  if (/(用途|原因|预约用途)/i.test(raw)) slots.push("reason")
  if (/(故障描述|故障现象|描述)/i.test(raw)) slots.push("description")
  if (/(位置|地点|报修位置)/i.test(raw)) slots.push("location")
  if (/(设备编号|资产编号|编号)/i.test(raw)) slots.push("equipmentHint")
  if (/(方案|plan)/i.test(raw)) slots.push("selectedPlanId")
  return [...new Set(slots)]
}

function normalizeHelperQuestions(rawQuestions) {
  if (!Array.isArray(rawQuestions)) return []
  return rawQuestions
    .map((item) => {
      const row = item && typeof item === "object" ? item : {}
      const key = normalizeHelperSlotKey(row.key)
      const question = String(row.question || "").trim()
      if (!key && !question) return null
      return { key, question }
    })
    .filter(Boolean)
}

function normalizeHelperPlans(rawPlans) {
  if (!Array.isArray(rawPlans)) return []
  return rawPlans
    .map((item) => {
      const row = item && typeof item === "object" ? item : {}
      const planId = String(row.planId || "").trim()
      if (!planId) return null
      return {
        planId,
        labName: String(row.labName || "").trim(),
        date: String(row.date || "").trim(),
        time: String(row.time || "").trim(),
        reason: String(row.reason || "").trim()
      }
    })
    .filter(Boolean)
}

function normalizeHelperPending(rawPending) {
  const row = rawPending && typeof rawPending === "object" ? rawPending : {}
  const slots = row.slots && typeof row.slots === "object" ? row.slots : {}
  const missingRaw = Array.isArray(row.missingSlots)
    ? row.missingSlots
    : Array.isArray(row.missing_slots)
      ? row.missing_slots
      : []
  return {
    intent: String(row.intent || "").trim(),
    state: String(row.state || "").trim(),
    slots,
    missingSlots: missingRaw.map((item) => normalizeHelperSlotKey(item)).filter(Boolean)
  }
}

function normalizeAssistantHelper(meta = {}, action = "", replyText = "") {
  if (String(action || "").trim() !== "ask_info") return null
  const pending = normalizeHelperPending(meta.pending)
  const questions = normalizeHelperQuestions(meta.questions)
  const plans = normalizeHelperPlans(meta.plans)
  let missingSlots = [...pending.missingSlots]
  if (missingSlots.length === 0 && questions.length > 0) {
    missingSlots = questions.map((item) => normalizeHelperSlotKey(item.key)).filter(Boolean)
  }
  if (missingSlots.length === 0) {
    const questionText = questions.map((item) => item.question).join(" ")
    missingSlots = inferHelperMissingSlotsFromText(`${replyText} ${questionText}`)
  }
  missingSlots = [...new Set(missingSlots.filter(Boolean))]
  if (String(action || "").trim() === "ask_info" && missingSlots.length === 0 && plans.length === 0 && questions.length === 0) {
    return null
  }
  return {
    intent: pending.intent,
    state: pending.state,
    slots: pending.slots,
    missingSlots,
    questions,
    plans
  }
}

let wechatSIPlugin = null
// #ifdef MP-WEIXIN
try {
  wechatSIPlugin = requirePlugin("WechatSI")
} catch (error) {
  wechatSIPlugin = null
}
// #endif

export default {
  mixins: [themePageMixin],
  data() {
    return {
      inputText: "",
      inputFocused: false,
      sending: false,
      recording: false,
      recognizer: null,
      scrollAnchorId: "chat-bottom-anchor",
      messageSeq: 0,
      composerHeight: 112,
      chatViewportHeight: 0,
      isNearBottom: true,
      showBackToBottom: false,
      lastUserText: "",
      messages: [],
      historyLoaded: false,
      loadingHistory: false,
      helperVisible: false,
      helperContext: null,
      helperLabOptions: [],
      helperForm: {
        labName: "",
        date: "",
        time: "",
        reason: "",
        description: "",
        location: "",
        equipmentHint: "",
        selectedPlanId: ""
      },
      helperDateOptions: buildHelperDateOptions(),
      helperTimeOptions: HELPER_TIME_OPTIONS.slice(),
      quickActions: [
        { label: "查我的预约", text: "查看我的预约" },
        { label: "查我的报修", text: "查看我的报修进度" },
        { label: "查资产状态", text: "帮我查一下资产状态" },
        { label: "查借出资产", text: "当前借出中的资产有多少" },
        { label: "改期预约", text: "把我的预约改期" },
        { label: "取消预约", text: "取消我的预约" },
        { label: "预约规则", text: "查看预约规则" },
        { label: "安全规范", text: "实验室安全规范有哪些" },
        { label: "设备说明", text: "示波器使用前要注意什么" },
        { label: "提交报修", text: "我要提交报修" }
      ]
    }
  },
  computed: {
    chatCardStyle() {
      const height = Math.max(88, Number(this.composerHeight || 112))
      return {
        marginBottom: `calc(${height}px + var(--tabbar-height) + env(safe-area-inset-bottom))`
      }
    },
    backToBottomWrapStyle() {
      const height = Math.max(88, Number(this.composerHeight || 112))
      return {
        bottom: `calc(${height}px + var(--tabbar-height) + env(safe-area-inset-bottom) + 12px)`
      }
    },
    helperPanelTitle() {
      const intent = String((((this.helperContext || {}).intent) || "")).trim()
      if (intent === "reserve_create") return "补充预约信息"
      if (intent === "reserve_query") return "补充查询条件"
      if (intent === "repair_create") return "补充报修信息"
      return "补充信息"
    },
    activeHelperQuestions() {
      return Array.isArray((this.helperContext || {}).questions) ? this.helperContext.questions : []
    },
    activeHelperPlans() {
      return Array.isArray((this.helperContext || {}).plans) ? this.helperContext.plans : []
    },
    activeHelperMissingSlots() {
      return Array.isArray((this.helperContext || {}).missingSlots) ? this.helperContext.missingSlots : []
    },
    canSubmitHelperForm() {
      return [
        this.helperForm.selectedPlanId,
        this.helperForm.labName,
        this.helperForm.date,
        this.helperForm.time,
        this.helperForm.reason,
        this.helperForm.description,
        this.helperForm.location,
        this.helperForm.equipmentHint
      ].some((item) => Boolean(String(item || "").trim()))
    }
  },
  onLoad() {
    this._scrollTimers = []
    this._measureTimer = null
    this.initVoiceRecognizer()
  },
  onShow() {
    this.loadHistory()
    this.scheduleMeasureLayout()
  },
  onUnload() {
    this.clearScrollTimers()
    this.clearMeasureTimer()
    if (this.recording) this.stopVoiceRecord()
  },
  methods: {
    createMessage(role, text, meta = "", tone = "", extra = {}) {
      const payload = extra && typeof extra === "object" ? extra : {}
      this.messageSeq += 1
      return {
        domId: `chat-msg-${Date.now()}-${this.messageSeq}`,
        role: role === "user" ? "user" : "assistant",
        text: String(text || ""),
        meta: String(meta || ""),
        tone: String(tone || ""),
        action: String(payload.action || "").trim(),
        sources: this.normalizeSources(payload.sources),
        helper: role === "user" ? null : normalizeAssistantHelper(payload, payload.action, text)
      }
    },
    appendMessage(role, text, meta = "", tone = "", forceScroll = false, extra = {}) {
      this.messages.push(this.createMessage(role, text, meta, tone, extra))
      this.scheduleMeasureLayout(forceScroll || this.isNearBottom)
      if (forceScroll || this.isNearBottom) {
        this.scrollToBottom(forceScroll)
        return
      }
      this.showBackToBottom = this.messages.length > 0
    },
    helperSlotLabel(slot) {
      const key = String(slot || "").trim()
      if (key === "labName") return "实验室"
      if (key === "date") return "日期"
      if (key === "time") return "时间段"
      if (key === "reason") return "用途"
      if (key === "description") return "故障描述"
      if (key === "location") return "报修位置"
      if (key === "equipmentHint") return "设备编号"
      if (key === "selectedPlanId") return "方案"
      return key || "补充信息"
    },
    resetHelperForm() {
      this.helperForm = {
        labName: "",
        date: "",
        time: "",
        reason: "",
        description: "",
        location: "",
        equipmentHint: "",
        selectedPlanId: ""
      }
    },
    fillHelperForm(helper) {
      this.resetHelperForm()
      const slots = helper && helper.slots && typeof helper.slots === "object" ? helper.slots : {}
      this.helperForm = {
        labName: String(slots.labName || "").trim(),
        date: String(slots.date || "").trim(),
        time: String(slots.time || "").trim(),
        reason: String(slots.reason || "").trim(),
        description: String(slots.description || "").trim(),
        location: String(slots.location || "").trim(),
        equipmentHint: String(slots.equipmentHint || "").trim(),
        selectedPlanId: String(slots.selectedPlanId || "").trim()
      }
    },
    async loadHelperLabs() {
      if (this.helperLabOptions.length > 0) return
      try {
        const response = await listLabs()
        const rows = Array.isArray(response && response.data && response.data.data) ? response.data.data : []
        this.helperLabOptions = rows
          .map((item) => ({
            id: Number((item || {}).id || 0),
            name: String((item || {}).name || "").trim()
          }))
          .filter((item) => item.name)
      } catch (error) {
        this.helperLabOptions = []
      }
    },
    async openHelperPanel(helper) {
      const payload = helper && typeof helper === "object" ? helper : null
      if (!payload) return
      const missingSlots = Array.isArray(payload.missingSlots) ? payload.missingSlots : []
      const plans = Array.isArray(payload.plans) ? payload.plans : []
      const questions = Array.isArray(payload.questions) ? payload.questions : []
      if (missingSlots.length === 0 && plans.length === 0 && questions.length === 0) return
      this.helperContext = payload
      this.fillHelperForm(payload)
      this.helperDateOptions = buildHelperDateOptions()
      this.helperVisible = true
      if (Array.isArray(payload.missingSlots) && payload.missingSlots.includes("labName")) {
        await this.loadHelperLabs()
      }
    },
    closeHelperPanel() {
      this.helperVisible = false
    },
    shouldShowHelperField(field) {
      if (field === "selectedPlanId") return this.activeHelperPlans.length > 0
      return this.activeHelperMissingSlots.includes(field)
    },
    selectHelperPlan(plan) {
      const row = plan && typeof plan === "object" ? plan : {}
      this.helperForm.selectedPlanId = String(row.planId || "").trim()
      if (row.labName) this.helperForm.labName = row.labName
      if (row.date) this.helperForm.date = row.date
      if (row.time) this.helperForm.time = row.time
    },
    buildHelperSubmitText() {
      const intent = String(((this.helperContext || {}).intent) || "").trim()
      const missingSlots = Array.isArray((this.helperContext || {}).missingSlots) ? this.helperContext.missingSlots : []
      const lines = []
      if (intent === "reserve_query" || (!intent && missingSlots.includes("labName") && (missingSlots.includes("date") || this.helperForm.date) && (missingSlots.includes("time") || this.helperForm.time))) {
        return `帮我查询 ${this.helperForm.labName || "该实验室"} ${this.helperForm.date || ""} ${this.helperForm.time || ""} 是否已被预约`.replace(/\s+/g, " ").trim()
      }
      if (intent === "reserve_create") {
        const reasonText = this.helperForm.reason ? `，用途：${this.helperForm.reason}` : ""
        return `帮我预约 ${this.helperForm.labName || "该实验室"} ${this.helperForm.date || ""} ${this.helperForm.time || ""}${reasonText}`.replace(/\s+/g, " ").trim()
      }
      if (intent === "repair_create") {
        const target = this.helperForm.equipmentHint || this.helperForm.location || this.helperForm.labName || "该位置"
        return `帮我提交报修，位置：${target}；故障描述：${this.helperForm.description || "待补充"}`
      }
      if (this.helperForm.selectedPlanId) lines.push(`我选择方案 ${this.helperForm.selectedPlanId}`)
      if (this.helperForm.labName) lines.push(`实验室名称：${this.helperForm.labName}`)
      if (this.helperForm.date) lines.push(`日期：${this.helperForm.date}`)
      if (this.helperForm.time) lines.push(`时间段：${this.helperForm.time}`)
      if (this.helperForm.reason) lines.push(`用途：${this.helperForm.reason}`)
      if (this.helperForm.description) lines.push(`故障描述：${this.helperForm.description}`)
      if (this.helperForm.location) lines.push(`报修位置：${this.helperForm.location}`)
      if (this.helperForm.equipmentHint) lines.push(`设备编号：${this.helperForm.equipmentHint}`)
      return lines.join("；")
    },
    submitHelperPanel() {
      if (!this.canSubmitHelperForm || this.sending) return
      const text = this.buildHelperSubmitText()
      if (!text) {
        uni.showToast({ title: "请先补充内容", icon: "none" })
        return
      }
      this.helperVisible = false
      this.sendText(text)
    },
    scrollToBottom(force = false) {
      if (force) {
        this.isNearBottom = true
        this.showBackToBottom = false
      }
      const targetId = this.messages.length > 0 ? this.messages[this.messages.length - 1].domId : "chat-bottom-anchor"
      this.clearScrollTimers()
      ;[0, 80, 180].forEach((delay) => {
        const timer = setTimeout(() => {
          this.$nextTick(() => {
            const scrolled = this.scrollToBottomH5()
            if (scrolled) return
            this.scrollAnchorId = ""
            this.$nextTick(() => {
              this.scrollAnchorId = targetId || "chat-bottom-anchor"
            })
          })
        }, delay)
        this._scrollTimers.push(timer)
      })
    },
    getH5ScrollElement() {
      if (typeof document === "undefined") return null
      const root = document.querySelector(".agentPage .chatScroll")
      if (!root) return null
      if (typeof root.scrollTo === "function" && root.scrollHeight > root.clientHeight) return root
      const candidates = root.querySelectorAll("*")
      for (let i = 0; i < candidates.length; i += 1) {
        const node = candidates[i]
        if (!node) continue
        if (node.scrollHeight > node.clientHeight + 4 && /(auto|scroll)/.test(String(window.getComputedStyle(node).overflowY || ""))) {
          return node
        }
      }
      return root
    },
    scrollToBottomH5() {
      if (typeof window === "undefined" || typeof document === "undefined") return false
      const el = this.getH5ScrollElement()
      if (!el) return false
      try {
        el.scrollTo({
          top: Math.max(0, Number(el.scrollHeight || 0)),
          behavior: "smooth"
        })
      } catch (e) {
        el.scrollTop = Math.max(0, Number(el.scrollHeight || 0))
      }
      return true
    },
    clearScrollTimers() {
      const timers = Array.isArray(this._scrollTimers) ? this._scrollTimers : []
      timers.forEach((timer) => clearTimeout(timer))
      this._scrollTimers = []
    },
    clearMeasureTimer() {
      if (this._measureTimer) {
        clearTimeout(this._measureTimer)
        this._measureTimer = null
      }
    },
    scheduleMeasureLayout(scrollAfterMeasure = false) {
      this.clearMeasureTimer()
      this._measureTimer = setTimeout(() => {
        this.measureLayout(scrollAfterMeasure)
      }, 40)
    },
    measureLayout(scrollAfterMeasure = false) {
      const query = uni.createSelectorQuery().in(this)
      query.select(".inputSection").boundingClientRect()
      query.select(".chatScroll").boundingClientRect()
      query.exec((res) => {
        const inputRect = (res && res[0]) || {}
        const chatRect = (res && res[1]) || {}
        const nextComposerHeight = Math.max(88, Math.ceil(Number(inputRect.height || 0) || 0))
        const nextViewportHeight = Math.max(0, Math.ceil(Number(chatRect.height || 0) || 0))
        if (nextComposerHeight) this.composerHeight = nextComposerHeight
        if (nextViewportHeight) this.chatViewportHeight = nextViewportHeight
        if (scrollAfterMeasure) this.scrollToBottom(true)
      })
    },
    onChatScroll(event) {
      const detail = (event && event.detail) || {}
      let scrollTop = Number(detail.scrollTop || 0)
      let scrollHeight = Number(detail.scrollHeight || 0)
      let viewportHeight = Number(this.chatViewportHeight || 0)
      const h5El = this.getH5ScrollElement()
      if (h5El) {
        scrollTop = Number(h5El.scrollTop || 0)
        scrollHeight = Number(h5El.scrollHeight || 0)
        viewportHeight = Number(h5El.clientHeight || viewportHeight || 0)
      }
      if (viewportHeight <= 0 || scrollHeight <= 0) return
      const remain = scrollHeight - (scrollTop + viewportHeight)
      const nearBottom = remain <= 96
      this.isNearBottom = nearBottom
      this.showBackToBottom = !nearBottom && this.messages.length > 0
    },
    onBackToBottom() {
      this.scrollToBottom(true)
    },
    onInputFocus() {
      this.inputFocused = true
      this.scheduleMeasureLayout(true)
    },
    onInputBlur() {
      this.inputFocused = false
      this.scheduleMeasureLayout(false)
    },
    async loadHistory(force = false) {
      if (this.loadingHistory) return
      if (!force && this.historyLoaded && this.messages.length > 0) {
        this.scheduleMeasureLayout(true)
        return
      }
      this.loadingHistory = true
      try {
        const res = await uni.request({
          url: `${BASE_URL}/agent/history?limit=120`,
          method: "GET"
        })
        const payload = (res && res.data) || {}
        const rows = payload && payload.data && Array.isArray(payload.data.messages) ? payload.data.messages : []
        this.messages = rows
          .map((row) => {
            const role = String((row && row.role) || "").trim() === "user" ? "user" : "assistant"
            const text = String((row && row.text) || "").trim()
            if (!text) return null
            const action = String((row && row.action) || "").trim()
            const meta = row && row.meta && typeof row.meta === "object" ? row.meta : {}
            return this.createMessage(
              role,
              text,
              role === "assistant" && action ? `动作：${action}` : "",
              "",
              {
                action,
                sources: meta.sources,
                pending: meta.pending,
                questions: meta.questions,
                plans: meta.plans
              }
            )
          })
          .filter(Boolean)
        const lastUser = [...this.messages].reverse().find((m) => m && m.role === "user" && m.text)
        this.lastUserText = lastUser ? String(lastUser.text || "").trim() : ""
        const lastHelper = [...this.messages].reverse().find((m) => m && m.role !== "user" && m.helper)
        if (lastHelper && lastHelper.helper) {
          this.openHelperPanel(lastHelper.helper)
        }
      } catch (e) {
      } finally {
        this.historyLoaded = true
        this.loadingHistory = false
        this.scheduleMeasureLayout(true)
      }
    },
    clearLocalHistory() {
      this.messages = []
      this.lastUserText = ""
      this.inputText = ""
      this.showBackToBottom = false
      this.isNearBottom = true
      this.scheduleMeasureLayout(true)
    },
    sendText(prefillText = "", displayText = "") {
      const text = String(prefillText || this.inputText || "").trim()
      if (!text || this.sending) return
      this.inputText = ""
      this.scrollToBottom(true)
      this.requestAgent(text, true, displayText)
    },
    sendWebSearch() {
      const query = String(this.inputText || "").trim()
      if (!query || this.sending) {
        if (!this.sending) uni.showToast({ title: "请输入要搜索的内容", icon: "none" })
        return
      }
      const normalizedQuery = query.replace(/^联网搜索[\s:：]*/i, "")
      const requestText = /^联网搜索[\s:：]/.test(query) ? query : `联网搜索 ${normalizedQuery}`
      this.sendText(requestText, `联网搜索：${normalizedQuery}`)
    },
    normalizeSources(rawSources) {
      if (!Array.isArray(rawSources)) return []
      const items = []
      rawSources.forEach((item) => {
        const row = item && typeof item === "object" ? item : {}
        const title = String(row.title || "").trim()
        const url = String(row.url || "").trim()
        const publishedDate = String(row.publishedDate || row.published_date || "").trim()
        if (!title && !url) return
        items.push({
          title: title.slice(0, 200),
          url: url.slice(0, 500),
          publishedDate: publishedDate.slice(0, 40)
        })
      })
      return items.slice(0, 6)
    },
    sourceHost(rawUrl) {
      const url = String(rawUrl || "").trim()
      if (!url) return "未提供链接"
      const compact = url.replace(/^https?:\/\//i, "").replace(/^www\./i, "")
      const host = compact.split("/")[0]
      return host || compact || url
    },
    openSourceLink(source) {
      const row = source && typeof source === "object" ? source : {}
      const url = String(row.url || "").trim()
      if (!url) return
      // #ifdef H5
      if (typeof window !== "undefined" && typeof window.open === "function") {
        window.open(url, "_blank")
        return
      }
      // #endif
      // #ifdef APP-PLUS
      try {
        if (typeof plus !== "undefined" && plus.runtime && typeof plus.runtime.openURL === "function") {
          plus.runtime.openURL(url)
          return
        }
      } catch (e) {}
      // #endif
      uni.setClipboardData({
        data: url,
        success: () => {
          uni.showToast({ title: "链接已复制", icon: "success" })
        }
      })
    },
    requestAgent(text, appendUser = true, displayText = "") {
      if (!text || this.sending) return
      const shouldForceReplyScroll = appendUser || this.isNearBottom
      if (appendUser) this.appendMessage("user", displayText || text, "", "", true)
      this.lastUserText = text
      this.sending = true

      uni.request({
        url: `${BASE_URL}/agent/chat`,
        method: "POST",
        header: { "Content-Type": "application/json" },
        data: { text },
        success: (res) => {
          const payload = res.data || {}
          const data = payload.data || {}
          const sources = this.normalizeSources(data.sources)
          const helperPayload = normalizeAssistantHelper(data, data.action)
          if (payload.code !== 0) {
            const msg = String(payload.msg || "").trim() || "请求失败"
            const reply = String(data.reply || "").trim() || msg || "处理失败，请稍后重试。"
            this.appendMessage("assistant", reply, msg, "warn", shouldForceReplyScroll, {
              action: data.action,
              sources,
              pending: data.pending,
              questions: data.questions,
              plans: data.plans
            })
            if (helperPayload) this.openHelperPanel(helperPayload)
            return
          }

          const reply = data.reply || "\u5df2\u5904\u7406\u5b8c\u6210\u3002"
          const action = data.action || "reply"
          this.appendMessage("assistant", reply, `\u52a8\u4f5c\uff1a${action}`, "", shouldForceReplyScroll, {
            action,
            sources,
            pending: data.pending,
            questions: data.questions,
            plans: data.plans
          })
          if (helperPayload) this.openHelperPanel(helperPayload)
          if (action === "update_profile") {
            this.applyProfilePatch(data.profile || {})
          }

        },
        fail: () => {
          this.appendMessage("assistant", "\u7f51\u7edc\u5f02\u5e38\uff0c\u8bf7\u7a0d\u540e\u91cd\u8bd5\u3002", "\u8fde\u63a5\u5931\u8d25", "warn", shouldForceReplyScroll)
        },
        complete: () => {
          this.sending = false
          if (shouldForceReplyScroll) this.scrollToBottom(true)
        }
      })
    },
    applyProfilePatch(rawProfile) {
      const profile = rawProfile && typeof rawProfile === "object" ? rawProfile : {}
      const hasNickname = Object.prototype.hasOwnProperty.call(profile, "nickname")
      const hasPhone = Object.prototype.hasOwnProperty.call(profile, "phone")
      const hasAvatarUrl = Object.prototype.hasOwnProperty.call(profile, "avatarUrl")
      if (!hasNickname && !hasPhone && !hasAvatarUrl) return false
      const session = uni.getStorageSync("session") || {}
      const account = String(session.username || "").trim()
      if (!account) return false

      const oldProfile = uni.getStorageSync(profileStorageKey(account)) || {}
      const nextProfile = {
        ...oldProfile,
        account
      }
      if (hasNickname) nextProfile.nickname = String(profile.nickname || "").trim().slice(0, 24)
      if (hasPhone) nextProfile.phone = String(profile.phone || "").trim().slice(0, 20)
      if (hasAvatarUrl) nextProfile.avatar = String(profile.avatarUrl || "").trim().slice(0, 255)

      uni.setStorageSync(profileStorageKey(account), {
        ...nextProfile
      })
      try {
        uni.$emit("profile:updated", {
          account,
          nickname: String(nextProfile.nickname || "").trim(),
          phone: String(nextProfile.phone || "").trim(),
          avatarUrl: String(nextProfile.avatar || "").trim()
        })
      } catch (e) {}
      return true
    },
    openHeaderMenu() {
      uni.showActionSheet({
        itemList: ["\u6e05\u7a7a\u5386\u53f2\u8bb0\u5f55"],
        success: (event) => {
          if (event.tapIndex !== 0) return
          this.confirmClearHistory()
        }
      })
    },
    confirmClearHistory() {
      uni.showModal({
        title: "\u63d0\u793a",
        content: "\u786e\u5b9a\u8981\u6e05\u7a7a\u5417\uff0c\u6b64\u64cd\u4f5c\u4e0d\u53ef\u9006\u3002",
        confirmColor: "#F5222D",
        success: async (res) => {
          if (!res.confirm) return
          this.clearLocalHistory()
          try {
            await uni.request({
              url: `${BASE_URL}/agent/history/clear`,
              method: "POST",
              header: { "Content-Type": "application/json" },
              data: {}
            })
          } catch (e) {
          }
          uni.showToast({ title: "\u5df2\u6e05\u7a7a", icon: "success" })
        }
      })
    },
    onMessageLongPress(index) {
      const item = this.messages[index]
      if (!item || !item.text) return

      uni.showActionSheet({
        itemList: ["\u590d\u5236\u5185\u5bb9", "\u91cd\u65b0\u751f\u6210"],
        success: (event) => {
          if (event.tapIndex === 0) {
            const sourceText = Array.isArray(item.sources) && item.sources.length > 0
              ? `\n\n来源：\n${item.sources.map((source, idx) => `[${idx + 1}] ${source.title || source.url}\n${source.url || ""}`).join("\n")}`
              : ""
            uni.setClipboardData({
              data: `${item.text || ""}${sourceText}`,
              success: () => {
                uni.showToast({ title: "\u5df2\u590d\u5236", icon: "success" })
              }
            })
            return
          }

          const sourceText = this.findNearestUserText(index)
          if (!sourceText) {
            uni.showToast({ title: "\u672a\u627e\u5230\u53ef\u91cd\u65b0\u751f\u6210\u5185\u5bb9", icon: "none" })
            return
          }
          this.requestAgent(sourceText, false)
        }
      })
    },
    findNearestUserText(index) {
      for (let i = Number(index); i >= 0; i -= 1) {
        const row = this.messages[i]
        if (row && row.role === "user" && row.text) return String(row.text).trim()
      }
      return String(this.lastUserText || "").trim()
    },
    toggleVoiceRecord() {
      if (this.recording) {
        this.stopVoiceRecord()
        return
      }
      this.startVoiceRecord()
    },
    initVoiceRecognizer() {
      // #ifdef MP-WEIXIN
      if (!wechatSIPlugin || !wechatSIPlugin.getRecordRecognitionManager) {
        this.recognizer = null
        return
      }
      const manager = wechatSIPlugin.getRecordRecognitionManager()
      if (!manager) {
        this.recognizer = null
        return
      }
      this.recognizer = manager

      manager.onRecognize = (res) => {
        const partial = res && res.result ? String(res.result) : ""
        if (partial) this.inputText = partial
      }

      manager.onStop = (res) => {
        this.recording = false
        this.scheduleMeasureLayout(false)
        const result = res && res.result ? String(res.result).trim() : ""
        if (!result) {
          uni.showToast({ title: "\u672a\u8bc6\u522b\u5230\u6709\u6548\u8bed\u97f3", icon: "none" })
          return
        }
        this.sendText(result)
      }

      manager.onError = () => {
        this.recording = false
        this.scheduleMeasureLayout(false)
        uni.showToast({ title: "\u8bed\u97f3\u8bc6\u522b\u5931\u8d25", icon: "none" })
      }
      // #endif
    },
    startVoiceRecord() {
      // #ifdef MP-WEIXIN
      if (!this.recognizer) {
        uni.showToast({ title: "\u5f53\u524d\u73af\u5883\u4e0d\u652f\u6301\u8bed\u97f3\u8bc6\u522b", icon: "none" })
        return
      }
      if (this.recording) return
      this.recording = true
      this.scheduleMeasureLayout(false)
      this.recognizer.start({
        lang: "zh_CN",
        duration: 60000
      })
      // #endif
      // #ifndef MP-WEIXIN
      uni.showToast({ title: "\u5f53\u524d\u73af\u5883\u4e0d\u652f\u6301\u8bed\u97f3\u8bc6\u522b", icon: "none" })
      // #endif
    },
    stopVoiceRecord() {
      // #ifdef MP-WEIXIN
      if (!this.recognizer || !this.recording) return
      this.recognizer.stop()
      this.scheduleMeasureLayout(false)
      // #endif
    }
  }
}
</script>

<style lang="scss">
page {
  background: var(--color-bg-page);
}

.agentPage {
  --color-primary-dark: var(--color-primary-strong);
  --color-primary-light: var(--color-info-soft);
  --color-warning: var(--warning);
  --color-danger: var(--danger);
  --color-page-bg: var(--color-bg-page);
  --color-card-bg: var(--color-bg-card);
  --color-input-bg: var(--color-bg-soft);
  --tabbar-height: 50px;
  --composer-height: 60px;
  height: 100vh;
  background: var(--color-bg-page);
  color: var(--color-text-primary);
  display: flex;
  justify-content: center;
  overflow: hidden;
  font-family: "Source Han Sans SC", "PingFang SC", "HarmonyOS Sans", "Inter", "SF Pro Text", "SF Pro", sans-serif;
}

.pageInner {
  width: 100%;
  max-width: 480px;
  height: 100vh;
  padding: 0;
  background: var(--color-bg-card);
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: 0;
  overflow: hidden;
}

.headerSection {
  position: fixed;
  left: 50%;
  transform: translateX(-50%);
  width: 100%;
  max-width: 480px;
  top: var(--window-top, 0px);
  z-index: 30;
  background: var(--color-bg-card);
}

.titleBar {
  height: 56px;
  border-radius: 0;
  background: var(--color-bg-card);
  padding: 0 16px;
  box-sizing: border-box;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.titleLeft {
  display: flex;
  align-items: center;
  gap: 12px;
}

.titleAvatar {
  width: 36px;
  height: 36px;
  border-radius: 18px;
  overflow: hidden;
  flex-shrink: 0;
}

.titleName {
  font-size: 18px;
  line-height: 26px;
  font-weight: 500;
  color: var(--color-text-primary);
}

.menuButton {
  width: 32px;
  height: 32px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg-soft);
}

.menuButton:active {
  transform: scale(0.97);
}

.menuDots {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--color-text-muted);
  position: relative;
}

.menuDots::before {
  content: "";
  position: absolute;
  left: 0;
  top: -7px;
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--color-text-muted);
}

.menuDots::after {
  content: "";
  position: absolute;
  left: 0;
  top: 7px;
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--color-text-muted);
}

.chatCard {
  flex: 1;
  min-height: 0;
  padding: 0;
  margin-top: calc(var(--window-top, 0px) + 56px);
  background: var(--color-bg-card);
  overflow: hidden;
}

.chatScroll {
  height: 100%;
}

.defaultDialog {
  min-height: 100%;
  padding: 8px 16px 24px;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
}

.defaultDialog.withMessages {
  min-height: auto;
  padding-bottom: 16px;
}

.defaultCircle {
  width: 52vw;
  height: 52vw;
  max-width: 260px;
  max-height: 260px;
  min-width: 180px;
  min-height: 180px;
  border-radius: 50%;
  overflow: hidden;
  background: var(--color-info-soft);
  flex-shrink: 0;
}

.defaultGif {
  width: 100%;
  height: 100%;
}

.defaultText {
  margin-top: 24px;
  max-width: 78%;
  background: var(--color-bg-soft);
  border-radius: 16px;
  padding: 12px;
  box-sizing: border-box;
  font-size: 14px;
  line-height: 22px;
  color: var(--color-text-primary);
  word-break: break-word;
}

.bubbleList {
  padding: 16px;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.bubbleRow {
  display: flex;
}

.bubbleRow.user {
  justify-content: flex-end;
}

.bubbleRow.assistant {
  justify-content: flex-start;
}

.bubble {
  max-width: 70%;
  border-radius: 16px;
  padding: 12px;
  box-sizing: border-box;
  animation: fadeIn 0.2s ease;
  word-break: break-word;
}

.userBubble {
  background: var(--color-primary);
  color: var(--color-text-inverse);
}

.assistantBubble {
  background: var(--color-bg-soft);
  color: var(--color-text-primary);
}

.bubbleText {
  font-size: 14px;
  line-height: 22px;
  font-weight: 400;
  white-space: pre-wrap;
}

.bubbleMeta {
  margin-top: 8px;
  font-size: 12px;
  line-height: 18px;
  font-weight: 400;
  color: var(--color-text-muted);
}

.bubbleWarn {
  color: var(--danger);
}

.bubbleActions {
  display: flex;
  justify-content: flex-end;
  margin-top: 10px;
}

.bubbleActionButton {
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(59, 130, 246, 0.1);
  color: var(--color-primary);
  font-size: 12px;
  line-height: 16px;
}

.bubbleActionButton:active {
  transform: scale(0.98);
}

.sourcePanel {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid rgba(148, 163, 184, 0.2);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sourceHeader {
  font-size: 12px;
  line-height: 18px;
  color: var(--color-text-muted);
}

.sourceItem {
  display: flex;
  gap: 10px;
  padding: 10px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.78);
}

.theme-dark .sourceItem {
  background: rgba(15, 23, 42, 0.36);
}

.sourceIndex {
  width: 20px;
  height: 20px;
  border-radius: 10px;
  background: var(--color-info-soft);
  color: var(--color-primary);
  font-size: 12px;
  line-height: 20px;
  text-align: center;
  flex-shrink: 0;
}

.sourceBody {
  min-width: 0;
  flex: 1;
}

.sourceTitle {
  font-size: 13px;
  line-height: 19px;
  color: var(--color-text-primary);
  word-break: break-word;
}

.sourceMeta {
  margin-top: 4px;
  font-size: 11px;
  line-height: 16px;
  color: var(--color-text-muted);
  word-break: break-all;
}

.buttonBase {
  height: 40px;
  border-radius: 20px;
  padding: 0 20px;
  box-sizing: border-box;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  line-height: 20px;
  font-weight: 500;
  transition: transform 0.1s ease, background-color 0.2s ease;
}

.buttonBase:active {
  transform: scale(0.97);
}

.primaryButton {
  background: var(--color-primary);
  color: var(--color-text-inverse);
}

.secondaryButton {
  background: var(--color-bg-soft);
  color: var(--color-primary);
  border: 1px solid var(--color-border-focus);
}

.primaryButton:active {
  background: var(--color-primary-strong);
}

.secondaryButton:active {
  transform: scale(0.97);
}

.inputSection {
  position: fixed;
  left: 50%;
  transform: translateX(-50%);
  width: 100%;
  max-width: 480px;
  bottom: calc(var(--tabbar-height) + env(safe-area-inset-bottom));
  z-index: 20;
  background: var(--color-bg-card);
  padding: 8px 16px;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.quickActions {
  width: 100%;
  white-space: nowrap;
}

.quickActionsInner {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-width: 100%;
}

.quickActionChip {
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.14);
  border: 1px solid rgba(148, 163, 184, 0.22);
  color: var(--color-text-primary);
  font-size: 13px;
  line-height: 18px;
  flex-shrink: 0;
}

.theme-dark .quickActionChip {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.12);
}

.quickActionChip:active {
  transform: scale(0.98);
}

.inputRow {
  display: flex;
  align-items: center;
  gap: 8px;
}

.inputWrap {
  flex: 1;
  height: 44px;
  border-radius: 20px;
  background: var(--color-bg-soft);
  border: 1px solid transparent;
  box-sizing: border-box;
  padding: 0 8px 0 14px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.inputWrap.focused {
  border: 1px solid var(--color-border-focus);
}

.inputBox {
  flex: 1;
  height: 100%;
  font-size: 14px;
  font-weight: 400;
  color: var(--color-text-primary);
  background: transparent;
}

.voiceIconBtn {
  width: 32px;
  height: 32px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-info-soft);
  flex-shrink: 0;
  transition: transform 0.1s ease, background-color 0.2s ease;
}

.voiceIconBtn:active {
  transform: scale(0.97);
}

.voiceIconBtn.recording {
  background: var(--color-info-soft);
}

.voiceIcon {
  width: 12px;
  height: 14px;
  border: 2px solid var(--color-primary);
  border-radius: 7px;
  box-sizing: border-box;
  position: relative;
}

.voiceIcon::before {
  content: "";
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  bottom: -6px;
  width: 2px;
  height: 5px;
  background: var(--color-primary);
}

.voiceIcon::after {
  content: "";
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  bottom: -9px;
  width: 10px;
  height: 2px;
  background: var(--color-primary);
}

.sendButton {
  min-width: 64px;
  flex-shrink: 0;
}

.searchTriggerButton {
  min-width: 78px;
  flex-shrink: 0;
}

.hintText {
  font-size: 12px;
  line-height: 18px;
  font-weight: 400;
  color: var(--warning);
}

.backToBottomWrap {
  position: fixed;
  left: 50%;
  transform: translateX(-50%);
  width: 100%;
  max-width: 480px;
  z-index: 25;
  padding: 0 16px;
  box-sizing: border-box;
  display: flex;
  justify-content: flex-end;
  pointer-events: none;
}

.backToBottomButton {
  min-width: 88px;
  height: 34px;
  padding: 0 14px;
  border-radius: 17px;
  background: rgba(15, 23, 42, 0.88);
  color: #fff;
  font-size: 12px;
  line-height: 34px;
  text-align: center;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.18);
  pointer-events: auto;
}

.theme-dark .backToBottomButton {
  background: rgba(30, 41, 59, 0.92);
}

.helperOverlay {
  position: fixed;
  inset: 0;
  z-index: 40;
  background: rgba(15, 23, 42, 0.36);
  display: flex;
  align-items: flex-end;
  justify-content: center;
}

.helperSheet {
  width: 100%;
  max-width: 480px;
  max-height: 78vh;
  background: var(--color-card-bg);
  border-radius: 24px 24px 0 0;
  padding: 12px 16px calc(20px + env(safe-area-inset-bottom));
  box-sizing: border-box;
  overflow-y: auto;
  box-shadow: 0 -18px 40px rgba(15, 23, 42, 0.18);
}

.helperHandle {
  width: 48px;
  height: 5px;
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.4);
  margin: 0 auto 12px;
}

.helperHeader {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.helperTitle {
  font-size: 18px;
  line-height: 26px;
  font-weight: 700;
  color: var(--color-text-primary);
}

.helperDesc {
  margin-top: 6px;
  font-size: 12px;
  line-height: 18px;
  color: var(--color-text-secondary);
}

.helperClose {
  font-size: 13px;
  line-height: 20px;
  color: var(--color-primary);
  padding-top: 2px;
}

.helperSection {
  margin-top: 16px;
  padding: 14px;
  border-radius: 18px;
  background: var(--color-bg-soft);
  border: 1px solid rgba(148, 163, 184, 0.16);
}

.helperLabel {
  margin-bottom: 10px;
  font-size: 12px;
  line-height: 18px;
  font-weight: 600;
  color: var(--color-text-secondary);
}

.helperTagRow,
.helperChipRow {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.helperTag,
.helperChip {
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(148, 163, 184, 0.2);
  color: var(--color-text-primary);
  font-size: 12px;
  line-height: 16px;
}

.helperChip.active {
  background: rgba(59, 130, 246, 0.12);
  border-color: rgba(59, 130, 246, 0.3);
  color: var(--color-primary);
}

.helperTip {
  font-size: 13px;
  line-height: 20px;
  color: var(--color-text-primary);
}

.helperTip + .helperTip {
  margin-top: 8px;
}

.helperPlanCard {
  padding: 12px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(148, 163, 184, 0.18);
}

.helperPlanCard + .helperPlanCard {
  margin-top: 10px;
}

.helperPlanCard.active {
  background: rgba(59, 130, 246, 0.1);
  border-color: rgba(59, 130, 246, 0.32);
}

.helperPlanTop {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.helperPlanId {
  font-size: 13px;
  line-height: 18px;
  font-weight: 700;
  color: var(--color-primary);
}

.helperPlanLab,
.helperPlanMeta {
  font-size: 12px;
  line-height: 18px;
  color: var(--color-text-secondary);
}

.helperPlanMeta {
  margin-top: 6px;
}

.helperTextarea,
.helperInput {
  width: 100%;
  box-sizing: border-box;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid rgba(148, 163, 184, 0.2);
  color: var(--color-text-primary);
  font-size: 13px;
  line-height: 20px;
  padding: 12px;
}

.helperTextarea {
  min-height: 92px;
}

.helperFooter {
  display: flex;
  gap: 10px;
  margin-top: 18px;
}

.helperSecondaryButton,
.helperPrimaryButton {
  flex: 1;
  height: 42px;
  border-radius: 21px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  line-height: 20px;
}

.helperSecondaryButton {
  background: var(--color-bg-soft);
  color: var(--color-text-secondary);
}

.helperPrimaryButton {
  background: var(--color-primary);
  color: #fff;
}

.helperPrimaryButton.disabled {
  opacity: 0.45;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (hover: hover) {
  .primaryButton:hover {
    background: var(--color-primary-strong);
  }
}

</style>


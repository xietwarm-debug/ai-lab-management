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

      <view class="chatCard">
        <scroll-view class="chatScroll" scroll-y :scroll-into-view="scrollAnchorId" :scroll-with-animation="true">
          <view class="defaultDialog" :class="{ withMessages: messages.length > 0 }">
            <view class="defaultCircle">
              <image class="defaultGif" src="/static/1.gif" mode="aspectFill"></image>
            </view>
            <view class="defaultText">
              &#21992;&#65292;&#25105;&#26159;&#20320;&#30340;&#26379;&#21451;&#23425;&#23425;&#65281;&#21021;&#27425;&#35265;&#38754;&#24456;&#24320;&#24515;&#12290;&#25105;&#21487;&#20197;&#24110;&#20320;&#29702;&#35299;&#23454;&#39564;&#23460;&#38382;&#39064;&#65292;&#20063;&#21487;&#20197;&#24110;&#20320;&#25552;&#20132;&#23454;&#39564;&#23460;&#39044;&#32422;&#12290;&#20320;&#24819;&#20808;&#20570;&#21738;&#19968;&#20214;&#65311;
            </view>
          </view>
          <view v-if="messages.length > 0" class="bubbleList">
            <view
              class="bubbleRow"
              v-for="(item, idx) in messages"
              :key="`${item.role}-${idx}`"
              :class="{ user: item.role === 'user', assistant: item.role !== 'user' }"
            >
              <view
                class="bubble"
                :class="{ userBubble: item.role === 'user', assistantBubble: item.role !== 'user' }"
                @longpress="onMessageLongPress(idx)"
              >
                <view class="bubbleText">{{ item.text }}</view>
                <view v-if="item.meta" class="bubbleMeta" :class="{ bubbleWarn: item.tone === 'warn' }">
                  {{ item.meta }}
                </view>
              </view>
            </view>
          </view>
          <view id="chat-bottom-anchor"></view>
        </scroll-view>
      </view>

      <view class="inputSection">
        <view class="inputRow">
          <view class="inputWrap" :class="{ focused: inputFocused }">
            <input
              class="inputBox"
              v-model.trim="inputText"
              placeholder="&#35831;&#36755;&#20837;&#39044;&#32422;&#38656;&#27714;"
              confirm-type="send"
              @confirm="sendText()"
              @focus="inputFocused = true"
              @blur="inputFocused = false"
            />
            <view class="voiceIconBtn" :class="{ recording }" @click="toggleVoiceRecord">
              <view class="voiceIcon"></view>
            </view>
          </view>
          <view class="primaryButton buttonBase sendButton" @click="sendText()">
            发送
          </view>
        </view>

        <view v-if="recording" class="hintText">正在录音，点击麦克风结束并发送</view>
      </view>
    </view>
  </view>
</template>

<script>
import { BASE_URL } from "@/common/api.js"
import { themePageMixin } from "@/common/theme.js"

function profileStorageKey(account) {
  return `user_profile_${account}`
}

function detectNicknameChangeCommand(rawText) {
  const text = String(rawText || "").trim()
  if (!text) return ""

  const normalized = text.replace(/[\uFF1A:]/g, " ").replace(/\s+/g, " ").trim()
  const patterns = [
    /(?:\u5e2e\u6211|\u8bf7|\u9ebb\u70e6)?(?:\u628a|\u5c06)?(?:\u6211(?:\u7684)?)?\u6635\u79f0(?:\u6539\u6210|\u6539\u4e3a|\u6362\u6210|\u8bbe\u4e3a|\u8bbe\u7f6e\u4e3a|\u53eb\u505a?)\s*["“”']?([^"“”'\uFF0C\u3002,.!?！？]{1,24})/i,
    /(?:\u5e2e\u6211|\u8bf7|\u9ebb\u70e6)?(?:\u628a|\u5c06)?\u540d\u5b57(?:\u6539\u6210|\u6539\u4e3a|\u6362\u6210|\u8bbe\u4e3a|\u8bbe\u7f6e\u4e3a)\s*["“”']?([^"“”'\uFF0C\u3002,.!?！？]{1,24})/i,
    /(?:\u6211\u7684?)?\u6635\u79f0(?:\u662f|\u53eb)\s*["“”']?([^"“”'\uFF0C\u3002,.!?！？]{1,24})/i
  ]

  for (const rule of patterns) {
    const match = normalized.match(rule)
    if (!match || !match[1]) continue
    return String(match[1]).trim().replace(/[\uFF0C\u3002,.!?！？]+$/g, "")
  }
  return ""
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
      lastUserText: "",
      messages: []
    }
  },
  onLoad() {
    this.initVoiceRecognizer()
  },
  onShow() {
    this.scrollToBottom()
  },
  onUnload() {
    if (this.recording) this.stopVoiceRecord()
  },
  methods: {
    appendMessage(role, text, meta = "", tone = "") {
      this.messages.push({
        role: role === "user" ? "user" : "assistant",
        text: String(text || ""),
        meta: String(meta || ""),
        tone: String(tone || "")
      })
      this.scrollToBottom()
    },
    scrollToBottom() {
      this.$nextTick(() => {
        this.scrollAnchorId = ""
        this.$nextTick(() => {
          this.scrollAnchorId = "chat-bottom-anchor"
        })
      })
    },
    sendText(prefillText = "") {
      const text = String(prefillText || this.inputText || "").trim()
      if (!text || this.sending) return
      this.inputText = ""
      this.requestAgent(text, true)
    },
    requestAgent(text, appendUser = true) {
      if (!text || this.sending) return
      if (appendUser) this.appendMessage("user", text)
      if (this.tryHandleNicknameCommand(text)) return
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
          if (payload.code !== 0) {
            const msg = payload.msg || "\u8bf7\u6c42\u5931\u8d25"
            this.appendMessage("assistant", "\u5904\u7406\u5931\u8d25\uff0c\u8bf7\u7a0d\u540e\u91cd\u8bd5\u3002", msg, "warn")
            return
          }

          const reply = data.reply || "\u5df2\u5904\u7406\u5b8c\u6210\u3002"
          const action = data.action || "reply"
          this.appendMessage("assistant", reply, `\u52a8\u4f5c\uff1a${action}`)
          if (action === "update_profile") {
            const nickname =
              String((((data.profile || {}).nickname) || "").trim()) ||
              detectNicknameChangeCommand(text)
            if (nickname) {
              this.applyNicknameToProfile(nickname)
            }
          }

          if (data.reservation && data.reservation.id) {
            const reservation = data.reservation
            this.appendMessage(
              "assistant",
              `\u9884\u7ea6\u5df2\u521b\u5efa\uff1a#${reservation.id} ${reservation.labName} ${reservation.date} ${reservation.time}`,
              `\u72b6\u6001\uff1a${reservation.status || "pending"}`
            )
          }
        },
        fail: () => {
          this.appendMessage("assistant", "\u7f51\u7edc\u5f02\u5e38\uff0c\u8bf7\u7a0d\u540e\u91cd\u8bd5\u3002", "\u8fde\u63a5\u5931\u8d25", "warn")
        },
        complete: () => {
          this.sending = false
        }
      })
    },
    applyNicknameToProfile(rawNickname) {
      const nickname = String(rawNickname || "").trim().slice(0, 24)
      if (!nickname) return false
      const session = uni.getStorageSync("session") || {}
      const account = String(session.username || "").trim()
      if (!account) return false

      const oldProfile = uni.getStorageSync(profileStorageKey(account)) || {}
      uni.setStorageSync(profileStorageKey(account), {
        ...oldProfile,
        account,
        nickname
      })
      try {
        uni.$emit("profile:updated", { account, nickname })
      } catch (e) {}
      return true
    },
    tryHandleNicknameCommand(text) {
      const nickname = detectNicknameChangeCommand(text)
      if (!nickname) return false

      const applied = this.applyNicknameToProfile(nickname)
      if (!applied) {
        this.appendMessage("assistant", "当前未登录，暂时不能修改昵称。", "请先登录", "warn")
        return true
      }
      this.appendMessage("assistant", `已帮你把昵称改成“${nickname}”`, "动作：update_profile")
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
        success: (res) => {
          if (!res.confirm) return
          this.messages = []
          this.lastUserText = ""
          this.inputText = ""
          this.scrollToBottom()
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
            uni.setClipboardData({
              data: item.text,
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
        const result = res && res.result ? String(res.result).trim() : ""
        if (!result) {
          uni.showToast({ title: "\u672a\u8bc6\u522b\u5230\u6709\u6548\u8bed\u97f3", icon: "none" })
          return
        }
        this.sendText(result)
      }

      manager.onError = () => {
        this.recording = false
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
  margin-bottom: calc(var(--composer-height) + var(--tabbar-height) + env(safe-area-inset-bottom));
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

.primaryButton:active {
  background: var(--color-primary-strong);
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
  min-width: 72px;
  flex-shrink: 0;
}

.hintText {
  font-size: 12px;
  line-height: 18px;
  font-weight: 400;
  color: var(--warning);
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


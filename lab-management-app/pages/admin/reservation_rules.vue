<template>
  <view class="container rulesPage">
    <view class="stack">
      <view class="card heroCard">
        <view class="rowBetween heroTop">
          <view>
            <view class="title">预约规则配置中心</view>
            <view class="subtitle">管理员可视化配置预约规则</view>
          </view>
          <button class="btnSecondary miniBtn" size="mini" :loading="loading" @click="loadRules">刷新</button>
        </view>
      </view>

      <view class="card" v-if="loading">
        <view class="muted">正在加载规则配置...</view>
      </view>

      <template v-else>
        <view class="card">
          <view class="rowBetween sectionHeader">
            <view class="cardTitle">全局规则</view>
            <view class="muted">默认作用于所有实验室</view>
          </view>

          <view class="label">可预约天数</view>
          <view class="grid2">
            <view>
              <view class="muted fieldHint">最小提前天数</view>
              <input class="inputBase" type="number" v-model.number="form.global.minDaysAhead" />
            </view>
            <view>
              <view class="muted fieldHint">最大提前天数</view>
              <input class="inputBase" type="number" v-model.number="form.global.maxDaysAhead" />
            </view>
          </view>

          <view class="label">时段边界</view>
          <view class="grid2">
            <view>
              <view class="muted fieldHint">开始时间（HH:mm）</view>
              <input class="inputBase" v-model.trim="form.global.minTime" placeholder="08:00" />
            </view>
            <view>
              <view class="muted fieldHint">结束时间（HH:mm）</view>
              <input class="inputBase" v-model.trim="form.global.maxTime" placeholder="22:00" />
            </view>
          </view>

          <view class="label">每日可预约时段</view>
          <textarea
            class="textareaBase largeText"
            v-model.trim="form.global.slotsText"
            placeholder="每行一个时段，例如：08:00-08:40"
          />
          <view class="muted">支持逗号/换行分隔</view>

          <view class="label">节假日/停用日</view>
          <textarea
            class="textareaBase"
            v-model.trim="form.global.disabledDatesText"
            placeholder="每行一个日期，例如：2026-03-10"
          />
        </view>

        <view class="card">
          <view class="rowBetween sectionHeader">
            <view class="cardTitle">审批策略</view>
            <view class="muted">全局默认审批流程</view>
          </view>

          <view class="chipRow">
            <view
              v-for="item in approvalModes"
              :key="item.value"
              class="chip modeChip"
              :class="{ chipOn: form.global.approvalMode === item.value }"
              @click="form.global.approvalMode = item.value"
            >
              {{ item.label }}
            </view>
          </view>

          <view class="rowBetween switchRow">
            <view>
              <view class="label inlineLabel">高峰时段强制审批</view>
              <view class="muted">仅当审批模式为自动通过时生效</view>
            </view>
            <switch :checked="form.global.peakForceApproval" @change="onGlobalPeakForceChange" />
          </view>

          <view class="label">高峰时段列表</view>
          <textarea
            class="textareaBase"
            v-model.trim="form.global.peakSlotsText"
            placeholder="每行一个时段，例如：14:30-15:10"
          />
        </view>

        <view class="card">
          <view class="rowBetween sectionHeader">
            <view class="cardTitle">黑名单时间段（全局）</view>
            <button class="btnSecondary miniBtn" size="mini" @click="addGlobalBlackout">新增</button>
          </view>
          <view class="muted" v-if="form.global.blackoutRows.length === 0">暂无黑名单时段</view>
          <view v-for="(row, idx) in form.global.blackoutRows" :key="`global-blackout-${idx}`" class="blackoutRow">
            <input class="inputBase" v-model.trim="row.date" placeholder="日期 YYYY-MM-DD" />
            <textarea class="textareaBase" v-model.trim="row.slotsText" placeholder="时段，逗号或换行分隔" />
            <input class="inputBase" v-model.trim="row.reason" maxlength="120" placeholder="原因（可选）" />
            <view class="rowRight">
              <button class="btnDanger miniBtn" size="mini" @click="removeGlobalBlackout(idx)">删除</button>
            </view>
          </view>
        </view>

        <view class="card">
          <view class="rowBetween sectionHeader">
            <view class="cardTitle">实验室覆盖规则</view>
            <button class="btnSecondary miniBtn" size="mini" @click="addLabRule">新增实验室规则</button>
          </view>
          <view class="muted" v-if="form.labRules.length === 0">暂无覆盖规则，当前仅使用全局规则</view>

          <view class="labRuleCard" v-for="(rule, idx) in form.labRules" :key="`lab-rule-${idx}`">
            <view class="rowBetween">
              <view class="cardTitle">规则 #{{ idx + 1 }}</view>
              <view class="rowBetween actionRow">
                <view class="muted">启用</view>
                <switch :checked="rule.enabled" @change="onLabRuleEnabledChange(idx, $event)" />
                <button class="btnDanger miniBtn" size="mini" @click="removeLabRule(idx)">删除</button>
              </view>
            </view>

            <view class="label">实验室</view>
            <picker :range="labs" range-key="labName" :value="labIndexById(rule.labId)" @change="onLabRuleLabChange(idx, $event)">
              <view class="pickerField">{{ rule.labName || "请选择实验室" }}</view>
            </picker>

            <view class="grid2">
              <view>
                <view class="muted fieldHint">最小提前天数</view>
                <input class="inputBase" type="number" v-model.number="rule.minDaysAhead" />
              </view>
              <view>
                <view class="muted fieldHint">最大提前天数</view>
                <input class="inputBase" type="number" v-model.number="rule.maxDaysAhead" />
              </view>
            </view>

            <view class="grid2">
              <view>
                <view class="muted fieldHint">开始时间</view>
                <input class="inputBase" v-model.trim="rule.minTime" />
              </view>
              <view>
                <view class="muted fieldHint">结束时间</view>
                <input class="inputBase" v-model.trim="rule.maxTime" />
              </view>
            </view>

            <view class="label">每日可预约时段</view>
            <textarea class="textareaBase" v-model.trim="rule.slotsText" placeholder="每行一个时段" />

            <view class="label">停用日</view>
            <textarea class="textareaBase" v-model.trim="rule.disabledDatesText" placeholder="每行一个日期" />

            <view class="label">审批策略</view>
            <view class="chipRow">
              <view
                v-for="item in approvalModes"
                :key="`${item.value}-${idx}`"
                class="chip modeChip"
                :class="{ chipOn: rule.approvalMode === item.value }"
                @click="rule.approvalMode = item.value"
              >
                {{ item.label }}
              </view>
            </view>

            <view class="rowBetween switchRow">
              <view class="muted">高峰时段强制审批</view>
              <switch :checked="rule.peakForceApproval" @change="onLabRulePeakForceChange(idx, $event)" />
            </view>
            <textarea class="textareaBase" v-model.trim="rule.peakSlotsText" placeholder="高峰时段列表（每行一个）" />

            <view class="rowBetween sectionHeader subHeader">
              <view class="muted">黑名单时间段</view>
              <button class="btnSecondary miniBtn" size="mini" @click="addLabBlackout(idx)">新增</button>
            </view>
            <view class="muted" v-if="rule.blackoutRows.length === 0">暂无黑名单时段</view>
            <view v-for="(row, bIdx) in rule.blackoutRows" :key="`lab-blackout-${idx}-${bIdx}`" class="blackoutRow">
              <input class="inputBase" v-model.trim="row.date" placeholder="日期 YYYY-MM-DD" />
              <textarea class="textareaBase" v-model.trim="row.slotsText" placeholder="时段，逗号或换行分隔" />
              <input class="inputBase" v-model.trim="row.reason" maxlength="120" placeholder="原因（可选）" />
              <view class="rowRight">
                <button class="btnDanger miniBtn" size="mini" @click="removeLabBlackout(idx, bIdx)">删除</button>
              </view>
            </view>
          </view>
        </view>

        <view class="card actionCard">
          <view class="rowBetween">
            <button class="btnSecondary miniBtn" size="mini" :loading="loading" @click="loadRules">重载配置</button>
            <button class="btnPrimary miniBtn" size="mini" :loading="saving" @click="saveRules">保存配置</button>
          </view>
        </view>
      </template>
    </view>
  </view>
</template>

<script>
import { BASE_URL } from "@/common/api.js"

const APPROVAL_MODES = [
  { value: "auto", label: "自动通过" },
  { value: "teacher", label: "仅教师审批" },
  { value: "admin", label: "管理员审批" }
]

function splitTextList(text) {
  return String(text || "")
    .split(/[\n,，]/)
    .map((s) => s.trim())
    .filter(Boolean)
}

function toTextList(arr) {
  if (!Array.isArray(arr)) return ""
  return arr
    .map((x) => String(x || "").trim())
    .filter(Boolean)
    .join("\n")
}

function toBlackoutRows(arr) {
  if (!Array.isArray(arr)) return []
  return arr.map((row) => ({
    date: String((row && row.date) || "").trim(),
    slotsText: toTextList((row && row.slots) || []),
    reason: String((row && row.reason) || "").trim()
  }))
}

function emptyBlackoutRow() {
  return { date: "", slotsText: "", reason: "" }
}

function safeRuleForm(rawRule) {
  const rule = rawRule || {}
  const approval = rule.approval || {}
  return {
    enabled: rule.enabled !== false,
    labId: Number(rule.labId || 0),
    labName: String(rule.labName || ""),
    minDaysAhead: Number(rule.minDaysAhead || 0),
    maxDaysAhead: Number(rule.maxDaysAhead || 30),
    minTime: String(rule.minTime || "08:00"),
    maxTime: String(rule.maxTime || "22:00"),
    slotsText: toTextList(rule.slots || []),
    disabledDatesText: toTextList(rule.disabledDates || []),
    approvalMode: String(approval.mode || "admin"),
    peakForceApproval: !!approval.peakForceApproval,
    peakSlotsText: toTextList(approval.peakSlots || []),
    blackoutRows: toBlackoutRows(rule.blackoutSlots || [])
  }
}

export default {
  data() {
    return {
      loading: false,
      saving: false,
      labs: [],
      form: {
        global: safeRuleForm({}),
        labRules: []
      },
      approvalModes: APPROVAL_MODES
    }
  },
  onShow() {
    const s = uni.getStorageSync("session")
    if (!s || s.role !== "admin") {
      uni.showToast({ title: "无权限", icon: "none" })
      uni.reLaunch({ url: "/pages/login/login" })
      return
    }
    this.loadRules()
  },
  methods: {
    normalizeLabNameById(labId) {
      const id = Number(labId || 0)
      const row = this.labs.find((x) => Number((x && x.labId) || 0) === id)
      return row ? String(row.labName || "") : ""
    },
    labIndexById(labId) {
      const id = Number(labId || 0)
      const idx = this.labs.findIndex((x) => Number((x && x.labId) || 0) === id)
      return idx >= 0 ? idx : 0
    },
    onGlobalPeakForceChange(e) {
      this.form.global.peakForceApproval = !!(e && e.detail && e.detail.value)
    },
    onLabRuleEnabledChange(idx, e) {
      if (!this.form.labRules[idx]) return
      this.form.labRules[idx].enabled = !!(e && e.detail && e.detail.value)
    },
    onLabRulePeakForceChange(idx, e) {
      if (!this.form.labRules[idx]) return
      this.form.labRules[idx].peakForceApproval = !!(e && e.detail && e.detail.value)
    },
    onLabRuleLabChange(idx, e) {
      const picked = this.labs[Number(e && e.detail && e.detail.value)]
      if (!picked || !this.form.labRules[idx]) return
      this.form.labRules[idx].labId = Number(picked.labId || 0)
      this.form.labRules[idx].labName = String(picked.labName || "")
    },
    addGlobalBlackout() {
      this.form.global.blackoutRows.push(emptyBlackoutRow())
    },
    removeGlobalBlackout(idx) {
      this.form.global.blackoutRows.splice(idx, 1)
    },
    addLabBlackout(idx) {
      if (!this.form.labRules[idx]) return
      this.form.labRules[idx].blackoutRows.push(emptyBlackoutRow())
    },
    removeLabBlackout(idx, bIdx) {
      if (!this.form.labRules[idx]) return
      this.form.labRules[idx].blackoutRows.splice(bIdx, 1)
    },
    addLabRule() {
      const used = new Set(this.form.labRules.map((x) => Number(x.labId || 0)))
      const candidate = this.labs.find((x) => !used.has(Number((x && x.labId) || 0)))
      if (!candidate) {
        uni.showToast({ title: "没有可新增的实验室", icon: "none" })
        return
      }
      const base = {
        enabled: true,
        labId: Number(candidate.labId || 0),
        labName: String(candidate.labName || ""),
        minDaysAhead: Number(this.form.global.minDaysAhead || 0),
        maxDaysAhead: Number(this.form.global.maxDaysAhead || 30),
        minTime: String(this.form.global.minTime || "08:00"),
        maxTime: String(this.form.global.maxTime || "22:00"),
        slotsText: String(this.form.global.slotsText || ""),
        disabledDatesText: String(this.form.global.disabledDatesText || ""),
        approvalMode: String(this.form.global.approvalMode || "admin"),
        peakForceApproval: !!this.form.global.peakForceApproval,
        peakSlotsText: String(this.form.global.peakSlotsText || ""),
        blackoutRows: toBlackoutRows(this.buildBlackoutPayload(this.form.global.blackoutRows || []))
      }
      this.form.labRules.push(base)
    },
    removeLabRule(idx) {
      this.form.labRules.splice(idx, 1)
    },
    async loadRules() {
      if (this.loading) return
      this.loading = true
      try {
        const res = await uni.request({
          url: `${BASE_URL}/admin/reservation-rules`,
          method: "GET"
        })
        const payload = (res && res.data) || {}
        if (!payload.ok || !payload.data) {
          uni.showToast({ title: payload.msg || "加载失败", icon: "none" })
          return
        }
        const data = payload.data || {}
        this.labs = Array.isArray(data.labs) ? data.labs : []
        this.form.global = safeRuleForm(data.global || {})
        this.form.labRules = Array.isArray(data.labRules) ? data.labRules.map((x) => safeRuleForm(x)) : []
        this.form.labRules.forEach((rule) => {
          if (!rule.labName) {
            rule.labName = this.normalizeLabNameById(rule.labId)
          }
        })
      } catch (e) {
        uni.showToast({ title: "加载失败", icon: "none" })
      } finally {
        this.loading = false
      }
    },
    buildBlackoutPayload(rows) {
      return (rows || [])
        .map((row) => ({
          date: String((row && row.date) || "").trim(),
          slots: splitTextList((row && row.slotsText) || ""),
          reason: String((row && row.reason) || "").trim()
        }))
        .filter((row) => row.date && row.slots.length > 0)
    },
    buildRulePayload(rule) {
      const source = rule || {}
      return {
        minDaysAhead: Number(source.minDaysAhead || 0),
        maxDaysAhead: Number(source.maxDaysAhead || 0),
        minTime: String(source.minTime || "").trim(),
        maxTime: String(source.maxTime || "").trim(),
        slots: splitTextList(source.slotsText || ""),
        disabledDates: splitTextList(source.disabledDatesText || ""),
        blackoutSlots: this.buildBlackoutPayload(source.blackoutRows || []),
        approval: {
          mode: String(source.approvalMode || "admin"),
          peakForceApproval: !!source.peakForceApproval,
          peakSlots: splitTextList(source.peakSlotsText || "")
        }
      }
    },
    validateBeforeSave(payload) {
      const globalRule = (payload && payload.global) || {}
      if (Number(globalRule.minDaysAhead || 0) > Number(globalRule.maxDaysAhead || 0)) {
        return "全局规则的最小提前天数不能大于最大提前天数"
      }
      const seen = new Set()
      for (const row of payload.labRules || []) {
        const labId = Number(row.labId || 0)
        if (!labId) return "实验室覆盖规则必须选择实验室"
        if (seen.has(labId)) return "实验室覆盖规则存在重复实验室"
        seen.add(labId)
        if (Number(row.minDaysAhead || 0) > Number(row.maxDaysAhead || 0)) {
          return `实验室 #${labId} 的最小提前天数不能大于最大提前天数`
        }
      }
      return ""
    },
    async saveRules() {
      if (this.saving) return
      const payload = {
        global: this.buildRulePayload(this.form.global),
        labRules: this.form.labRules.map((rule) => ({
          ...this.buildRulePayload(rule),
          enabled: !!rule.enabled,
          labId: Number(rule.labId || 0),
          labName: String(rule.labName || "").trim() || this.normalizeLabNameById(rule.labId)
        }))
      }
      const validationError = this.validateBeforeSave(payload)
      if (validationError) {
        uni.showToast({ title: validationError, icon: "none" })
        return
      }

      this.saving = true
      try {
        const res = await uni.request({
          url: `${BASE_URL}/admin/reservation-rules`,
          method: "POST",
          header: { "Content-Type": "application/json" },
          data: payload
        })
        const body = (res && res.data) || {}
        if (!body.ok || !body.data) {
          uni.showToast({ title: body.msg || "保存失败", icon: "none" })
          return
        }
        uni.showToast({ title: "规则已保存", icon: "success" })
        this.labs = Array.isArray(body.data.labs) ? body.data.labs : this.labs
        this.form.global = safeRuleForm(body.data.global || {})
        this.form.labRules = Array.isArray(body.data.labRules) ? body.data.labRules.map((x) => safeRuleForm(x)) : []
      } catch (e) {
        uni.showToast({ title: "保存失败", icon: "none" })
      } finally {
        this.saving = false
      }
    }
  }
}
</script>

<style lang="scss">
.rulesPage {
  padding-bottom: 20px;
}

.heroCard {
  border: 1px solid rgba(22, 119, 255, 0.2);
  background: linear-gradient(160deg, #ffffff 0%, #eef5ff 100%);
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

.sectionHeader {
  align-items: center;
}

.subHeader {
  margin-top: 10px;
}

.grid2 {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.fieldHint {
  margin-bottom: 6px;
}

.inlineLabel {
  margin: 0;
}

.switchRow {
  margin-top: 10px;
}

.chipRow {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.modeChip {
  cursor: pointer;
}

.largeText {
  min-height: 100px;
}

.blackoutRow {
  margin-top: 10px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 10px;
  padding: 10px;
  background: #f8fafc;
}

.rowRight {
  margin-top: 8px;
  display: flex;
  justify-content: flex-end;
}

.labRuleCard {
  margin-top: 10px;
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 12px;
  padding: 10px;
  background: #f9fbff;
}

.actionRow {
  gap: 8px;
  align-items: center;
}

.pickerField {
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid rgba(148, 163, 184, 0.3);
  background: #fff;
  color: #0f172a;
  font-size: 13px;
}

.actionCard {
  margin-bottom: 8px;
}
</style>

<template>
  <view class="container importPage">
    <view class="stack">
      <view class="card heroCard">
        <view class="title">{{ isEditMode ? "课表模板编辑" : "课表导入" }}</view>
        <view class="subtitle">{{ isEditMode ? "修改已导入模板并保存覆盖" : "支持手工录入与 Excel 粘贴导入（复制表格行到文本框）" }}</view>
      </view>

      <view class="card">
        <view class="cardTitle">模板信息</view>
        <view class="muted mt8" v-if="isEditMode">编辑模板ID：{{ editingTemplateId }}</view>
        <view class="muted mt8" v-if="loadingTemplate">模板数据加载中...</view>
        <input class="inputBase" v-model="form.termName" placeholder="学期名称，如 2025-2026-2" />
        <view class="rowBetween mt8">
          <view class="field">
            <view class="label">开学日期</view>
            <picker mode="date" :value="form.semesterStartDate" @change="onStartDateChange">
              <view class="pickerLike">{{ form.semesterStartDate || "请选择日期" }}</view>
            </picker>
          </view>
          <view class="field">
            <view class="label">教学周数</view>
            <input class="inputBase" type="number" v-model="form.semesterWeeks" />
          </view>
        </view>
        <view class="rowBetween mt8">
          <view class="field">
            <view class="label">提前提醒（分钟）</view>
            <input class="inputBase" type="number" v-model="form.reminderLeadMinutes" />
          </view>
          <view class="field">
            <view class="label">来源</view>
            <picker :range="sourceOptions" range-key="label" :value="sourceIndex" @change="onSourceChange">
              <view class="pickerLike">{{ sourceOptions[sourceIndex].label }}</view>
            </picker>
          </view>
        </view>
        <view class="chipRow">
          <view class="chip" :class="{ chipOn: form.activate }" @click="form.activate = !form.activate">{{ form.activate ? "导入后启用" : "导入为草稿" }}</view>
          <view class="chip" :class="{ chipOn: form.mode === 'replace' }" @click="form.mode='replace'">覆盖导入</view>
          <view class="chip" :class="{ chipOn: form.mode === 'append' }" @click="form.mode='append'">追加导入</view>
        </view>
      </view>

      <view class="card">
        <view class="rowBetween">
          <view class="cardTitle">手工录入</view>
          <view class="muted">已录入 {{ manualItems.length }} 条</view>
        </view>
        <input class="inputBase mt8" v-model="draft.courseName" placeholder="课程名称" />
        <view class="rowBetween mt8">
          <picker :range="labs" range-key="name" :value="draftLabIndex" @change="onDraftLabChange">
            <view class="pickerLike field">{{ currentDraftLab ? currentDraftLab.name : "请选择实验室" }}</view>
          </picker>
          <input class="inputBase field" v-model="draft.teacherName" placeholder="教师" />
        </view>
        <view class="rowBetween mt8">
          <input class="inputBase field" v-model="draft.className" placeholder="班级/专业" />
          <picker :range="weekDayOptions" range-key="label" :value="weekDayIndex" @change="onWeekDayChange">
            <view class="pickerLike field">{{ weekDayOptions[weekDayIndex].label }}</view>
          </picker>
        </view>
        <view class="rowBetween mt8">
          <input class="inputBase field" v-model="draft.periodRange" placeholder="节次，如 1-2" />
          <input class="inputBase field" v-model="draft.weekRange" placeholder="周次，如 2-17" />
        </view>
        <view class="mt8">
          <view class="label">课程时间段（可预约时段）</view>
          <view class="chipRow">
            <view
              class="chip"
              :class="{ chipOn: draft.timeSlots.includes(slot) }"
              v-for="slot in slotOptions"
              :key="slot"
              @click="toggleDraftTime(slot)"
            >
              {{ slot }}
            </view>
            <view class="chip" @click="clearDraftTime">清空时间段</view>
          </view>
        </view>
        <view class="rowBetween mt8">
          <picker :range="weekTypeOptions" range-key="label" :value="weekTypeIndex" @change="onWeekTypeChange">
            <view class="pickerLike field">{{ weekTypeOptions[weekTypeIndex].label }}</view>
          </picker>
          <input class="inputBase field" v-model="draft.note" placeholder="备注（可选）" />
        </view>
        <view class="chipRow">
          <view class="chip chipOn" @click="addManualRow">添加一条</view>
          <view class="chip" @click="clearManualRows">清空手工条目</view>
        </view>
        <view class="list" v-if="manualItems.length>0">
          <view class="rowItem" v-for="(item, idx) in manualItems" :key="idx">
            <view class="rowTitle">{{ item.courseName }} · {{ item.labName }}</view>
            <view class="rowMeta">{{ weekText(item.weekDay) }} · {{ item.periodRange ? (item.periodRange + "节") : "按时间段" }} · {{ item.weekRange }}周 · {{ weekTypeText(item.weekType) }}</view>
            <view class="rowMeta">时间段：{{ item.timeRange || "-" }}</view>
            <view class="rowMeta">{{ item.teacherName || "-" }} · {{ item.className || "-" }}</view>
            <view class="rowActionsInline">
              <view class="rowEdit" @click="editManualRow(idx)">编辑</view>
              <view class="rowRemove" @click="removeManualRow(idx)">删除</view>
            </view>
          </view>
        </view>
      </view>

      <view class="card">
        <view class="cardTitle">Excel 粘贴导入</view>
        <view class="muted">每行列顺序(推荐9列)：课程名, 星期几, 节次(1-2), 时间段(08:00-08:40,08:45-09:35), 周次(2-17), 实验室, 教师, 班级, 备注</view>
        <view class="muted">兼容旧8列：课程名, 星期几, 节次, 周次, 实验室, 教师, 班级, 备注</view>
        <textarea class="textareaBase mt8" v-model="pasteText" placeholder="将 Excel 多行复制到这里（支持制表符或逗号分隔）"></textarea>
        <view class="chipRow">
          <view class="chip chipOn" @click="parsePasteText">解析粘贴内容</view>
          <view class="chip" @click="clearPasteRows">清空粘贴条目</view>
          <view class="muted">已解析 {{ pasteItems.length }} 条</view>
        </view>
      </view>

      <view class="card">
        <view class="rowBetween">
          <view class="cardTitle">{{ isEditMode ? "提交修改" : "提交导入" }}</view>
          <view class="muted">总计 {{ allItems.length }} 条</view>
        </view>
        <button class="btnPrimary" :loading="saving" @click="submitImport">{{ isEditMode ? "保存模板修改" : "开始导入" }}</button>
      </view>
    </view>
  </view>
</template>

<script>
import { BASE_URL, adminGetScheduleTemplateDetail, adminImportSchedule, getApiListData, listLabs } from "@/common/api.js"

const WEEK_DAY_OPTIONS = [
  { label: "周一", value: 1 },
  { label: "周二", value: 2 },
  { label: "周三", value: 3 },
  { label: "周四", value: 4 },
  { label: "周五", value: 5 },
  { label: "周六", value: 6 },
  { label: "周日", value: 7 }
]

const WEEK_TYPE_OPTIONS = [
  { label: "全部周", value: "all" },
  { label: "单周", value: "odd" },
  { label: "双周", value: "even" }
]

const SOURCE_OPTIONS = [
  { label: "手工", value: "manual" },
  { label: "Excel", value: "excel" }
]

function todayText() {
  const d = new Date()
  const p = (n) => (n < 10 ? `0${n}` : `${n}`)
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

function ensureAdmin() {
  const s = uni.getStorageSync("session")
  return !!(s && s.role === "admin")
}

export default {
  data() {
    return {
      saving: false,
      form: {
        termName: "",
        semesterStartDate: todayText(),
        semesterWeeks: 20,
        reminderLeadMinutes: 20,
        sourceType: "manual",
        activate: true,
        mode: "replace"
      },
      draft: {
        courseName: "",
        labId: 0,
        labName: "",
        teacherName: "",
        className: "",
        weekDay: 1,
        periodRange: "1-2",
        timeSlots: [],
        weekRange: "1-16",
        weekType: "all",
        note: ""
      },
      weekDayOptions: WEEK_DAY_OPTIONS,
      weekTypeOptions: WEEK_TYPE_OPTIONS,
      sourceOptions: SOURCE_OPTIONS,
      labs: [],
      slotOptions: [],
      pasteText: "",
      manualItems: [],
      pasteItems: [],
      editingTemplateId: 0,
      loadedTemplateId: 0,
      loadingTemplate: false
    }
  },
  computed: {
    weekDayIndex() {
      const idx = this.weekDayOptions.findIndex((x) => Number(x.value) === Number(this.draft.weekDay))
      return idx >= 0 ? idx : 0
    },
    weekTypeIndex() {
      const idx = this.weekTypeOptions.findIndex((x) => String(x.value) === String(this.draft.weekType))
      return idx >= 0 ? idx : 0
    },
    sourceIndex() {
      const idx = this.sourceOptions.findIndex((x) => String(x.value) === String(this.form.sourceType))
      return idx >= 0 ? idx : 0
    },
    currentDraftLab() {
      const targetId = Number(this.draft.labId || 0)
      if (targetId > 0) {
        return this.labs.find((x) => Number((x || {}).id || 0) === targetId) || null
      }
      const targetName = String(this.draft.labName || "").trim()
      if (!targetName) return null
      return this.labs.find((x) => String((x || {}).name || "").trim() === targetName) || null
    },
    draftLabIndex() {
      if (!Array.isArray(this.labs) || this.labs.length <= 0) return 0
      const targetId = Number(this.draft.labId || 0)
      let idx = -1
      if (targetId > 0) {
        idx = this.labs.findIndex((x) => Number((x || {}).id || 0) === targetId)
      }
      if (idx < 0) {
        const targetName = String(this.draft.labName || "").trim()
        if (targetName) idx = this.labs.findIndex((x) => String((x || {}).name || "").trim() === targetName)
      }
      return idx >= 0 ? idx : 0
    },
    isEditMode() {
      return Number(this.editingTemplateId || 0) > 0
    },
    allItems() {
      return [...this.manualItems, ...this.pasteItems]
    }
  },
  onLoad(options) {
    const tid = Number((options && options.templateId) || 0)
    if (tid > 0) this.editingTemplateId = tid
  },
  async onShow() {
    if (!ensureAdmin()) {
      uni.showToast({ title: "无权限", icon: "none" })
      uni.reLaunch({ url: "/pages/login/login" })
      return
    }
    await Promise.all([this.loadRuleSlots(), this.loadLabs()])
    if (this.isEditMode && this.loadedTemplateId !== this.editingTemplateId) {
      await this.loadTemplateForEdit()
    }
  },
  methods: {
    async loadLabs() {
      try {
        const res = await listLabs({})
        this.labs = getApiListData(res && res.data)
        if (Number(this.draft.labId || 0) <= 0 && this.draft.labName) {
          const row = this.labs.find((x) => String((x || {}).name || "").trim() === String(this.draft.labName || "").trim())
          if (row) {
            this.draft.labId = Number((row || {}).id || 0)
            this.draft.labName = String((row || {}).name || "").trim()
          }
        } else if (Number(this.draft.labId || 0) <= 0 && !this.draft.labName && this.labs.length > 0) {
          const first = this.labs[0] || {}
          this.draft.labId = Number((first || {}).id || 0)
          this.draft.labName = String((first || {}).name || "").trim()
        }
      } catch (e) {
        this.labs = []
      }
    },
    loadRuleSlots() {
      return new Promise((resolve) => {
        uni.request({
          url: `${BASE_URL}/reservation-rules`,
          method: "GET",
          success: (res) => {
            const payload = (res && res.data) || {}
            const data = payload && payload.ok ? (payload.data || {}) : {}
            const slots = Array.isArray(data.slots) ? data.slots : []
            this.slotOptions = slots.filter((x) => String(x || "").trim())
          },
          fail: () => {
            this.slotOptions = []
          },
          complete: () => resolve()
        })
      })
    },
    onDraftLabChange(e) {
      const idx = Number((e && e.detail && e.detail.value) || 0)
      const row = this.labs[idx] || null
      if (!row) return
      this.draft.labId = Number((row || {}).id || 0)
      this.draft.labName = String((row || {}).name || "").trim()
    },
    async loadTemplateForEdit() {
      if (!this.isEditMode || this.loadingTemplate) return
      this.loadingTemplate = true
      try {
        const res = await adminGetScheduleTemplateDetail(this.editingTemplateId)
        const payload = (res && res.data) || {}
        if (!payload.ok) {
          uni.showToast({ title: payload.msg || "模板加载失败", icon: "none" })
          return
        }
        const data = payload.data || {}
        const template = data.template || {}
        const items = Array.isArray(data.items) ? data.items : []
        this.form.termName = String(template.termName || "").trim()
        this.form.semesterStartDate = String(template.semesterStartDate || "").trim() || this.form.semesterStartDate
        this.form.semesterWeeks = Number(template.semesterWeeks || 20)
        this.form.reminderLeadMinutes = Number(template.reminderLeadMinutes || 20)
        this.form.sourceType = String(template.sourceType || "manual").trim() || "manual"
        this.form.activate = String(template.status || "").trim() === "active"
        this.form.mode = "replace"
        this.manualItems = items.map((item, idx) => {
          const periodStart = Number(item.periodStart || 0)
          const periodEnd = Number(item.periodEnd || 0)
          const weekStart = Number(item.weekStart || 0)
          const weekEnd = Number(item.weekEnd || 0)
          const timeRange = String(item.timeRange || "").trim()
          return {
            rowNo: Number(item.rowNo || idx + 1),
            courseName: String(item.courseName || "").trim(),
            weekDay: Number(item.weekDay || 1),
            periodStart,
            periodEnd,
            periodRange: periodStart > 0 && periodEnd > 0 ? `${periodStart}-${periodEnd}` : "",
            timeRange,
            timeSlots: timeRange ? timeRange.split(/,|，/).map((x) => String(x || "").trim()).filter(Boolean) : [],
            weekStart,
            weekEnd,
            weekRange: weekStart > 0 && weekEnd > 0 ? `${weekStart}-${weekEnd}` : "",
            weekType: String(item.weekType || "all").trim() || "all",
            labId: item.labId || 0,
            labName: String(item.labName || "").trim(),
            teacherName: String(item.teacherName || "").trim(),
            className: String(item.className || "").trim(),
            note: String(item.note || "").trim()
          }
        })
        this.pasteItems = []
        this.loadedTemplateId = this.editingTemplateId
      } catch (e) {
        uni.showToast({ title: "模板加载失败", icon: "none" })
      } finally {
        this.loadingTemplate = false
      }
    },
    onStartDateChange(e) {
      this.form.semesterStartDate = e.detail.value
    },
    onSourceChange(e) {
      const idx = Number((e && e.detail && e.detail.value) || 0)
      this.form.sourceType = (this.sourceOptions[idx] || this.sourceOptions[0]).value
    },
    onWeekDayChange(e) {
      const idx = Number((e && e.detail && e.detail.value) || 0)
      this.draft.weekDay = (this.weekDayOptions[idx] || this.weekDayOptions[0]).value
    },
    onWeekTypeChange(e) {
      const idx = Number((e && e.detail && e.detail.value) || 0)
      this.draft.weekType = (this.weekTypeOptions[idx] || this.weekTypeOptions[0]).value
    },
    weekText(v) {
      const row = this.weekDayOptions.find((x) => Number(x.value) === Number(v))
      return row ? row.label : `周${v}`
    },
    weekTypeText(v) {
      const row = this.weekTypeOptions.find((x) => String(x.value) === String(v))
      return row ? row.label : v
    },
    toggleDraftTime(slot) {
      const text = String(slot || "").trim()
      if (!text) return
      const idx = this.draft.timeSlots.indexOf(text)
      if (idx >= 0) this.draft.timeSlots.splice(idx, 1)
      else this.draft.timeSlots.push(text)
    },
    clearDraftTime() {
      this.draft.timeSlots = []
    },
    addManualRow() {
      if (!this.draft.courseName.trim()) {
        uni.showToast({ title: "请填写课程名", icon: "none" })
        return
      }
      if (Number(this.draft.labId || 0) <= 0 || !this.draft.labName.trim()) {
        uni.showToast({ title: "请选择实验室", icon: "none" })
        return
      }
      const timeRange = this.draft.timeSlots.join(",")
      if (!this.draft.periodRange.trim() && !timeRange) {
        uni.showToast({ title: "请填写节次或选择时间段", icon: "none" })
        return
      }
      this.manualItems.push({ ...this.draft, timeRange, timeSlots: [...this.draft.timeSlots] })
      this.draft.courseName = ""
      this.draft.note = ""
      this.draft.timeSlots = []
    },
    removeManualRow(idx) {
      this.manualItems.splice(idx, 1)
    },
    editManualRow(idx) {
      const row = this.manualItems[idx]
      if (!row) return
      const periodStart = Number(row.periodStart || 0)
      const periodEnd = Number(row.periodEnd || 0)
      const weekStart = Number(row.weekStart || 0)
      const weekEnd = Number(row.weekEnd || 0)
      const weekDay = Number(row.weekDay || 1)
      const timeRange = String(row.timeRange || (Array.isArray(row.timeSlots) ? row.timeSlots.join(",") : "")).trim()
      this.draft.courseName = String(row.courseName || "").trim()
      this.draft.labId = Number(row.labId || 0)
      this.draft.labName = String(row.labName || "").trim()
      this.draft.teacherName = String(row.teacherName || "").trim()
      this.draft.className = String(row.className || "").trim()
      this.draft.weekDay = weekDay >= 1 && weekDay <= 7 ? weekDay : 1
      this.draft.periodRange = String(row.periodRange || "").trim() || (periodStart > 0 && periodEnd > 0 ? `${periodStart}-${periodEnd}` : "")
      this.draft.timeSlots = timeRange ? timeRange.split(/,|，/).map((x) => String(x || "").trim()).filter(Boolean) : []
      this.draft.weekRange = String(row.weekRange || "").trim() || (weekStart > 0 && weekEnd > 0 ? `${weekStart}-${weekEnd}` : "")
      this.draft.weekType = ["all", "odd", "even"].includes(String(row.weekType || "").trim()) ? String(row.weekType || "").trim() : "all"
      this.draft.note = String(row.note || "").trim()
      this.manualItems.splice(idx, 1)
      uni.showToast({ title: "已载入编辑区", icon: "none" })
    },
    clearManualRows() {
      this.manualItems = []
    },
    clearPasteRows() {
      this.pasteItems = []
      this.pasteText = ""
    },
    parsePasteText() {
      const lines = String(this.pasteText || "").split(/\r?\n/)
      const out = []
      lines.forEach((line) => {
        const text = String(line || "").trim()
        if (!text) return
        const rawParts = (text.includes("\t") ? text.split("\t") : text.split(/,|，/)).map((x) => String(x || "").trim())
        const originalLen = rawParts.length
        const parts = rawParts.slice()
        if (parts[0] === "课程名" || parts[0] === "课程名称") return
        while (parts.length < 9) parts.push("")
        if (!parts[0]) return
        let weekDay = ""
        let periodRange = ""
        let timeRange = ""
        let weekRange = ""
        let labName = ""
        let teacherName = ""
        let className = ""
        let note = ""
        if (originalLen >= 9) {
          weekDay = parts[1]
          periodRange = parts[2]
          timeRange = parts[3]
          weekRange = parts[4]
          labName = parts[5]
          teacherName = parts[6]
          className = parts[7]
          note = parts[8]
        } else {
          weekDay = parts[1]
          periodRange = parts[2]
          weekRange = parts[3]
          labName = parts[4]
          teacherName = parts[5]
          className = parts[6]
          note = parts[7]
        }
        out.push({
          courseName: parts[0],
          weekDay,
          periodRange,
          timeRange,
          weekRange,
          labName,
          teacherName,
          className,
          note,
          weekType: "all"
        })
      })
      this.pasteItems = out
      uni.showToast({ title: `已解析 ${out.length} 条`, icon: "none" })
    },
    async submitImport() {
      if (this.saving) return
      if (!this.form.semesterStartDate) {
        uni.showToast({ title: "请选择开学日期", icon: "none" })
        return
      }
      if (this.allItems.length <= 0) {
        uni.showToast({ title: "请先录入或粘贴课表", icon: "none" })
        return
      }
      this.saving = true
      try {
        const templatePayload = {
          termName: this.form.termName,
          semesterStartDate: this.form.semesterStartDate,
          semesterWeeks: Number(this.form.semesterWeeks || 20),
          reminderLeadMinutes: Number(this.form.reminderLeadMinutes || 20),
          sourceType: this.form.sourceType
        }
        if (this.isEditMode) {
          templatePayload.id = Number(this.editingTemplateId || 0)
        }
        const res = await adminImportSchedule({
          template: templatePayload,
          mode: this.form.mode,
          activate: !!this.form.activate,
          items: this.allItems
        })
        const payload = (res && res.data) || {}
        if (!payload.ok) {
          uni.showToast({ title: payload.msg || "导入失败", icon: "none" })
          return
        }
        const data = payload.data || {}
        uni.showModal({
          title: this.isEditMode ? "保存完成" : "导入完成",
          content: `模板ID: ${data.templateId || "-"}\n导入条数: ${data.inserted || 0}\n错误条数: ${(data.errors || []).length}`,
          showCancel: false,
          success: () => {
            uni.navigateBack()
          }
        })
      } catch (e) {
        uni.showToast({ title: "导入失败", icon: "none" })
      } finally {
        this.saving = false
      }
    }
  }
}
</script>

<style lang="scss">
.importPage {
  padding-bottom: 20px;
}

.heroCard {
  border: 1px solid rgba(22, 119, 255, 0.18);
  background: linear-gradient(160deg, #ffffff 0%, #f2f7ff 100%);
}

.mt8 {
  margin-top: 8px;
}

.field {
  flex: 1;
}

.label {
  font-size: 12px;
  color: #64748b;
  margin-bottom: 4px;
}

.pickerLike {
  min-height: 36px;
  border: 1px solid #d0d8e2;
  border-radius: 8px;
  padding: 8px 10px;
  box-sizing: border-box;
  font-size: 13px;
  color: #0f172a;
  background: #fff;
}

.chipRow {
  margin-top: 8px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}

.chipOn {
  border-color: #bfdbfe;
  background: #eaf3ff;
  color: #1d4ed8;
}

.textareaBase {
  min-height: 140px;
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

.rowActionsInline {
  margin-top: 8px;
  display: flex;
  gap: 12px;
}

.rowEdit {
  font-size: 12px;
  color: #1d4ed8;
}

.rowRemove {
  font-size: 12px;
  color: #b42318;
}
</style>

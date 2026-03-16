<template>
  <view class="container detailPage">
    <view class="stack">
      <view class="card heroCard">
        <view class="rowBetween heroTop">
          <view>
            <view class="title">实验室详情</view>
            <view class="subtitle">查看实验室状态、容量与设备信息</view>
          </view>
          <button class="btnSecondary miniBtn" size="mini" @click="fetchDetail">刷新</button>
        </view>
      </view>

      <view class="card loadingCard" v-if="loading">
        <view class="muted">正在加载实验室信息...</view>
      </view>

      <view class="stack" v-else-if="lab">
        <view class="card coverCard">
          <view class="cover">
            <image
              v-if="hasCover"
              :src="imgSrc(lab.imageUrl)"
              class="coverImage"
              mode="aspectFill"
              @error="onImageError"
            />
            <view v-else class="coverFallback" :style="fallbackStyle">
              <text class="fallbackText">{{ shortName }}</text>
            </view>
          </view>

          <view class="infoHeader">
            <view class="labName">{{ lab.name || labName || '未命名实验室' }}</view>
            <view class="statusTag" :class="statusClass(lab.status)">{{ statusText(lab.status) }}</view>
          </view>
          <view class="muted">数据更新时间：{{ nowText }}</view>
        </view>

        <view class="card">
          <view class="cardTitle">基础信息</view>
          <view class="infoGrid">
            <view class="infoItem">
              <view class="labelText">容量</view>
              <view class="valueText">{{ lab.capacity || 0 }}</view>
            </view>
            <view class="infoItem">
              <view class="labelText">设备数量</view>
              <view class="valueText">{{ lab.deviceCount || 0 }}</view>
            </view>
          </view>

          <view class="label">简介</view>
          <view class="descBox">{{ lab.description || '暂无实验室简介' }}</view>
        </view>

        <view class="card">
          <view class="rowBetween">
            <view class="cardTitle">电脑与报修</view>
            <button class="btnSecondary miniBtn" size="mini" @click="fetchEquipments" :disabled="equipLoading">刷新设备</button>
          </view>
          <view class="muted repairTip">点击故障电脑可提交报修；其他问题（电灯/地板等）也可提交。</view>

          <view class="mapSection" v-if="pcRows.length > 0">
            <view class="label">电脑分布图</view>
            <view class="teacherRowMap">
              <view
                class="pcSeat"
                :class="pcSeatClass(teacherSeat)"
                @click="onPcSeatTap(teacherSeat)"
              >
                <view class="rowBetween">
                  <view class="seatCode">{{ teacherSeat.code }}</view>
                </view>
                <image src="/static/电脑.png" class="pcSeatIcon" mode="aspectFit" />
                <view class="pcSeatName">{{ teacherSeat.eq ? (teacherSeat.eq.assetCode || teacherSeat.eq.name || "-") : "空位" }}</view>
                <view class="pcSeatSub">{{ teacherSeat.eq ? pcStatusText(teacherSeat.eq.status) : "教师位" }}</view>
              </view>
            </view>
            <view class="seatGridMap">
              <view
                class="pcSeat"
                v-for="seat in seatGrid"
                :key="seat.code"
                :class="pcSeatClass(seat)"
                @click="onPcSeatTap(seat)"
              >
                <view class="rowBetween">
                  <view class="seatCode">{{ seat.code }}</view>
                </view>
                <image src="/static/电脑.png" class="pcSeatIcon" mode="aspectFit" />
                <view class="pcSeatName">{{ seat.eq ? (seat.eq.assetCode || seat.eq.name || "-") : "空位" }}</view>
                <view class="pcSeatSub">{{ seat.eq ? pcStatusText(seat.eq.status) : "-" }}</view>
              </view>
            </view>
          </view>

          <view class="muted" v-if="equipLoading">正在加载电脑设备...</view>
          <view class="empty miniEmpty" v-else>暂无电脑设备，可直接提交其他问题报修</view>

          <button class="btnSecondary fullBtn" @click="openRepair(null, 'other')">提交其他问题报修</button>
        </view>

        <view class="card">
          <view class="cardTitle">快捷操作</view>
          <view class="actions">
            <button class="btnPrimary actionBtn" @click="goReserve">立即预约</button>
            <button class="btnSecondary actionBtn" @click="goCalendar">查看日历</button>
          </view>
          <button class="btnGhost fullBtn" @click="goList">返回实验室列表</button>
        </view>
      </view>

      <view class="emptyState" v-else>
        <view class="emptyIcon">室</view>
        <view class="emptyTitle">未找到实验室信息</view>
        <view class="emptySub">请返回列表重新选择，或稍后刷新重试</view>
        <button class="btnSecondary retryBtn" @click="goList">返回列表</button>
      </view>

      <view class="modalMask" v-if="repairVisible" @click="closeRepair" />
      <view class="card modalPanel" v-if="repairVisible">
        <view class="rowBetween">
          <view class="cardTitle">提交报修</view>
          <button class="btnSecondary miniBtn" size="mini" @click="closeRepair">取消</button>
        </view>
        <view class="label">问题类型</view>
        <view class="issueChips">
          <view
            class="chip issueChip"
            v-for="opt in repairTypeOptions"
            :key="opt.value"
            :class="{ chipOn: repairForm.issueType === opt.value }"
            @click="repairForm.issueType = opt.value"
          >
            {{ opt.label }}
          </view>
        </view>

        <view class="label">关联电脑</view>
        <picker :range="repairTargetOptions" range-key="label" @change="onRepairTargetChange">
          <view class="pickerLike">{{ currentRepairTargetLabel }}</view>
        </picker>

        <view class="label">问题描述</view>
        <textarea
          class="textareaBase"
          v-model.trim="repairForm.description"
          maxlength="1000"
          placeholder="请描述故障现象，例如：开机蓝屏、投影灯不亮、地板瓷砖松动等"
        />
        <view class="label">故障图片（可选）</view>
        <view class="rowBetween uploadRow">
          <button class="btnGhost miniBtn" size="mini" @click="chooseRepairImage">上传图片</button>
          <button v-if="repairAttachments.length > 0" class="btnSecondary miniBtn" size="mini" @click="clearRepairImage">清空图片</button>
          <view class="muted">{{ repairAttachments.length > 0 ? `已上传 ${repairAttachments.length} 张` : "未上传" }}</view>
        </view>
        <view class="repairPreviewList" v-if="repairAttachments.length > 0">
          <view class="repairPreviewItem" v-for="(item, idx) in repairAttachments" :key="`repair-attachment-${idx}`">
            <image :src="imgSrc(item.url)" class="repairPreview" mode="aspectFill" />
            <view class="meta repairPreviewMeta">{{ item.name || `图片 ${idx + 1}` }}</view>
            <button class="btnGhost miniBtn" size="mini" @click="removeRepairAttachment(idx)">移除</button>
          </view>
        </view>
        <view class="label">错误码 / OCR 文本（可选）</view>
        <textarea
          class="textareaBase miniTextarea"
          v-model.trim="repairForm.ocrText"
          maxlength="1000"
          placeholder="例如：0x0000007E、No signal、网络不可达"
        />
        <view class="aiRepairBox">
          <view class="rowBetween">
            <view class="strongMeta">AI 辅助识别</view>
            <button class="btnGhost miniBtn" size="mini" :disabled="repairAiLoading" @click="runRepairAiDiagnose">
              {{ repairAiLoading ? "识别中..." : "识别故障类型" }}
            </button>
          </view>
          <view class="meta" v-if="repairAiResult.summary">{{ repairAiResult.summary }}</view>
          <view class="meta" v-if="repairAiResult.issueTypeLabel">
            识别结果：{{ repairAiResult.issueTypeLabel }} · 优先级 {{ repairAiResult.priority || "-" }} · 置信度 {{ aiConfidenceText }}
          </view>
          <view class="meta" v-if="repairAiResult.faultPart">疑似故障部位：{{ repairAiResult.faultPart }}</view>
          <view class="meta" v-if="repairAiResult.ocrSummary">OCR 线索：{{ repairAiResult.ocrSummary }}</view>
          <view class="meta" v-for="(line, idx) in aiCauseLines" :key="`repair-ai-cause-${idx}`">可能原因 {{ idx + 1 }}：{{ line }}</view>
          <view class="meta" v-for="(tip, idx) in aiSuggestionLines" :key="'repair-ai-' + idx">{{ idx + 1 }}. {{ tip }}</view>
        </view>

        <button class="btnPrimary submitBtn" :disabled="repairSaving" @click="submitRepair">
          {{ repairSaving ? "提交中..." : "提交报修" }}
        </button>
      </view>
    </view>
  </view>
</template>

<script>
import { BASE_URL, apiRequest, getApiListData, toQuery } from "@/common/api.js"

const FALLBACK_BG = [
  "linear-gradient(135deg, #dbeafe 0%, #e0f2fe 100%)",
  "linear-gradient(135deg, #dcfce7 0%, #d9f99d 100%)",
  "linear-gradient(135deg, #fae8ff 0%, #e9d5ff 100%)",
  "linear-gradient(135deg, #fef3c7 0%, #fde68a 100%)"
]

function nowTimeText() {
  const d = new Date()
  const p = (n) => (n < 10 ? `0${n}` : `${n}`)
  return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`
}

const REPAIR_TYPE_OPTIONS = [
  { label: "电脑问题", value: "computer" },
  { label: "电灯问题", value: "lighting" },
  { label: "地板问题", value: "floor" },
  { label: "网络问题", value: "network" },
  { label: "其他问题", value: "other" }
]

function parseSpec(raw) {
  if (!raw) return {}
  if (typeof raw === "object" && !Array.isArray(raw)) return { ...raw }
  try {
    const obj = JSON.parse(raw)
    return obj && typeof obj === "object" && !Array.isArray(obj) ? obj : {}
  } catch (e) {
    return {}
  }
}

function seatCodeOf(raw) {
  const txt = String(raw || "").trim().toUpperCase()
  const m = txt.match(/^([A-Z]+)(\d{1,3})$/)
  if (!m) return ""
  return `${m[1]}${Number(m[2])}`
}

function rowIndex(letters) {
  let sum = 0
  for (let i = 0; i < letters.length; i += 1) {
    sum = sum * 26 + (letters.charCodeAt(i) - 64)
  }
  return sum
}

function rowLetters(index) {
  let n = Number(index || 1)
  if (!Number.isFinite(n) || n < 1) n = 1
  let out = ""
  while (n > 0) {
    const rem = (n - 1) % 26
    out = String.fromCharCode(65 + rem) + out
    n = Math.floor((n - 1) / 26)
  }
  return out || "A"
}

function parseSeat(code) {
  const c = seatCodeOf(code)
  const m = c.match(/^([A-Z]+)(\d{1,3})$/)
  if (!m) return null
  return { code: c, row: rowIndex(m[1]), col: Number(m[2]) }
}

function normalizeEquipment(row) {
  const spec = parseSpec((row && (row.specJson || row.spec_json)) || "")
  const seatCode = seatCodeOf(spec.seatCode || spec.seat || spec.seat_code || row.seatCode || row.seat_code)
  return {
    id: Number((row && row.id) || 0),
    assetCode: String((row && (row.assetCode || row.asset_code)) || ""),
    name: String((row && row.name) || ""),
    status: String((row && row.status) || ""),
    labId: Number((row && (row.labId || row.lab_id)) || 0),
    spec,
    seatCode
  }
}

function isPcEquipment(eq) {
  const category = String((eq.spec && eq.spec.category) || "").toLowerCase()
  if (category) return category === "pc"
  return /^PC-/i.test(eq.assetCode || "")
}

export default {
  data() {
    return {
      labName: "",
      lab: null,
      loading: false,
      badImage: false,
      nowText: "",
      equipLoading: false,
      equipments: [],
      repairVisible: false,
      repairSaving: false,
      repairAiLoading: false,
      repairAttachments: [],
      repairImageName: "",
      repairAiResult: {},
      repairForm: {
        targetId: 0,
        issueType: "computer",
        description: "",
        attachmentUrl: "",
        ocrText: ""
      }
    }
  },
  computed: {
    shortName() {
      const name = String((this.lab && this.lab.name) || this.labName || "LAB")
      return name.slice(0, 4).toUpperCase()
    },
    hasCover() {
      return !!(this.lab && this.lab.imageUrl && !this.badImage)
    },
    fallbackStyle() {
      const key = Number((this.lab && this.lab.id) || 0) % FALLBACK_BG.length
      return { backgroundImage: FALLBACK_BG[key] }
    },
    pcRows() {
      return this.equipments.filter((x) => isPcEquipment(x))
    },
    repairTypeOptions() {
      return REPAIR_TYPE_OPTIONS
    },
    teacherSeat() {
      const teacherPc = this.pcRows.find((x) => x.seatCode === "O1") || null
      return { code: "O1", eq: teacherPc }
    },
    seatGrid() {
      const MAX_COL = 6
      const map = {}
      let maxRow = 1
      this.pcRows.forEach((pc) => {
        if (!pc.seatCode) return
        if (/^O\d+$/i.test(pc.seatCode)) return
        const p = parseSeat(pc.seatCode)
        if (!p || p.col < 1 || p.col > MAX_COL) return
        const code = `${rowLetters(p.row)}${p.col}`
        map[code] = pc
        if (p.row > maxRow) maxRow = p.row
      })
      const seats = []
      for (let r = 1; r <= maxRow; r += 1) {
        for (let c = 1; c <= MAX_COL; c += 1) {
          const code = `${rowLetters(r)}${c}`
          seats.push({ code, eq: map[code] || null })
        }
      }
      return seats
    },
    repairTargetOptions() {
      const options = this.equipments.map((eq) => ({
        label: `${eq.seatCode || "-"} ${eq.assetCode || eq.name || "#" + eq.id}`,
        value: eq.id
      }))
      options.unshift({ label: "不关联设备（通用问题）", value: 0 })
      return options
    },
    currentRepairTargetLabel() {
      const hit = this.repairTargetOptions.find((x) => Number(x.value) === Number(this.repairForm.targetId))
      return (hit && hit.label) || "请选择关联设备（可选）"
    },
    aiSuggestionLines() {
      return Array.isArray(this.repairAiResult.suggestions) ? this.repairAiResult.suggestions : []
    },
    aiCauseLines() {
      return Array.isArray(this.repairAiResult.possibleCauses) ? this.repairAiResult.possibleCauses : []
    },
    aiConfidenceText() {
      const n = Number(this.repairAiResult.confidence || 0)
      if (!Number.isFinite(n) || n <= 0) return "0%"
      return `${Math.round(n * 100)}%`
    }
  },
  onLoad(options) {
    if (options && options.labName) {
      this.labName = decodeURIComponent(options.labName)
    }
    this.fetchDetail()
  },
  methods: {
    statusText(status) {
      return status === "free" ? "空闲" : "已满"
    },
    statusClass(status) {
      return status === "free" ? "success" : "danger"
    },
    pcStatusText(status) {
      if (status === "in_service") return "在用"
      if (status === "repairing") return "维修中"
      if (status === "scrapped") return "报废"
      return status || "-"
    },
    pcStatusClass(status) {
      if (status === "in_service") return "success"
      if (status === "repairing") return "warning"
      if (status === "scrapped") return "danger"
      return "info"
    },
    pcSeatClass(seat) {
      if (!seat || !seat.eq) return "pcSeatEmpty"
      const status = String(seat.eq.status || "")
      if (status === "repairing") return "pcSeatWarning"
      if (status === "scrapped") return "pcSeatDanger"
      if (status === "in_service") return "pcSeatSuccess"
      return "pcSeatInfo"
    },
    onPcSeatTap(seat) {
      if (!seat || !seat.eq) return
      this.openRepair(seat.eq, "computer")
    },
    imgSrc(url) {
      if (!url) return ""
      if (String(url).startsWith("http")) return url
      return `${BASE_URL}${url}`
    },
    onImageError() {
      this.badImage = true
    },
    async fetchDetail() {
      if (!this.labName) {
        this.lab = null
        this.equipments = []
        return
      }
      this.loading = true
      this.badImage = false
      try {
        const res = await apiRequest({
          url: `/labs?keyword=${encodeURIComponent(this.labName)}`,
          method: "GET"
        })
        const rows = getApiListData(res.data)
        const exact = rows.find((x) => x.name === this.labName)
        this.lab = exact || rows[0] || null
        this.nowText = nowTimeText()
        await this.fetchEquipments()
      } catch (e) {
        this.lab = null
        this.equipments = []
        uni.showToast({ title: "获取详情失败", icon: "none" })
      } finally {
        this.loading = false
      }
    },
    async fetchEquipments() {
      if (!this.lab || !this.lab.id) {
        this.equipments = []
        return
      }
      this.equipLoading = true
      try {
        const query = toQuery({ labId: this.lab.id, page: 1, pageSize: 200 })
        const res = await apiRequest({
          url: `/equipments${query ? `?${query}` : ""}`,
          method: "GET"
        })
        const payload = (res && res.data) || {}
        const list = Array.isArray(payload.data) ? payload.data : Array.isArray(payload) ? payload : []
        this.equipments = Array.isArray(list) ? list.map((x) => normalizeEquipment(x)) : []
      } catch (e) {
        this.equipments = []
        uni.showToast({ title: "设备加载失败", icon: "none" })
      } finally {
        this.equipLoading = false
      }
    },
    openRepair(pc = null, issueType = "computer") {
      const defaultTarget = pc || (issueType === "computer" ? this.equipments[0] || null : null)
      if (!defaultTarget && issueType === "computer") {
        uni.showToast({ title: "当前实验室暂无可关联设备", icon: "none" })
        return
      }
      this.repairForm = {
        targetId: defaultTarget ? Number(defaultTarget.id || 0) : 0,
        issueType: issueType || "other",
        description: "",
        attachmentUrl: "",
        ocrText: ""
      }
      this.repairAttachments = []
      this.repairAiResult = {}
      this.repairImageName = ""
      this.repairVisible = true
    },
    closeRepair() {
      this.repairVisible = false
      this.repairSaving = false
      this.repairAiLoading = false
    },
    onRepairTargetChange(e) {
      const idx = Number((e && e.detail && e.detail.value) || -1)
      if (idx < 0 || idx >= this.repairTargetOptions.length) return
      const item = this.repairTargetOptions[idx]
      this.repairForm.targetId = Number(item.value || 0)
    },
    repairTypeLabel(value) {
      const hit = REPAIR_TYPE_OPTIONS.find((x) => x.value === value)
      return (hit && hit.label) || "其他问题"
    },
    clearRepairImage() {
      this.repairForm.attachmentUrl = ""
      this.repairForm.ocrText = ""
      this.repairAttachments = []
      this.repairImageName = ""
    },
    removeRepairAttachment(index) {
      const idx = Number(index)
      if (!Number.isFinite(idx) || idx < 0 || idx >= this.repairAttachments.length) return
      const next = this.repairAttachments.slice()
      next.splice(idx, 1)
      this.repairAttachments = next
      this.repairForm.attachmentUrl = next[0] && next[0].url ? String(next[0].url) : ""
      this.repairImageName = next[0] && next[0].name ? String(next[0].name) : ""
    },
    chooseRepairImage() {
      if (this.repairAttachments.length >= 3) {
        uni.showToast({ title: "最多上传 3 张图片", icon: "none" })
        return
      }
      uni.chooseImage({
        count: Math.max(1, 3 - this.repairAttachments.length),
        success: (res) => {
          const paths = Array.isArray(res && res.tempFilePaths) ? res.tempFilePaths : []
          if (paths.length === 0) return
          paths.forEach((filePath) => {
            const cleanPath = String(filePath || "").trim()
            if (!cleanPath) return
            const parts = cleanPath.split(/[\\/]/)
            const fileName = parts[parts.length - 1] || ""
            uni.uploadFile({
              url: `${BASE_URL}/upload`,
              filePath: cleanPath,
              name: "file",
              success: (up) => {
                let payload = null
                try {
                  payload = typeof up.data === "string" ? JSON.parse(up.data) : up.data
                } catch (e) {
                  payload = null
                }
                if (!payload || !payload.ok || !payload.data || !payload.data.url) {
                  uni.showToast({ title: (payload && payload.msg) || "上传失败", icon: "none" })
                  return
                }
                const next = this.repairAttachments.concat([
                  {
                    url: String(payload.data.url || "").trim(),
                    name: fileName
                  }
                ])
                this.repairAttachments = next.slice(0, 3)
                this.repairForm.attachmentUrl = this.repairAttachments[0] ? String(this.repairAttachments[0].url || "") : ""
                this.repairImageName = this.repairAttachments[0] ? String(this.repairAttachments[0].name || "") : ""
                uni.showToast({ title: "图片已上传", icon: "success" })
              },
              fail: () => {
                uni.showToast({ title: "上传失败", icon: "none" })
              }
            })
          })
        }
      })
    },
    async runRepairAiDiagnose() {
      if (this.repairAiLoading) return
      const description = String(this.repairForm.description || "").trim()
      const attachmentUrl = String(this.repairForm.attachmentUrl || "").trim()
      const attachments = Array.isArray(this.repairAttachments) ? this.repairAttachments : []
      if (!description && !attachmentUrl && attachments.length === 0) {
        uni.showToast({ title: "请先填写描述或上传图片", icon: "none" })
        return
      }
      this.repairAiLoading = true
      try {
        const res = await apiRequest({
          url: "/repair-orders/ai-diagnose",
          method: "POST",
          header: { "Content-Type": "application/json" },
          data: {
            equipmentId: Number(this.repairForm.targetId || 0) || null,
            labId: Number((this.lab && this.lab.id) || 0) || null,
            labName: String((this.lab && this.lab.name) || this.labName || "").trim(),
            issueType: String(this.repairForm.issueType || "other"),
            description,
            attachmentUrl,
            attachmentName: this.repairImageName,
            ocrText: String(this.repairForm.ocrText || "").trim(),
            attachments: attachments.map((item) => ({
              url: item.url,
              name: item.name,
              ocrText: String(this.repairForm.ocrText || "").trim()
            }))
          }
        })
        const payload = (res && res.data) || {}
        if (!payload.ok || !payload.data) {
          uni.showToast({ title: payload.msg || "识别失败", icon: "none" })
          return
        }
        this.repairAiResult = payload.data || {}
        if (payload.data && payload.data.issueType) {
          this.repairForm.issueType = payload.data.issueType
        }
        uni.showToast({ title: payload.data && payload.data.fallback ? "已给出人工兜底建议" : "识别完成", icon: "success" })
      } catch (e) {
        this.repairAiResult = {
          summary: "AI 识别失败，请补充描述后直接提交报修，管理员会人工处理。",
          suggestions: ["补充故障出现时间、影响范围和现场图片。"]
        }
        uni.showToast({ title: "识别失败", icon: "none" })
      } finally {
        this.repairAiLoading = false
      }
    },
    async submitRepair() {
      if (this.repairSaving) return
      const targetId = Number(this.repairForm.targetId || 0)
      const desc = String(this.repairForm.description || "").trim()
      if (!targetId && this.repairForm.issueType === "computer") {
        uni.showToast({ title: "电脑报修请关联设备", icon: "none" })
        return
      }
      if (!desc) {
        uni.showToast({ title: "请填写问题描述", icon: "none" })
        return
      }
      this.repairSaving = true
      try {
        const attachments = Array.isArray(this.repairAttachments) ? this.repairAttachments : []
        const res = await apiRequest({
          url: "/repair-orders",
          method: "POST",
          header: { "Content-Type": "application/json" },
          data: {
            equipmentId: targetId || null,
            labId: Number((this.lab && this.lab.id) || 0) || null,
            labName: String((this.lab && this.lab.name) || this.labName || "").trim(),
            issueType: this.repairForm.issueType || "other",
            description: `[${this.repairTypeLabel(this.repairForm.issueType)}] ${desc}`,
            attachmentUrl: String(this.repairForm.attachmentUrl || "").trim(),
            attachmentName: this.repairImageName,
            ocrText: String(this.repairForm.ocrText || "").trim(),
            attachments: attachments.map((item) => ({
              url: item.url,
              name: item.name,
              ocrText: String(this.repairForm.ocrText || "").trim()
            }))
          }
        })
        const payload = (res && res.data) || {}
        if (!payload.ok) {
          if (String(payload.msg || "").includes("forbidden")) {
            uni.showToast({ title: "当前账号没有报修权限", icon: "none" })
            return
          }
          uni.showToast({ title: payload.msg || "报修提交失败", icon: "none" })
          return
        }
        uni.showToast({ title: "工单已提交", icon: "success" })
        this.closeRepair()
      } catch (e) {
        uni.showToast({ title: "工单提交失败", icon: "none" })
      } finally {
        this.repairSaving = false
      }
    },
    goReserve() {
      const name = encodeURIComponent((this.lab && this.lab.name) || this.labName)
      uni.navigateTo({ url: `/pages/reserve/reserve?labName=${name}` })
    },
    goCalendar() {
      const name = encodeURIComponent((this.lab && this.lab.name) || this.labName)
      uni.navigateTo({ url: `/pages/labs/calendar?labName=${name}` })
    },
    goList() {
      const pages = getCurrentPages ? getCurrentPages() : []
      if (pages.length > 1) {
        uni.navigateBack()
        return
      }
      uni.navigateTo({ url: "/pages/labs/labs" })
    }
  }
}
</script>

<style lang="scss">
.detailPage {
  padding-bottom: 20px;
}

.heroCard {
  border: 1px solid rgba(22, 119, 255, 0.18);
  background: linear-gradient(160deg, #ffffff 0%, #f2f7ff 100%);
}

.heroTop {
  align-items: flex-start;
}

.loadingCard {
  min-height: 70px;
  display: flex;
  align-items: center;
}

.coverCard {
  border: 1px solid rgba(148, 163, 184, 0.24);
}

.cover {
  position: relative;
  width: 100%;
  padding-top: 56.25%;
  border-radius: 12px;
  overflow: hidden;
  background: #f1f5f9;
}

.coverImage,
.coverFallback {
  position: absolute;
  left: 0;
  top: 0;
  width: 100%;
  height: 100%;
}

.coverFallback {
  display: flex;
  align-items: center;
  justify-content: center;
}

.fallbackText {
  color: rgba(30, 41, 59, 0.78);
  font-weight: 700;
  font-size: 18px;
  letter-spacing: 1px;
}

.infoHeader {
  margin-top: 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.labName {
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
  flex: 1;
  min-width: 0;
}

.statusTag.warning {
  background: #fffbeb;
  color: #b45309;
}

.statusTag.info {
  background: #eff6ff;
  color: #1d4ed8;
}

.infoGrid {
  margin-top: 10px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.infoItem {
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 12px;
  padding: 10px;
  background: #fff;
}

.labelText {
  font-size: 12px;
  color: #64748b;
}

.valueText {
  margin-top: 4px;
  font-size: 20px;
  line-height: 1.2;
  font-weight: 700;
  color: #0f172a;
}

.descBox {
  margin-top: 8px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 12px;
  padding: 10px;
  font-size: 12px;
  color: #475569;
  line-height: 18px;
  background: #f8fafc;
}

.repairTip {
  margin-top: 6px;
}

.uploadRow {
  margin-top: 4px;
}

.repairPreviewList {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 8px;
}

.repairPreviewItem {
  padding: 10px;
  border-radius: 12px;
  background: #f8fafc;
}

.repairPreview {
  width: 100%;
  height: 148px;
  border-radius: 12px;
}

.repairPreviewMeta {
  margin-top: 6px;
}

.miniTextarea {
  min-height: 88px;
}

.aiRepairBox {
  margin-top: 10px;
  padding: 10px;
  border-radius: 12px;
  background: #f8fafc;
  border: 1px solid rgba(59, 130, 246, 0.16);
}

.mapSection {
  margin-top: 10px;
}

.teacherRowMap {
  margin-top: 8px;
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 6px;
}

.seatGridMap {
  margin-top: 6px;
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 6px;
}

.pcSeat {
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 8px;
  background: #f8fafc;
  padding: 6px 4px;
}

.seatCode {
  font-size: 10px;
  line-height: 14px;
  font-weight: 700;
  color: #334155;
}

.pcSeatIcon {
  margin-top: 4px;
  width: 16px;
  height: 16px;
}

.pcSeatName {
  margin-top: 3px;
  font-size: 10px;
  line-height: 13px;
  font-weight: 600;
  color: #0f172a;
  word-break: break-all;
}

.pcSeatSub {
  margin-top: 2px;
  font-size: 9px;
  line-height: 12px;
  color: #64748b;
}

.pcSeatSuccess {
  background: #f0fdf4;
  border-color: rgba(34, 197, 94, 0.35);
}

.pcSeatWarning {
  background: #fffbeb;
  border-color: rgba(245, 158, 11, 0.4);
}

.pcSeatDanger {
  background: #fef2f2;
  border-color: rgba(239, 68, 68, 0.35);
}

.pcSeatInfo {
  background: #eff6ff;
  border-color: rgba(59, 130, 246, 0.3);
}

.pcSeatEmpty {
  background: #f8fafc;
  border-color: rgba(148, 163, 184, 0.24);
}

.miniEmpty {
  margin-top: 8px;
}

.actions {
  margin-top: 10px;
  display: flex;
  gap: 8px;
}

.actionBtn {
  flex: 1;
}

.fullBtn {
  width: 100%;
  margin-top: 8px;
}

.retryBtn {
  margin-top: 10px;
}

.issueChips {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.issueChip {
  transition: all 0.14s ease;
}

.chipOn {
  border-color: #bfdbfe;
  background: #eaf3ff;
  color: #1d4ed8;
}

.pickerLike {
  min-height: 36px;
  border: 1px solid var(--color-border-primary);
  border-radius: 10px;
  background: #fff;
  padding: 8px 10px;
  color: var(--color-text-primary);
  font-size: 14px;
  box-sizing: border-box;
  display: flex;
  align-items: center;
}

.modalMask {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.36);
  z-index: 990;
}

.modalPanel {
  position: fixed;
  left: 10px;
  right: 10px;
  bottom: 14px;
  max-height: 80vh;
  overflow-y: auto;
  z-index: 991;
}

.miniBtn {
  min-height: 30px;
  line-height: 30px;
  padding: 0 10px;
  font-size: 12px;
  border-radius: 9px;
}
</style>

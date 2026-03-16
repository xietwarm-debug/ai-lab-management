<template>
  <view class="container roomMapPage">
    <view class="stack">
      <view class="card">
        <view class="rowBetween">
          <view>
            <view class="title">机房状态编辑</view>
            <view class="subtitle">labId={{ labId || "-" }} {{ labName || "" }}</view>
          </view>
          <view class="row">
            <button class="btnSecondary miniBtn" size="mini" @click="refreshAll" :disabled="loading">刷新</button>
            <button class="btnPrimary miniBtn" size="mini" @click="openCreate()">新增电脑</button>
          </view>
        </view>
        <view class="muted">状态来源：{{ runtimeMode === "api" ? "/pcs/status" : "模拟状态" }}</view>
      </view>

      <view class="card" v-if="!hasLabId">
        <view class="emptyTitle">缺少 labId</view>
        <view class="emptySub">请从实验室管理页进入</view>
      </view>

      <view class="card" v-else>
        <view class="rowBetween">
          <view class="muted">电脑 {{ equipments.length }} 台，空位 {{ emptySeatCodes.length }}</view>
          <view class="row">
            <button class="btnSecondary miniBtn" size="mini" @click="togglePolling">{{ polling ? "停止轮询" : "启动轮询" }}</button>
            <button class="btnPrimary miniBtn" size="mini" @click="openBatch" :disabled="selectedIds.length === 0">
              批量编辑({{ selectedIds.length }})
            </button>
            <button class="btnSecondary miniBtn" size="mini" v-if="multiSelect" @click="clearSelect">退出多选</button>
          </view>
        </view>
        <view class="muted tip">点击看详情，长按进入多选</view>

        <view class="loading" v-if="loading">加载中...</view>
        <view v-else>
          <view class="teacherRow">
            <view class="seat teacherSeat" :class="[seatClass(teacherSeat), isSelected(teacherSeat) ? 'selected' : '']" @click="onSeatTap(teacherSeat)" @longpress="onSeatLongPress(teacherSeat)">
              <view class="rowBetween">
                <view class="seatCode">{{ teacherSeat.code }}</view>
                <view class="check" v-if="multiSelect">{{ isSelected(teacherSeat) ? "✓" : "" }}</view>
              </view>
              <image src="/static/电脑.png" class="pcIcon" mode="aspectFit" />
              <view class="seatText">{{ teacherSeat.eq ? (teacherSeat.eq.assetCode || teacherSeat.eq.name || "-") : "空位" }}</view>
              <view class="seatSub">{{ teacherSeat.eq ? runtimeText(teacherSeat.eq) : "教师电脑位" }}</view>
            </view>
          </view>
          <view class="grid" :style="gridStyle">
            <view
              v-for="seat in seats"
              :key="seat.code"
              class="seat"
              :class="[seatClass(seat), isSelected(seat) ? 'selected' : '']"
              @click="onSeatTap(seat)"
              @longpress="onSeatLongPress(seat)"
            >
              <view class="rowBetween">
                <view class="seatCode">{{ seat.code }}</view>
                <view class="check" v-if="multiSelect">{{ isSelected(seat) ? "✓" : "" }}</view>
              </view>
              <image src="/static/电脑.png" class="pcIcon" mode="aspectFit" />
              <view class="seatText">{{ seat.eq ? (seat.eq.assetCode || seat.eq.name || "-") : "空位" }}</view>
              <view class="seatSub">{{ seat.eq ? runtimeText(seat.eq) : "点击新增" }}</view>
            </view>
          </view>
        </view>
      </view>

      <view class="modalMask" v-if="detailEq" @click="detailEq = null" />
      <view class="card modalPanel" v-if="detailEq">
        <view class="rowBetween">
          <view class="cardTitle">电脑详情</view>
          <button class="btnSecondary miniBtn" size="mini" @click="detailEq = null">关闭</button>
        </view>
        <view class="line">资产编号：{{ detailEq.assetCode || "-" }}</view>
        <view class="line">名称：{{ detailEq.name || "-" }}</view>
        <view class="line">座位：{{ detailEq.seatCode || "-" }}</view>
        <view class="line">系统：{{ detailEq.spec.os || "-" }}</view>
        <view class="line">芯片：{{ detailEq.spec.chip || "-" }}</view>
        <view class="line">备注：{{ detailEq.spec.notes || "-" }}</view>
        <view class="line">最近在线：{{ runtimeLastSeen(detailEq) }}</view>
        <view class="line">设备状态：{{ equipmentStatusText(detailEq.status) }}</view>
        <button class="btnPrimary submitBtn" @click="openEdit(detailEq)">编辑</button>
      </view>

      <view class="modalMask" v-if="formMode" @click="closeForm" />
      <view class="card modalPanel" v-if="formMode">
        <view class="rowBetween">
          <view class="cardTitle">{{ formTitle }}</view>
          <button class="btnSecondary miniBtn" size="mini" @click="closeForm">取消</button>
        </view>
        <view class="label">座位编号</view>
        <input class="inputBase" v-model.trim="form.seatCode" placeholder="例如 A1" v-if="formMode !== 'batch'" />
        <picker :range="emptySeatCodes" @change="onSeatPick" v-if="formMode === 'create'">
          <view class="pickerLike">{{ form.seatCode || "选择空位" }}</view>
        </picker>
        <view class="label" v-if="formMode === 'create'">设备名称</view>
        <input class="inputBase" v-if="formMode === 'create'" v-model.trim="form.name" placeholder="默认 PC-座位号" />
        <view class="label">设备状态</view>
        <view class="chips">
          <view class="chip" :class="{ on: form.status === '' }" v-if="formMode === 'batch'" @click="form.status = ''">不修改</view>
          <view class="chip" :class="{ on: form.status === 'in_service' }" @click="form.status = 'in_service'">在用</view>
          <view class="chip" :class="{ on: form.status === 'repairing' }" @click="form.status = 'repairing'">维修中</view>
          <view class="chip" :class="{ on: form.status === 'scrapped' }" @click="form.status = 'scrapped'">已报废</view>
        </view>
        <view class="label">操作系统</view>
        <input class="inputBase" v-model.trim="form.os" placeholder="例如 Windows 11" />
        <view class="label">芯片</view>
        <input class="inputBase" v-model.trim="form.chip" placeholder="例如 i5-12400" />
        <view class="label">备注</view>
        <textarea class="textareaBase" v-model.trim="form.notes" maxlength="800" placeholder="备注" />
        <view class="label" v-if="formMode === 'edit'">最近在线</view>
        <input class="inputBase" v-if="formMode === 'edit'" v-model.trim="form.lastSeen" placeholder="2026-03-03 12:30:00" />
        <button class="btnPrimary submitBtn" :disabled="saving || deleting" @click="submitForm">{{ saving ? "提交中..." : formSubmitText }}</button>
        <button
          class="btnDanger submitBtn"
          v-if="formMode === 'edit'"
          :disabled="saving || deleting"
          @click="deleteCurrentEquipment"
        >
          {{ deleting ? "删除中..." : "删除电脑" }}
        </button>
      </view>
    </view>
  </view>
</template>

<script>
import { apiRequest, toQuery } from "@/common/api.js"

function pick(obj, ...keys) {
  for (let i = 0; i < keys.length; i += 1) {
    const v = obj && obj[keys[i]]
    if (v !== undefined && v !== null) return v
  }
  return ""
}

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
  let v = 0
  for (let i = 0; i < letters.length; i += 1) v = v * 26 + (letters.charCodeAt(i) - 64)
  return v
}

function rowLetters(index) {
  let n = Number(index || 1)
  let out = ""
  while (n > 0) {
    const r = (n - 1) % 26
    out = String.fromCharCode(65 + r) + out
    n = Math.floor((n - 1) / 26)
  }
  return out || "A"
}

function parseSeat(code) {
  const c = seatCodeOf(code)
  const m = c.match(/^([A-Z]+)(\d{1,3})$/)
  if (!m) return null
  return { row: rowIndex(m[1]), col: Number(m[2]), code: c }
}

function isAllowedSeatCode(code) {
  const c = seatCodeOf(code)
  if (!c) return false
  if (/^O\d+$/i.test(c)) return c === "O1"
  const p = parseSeat(c)
  if (!p) return false
  return p.col >= 1 && p.col <= 6
}

function nowText() {
  const d = new Date()
  const p = (n) => (n < 10 ? `0${n}` : `${n}`)
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`
}

export default {
  data() {
    return {
      labId: 0,
      labName: "",
      loading: false,
      polling: false,
      timer: null,
      runtimeMode: "mock",
      equipments: [],
      runtimeMap: {},
      multiSelect: false,
      selectedIds: [],
      detailEq: null,
      formMode: "",
      formEqId: 0,
      form: { seatCode: "", name: "", status: "in_service", os: "", chip: "", notes: "", lastSeen: "" },
      saving: false,
      deleting: false
    }
  },
  computed: {
    hasLabId() {
      return Number(this.labId) > 0
    },
    teacherSeat() {
      const teacherEq = this.equipments.find((eq) => eq.seatCode === "O1") || null
      return { code: "O1", eq: teacherEq }
    },
    seats() {
      const MAX_COL = 6
      const RESERVE_SLOTS = 6
      const map = {}
      let occupiedStudents = 0
      let maxRowIndex = 1
      this.equipments.forEach((eq) => {
        if (!eq.seatCode) return
        if (/^O\d+$/i.test(eq.seatCode)) return
        const p = parseSeat(eq.seatCode)
        if (!p) return
        if (p.col < 1 || p.col > MAX_COL) return
        const code = `${rowLetters(p.row)}${p.col}`
        map[code] = eq
        occupiedStudents += 1
        if (p.row > maxRowIndex) maxRowIndex = p.row
      })

      const rowsByCapacity = Math.max(1, Math.ceil((occupiedStudents + RESERVE_SLOTS) / MAX_COL))
      const totalRows = Math.max(maxRowIndex, rowsByCapacity)
      const out = []
      for (let r = 1; r <= totalRows; r += 1) {
        for (let c = 1; c <= MAX_COL; c += 1) {
          const code = `${rowLetters(r)}${c}`
          out.push({ code, eq: map[code] || null })
        }
      }
      out.sort((a, b) => {
        const pa = parseSeat(a.code)
        const pb = parseSeat(b.code)
        if (!pa || !pb) return String(a.code).localeCompare(String(b.code))
        return pa.row * 10000 + pa.col - (pb.row * 10000 + pb.col)
      })
      return out
    },
    gridStyle() {
      return { gridTemplateColumns: "repeat(6, minmax(0, 1fr))" }
    },
    emptySeatCodes() {
      const out = []
      if (!this.teacherSeat.eq) out.push("O1")
      this.seats.forEach((x) => {
        if (!x.eq) out.push(x.code)
      })
      return out
    },
    formTitle() {
      if (this.formMode === "create") return "新增电脑"
      if (this.formMode === "edit") return "编辑电脑"
      if (this.formMode === "batch") return `批量编辑（${this.selectedIds.length} 台）`
      return ""
    },
    formSubmitText() {
      if (this.formMode === "create") return "创建电脑"
      if (this.formMode === "edit") return "保存修改"
      if (this.formMode === "batch") return "提交批量更新"
      return "提交"
    }
  },
  onLoad(options) {
    this.labId = Number((options && options.labId) || 0)
    this.labName = (options && options.labName) || ""
    if (!this.ensureAdmin()) return
    if (!this.hasLabId) {
      uni.showToast({ title: "缺少 labId", icon: "none" })
      return
    }
    this.refreshAll()
    this.startPolling()
  },
  onShow() {
    if (!this.ensureAdmin()) return
    if (this.hasLabId) this.startPolling()
  },
  onHide() {
    this.stopPolling()
  },
  onUnload() {
    this.stopPolling()
  },
  methods: {
    ensureAdmin() {
      const s = uni.getStorageSync("session") || {}
      if (s.role === "admin") return true
      uni.showToast({ title: "无权限", icon: "none" })
      const pages = typeof getCurrentPages === "function" ? getCurrentPages() || [] : []
      if (pages.length > 1) uni.navigateBack()
      else uni.switchTab({ url: "/pages/index/index" })
      return false
    },
    normalizeEq(row) {
      const spec = parseSpec(pick(row, "specJson", "spec_json"))
      let seatCode = seatCodeOf(pick(spec, "seatCode", "seat", "seat_code") || pick(row, "seatCode", "seat_code"))
      if (!seatCode) {
        const m = String(pick(row, "assetCode", "asset_code") || "").toUpperCase().match(/^PC-([A-Z]+\d{1,3})$/)
        seatCode = m ? seatCodeOf(m[1]) : ""
      }
      return {
        id: Number(pick(row, "id") || 0),
        assetCode: String(pick(row, "assetCode", "asset_code") || ""),
        name: String(pick(row, "name") || ""),
        model: String(pick(row, "model") || ""),
        brand: String(pick(row, "brand") || ""),
        labId: pick(row, "labId", "lab_id"),
        labName: String(pick(row, "labName", "lab_name") || ""),
        status: String(pick(row, "status") || "in_service"),
        keeper: String(pick(row, "keeper") || ""),
        purchaseDate: String(pick(row, "purchaseDate", "purchase_date") || ""),
        price: pick(row, "price"),
        imageUrl: String(pick(row, "imageUrl", "image_url") || ""),
        spec,
        seatCode
      }
    },
    isPc(eq) {
      const c = String((eq.spec && eq.spec.category) || "").toLowerCase()
      if (c) return c === "pc"
      return /^PC-/i.test(eq.assetCode || "")
    },
    async refreshAll() {
      if (!this.hasLabId || this.loading) return
      this.loading = true
      try {
        let page = 1
        const rows = []
        for (let i = 0; i < 20; i += 1) {
          const qs = toQuery({ labId: this.labId, category: "pc", page, pageSize: 100 })
          const res = await apiRequest({ url: `/equipments?${qs}`, method: "GET" })
          const body = (res && res.data) || {}
          const list = Array.isArray(body.data) ? body.data : Array.isArray(body) ? body : []
          if (!Array.isArray(list)) break
          rows.push(...list)
          const total = Number((body.meta && body.meta.total) || rows.length)
          if (rows.length >= total || list.length === 0) break
          page += 1
        }
        this.equipments = rows.map((x) => this.normalizeEq(x)).filter((x) => x.id > 0 && this.isPc(x))
        if (!this.labName && this.equipments.length) this.labName = this.equipments[0].labName || ""
        this.selectedIds = this.selectedIds.filter((id) => this.equipments.some((x) => x.id === id))
        await this.refreshRuntime()
      } catch (e) {
        uni.showToast({ title: "加载失败", icon: "none" })
      } finally {
        this.loading = false
      }
    },
    async refreshRuntime() {
      try {
        const qs = toQuery({ labId: this.labId })
        const res = await apiRequest({ url: `/pcs/status?${qs}`, method: "GET" })
        const body = (res && res.data) || {}
        const rows = Array.isArray(body) ? body : Array.isArray(body.data) ? body.data : []
        if (!rows.length || (body.ok === false && !Array.isArray(body))) throw new Error("no api")
        const map = {}
        const seatId = {}
        this.equipments.forEach((eq) => { if (eq.seatCode) seatId[eq.seatCode] = eq.id })
        rows.forEach((r) => {
          let id = Number(pick(r, "equipmentId", "equipment_id", "id") || 0)
          if (!id) {
            const sc = seatCodeOf(pick(r, "seatCode", "seat_code"))
            if (sc && seatId[sc]) id = Number(seatId[sc])
          }
          if (!id) return
          map[String(id)] = {
            status: String(pick(r, "status", "state") || "online").toLowerCase(),
            lastSeen: String(pick(r, "lastSeen", "last_seen", "updatedAt", "updated_at") || "")
          }
        })
        this.runtimeMap = map
        this.runtimeMode = "api"
      } catch (e) {
        const states = ["online", "offline", "warning"]
        const map = {}
        this.equipments.forEach((eq, idx) => {
          map[String(eq.id)] = { status: states[(idx + Math.floor(Math.random() * 3)) % 3], lastSeen: nowText() }
        })
        this.runtimeMap = map
        this.runtimeMode = "mock"
      }
    },
    startPolling() {
      if (this.polling || !this.hasLabId) return
      this.polling = true
      this.timer = setInterval(() => this.refreshRuntime(), 10000)
    },
    stopPolling() {
      if (this.timer) clearInterval(this.timer)
      this.timer = null
      this.polling = false
    },
    togglePolling() {
      if (this.polling) this.stopPolling()
      else this.startPolling()
    },
    runtimeText(eq) {
      const rt = this.runtimeMap[String(eq.id)] || {}
      if (rt.status === "online") return "在线"
      if (rt.status === "offline") return "离线"
      if (rt.status === "warning" || rt.status === "fault") return "异常"
      return this.equipmentStatusText(eq.status)
    },
    runtimeLastSeen(eq) {
      const rt = this.runtimeMap[String(eq.id)] || {}
      return rt.lastSeen || eq.spec.lastSeen || "-"
    },
    equipmentStatusText(status) {
      if (status === "in_service") return "在用"
      if (status === "repairing") return "维修中"
      if (status === "scrapped") return "已报废"
      return status || "-"
    },
    seatClass(seat) {
      if (!seat.eq) return "empty"
      const st = (this.runtimeMap[String(seat.eq.id)] || {}).status
      if (st === "online") return "online"
      if (st === "offline") return "offline"
      if (st === "warning" || st === "fault") return "warning"
      if (seat.eq.status === "scrapped") return "danger"
      if (seat.eq.status === "repairing") return "warning"
      return "online"
    },
    isSelected(seat) {
      return !!(seat && seat.eq && this.selectedIds.includes(seat.eq.id))
    },
    onSeatTap(seat) {
      if (this.multiSelect) {
        if (!seat.eq) return
        const i = this.selectedIds.indexOf(seat.eq.id)
        if (i >= 0) this.selectedIds.splice(i, 1)
        else this.selectedIds.push(seat.eq.id)
        if (!this.selectedIds.length) this.multiSelect = false
        return
      }
      if (seat.eq) this.detailEq = seat.eq
      else this.openCreate(seat.code)
    },
    onSeatLongPress(seat) {
      if (!seat.eq) return
      if (!this.multiSelect) {
        this.multiSelect = true
        this.selectedIds = []
      }
      if (!this.selectedIds.includes(seat.eq.id)) this.selectedIds.push(seat.eq.id)
    },
    clearSelect() {
      this.multiSelect = false
      this.selectedIds = []
    },
    openCreate(code = "") {
      this.detailEq = null
      this.deleting = false
      this.formMode = "create"
      this.formEqId = 0
      this.form = { seatCode: seatCodeOf(code), name: "", status: "in_service", os: "", chip: "", notes: "", lastSeen: "" }
    },
    openEdit(eq) {
      if (!eq) return
      this.detailEq = null
      this.deleting = false
      this.formMode = "edit"
      this.formEqId = eq.id
      this.form = {
        seatCode: eq.seatCode || "",
        name: eq.name || "",
        status: eq.status || "in_service",
        os: eq.spec.os || "",
        chip: eq.spec.chip || "",
        notes: eq.spec.notes || "",
        lastSeen: eq.spec.lastSeen || ""
      }
    },
    openBatch() {
      if (!this.selectedIds.length) return
      this.detailEq = null
      this.deleting = false
      this.formMode = "batch"
      this.formEqId = 0
      this.form = { seatCode: "", name: "", status: "", os: "", chip: "", notes: "", lastSeen: "" }
    },
    closeForm() {
      this.formMode = ""
      this.formEqId = 0
      this.saving = false
      this.deleting = false
    },
    onSeatPick(e) {
      const idx = Number((e && e.detail && e.detail.value) || -1)
      if (idx >= 0 && idx < this.emptySeatCodes.length) this.form.seatCode = this.emptySeatCodes[idx]
    },
    payloadFor(eq, nextStatus, nextSpec) {
      return {
        assetCode: String(eq.assetCode || "").trim(),
        name: String(eq.name || eq.assetCode || "").trim(),
        model: String(eq.model || "").trim(),
        brand: String(eq.brand || "").trim(),
        labId: Number(eq.labId || this.labId || 0) || null,
        labName: String(eq.labName || this.labName || "").trim(),
        status: String(nextStatus || eq.status || "in_service").trim(),
        keeper: String(eq.keeper || "").trim(),
        purchaseDate: String(eq.purchaseDate || "").trim(),
        price: eq.price === null || eq.price === undefined ? "" : String(eq.price),
        specJson: JSON.stringify(nextSpec || {}),
        imageUrl: String(eq.imageUrl || "").trim()
      }
    },
    async submitForm() {
      if (this.saving) return
      if (!this.ensureAdmin()) return
      this.saving = true
      try {
        if (this.formMode === "create") {
          const seatCode = seatCodeOf(this.form.seatCode)
          if (!seatCode) throw new Error("座位号格式错误")
          if (!isAllowedSeatCode(seatCode)) throw new Error("座位号仅支持 O1 或 *1-*6")
          if (this.equipments.some((x) => x.seatCode === seatCode)) throw new Error(`座位 ${seatCode} 已占用`)
          const assetCode = `PC-${seatCode}`
          const payload = {
            assetCode,
            name: String(this.form.name || "").trim() || assetCode,
            model: "",
            brand: "",
            labId: Number(this.labId),
            labName: String(this.labName || "").trim(),
            status: this.form.status || "in_service",
            keeper: "",
            purchaseDate: "",
            price: "",
            specJson: JSON.stringify({
              category: "pc",
              seatCode,
              os: String(this.form.os || "").trim(),
              chip: String(this.form.chip || "").trim(),
              notes: String(this.form.notes || "").trim(),
              lastSeen: nowText()
            }),
            imageUrl: ""
          }
          const res = await apiRequest({ url: "/equipments", method: "POST", header: { "Content-Type": "application/json" }, data: payload })
          const body = (res && res.data) || {}
          if (!body.ok) throw new Error(body.msg || "创建失败")
        } else if (this.formMode === "edit") {
          const eq = this.equipments.find((x) => x.id === this.formEqId)
          if (!eq) throw new Error("设备不存在")
          const seatCode = seatCodeOf(this.form.seatCode)
          if (!seatCode) throw new Error("座位号格式错误")
          if (!isAllowedSeatCode(seatCode)) throw new Error("座位号仅支持 O1 或 *1-*6")
          const conflict = this.equipments.find((x) => x.id !== eq.id && x.seatCode === seatCode)
          if (conflict) throw new Error(`座位 ${seatCode} 已占用`)
          const spec = {
            ...(eq.spec || {}),
            category: "pc",
            seatCode,
            os: String(this.form.os || "").trim(),
            chip: String(this.form.chip || "").trim(),
            notes: String(this.form.notes || "").trim()
          }
          if (String(this.form.lastSeen || "").trim()) spec.lastSeen = String(this.form.lastSeen || "").trim()
          else delete spec.lastSeen
          const payload = this.payloadFor(eq, this.form.status, spec)
          const res = await apiRequest({ url: `/equipments/${eq.id}`, method: "POST", header: { "Content-Type": "application/json" }, data: payload })
          const body = (res && res.data) || {}
          if (!body.ok) throw new Error(body.msg || "保存失败")
        } else if (this.formMode === "batch") {
          const targets = this.equipments.filter((x) => this.selectedIds.includes(x.id))
          if (!targets.length) throw new Error("未选中设备")
          const patch = {
            status: String(this.form.status || "").trim(),
            os: String(this.form.os || "").trim(),
            chip: String(this.form.chip || "").trim(),
            notes: String(this.form.notes || "").trim()
          }
          if (!patch.status && !patch.os && !patch.chip && !patch.notes) throw new Error("请至少填写一个修改字段")
          let batchOk = false
          try {
            const batchRes = await apiRequest({
              url: "/equipments/batch-update",
              method: "POST",
              header: { "Content-Type": "application/json" },
              data: { ids: targets.map((x) => x.id), patch }
            })
            const b = (batchRes && batchRes.data) || {}
            batchOk = !!b.ok
          } catch (e) {
            batchOk = false
          }
          if (!batchOk) {
            for (let i = 0; i < targets.length; i += 1) {
              const eq = targets[i]
              const spec = { ...(eq.spec || {}), category: "pc", seatCode: eq.seatCode || "" }
              if (patch.os) spec.os = patch.os
              if (patch.chip) spec.chip = patch.chip
              if (patch.notes) spec.notes = patch.notes
              const payload = this.payloadFor(eq, patch.status || eq.status, spec)
              const r = await apiRequest({ url: `/equipments/${eq.id}`, method: "POST", header: { "Content-Type": "application/json" }, data: payload })
              const body = (r && r.data) || {}
              if (!body.ok) throw new Error(body.msg || `批量更新失败(${eq.assetCode || eq.id})`)
            }
          }
        }
        uni.showToast({ title: "操作成功", icon: "success" })
        this.closeForm()
        this.clearSelect()
        this.detailEq = null
        await this.refreshAll()
      } catch (e) {
        uni.showToast({ title: (e && e.message) || "操作失败", icon: "none" })
      } finally {
        this.saving = false
      }
    },
    async deleteCurrentEquipment() {
      if (!this.ensureAdmin()) return
      if (this.formMode !== "edit" || this.deleting || this.saving) return
      const eq = this.equipments.find((x) => x.id === this.formEqId)
      if (!eq) {
        uni.showToast({ title: "设备不存在", icon: "none" })
        return
      }

      const confirmed = await new Promise((resolve) => {
        uni.showModal({
          title: "删除电脑",
          content: `确认删除 ${eq.assetCode || eq.name || eq.id} 吗？`,
          success: (res) => resolve(!!(res && res.confirm)),
          fail: () => resolve(false)
        })
      })
      if (!confirmed) return

      this.deleting = true
      try {
        const res = await apiRequest({
          url: `/equipments/${eq.id}/delete`,
          method: "POST"
        })
        const body = (res && res.data) || {}
        if (!body.ok) throw new Error(body.msg || "删除失败")
        uni.showToast({ title: "删除成功", icon: "success" })
        this.closeForm()
        this.clearSelect()
        this.detailEq = null
        await this.refreshAll()
      } catch (e) {
        uni.showToast({ title: (e && e.message) || "删除失败", icon: "none" })
      } finally {
        this.deleting = false
      }
    }
  }
}
</script>

<style lang="scss">
.roomMapPage { padding-bottom: 20px; }
.miniBtn { min-height: 30px; line-height: 30px; padding: 0 10px; border-radius: 9px; font-size: 12px; }
.row { display: flex; gap: 8px; }
.tip { margin-top: 6px; }
.loading { margin-top: 10px; font-size: 12px; color: #64748b; }
.teacherRow { margin-top: 8px; margin-bottom: 8px; display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 6px; }
.teacherSeat { width: auto; }
.grid { margin-top: 8px; display: grid; gap: 6px; }
.seat { border-radius: 8px; padding: 6px 4px; border: 1px solid rgba(148,163,184,.28); background: #f8fafc; }
.seatCode { font-size: 10px; font-weight: 700; }
.check { width: 14px; height: 14px; line-height: 14px; text-align: center; border-radius: 999px; border: 1px solid rgba(15,23,42,.2); font-size: 9px; }
.pcIcon { margin-top: 4px; width: 16px; height: 16px; }
.seatText { margin-top: 3px; font-size: 10px; color: #0f172a; font-weight: 600; line-height: 13px; word-break: break-all; }
.seatSub { margin-top: 2px; font-size: 9px; color: #475569; line-height: 12px; }
.online { background: #f0fdf4; border-color: rgba(34,197,94,.35); }
.offline { background: #f1f5f9; border-color: rgba(148,163,184,.35); }
.warning { background: #fffbeb; border-color: rgba(245,158,11,.38); }
.danger { background: #fef2f2; border-color: rgba(239,68,68,.35); }
.empty { background: #f8fafc; border-color: rgba(148,163,184,.28); }
.selected { box-shadow: 0 0 0 2px rgba(59,130,246,.25); }
.line { margin-top: 6px; font-size: 13px; color: #334155; }
.submitBtn { margin-top: 12px; width: 100%; }
.chips { margin-top: 8px; display: flex; gap: 8px; flex-wrap: wrap; }
.chip { padding: 4px 10px; border-radius: 999px; border: 1px solid rgba(148,163,184,.3); font-size: 12px; color: #334155; }
.chip.on { background: #eaf3ff; border-color: #bfdbfe; color: #1d4ed8; }
.pickerLike { min-height: 36px; border: 1px solid var(--color-border-primary); border-radius: 10px; background: #fff; padding: 8px 10px; display: flex; align-items: center; font-size: 14px; color: var(--color-text-primary); }
.modalMask { position: fixed; inset: 0; background: rgba(15,23,42,.36); z-index: 990; }
.modalPanel { position: fixed; left: 10px; right: 10px; bottom: 14px; max-height: 80vh; overflow-y: auto; z-index: 991; }
</style>

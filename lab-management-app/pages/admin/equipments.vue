<template>
  <view class="container equipmentsPage">
    <view class="stack">
      <view class="card heroCard">
        <view class="rowBetween heroTop">
          <view>
            <view class="title">设备资产生命周期</view>
            <view class="subtitle">借还、调拨、报废、维保、盘点、扫码定位</view>
          </view>
          <view class="heroActions">
            <button class="btnPrimary miniBtn" size="mini" @click="goCreate">新增设备</button>
            <button class="btnSecondary miniBtn" size="mini" @click="startInventorySession">新建盘点</button>
          </view>
        </view>
      </view>

      <view class="card filterCard">
        <view class="label">关键词</view>
        <input
          class="inputBase"
          v-model.trim="keyword"
          placeholder="搜索资产编号、设备名、实验室"
          confirm-type="search"
          @confirm="doSearch"
        />

        <view class="label">状态</view>
        <view class="chipRow">
          <view
            class="chip statusChip"
            v-for="opt in statusOptions"
            :key="opt.value"
            :class="{ chipOn: status === opt.value }"
            @click="setStatus(opt.value)"
          >
            {{ opt.label }}
          </view>
        </view>

        <view class="label">借用筛选</view>
        <view class="chipRow">
          <view
            class="chip statusChip"
            v-for="opt in borrowedOptions"
            :key="opt.value"
            :class="{ chipOn: borrowedFilter === opt.value }"
            @click="setBorrowedFilter(opt.value)"
          >
            {{ opt.label }}
          </view>
        </view>

        <view class="label">到期筛选</view>
        <view class="chipRow">
          <view
            class="chip statusChip"
            v-for="opt in dueOptions"
            :key="opt.value"
            :class="{ chipOn: dueMode === opt.value }"
            @click="setDueMode(opt.value)"
          >
            {{ opt.label }}
          </view>
        </view>

        <view class="actions">
          <button class="btnPrimary miniBtn" size="mini" @click="doSearch">查询</button>
          <button class="btnSecondary miniBtn" size="mini" @click="resetFilters">重置</button>
          <button class="btnSecondary miniBtn" size="mini" @click="refreshPanel">刷新工作台</button>
        </view>
      </view>

      <view class="card inventoryCard">
        <view class="rowBetween sectionHeader">
          <view>
            <view class="cardTitle">盘点任务</view>
            <view class="muted" v-if="inventorySession">
              {{ inventorySession.inventoryNo || "-" }} ｜ 已扫 {{ inventorySession.checkedCount || 0 }} / {{ inventorySession.plannedCount || 0 }}
            </view>
            <view class="muted" v-else>当前无进行中盘点</view>
          </view>
          <view class="rowActions">
            <button class="btnSecondary miniBtn" size="mini" @click="fetchOpenInventorySession">刷新</button>
            <button
              class="btnDanger miniBtn"
              size="mini"
              :disabled="!inventorySession"
              @click="closeInventorySession"
            >
              结束盘点
            </button>
          </view>
        </view>

        <view class="inventoryBody" v-if="inventorySession">
          <view class="rowGrid">
            <input
              class="inputBase"
              v-model.trim="inventoryCode"
              placeholder="输入或扫码资产码/二维码"
              confirm-type="done"
              @confirm="submitInventoryScan"
            />
            <input
              class="inputBase"
              v-model.trim="inventoryNote"
              placeholder="盘点备注（可选）"
              confirm-type="done"
            />
          </view>
          <view class="actions">
            <button class="btnPrimary miniBtn" size="mini" :disabled="lifecycleBusy" @click="submitInventoryScan">登记扫描</button>
            <button class="btnSecondary miniBtn" size="mini" :disabled="lifecycleBusy" @click="scanInventoryByCamera">扫码填入</button>
            <button class="btnSecondary miniBtn" size="mini" :disabled="lifecycleBusy" @click="showInventoryDiffs">差异记录</button>
          </view>
        </view>
      </view>

      <view class="card locateCard">
        <view class="rowBetween sectionHeader">
          <view>
            <view class="cardTitle">扫码定位</view>
            <view class="muted">输入资产码/二维码内容定位设备所在实验室</view>
          </view>
        </view>
        <view class="rowGrid">
          <input class="inputBase" v-model.trim="locateCode" placeholder="例如 EQ-1001 或 LAB-ASSET:xxxx" />
          <view class="actions">
            <button class="btnPrimary miniBtn" size="mini" @click="locateByCode">定位</button>
            <button class="btnSecondary miniBtn" size="mini" @click="scanLocateByCamera">扫码</button>
          </view>
        </view>
      </view>

      <view class="card dueCard" v-if="dueRows.length > 0">
        <view class="rowBetween sectionHeader">
          <view>
            <view class="cardTitle">30 天内到期提醒</view>
            <view class="muted">维保 / 质保 到期设备 {{ dueRows.length }} 台</view>
          </view>
          <button class="btnSecondary miniBtn" size="mini" @click="fetchDueList">刷新</button>
        </view>
        <view class="stack dueList">
          <view class="dueItem" v-for="row in dueRows" :key="`due-${row.id}`">
            <view class="lineClampOne">{{ row.assetCode || "-" }} · {{ row.name || "-" }}</view>
            <view class="muted lineClampOne">{{ row.labName || "-" }} ｜ 下次保养 {{ row.nextMaintenanceAt || "-" }} ｜ 质保到期 {{ row.warrantyUntil || "-" }}</view>
          </view>
        </view>
      </view>

      <view class="card" v-if="loading && rows.length === 0">
        <view class="muted">加载中...</view>
      </view>

      <view class="emptyState card" v-else-if="rows.length === 0">
        <view class="emptyIcon">📭</view>
        <view class="emptyTitle">暂无设备数据</view>
        <view class="emptySub">可点击“新增设备”创建第一条设备台账</view>
      </view>

      <view class="stack" v-else>
        <view class="card itemCard" v-for="item in rows" :key="item.id" @click="goEdit(item)">
          <view class="rowBetween">
            <view class="itemName">{{ item.name || "-" }}</view>
            <view class="statusTag" :class="statusTone(item.status)">
              {{ statusText(item.status) }}
            </view>
          </view>

          <view class="meta">资产编号：{{ item.assetCode || "-" }}</view>
          <view class="meta">实验室：{{ item.labName || "-" }}</view>
          <view class="meta">借用状态：{{ item.isBorrowed ? `已借出（${item.borrowedBy || "未知"}）` : "在库" }}</view>
          <view class="meta">借用权限：{{ item.allowBorrow === false ? "禁止借用" : "允许借用" }}</view>
          <view class="meta">下次保养：{{ item.nextMaintenanceAt || "-" }}</view>
          <view class="meta">质保到期：{{ item.warrantyUntil || "-" }}</view>
          <view class="meta" v-if="item.locationNote">定位备注：{{ item.locationNote }}</view>

          <view class="actions itemActions">
            <button
              class="btnSecondary miniBtn"
              size="mini"
              @click.stop="item.isBorrowed ? handleReturn(item) : handleBorrow(item)"
              :disabled="lifecycleBusy || item.status === 'scrapped' || (!item.isBorrowed && item.allowBorrow === false)"
            >
              {{ item.isBorrowed ? "归还" : "借用" }}
            </button>
            <button
              class="btnSecondary miniBtn"
              size="mini"
              @click.stop="handleTransfer(item)"
              :disabled="lifecycleBusy || item.status === 'scrapped'"
            >
              调拨
            </button>
            <button class="btnSecondary miniBtn" size="mini" @click.stop="handleMaintenance(item)" :disabled="lifecycleBusy">维保</button>
            <button class="btnSecondary miniBtn" size="mini" @click.stop="showCode(item)" :disabled="lifecycleBusy">资产码</button>
            <button
              class="btnDanger miniBtn"
              size="mini"
              @click.stop="handleScrap(item)"
              :disabled="lifecycleBusy || item.status === 'scrapped'"
            >
              报废
            </button>
          </view>
        </view>
      </view>

      <view class="card pageCard rowBetween" v-if="rows.length > 0">
        <view class="muted">第 {{ page }} 页 / 共 {{ total }} 条</view>
        <view class="muted" v-if="loadingMore">加载更多中...</view>
        <view class="muted" v-else-if="!hasMore">没有更多了</view>
        <view class="muted" v-else>上拉加载更多</view>
      </view>
    </view>

    <view class="scannerMask" v-if="h5ScannerVisible" @click="closeH5Scanner">
      <view class="scannerDialog card" @click.stop>
        <view class="rowBetween sectionHeader">
          <view>
            <view class="cardTitle">{{ h5ScannerTitle || "浏览器扫码" }}</view>
            <view class="muted">{{ h5ScannerHint || "请将资产二维码或条码置于取景框中央" }}</view>
          </view>
          <button class="btnSecondary miniBtn" size="mini" @click="closeH5Scanner">关闭</button>
        </view>

        <view class="scannerPreview">
          <video ref="h5ScannerVideo" class="scannerVideo" autoplay muted playsinline></video>
          <view class="scannerGuide"></view>
        </view>

        <view class="scannerError" v-if="h5ScannerError">{{ h5ScannerError }}</view>

        <view class="actions">
          <button class="btnPrimary miniBtn" size="mini" @click="restartH5Scanner">重新识别</button>
          <button class="btnSecondary miniBtn" size="mini" @click="closeH5Scanner">取消</button>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { apiRequest, toQuery } from "@/common/api.js"

export default {
  data() {
    return {
      keyword: "",
      status: "",
      borrowedFilter: "",
      dueMode: "",
      rows: [],
      page: 1,
      pageSize: 20,
      total: 0,
      loading: false,
      loadingMore: false,
      lifecycleBusy: false,
      inventorySession: null,
      inventoryCode: "",
      inventoryNote: "",
      locateCode: "",
      dueRows: [],
      h5ScannerVisible: false,
      h5ScannerTitle: "",
      h5ScannerHint: "",
      h5ScannerTarget: "",
      h5ScannerError: ""
    }
  },
  computed: {
    hasMore() {
      return this.rows.length < this.total
    },
    statusOptions() {
      return [
        { label: "全部", value: "" },
        { label: "在用", value: "in_service" },
        { label: "维修中", value: "repairing" },
        { label: "已报废", value: "scrapped" }
      ]
    },
    borrowedOptions() {
      return [
        { label: "全部", value: "" },
        { label: "已借出", value: "borrowed" },
        { label: "在库", value: "free" }
      ]
    },
    dueOptions() {
      return [
        { label: "不限", value: "" },
        { label: "维保到期", value: "maintenance" },
        { label: "质保到期", value: "warranty" }
      ]
    }
  },
  onShow() {
    if (!this.ensureAdmin()) return
    this.refreshPanel()
  },
  onHide() {
    this.closeH5Scanner()
  },
  onUnload() {
    this.closeH5Scanner()
  },
  onPullDownRefresh() {
    if (!this.ensureAdmin()) {
      uni.stopPullDownRefresh()
      return
    }
    this.refreshPanel(true)
  },
  onReachBottom() {
    if (!this.ensureAdmin()) return
    this.fetchList(false)
  },
  methods: {
    ensureAdmin() {
      const session = uni.getStorageSync("session") || {}
      if (session.role === "admin") return true
      uni.showToast({ title: "无权限", icon: "none" })
      const pages = typeof getCurrentPages === "function" ? (getCurrentPages() || []) : []
      if (pages.length > 1) {
        uni.navigateBack()
      } else {
        uni.switchTab({ url: "/pages/index/index" })
      }
      return false
    },
    statusText(status) {
      if (status === "in_service") return "在用"
      if (status === "repairing") return "维修中"
      if (status === "scrapped") return "已报废"
      return status || "-"
    },
    statusTone(status) {
      if (status === "in_service") return "success"
      if (status === "repairing") return "warning"
      if (status === "scrapped") return "danger"
      return "info"
    },
    setStatus(value) {
      this.status = value
      this.fetchList(true)
    },
    setBorrowedFilter(value) {
      this.borrowedFilter = value
      this.fetchList(true)
    },
    setDueMode(value) {
      this.dueMode = value
      this.fetchList(true)
    },
    doSearch() {
      this.fetchList(true)
    },
    resetFilters() {
      this.keyword = ""
      this.status = ""
      this.borrowedFilter = ""
      this.dueMode = ""
      this.fetchList(true)
    },
    buildListQuery(page) {
      const q = {
        keyword: this.keyword,
        status: this.status,
        page,
        pageSize: this.pageSize
      }
      if (this.borrowedFilter === "borrowed") q.isBorrowed = 1
      else if (this.borrowedFilter === "free") q.isBorrowed = 0

      if (this.dueMode === "maintenance") q.maintenanceDueDays = 30
      else if (this.dueMode === "warranty") q.warrantyDueDays = 30

      return q
    },
    async fetchList(reset = false) {
      if (reset) {
        if (this.loading) return
      } else if (this.loadingMore || this.loading || !this.hasMore) {
        return
      }

      const nextPage = reset ? 1 : this.page + 1
      if (reset) this.loading = true
      else this.loadingMore = true

      try {
        const query = toQuery(this.buildListQuery(nextPage))
        const res = await apiRequest({
          url: `/equipments${query ? `?${query}` : ""}`,
          method: "GET"
        })
        const body = (res && res.data) || {}
        if (!body.ok) {
          uni.showToast({ title: body.msg || "加载失败", icon: "none" })
          return
        }
        const list = Array.isArray(body.data) ? body.data : []
        const meta = body.meta || {}
        this.page = Number(meta.page || nextPage)
        this.pageSize = Number(meta.pageSize || this.pageSize)
        this.total = Number(meta.total || 0)
        this.rows = reset ? list : this.rows.concat(list)
      } catch (e) {
        uni.showToast({ title: "加载失败，请重试", icon: "none" })
      } finally {
        this.loading = false
        this.loadingMore = false
      }
    },
    async refreshPanel(stopRefresh = false) {
      try {
        await Promise.all([this.fetchList(true), this.fetchOpenInventorySession(), this.fetchDueList()])
      } finally {
        if (stopRefresh) uni.stopPullDownRefresh()
      }
    },
    goCreate() {
      uni.navigateTo({ url: "/pages/admin/equipment_edit" })
    },
    goEdit(item) {
      if (!item || !item.id) return
      uni.navigateTo({ url: `/pages/admin/equipment_edit?eid=${item.id}` })
    },
    askText(title, placeholder, content = "") {
      return new Promise((resolve) => {
        uni.showModal({
          title,
          editable: true,
          placeholderText: placeholder,
          content: String(content || ""),
          success: (res) => {
            if (!res.confirm) {
              resolve(null)
              return
            }
            const text = typeof res.content === "string" ? res.content.trim() : ""
            resolve(text)
          },
          fail: () => resolve(null)
        })
      })
    },
    confirmText(title, content) {
      return new Promise((resolve) => {
        uni.showModal({
          title,
          content,
          success: (res) => resolve(!!res.confirm),
          fail: () => resolve(false)
        })
      })
    },
    async postAdminAction(url, payload, successText) {
      if (this.lifecycleBusy) return false
      this.lifecycleBusy = true
      try {
        const res = await apiRequest({
          url,
          method: "POST",
          header: { "Content-Type": "application/json" },
          data: payload || {}
        })
        const body = (res && res.data) || {}
        if (!body.ok) {
          uni.showToast({ title: body.msg || "操作失败", icon: "none" })
          return false
        }
        if (successText) uni.showToast({ title: successText, icon: "success" })
        await this.refreshPanel()
        return true
      } catch (e) {
        uni.showToast({ title: "操作失败，请重试", icon: "none" })
        return false
      } finally {
        this.lifecycleBusy = false
      }
    },
    async handleBorrow(item) {
      if (item && item.allowBorrow === false) {
        uni.showToast({ title: "该设备已禁止借用", icon: "none" })
        return
      }
      const borrowerName = await this.askText("设备借用", "请输入借用人（姓名/学号）")
      if (borrowerName === null) return
      if (!borrowerName) {
        uni.showToast({ title: "借用人不能为空", icon: "none" })
        return
      }
      const expectedReturnAt = await this.askText("预计归还", "可选：YYYY-MM-DD HH:mm")
      if (expectedReturnAt === null) return
      await this.postAdminAction(`/equipments/${item.id}/borrow`, { borrowerName, expectedReturnAt }, "借用登记成功")
    },
    async handleReturn(item) {
      const ok = await this.confirmText("确认归还", `确认将 ${item.assetCode || "该设备"} 归还入库吗？`)
      if (!ok) return
      await this.postAdminAction(`/equipments/${item.id}/return`, {}, "归还成功")
    },
    async handleTransfer(item) {
      const toLabName = await this.askText("设备调拨", "请输入目标实验室名称")
      if (toLabName === null) return
      if (!toLabName) {
        uni.showToast({ title: "目标实验室不能为空", icon: "none" })
        return
      }
      await this.postAdminAction(`/equipments/${item.id}/transfer`, { toLabName }, "调拨成功")
    },
    async handleScrap(item) {
      const reason = await this.askText("设备报废", "请输入报废原因")
      if (reason === null) return
      if (!reason) {
        uni.showToast({ title: "报废原因不能为空", icon: "none" })
        return
      }
      const ok = await this.confirmText("确认报废", `设备 ${item.assetCode || "-"} 报废后将不可恢复，确认继续？`)
      if (!ok) return
      await this.postAdminAction(`/equipments/${item.id}/scrap`, { reason }, "报废完成")
    },
    async handleMaintenance(item) {
      const nextMaintenanceAt = await this.askText("下次保养时间", "可选：YYYY-MM-DD HH:mm", item.nextMaintenanceAt || "")
      if (nextMaintenanceAt === null) return
      const warrantyUntil = await this.askText("质保到期日期", "可选：YYYY-MM-DD", item.warrantyUntil || "")
      if (warrantyUntil === null) return
      const maintenanceNote = await this.askText("维保备注", "可选")
      if (maintenanceNote === null) return

      if (!nextMaintenanceAt && !warrantyUntil && !maintenanceNote) {
        uni.showToast({ title: "至少填写一项", icon: "none" })
        return
      }
      await this.postAdminAction(
        `/equipments/${item.id}/maintenance-plan`,
        { nextMaintenanceAt, warrantyUntil, maintenanceNote },
        "维保计划已更新"
      )
    },
    async showCode(item) {
      if (!item || !item.id) return
      try {
        const res = await apiRequest({ url: `/equipments/${item.id}/code`, method: "GET" })
        const body = (res && res.data) || {}
        if (!body.ok || !body.data) {
          uni.showToast({ title: body.msg || "获取资产码失败", icon: "none" })
          return
        }
        const row = body.data || {}
        const content = `设备：${row.assetCode || "-"}\n二维码内容：${row.qrText || "-"}\n条码内容：${row.barcodeValue || "-"}`
        uni.showModal({
          title: "资产二维码 / 条码",
          content,
          confirmText: "复制二维码",
          cancelText: "关闭",
          success: (m) => {
            if (!m.confirm) return
            uni.setClipboardData({ data: String(row.qrText || "") })
          }
        })
      } catch (e) {
        uni.showToast({ title: "获取资产码失败", icon: "none" })
      }
    },
    async locateByCode() {
      const code = String(this.locateCode || "").trim()
      if (!code) {
        uni.showToast({ title: "请先输入资产码", icon: "none" })
        return
      }
      try {
        const query = toQuery({ code })
        const res = await apiRequest({ url: `/equipments/scan?${query}`, method: "GET" })
        const body = (res && res.data) || {}
        if (!body.ok || !body.data) {
          uni.showToast({ title: body.msg || "未定位到设备", icon: "none" })
          return
        }
        const row = body.data || {}
        uni.showModal({
          title: "设备定位结果",
          content: `设备：${row.assetCode || "-"} ${row.name || ""}\n实验室：${row.labName || "-"}\n定位备注：${row.locationNote || "-"}`,
          showCancel: false
        })
      } catch (e) {
        uni.showToast({ title: "定位失败", icon: "none" })
      }
    },
    scanLocateByCamera() {
      this.startScan("locate")
    },
    async fetchOpenInventorySession() {
      try {
        const query = toQuery({ status: "open", page: 1, pageSize: 1 })
        const res = await apiRequest({ url: `/equipments/inventory-sessions?${query}`, method: "GET" })
        const body = (res && res.data) || {}
        if (!body.ok) return
        const list = Array.isArray(body.data) ? body.data : []
        this.inventorySession = list.length > 0 ? list[0] : null
      } catch (e) {
        this.inventorySession = null
      }
    },
    async startInventorySession() {
      const labName = await this.askText("新建盘点任务", "可选：输入实验室名称，不填即全量")
      if (labName === null) return
      const note = await this.askText("盘点备注", "可选")
      if (note === null) return
      const payload = {}
      if (labName) payload.labName = labName
      if (note) payload.note = note
      await this.postAdminAction("/equipments/inventory-sessions", payload, "盘点任务已创建")
      await this.fetchOpenInventorySession()
    },
    scanInventoryByCamera() {
      this.startScan("inventory")
    },
    startScan(target) {
      if (this.isWebPlatform()) {
        this.openH5Scanner(target)
        return
      }

      uni.scanCode({
        onlyFromCamera: true,
        scanType: ["qrCode", "barCode"],
        success: (res) => {
          const code = this.extractScanText(res)
          if (!code) {
            uni.showToast({ title: "未识别到有效码内容", icon: "none" })
            return
          }
          this.applyScannedCode(target, code)
        },
        fail: (err) => {
          const message = this.describeScanError(err)
          if (message) uni.showToast({ title: message, icon: "none" })
        }
      })
    },
    extractScanText(res) {
      return String((res && (res.result || res.code || res.rawData || res.path)) || "").trim()
    },
    applyScannedCode(target, code) {
      const text = String(code || "").trim()
      if (!text) {
        uni.showToast({ title: "未识别到有效码内容", icon: "none" })
        return
      }
      if (target === "inventory") {
        this.inventoryCode = text
        this.submitInventoryScan()
        return
      }
      this.locateCode = text
      this.locateByCode()
    },
    describeScanError(err) {
      const raw = String((err && (err.errMsg || err.message || err.code)) || "").toLowerCase()
      if (!raw) return "扫码失败，请重试"
      if (raw.includes("cancel")) return "已取消扫码"
      if (raw.includes("auth deny") || raw.includes("permission") || raw.includes("denied")) {
        return "未获得相机权限，请在系统设置中开启"
      }
      if (raw.includes("unsupported") || raw.includes("not support")) {
        return "当前环境不支持扫码，请改用真机或手动输入"
      }
      if (raw.includes("notfound") || raw.includes("device not found")) return "未检测到可用摄像头"
      if (raw.includes("notreadable") || raw.includes("trackstart") || raw.includes("occupied")) {
        return "相机可能正被占用，请关闭后重试"
      }
      return "扫码失败，请重试"
    },
    isWebPlatform() {
      try {
        const info = uni.getSystemInfoSync ? uni.getSystemInfoSync() : {}
        const uniPlatform = String(info.uniPlatform || "").toLowerCase()
        const platform = String(info.platform || "").toLowerCase()
        return uniPlatform === "web" || uniPlatform === "h5" || platform === "web"
      } catch (e) {
        return false
      }
    },
    scanModeTitle(target) {
      return target === "inventory" ? "盘点扫码" : "设备定位扫码"
    },
    async openH5Scanner(target) {
      if (typeof window === "undefined" || typeof navigator === "undefined") {
        uni.showToast({ title: "当前环境不支持浏览器扫码", icon: "none" })
        return
      }
      if (!window.isSecureContext) {
        uni.showToast({ title: "浏览器扫码需在 HTTPS 或 localhost 下使用", icon: "none" })
        return
      }
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        uni.showToast({ title: "当前浏览器不支持调用摄像头", icon: "none" })
        return
      }
      if (typeof window.BarcodeDetector === "undefined") {
        uni.showToast({ title: "当前浏览器不支持识别条码，请改用真机或手动输入", icon: "none" })
        return
      }

      this.h5ScannerTarget = target
      this.h5ScannerTitle = this.scanModeTitle(target)
      this.h5ScannerHint = "请将资产二维码或条码置于取景框中央"
      this.h5ScannerError = ""
      this.h5ScannerVisible = true

      this.$nextTick(() => {
        this.startH5Scanner()
      })
    },
    getH5ScannerVideo() {
      const ref = this.$refs.h5ScannerVideo
      if (Array.isArray(ref)) return ref[0] || null
      return ref || null
    },
    async startH5Scanner() {
      if (!this.h5ScannerVisible || typeof navigator === "undefined" || typeof window === "undefined") return

      this.releaseH5Scanner()
      const video = this.getH5ScannerVideo()
      if (!video) {
        this.h5ScannerError = "扫码预览初始化失败，请刷新页面后重试"
        return
      }

      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: false,
          video: {
            facingMode: { ideal: "environment" },
            width: { ideal: 1280 },
            height: { ideal: 720 }
          }
        })
        this._h5ScannerStream = stream
        video.srcObject = stream
        if (typeof video.play === "function") {
          await video.play()
        }
        const desiredFormats = ["qr_code", "code_128", "code_39", "ean_13", "ean_8", "upc_a", "upc_e", "codabar"]
        let formats = desiredFormats
        if (typeof window.BarcodeDetector.getSupportedFormats === "function") {
          const supportedFormats = await window.BarcodeDetector.getSupportedFormats()
          const supportSet = new Set(Array.isArray(supportedFormats) ? supportedFormats : [])
          const filteredFormats = desiredFormats.filter((item) => supportSet.has(item))
          if (filteredFormats.length > 0) formats = filteredFormats
        }
        this._h5BarcodeDetector = new window.BarcodeDetector({ formats })
        this.scheduleH5Detect()
      } catch (e) {
        this.releaseH5Scanner()
        this.h5ScannerError = this.describeH5CameraError(e)
      }
    },
    scheduleH5Detect() {
      this.clearH5DetectTimer()
      this._h5DetectTimer = setInterval(async () => {
        if (!this.h5ScannerVisible || this._h5Detecting || !this._h5BarcodeDetector) return
        const video = this.getH5ScannerVideo()
        if (!video || Number(video.readyState || 0) < 2) return

        this._h5Detecting = true
        try {
          const results = await this._h5BarcodeDetector.detect(video)
          const hit = Array.isArray(results) ? results.find((item) => item && item.rawValue) : null
          if (!hit || !hit.rawValue) return

          const text = String(hit.rawValue || "").trim()
          const target = this.h5ScannerTarget
          this.closeH5Scanner()
          this.applyScannedCode(target, text)
        } catch (e) {
          this.h5ScannerError = "识别中断，请点击“重新识别”后重试"
          this.releaseH5Scanner()
        } finally {
          this._h5Detecting = false
        }
      }, 450)
    },
    clearH5DetectTimer() {
      if (this._h5DetectTimer) {
        clearInterval(this._h5DetectTimer)
        this._h5DetectTimer = null
      }
    },
    releaseH5Scanner() {
      this.clearH5DetectTimer()
      this._h5Detecting = false
      this._h5BarcodeDetector = null

      const video = this.getH5ScannerVideo()
      if (video) {
        if (typeof video.pause === "function") video.pause()
        try {
          video.srcObject = null
        } catch (e) {}
      }

      const stream = this._h5ScannerStream
      if (stream && typeof stream.getTracks === "function") {
        stream.getTracks().forEach((track) => {
          if (track && typeof track.stop === "function") track.stop()
        })
      }
      this._h5ScannerStream = null
    },
    closeH5Scanner() {
      this.releaseH5Scanner()
      this.h5ScannerVisible = false
      this.h5ScannerTitle = ""
      this.h5ScannerHint = ""
      this.h5ScannerTarget = ""
      this.h5ScannerError = ""
    },
    restartH5Scanner() {
      if (!this.h5ScannerVisible) return
      this.h5ScannerError = ""
      this.$nextTick(() => {
        this.startH5Scanner()
      })
    },
    describeH5CameraError(err) {
      const raw = String((err && (err.name || err.message || err.code)) || "").toLowerCase()
      if (!raw) return "摄像头启动失败，请改用手动输入"
      if (raw.includes("notallowed") || raw.includes("permission") || raw.includes("denied")) {
        return "未获得相机权限，请允许浏览器访问摄像头"
      }
      if (raw.includes("notfound") || raw.includes("devicesnotfound")) return "未检测到可用摄像头"
      if (raw.includes("notreadable") || raw.includes("trackstart")) return "相机正被其他程序占用"
      if (raw.includes("overconstrained")) return "当前摄像头无法切换到后置模式，请重试"
      return "摄像头启动失败，请改用手动输入"
    },
    async submitInventoryScan() {
      if (!this.inventorySession || !this.inventorySession.id) {
        uni.showToast({ title: "请先创建盘点任务", icon: "none" })
        return
      }
      const code = String(this.inventoryCode || "").trim()
      if (!code) {
        uni.showToast({ title: "请输入或扫码资产码", icon: "none" })
        return
      }
      if (this.lifecycleBusy) return
      this.lifecycleBusy = true
      try {
        const res = await apiRequest({
          url: `/equipments/inventory-sessions/${this.inventorySession.id}/scan`,
          method: "POST",
          header: { "Content-Type": "application/json" },
          data: { code, note: this.inventoryNote }
        })
        const body = (res && res.data) || {}
        if (!body.ok) {
          uni.showToast({ title: body.msg || "盘点登记失败", icon: "none" })
          return
        }
        const row = body.data || {}
        const text = row.duplicate ? "该设备已登记过" : `登记成功：${row.scanStatus || "matched"}`
        uni.showToast({ title: text, icon: "none" })
        this.inventoryCode = ""
        this.inventoryNote = ""
        await this.fetchOpenInventorySession()
        await this.fetchList(true)
      } catch (e) {
        uni.showToast({ title: "盘点登记失败", icon: "none" })
      } finally {
        this.lifecycleBusy = false
      }
    },
    async closeInventorySession() {
      if (!this.inventorySession || !this.inventorySession.id) return
      const ok = await this.confirmText("结束盘点", "结束后将自动标记未扫码资产为缺失，确认继续？")
      if (!ok) return
      await this.postAdminAction(`/equipments/inventory-sessions/${this.inventorySession.id}/close`, {}, "盘点已结束")
      await this.fetchOpenInventorySession()
    },
    async showInventoryDiffs() {
      if (!this.inventorySession || !this.inventorySession.id) {
        uni.showToast({ title: "当前无盘点任务", icon: "none" })
        return
      }
      try {
        const res = await apiRequest({
          url: `/equipments/inventory-sessions/${this.inventorySession.id}/diffs`,
          method: "GET"
        })
        const body = (res && res.data) || {}
        if (!body.ok) {
          uni.showToast({ title: body.msg || "获取差异失败", icon: "none" })
          return
        }
        const list = Array.isArray(body.data) ? body.data : []
        if (list.length === 0) {
          uni.showToast({ title: "暂无差异记录", icon: "none" })
          return
        }
        const lines = list.slice(0, 12).map((row, idx) => {
          const code = row.assetCode || "-"
          const diff = row.discrepancyType || row.scanStatus || "-"
          const exp = row.expectedLabName || "-"
          const scan = row.scannedLabName || "-"
          return `${idx + 1}. ${code}｜${diff}｜期望:${exp} 实际:${scan}`
        })
        uni.showModal({
          title: `盘点差异（共 ${list.length} 条）`,
          content: lines.join("\n"),
          showCancel: false
        })
      } catch (e) {
        uni.showToast({ title: "获取差异失败", icon: "none" })
      }
    },
    async fetchDueList() {
      try {
        const query = toQuery({ days: 30, limit: 8 })
        const res = await apiRequest({ url: `/equipments/maintenance/due?${query}`, method: "GET" })
        const body = (res && res.data) || {}
        if (!body.ok) {
          this.dueRows = []
          return
        }
        this.dueRows = Array.isArray(body.data) ? body.data : []
      } catch (e) {
        this.dueRows = []
      }
    }
  }
}
</script>

<style lang="scss">
.equipmentsPage {
  padding-bottom: 24px;
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

.miniBtn {
  min-height: 30px;
  line-height: 30px;
  padding: 0 10px;
  border-radius: 9px;
  font-size: 12px;
}

.filterCard,
.inventoryCard,
.locateCard,
.dueCard,
.itemCard,
.pageCard {
  border: 1px solid rgba(148, 163, 184, 0.24);
}

.chipRow {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.statusChip {
  transition: all 0.14s ease;
}

.chipOn {
  border-color: #bfdbfe;
  background: #eaf3ff;
  color: #1d4ed8;
}

.actions {
  margin-top: 10px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.rowActions {
  display: flex;
  gap: 8px;
}

.rowGrid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 10px;
}

.inventoryBody {
  margin-top: 8px;
}

.dueList {
  margin-top: 8px;
}

.dueItem {
  padding: 8px;
  border-radius: 10px;
  border: 1px solid rgba(148, 163, 184, 0.18);
}

.itemName {
  font-size: 15px;
  line-height: 21px;
  font-weight: 700;
  color: #0f172a;
}

.meta {
  margin-top: 6px;
  font-size: 12px;
  color: #64748b;
}

.itemActions {
  margin-top: 12px;
}

.scannerMask {
  position: fixed;
  inset: 0;
  z-index: 60;
  padding: 24px 16px;
  background: rgba(15, 23, 42, 0.58);
  display: flex;
  align-items: center;
  justify-content: center;
}

.scannerDialog {
  width: 100%;
  max-width: 420px;
  border: 1px solid rgba(148, 163, 184, 0.28);
  background: #ffffff;
}

.scannerPreview {
  position: relative;
  margin-top: 10px;
  width: 100%;
  aspect-ratio: 1;
  overflow: hidden;
  border-radius: 14px;
  background: #0f172a;
}

.scannerVideo {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.scannerGuide {
  position: absolute;
  left: 50%;
  top: 50%;
  width: 62%;
  height: 62%;
  transform: translate(-50%, -50%);
  border: 2px solid rgba(255, 255, 255, 0.92);
  border-radius: 16px;
  box-shadow: 0 0 0 999px rgba(15, 23, 42, 0.18);
}

.scannerError {
  margin-top: 10px;
  font-size: 12px;
  line-height: 18px;
  color: #b91c1c;
}

@media screen and (max-width: 420px) {
  .heroActions {
    flex-direction: column;
    align-items: flex-end;
  }

  .scannerMask {
    padding: 16px 12px;
  }
}
</style>

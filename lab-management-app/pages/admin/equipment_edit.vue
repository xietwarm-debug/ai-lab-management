<template>
  <view class="container equipmentEditPage">
    <view class="stack">
      <view class="card heroCard">
        <view class="rowBetween heroTop">
          <view>
            <view class="title">{{ isCreate ? "新增设备" : "编辑设备" }}</view>
            <view class="subtitle">维护设备基础台账信息</view>
          </view>
          <button class="btnSecondary miniBtn" size="mini" @click="goBack">返回</button>
        </view>
      </view>

      <view class="card loadingCard" v-if="loading">
        <view class="muted">加载中...</view>
      </view>

      <view class="card formCard" v-else>
        <view class="label">资产编号 *</view>
        <input class="inputBase" v-model.trim="form.assetCode" maxlength="64" placeholder="例如：EQ-0001" />
        <view class="fieldError" v-if="errors.assetCode">{{ errors.assetCode }}</view>

        <view class="label">设备名称 *</view>
        <input class="inputBase" v-model.trim="form.name" maxlength="128" placeholder="例如：示波器" />
        <view class="fieldError" v-if="errors.name">{{ errors.name }}</view>

        <view class="rowGrid">
          <view>
            <view class="label">型号</view>
            <input class="inputBase" v-model.trim="form.model" maxlength="128" placeholder="例如：TBS1102" />
          </view>
          <view>
            <view class="label">品牌</view>
            <input class="inputBase" v-model.trim="form.brand" maxlength="128" placeholder="例如：Tek" />
          </view>
        </view>

        <view class="label">实验室名称</view>
        <input class="inputBase" v-model.trim="form.labName" maxlength="128" placeholder="例如：C406" />

        <view class="label">状态</view>
        <view class="chipRow">
          <view
            class="chip statusChip"
            v-for="opt in statusOptions"
            :key="opt.value"
            :class="{ chipOn: form.status === opt.value }"
            @click="form.status = opt.value"
          >
            {{ opt.label }}
          </view>
        </view>
        <view class="fieldError" v-if="errors.status">{{ errors.status }}</view>

        <view class="label">是否允许借用</view>
        <view class="chipRow">
          <view class="chip statusChip" :class="{ chipOn: form.allowBorrow === true }" @click="setAllowBorrow(true)">
            允许
          </view>
          <view class="chip statusChip" :class="{ chipOn: form.allowBorrow === false }" @click="setAllowBorrow(false)">
            不允许
          </view>
        </view>

        <view class="rowGrid">
          <view>
            <view class="label">保管人</view>
            <input class="inputBase" v-model.trim="form.keeper" maxlength="128" placeholder="例如：张三" />
          </view>
          <view>
            <view class="label">采购日期</view>
            <picker mode="date" :value="form.purchaseDate" @change="onDateChange">
              <view class="pickerLike">{{ form.purchaseDate || "请选择日期" }}</view>
            </picker>
          </view>
        </view>
        <view class="fieldError" v-if="errors.purchaseDate">{{ errors.purchaseDate }}</view>

        <view class="label">价格</view>
        <input class="inputBase" v-model.trim="form.price" type="digit" placeholder="例如：5999.00" />
        <view class="fieldError" v-if="errors.price">{{ errors.price }}</view>

        <view class="label">规格 JSON</view>
        <textarea
          class="textareaBase"
          v-model.trim="form.specJson"
          maxlength="5000"
          placeholder='例如：{"channel":2}'
        />
      </view>

      <view class="card summaryCard" v-if="!loading">
        <view class="cardTitle">提交前确认</view>
        <view class="summaryLine">资产编号：{{ form.assetCode || "-" }}</view>
        <view class="summaryLine">设备名称：{{ form.name || "-" }}</view>
        <view class="summaryLine">状态：{{ statusText(form.status) }}</view>
        <view class="summaryLine">借用权限：{{ form.allowBorrow ? "允许借用" : "禁止借用" }}</view>
        <button class="btnPrimary submitBtn" :disabled="saving" @click="submit">
          {{ saving ? "提交中..." : (isCreate ? "创建设备" : "保存修改") }}
        </button>
      </view>
    </view>
  </view>
</template>

<script>
import { apiRequest } from "@/common/api.js"

export default {
  data() {
    return {
      eid: null,
      isCreate: true,
      loading: false,
      saving: false,
      form: {
        assetCode: "",
        name: "",
        model: "",
        brand: "",
        labId: "",
        labName: "",
        status: "in_service",
        allowBorrow: true,
        keeper: "",
        purchaseDate: "",
        price: "",
        specJson: "",
        imageUrl: ""
      },
      allowBorrowTouched: false,
      errors: {
        assetCode: "",
        name: "",
        status: "",
        purchaseDate: "",
        price: ""
      }
    }
  },
  computed: {
    statusOptions() {
      return [
        { label: "在用", value: "in_service" },
        { label: "维修中", value: "repairing" },
        { label: "已报废", value: "scrapped" }
      ]
    }
  },
  onLoad(options) {
    this.eid = options && options.eid ? Number(options.eid) : null
    this.isCreate = !this.eid
    if (!this.ensureAdmin()) return
    if (!this.isCreate) this.fetchDetail()
  },
  onShow() {
    this.ensureAdmin()
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
    setAllowBorrow(value) {
      this.form.allowBorrow = value === true
      this.allowBorrowTouched = true
    },
    isLikelyLabPc(payload) {
      const data = payload || {}
      const assetCode = String(data.assetCode || "").trim().toUpperCase()
      const name = String(data.name || "").trim()
      const labName = String(data.labName || "").trim()
      const labId = data.labId
      const labIdNum = Number(labId)
      const hasLabId = labId !== null && labId !== undefined && String(labId).trim() !== "" && Number.isFinite(labIdNum) && labIdNum > 0
      const hasLab = !!labName || hasLabId
      if (!hasLab) return false
      if (assetCode.startsWith("PC-")) return true
      if (name.includes("电脑")) return true
      if (/\bpc\b/i.test(name)) return true
      const specText = String(data.specJson || "")
      return /"category"\s*:\s*"(pc|computer)"/i.test(specText)
    },
    goBack() {
      uni.navigateBack()
    },
    onDateChange(e) {
      this.form.purchaseDate = (e && e.detail && e.detail.value) || ""
      this.errors.purchaseDate = ""
    },
    clearErrors() {
      this.errors = {
        assetCode: "",
        name: "",
        status: "",
        purchaseDate: "",
        price: ""
      }
    },
    validate() {
      this.clearErrors()
      let ok = true
      const assetCode = String(this.form.assetCode || "").trim()
      const name = String(this.form.name || "").trim()
      const status = String(this.form.status || "").trim()
      const purchaseDate = String(this.form.purchaseDate || "").trim()
      const price = String(this.form.price || "").trim()

      if (!assetCode) {
        this.errors.assetCode = "请输入资产编号"
        ok = false
      }
      if (!name) {
        this.errors.name = "请输入设备名称"
        ok = false
      }
      if (!["in_service", "repairing", "scrapped"].includes(status)) {
        this.errors.status = "设备状态不合法"
        ok = false
      }
      if (purchaseDate && !/^\d{4}-\d{2}-\d{2}$/.test(purchaseDate)) {
        this.errors.purchaseDate = "采购日期格式必须为 YYYY-MM-DD"
        ok = false
      }
      if (price) {
        const n = Number(price)
        if (!Number.isFinite(n)) {
          this.errors.price = "价格格式不正确"
          ok = false
        }
      }
      return ok
    },
    async fetchDetail() {
      if (!this.eid) return
      this.loading = true
      try {
        const res = await apiRequest({
          url: `/equipments/${this.eid}`,
          method: "GET"
        })
        const payload = (res && res.data) || {}
        if (!payload.ok || !payload.data) {
          uni.showToast({ title: payload.msg || "加载失败", icon: "none" })
          return
        }
        const row = payload.data || {}
        this.form.assetCode = row.assetCode || ""
        this.form.name = row.name || ""
        this.form.model = row.model || ""
        this.form.brand = row.brand || ""
        this.form.labId = row.labId != null ? String(row.labId) : ""
        this.form.labName = row.labName || ""
        this.form.status = row.status || "in_service"
        this.form.allowBorrow = row.allowBorrow !== false
        this.form.keeper = row.keeper || ""
        this.form.purchaseDate = row.purchaseDate || ""
        this.form.price = row.price != null && row.price !== "" ? String(row.price) : ""
        this.form.specJson = row.specJson || ""
        this.form.imageUrl = row.imageUrl || ""
        this.allowBorrowTouched = false
      } catch (e) {
        uni.showToast({ title: "加载失败", icon: "none" })
      } finally {
        this.loading = false
      }
    },
    buildPayload() {
      const labIdInt = this.form.labId === "" ? null : Number(this.form.labId)
      const payload = {
        assetCode: String(this.form.assetCode || "").trim(),
        name: String(this.form.name || "").trim(),
        model: String(this.form.model || "").trim(),
        brand: String(this.form.brand || "").trim(),
        labId: Number.isFinite(labIdInt) ? labIdInt : null,
        labName: String(this.form.labName || "").trim(),
        status: String(this.form.status || "").trim(),
        keeper: String(this.form.keeper || "").trim(),
        purchaseDate: String(this.form.purchaseDate || "").trim(),
        price: String(this.form.price || "").trim(),
        specJson: String(this.form.specJson || "").trim(),
        imageUrl: String(this.form.imageUrl || "").trim(),
        allowBorrow: this.form.allowBorrow === true
      }
      if (this.isCreate && !this.allowBorrowTouched) {
        payload.allowBorrow = !this.isLikelyLabPc(payload)
      }
      return payload
    },
    async submit() {
      if (!this.ensureAdmin()) return
      if (this.saving) return
      if (!this.validate()) return

      const payload = this.buildPayload()
      this.saving = true
      try {
        const res = await apiRequest({
          url: this.isCreate ? "/equipments" : `/equipments/${this.eid}`,
          method: "POST",
          header: { "Content-Type": "application/json" },
          data: payload
        })
        const body = (res && res.data) || {}
        if (!body.ok) {
          uni.showToast({ title: body.msg || "保存失败", icon: "none" })
          return
        }
        uni.showToast({ title: this.isCreate ? "创建成功" : "保存成功", icon: "success" })
        setTimeout(() => {
          uni.navigateBack()
        }, 250)
      } catch (e) {
        uni.showToast({ title: "保存失败，请重试", icon: "none" })
      } finally {
        this.saving = false
      }
    }
  }
}
</script>

<style lang="scss">
.equipmentEditPage {
  padding-bottom: 24px;
}

.heroCard {
  border: 1px solid rgba(22, 119, 255, 0.18);
  background: linear-gradient(160deg, #ffffff 0%, #f2f7ff 100%);
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

.loadingCard {
  min-height: 72px;
  display: flex;
  align-items: center;
}

.formCard {
  border: 1px solid rgba(148, 163, 184, 0.24);
}

.rowGrid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
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

.summaryCard {
  border: 1px solid rgba(148, 163, 184, 0.24);
}

.summaryLine {
  margin-top: 8px;
  font-size: 12px;
  color: #475569;
}

.submitBtn {
  margin-top: 12px;
  width: 100%;
}

@media screen and (max-width: 420px) {
  .rowGrid {
    grid-template-columns: 1fr;
  }
}
</style>

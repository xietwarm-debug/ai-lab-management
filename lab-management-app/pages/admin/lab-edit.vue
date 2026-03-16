<template>
  <view class="container labEditPage">
    <view class="stack">
      <view class="card heroCard">
        <view class="rowBetween heroTop">
          <view>
            <view class="title">{{ isCreate ? "新增实验室" : "编辑实验室" }}</view>
            <view class="subtitle">
              {{ isCreate ? "创建新的实验室资源并设置基础信息" : "更新实验室状态、容量和展示信息" }}
            </view>
          </view>
          <view class="heroActions">
            <button class="btnSecondary miniBtn" size="mini" @click="goBack">返回</button>
          </view>
        </view>
      </view>

      <view class="card loadingCard" v-if="loading">
        <view class="muted">正在加载实验室信息...</view>
      </view>

      <view class="card formCard" v-else>
        <view class="label">实验室名称 *</view>
        <input
          class="inputBase"
          v-model.trim="form.name"
          maxlength="60"
          placeholder="例如：A101 计算机实验室"
        />
        <view class="fieldError" v-if="errors.name">{{ errors.name }}</view>

        <view class="label">实验室状态 *</view>
        <view class="statusRow">
          <view
            class="chip statusChip"
            :class="{ chipOn: form.status === 'free' }"
            @click="setStatus('free')"
          >
            空闲（可预约）
          </view>
          <view
            class="chip statusChip"
            :class="{ chipOn: form.status === 'busy' }"
            @click="setStatus('busy')"
          >
            使用中
          </view>
        </view>
        <view class="fieldError" v-if="errors.status">{{ errors.status }}</view>

        <view class="rowGrid">
          <view>
            <view class="label">容量</view>
            <input
              class="inputBase"
              v-model.trim="form.capacity"
              type="number"
              placeholder="例如：40"
            />
            <view class="fieldError" v-if="errors.capacity">{{ errors.capacity }}</view>
          </view>

          <view>
            <view class="label">设备数量</view>
            <input
              class="inputBase"
              v-model.trim="form.deviceCount"
              type="number"
              placeholder="例如：32"
            />
            <view class="fieldError" v-if="errors.deviceCount">{{ errors.deviceCount }}</view>
          </view>
        </view>

        <view class="label">实验室说明</view>
        <textarea
          class="textareaBase"
          v-model.trim="form.description"
          maxlength="255"
          placeholder="例如：配备高性能计算机，支持软件工程课程实验"
        />
        <view class="fieldError" v-if="errors.description">{{ errors.description }}</view>

        <view class="label">封面图片</view>
        <view class="uploadRow">
          <button class="btnSecondary miniBtn" size="mini" :disabled="uploading" @click="chooseImage">
            {{ uploading ? "上传中..." : "上传图片" }}
          </button>
          <button
            v-if="form.imageUrl"
            class="btnGhost miniBtn"
            size="mini"
            :disabled="uploading"
            @click="removeImage"
          >
            移除图片
          </button>
        </view>
        <input
          class="inputBase"
          v-model.trim="form.imageUrl"
          placeholder="可粘贴图片 URL，或使用上传按钮"
        />
        <view class="fieldError" v-if="errors.imageUrl">{{ errors.imageUrl }}</view>

        <image
          v-if="form.imageUrl"
          class="preview"
          :src="imgSrc(form.imageUrl)"
          mode="aspectFill"
        />
      </view>

      <view class="card summaryCard" v-if="!loading">
        <view class="cardTitle">提交前确认</view>
        <view class="summaryLine">名称：{{ form.name || "-" }}</view>
        <view class="summaryLine">状态：{{ statusText(form.status) }}</view>
        <view class="summaryLine">容量：{{ normalizedInt(form.capacity) }}</view>
        <view class="summaryLine">设备数：{{ normalizedInt(form.deviceCount) }}</view>
        <view class="summaryLine lineClamp">说明：{{ form.description || "-" }}</view>

        <button class="btnPrimary submitBtn" :disabled="saving || uploading" @click="save">
          {{ saving ? "提交中..." : isCreate ? "创建实验室" : "保存修改" }}
        </button>
      </view>
    </view>
  </view>
</template>

<script>
import { BASE_URL, getApiListData } from "@/common/api.js"

export default {
  data() {
    return {
      id: null,
      isCreate: true,
      loading: false,
      saving: false,
      uploading: false,
      form: {
        name: "",
        status: "free",
        capacity: "",
        deviceCount: "",
        description: "",
        imageUrl: ""
      },
      errors: {
        name: "",
        status: "",
        capacity: "",
        deviceCount: "",
        description: "",
        imageUrl: ""
      }
    }
  },
  onLoad(options) {
    this.id = options && options.id ? Number(options.id) : null
    this.isCreate = !this.id
    if (!this.isCreate) this.fetch()
  },
  onShow() {
    const s = uni.getStorageSync("session")
    if (!s || s.role !== "admin") {
      uni.showToast({ title: "无权限", icon: "none" })
      uni.reLaunch({ url: "/pages/login/login" })
    }
  },
  methods: {
    goBack() {
      uni.navigateBack()
    },
    statusText(status) {
      return status === "free" ? "空闲" : "使用中"
    },
    setStatus(status) {
      this.form.status = status
      this.errors.status = ""
    },
    normalizedInt(raw) {
      const text = String(raw || "").trim()
      if (!text) return 0
      const n = Number(text)
      if (!Number.isFinite(n) || n < 0) return 0
      return Math.floor(n)
    },
    imgSrc(url) {
      if (!url) return ""
      if (String(url).startsWith("http")) return url
      return `${BASE_URL}${url}`
    },
    clearErrors() {
      this.errors = {
        name: "",
        status: "",
        capacity: "",
        deviceCount: "",
        description: "",
        imageUrl: ""
      }
    },
    fetch() {
      if (!this.id) return
      this.loading = true
      uni.request({
        url: `${BASE_URL}/labs`,
        method: "GET",
        success: (res) => {
          const row = getApiListData(res.data).find((x) => String(x.id) === String(this.id))
          if (!row) {
            uni.showToast({ title: "实验室不存在", icon: "none" })
            setTimeout(() => this.goBack(), 250)
            return
          }
          this.form.name = row.name || ""
          this.form.status = row.status || "free"
          this.form.capacity = row.capacity != null ? String(row.capacity) : ""
          this.form.deviceCount = row.deviceCount != null ? String(row.deviceCount) : ""
          this.form.description = row.description || ""
          this.form.imageUrl = row.imageUrl || ""
        },
        fail: () => {
          uni.showToast({ title: "加载失败", icon: "none" })
        },
        complete: () => {
          this.loading = false
        }
      })
    },
    validate() {
      this.clearErrors()
      const name = (this.form.name || "").trim()
      const status = (this.form.status || "").trim()
      const capacity = (this.form.capacity || "").trim()
      const deviceCount = (this.form.deviceCount || "").trim()
      const description = (this.form.description || "").trim()
      const imageUrl = (this.form.imageUrl || "").trim()
      let hasError = false

      if (!name) {
        this.errors.name = "请输入实验室名称"
        hasError = true
      } else if (name.length > 60) {
        this.errors.name = "名称长度不能超过 60 个字符"
        hasError = true
      }

      if (status !== "free" && status !== "busy") {
        this.errors.status = "请选择有效状态"
        hasError = true
      }

      if (capacity && !/^\d+$/.test(capacity)) {
        this.errors.capacity = "容量必须是非负整数"
        hasError = true
      }

      if (deviceCount && !/^\d+$/.test(deviceCount)) {
        this.errors.deviceCount = "设备数量必须是非负整数"
        hasError = true
      }

      if (description.length > 255) {
        this.errors.description = "说明不能超过 255 个字符"
        hasError = true
      }

      if (imageUrl && !/^(https?:\/\/|\/uploads\/)/.test(imageUrl)) {
        this.errors.imageUrl = "图片地址需为 http(s) 链接或 /uploads/ 路径"
        hasError = true
      }

      return !hasError
    },
    buildPayload() {
      return {
        name: (this.form.name || "").trim(),
        status: (this.form.status || "").trim(),
        capacity: this.normalizedInt(this.form.capacity),
        deviceCount: this.normalizedInt(this.form.deviceCount),
        description: (this.form.description || "").trim(),
        imageUrl: (this.form.imageUrl || "").trim()
      }
    },
    save() {
      if (this.saving || this.uploading) return
      if (!this.validate()) return
      const payload = this.buildPayload()

      uni.showModal({
        title: this.isCreate ? "确认创建" : "确认保存",
        content: `名称：${payload.name}\n状态：${this.statusText(payload.status)}\n容量：${payload.capacity}`,
        success: (m) => {
          if (!m.confirm) return
          this.submit(payload)
        }
      })
    },
    submit(payload) {
      this.saving = true
      uni.request({
        url: this.isCreate ? `${BASE_URL}/labs` : `${BASE_URL}/labs/${this.id}`,
        method: "POST",
        header: { "Content-Type": "application/json" },
        data: payload,
        success: (res) => {
          if (!res.data || !res.data.ok) {
            uni.showToast({ title: (res.data && res.data.msg) || "保存失败", icon: "none" })
            return
          }
          const resultId = (res.data && res.data.data && res.data.data.id) || this.id || "-"
          uni.showModal({
            title: this.isCreate ? "创建成功" : "保存成功",
            content: `实验室编号：${resultId}`,
            showCancel: false,
            success: () => {
              uni.navigateBack()
            }
          })
        },
        fail: () => {
          uni.showToast({ title: "保存失败", icon: "none" })
        },
        complete: () => {
          this.saving = false
        }
      })
    },
    removeImage() {
      this.form.imageUrl = ""
      this.errors.imageUrl = ""
    },
    chooseImage() {
      if (this.uploading) return
      uni.chooseImage({
        count: 1,
        success: (res) => {
          const filePath = res.tempFilePaths && res.tempFilePaths[0]
          if (!filePath) return

          this.uploading = true
          uni.uploadFile({
            url: `${BASE_URL}/upload`,
            filePath,
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

              this.form.imageUrl = payload.data.url
              this.errors.imageUrl = ""
              uni.showToast({ title: "上传成功", icon: "success" })
            },
            fail: () => {
              uni.showToast({ title: "上传失败", icon: "none" })
            },
            complete: () => {
              this.uploading = false
            }
          })
        }
      })
    }
  }
}
</script>

<style lang="scss">
.labEditPage {
  padding-bottom: 20px;
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

.loadingCard {
  min-height: 72px;
  display: flex;
  align-items: center;
}

.formCard {
  border: 1px solid rgba(148, 163, 184, 0.24);
}

.statusRow {
  margin-top: 6px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.statusChip {
  transition: all 0.14s ease;
}

.chipOn {
  border-color: #bfdbfe;
  background: #eaf3ff;
  color: #1d4ed8;
}

.rowGrid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.uploadRow {
  margin-top: 6px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.preview {
  margin-top: 10px;
  width: 100%;
  height: 170px;
  border-radius: 12px;
}

.summaryCard {
  border: 1px solid rgba(148, 163, 184, 0.24);
}

.summaryLine {
  margin-top: 8px;
  font-size: 12px;
  color: #475569;
}

.lineClamp {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.submitBtn {
  width: 100%;
  margin-top: 12px;
}

@media screen and (max-width: 420px) {
  .rowGrid {
    grid-template-columns: 1fr;
  }
}
</style>

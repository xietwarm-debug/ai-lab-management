<template>
  <view class="container postPage">
    <view class="stack">
      <view class="card heroCard">
        <view class="rowBetween heroTop">
          <view>
            <view class="title">{{ form.type === 'found' ? '发布拾到物品' : '发布失物信息' }}</view>
            <view class="subtitle">填写关键信息，帮助物品尽快找回</view>
          </view>
          <button class="btnSecondary miniBtn" size="mini" @click="clearForm">重置</button>
        </view>
      </view>

      <view class="card formCard">
        <view class="label">类型</view>
        <view class="typeRow">
          <view class="chip typeChip" :class="{ chipOn: form.type === 'lost' }" @click="setType('lost')">失物</view>
          <view class="chip typeChip" :class="{ chipOn: form.type === 'found' }" @click="setType('found')">拾到物品</view>
        </view>

        <view class="label">标题</view>
        <input
          class="inputBase"
          v-model="form.title"
          placeholder="例如：黑色雨伞"
          maxlength="60"
        />
        <view class="muted">{{ (form.title || '').length }} / 60</view>
        <view class="fieldError" v-if="errors.title">{{ errors.title }}</view>

        <view class="label">地点</view>
        <input
          class="inputBase"
          v-model="form.location"
          placeholder="例如：C301 门口"
          maxlength="120"
        />
        <view class="fieldError" v-if="errors.location">{{ errors.location }}</view>

        <view class="label">联系方式</view>
        <input
          class="inputBase"
          v-model="form.contact"
          placeholder="电话 / 微信"
          maxlength="80"
        />
        <view class="fieldError" v-if="errors.contact">{{ errors.contact }}</view>

        <view class="label">描述</view>
        <textarea
          class="textareaBase"
          v-model="form.description"
          placeholder="补充细节，例如颜色、品牌、明显特征"
          maxlength="500"
        />
        <view class="muted">{{ (form.description || '').length }} / 500</view>
        <view class="fieldError" v-if="errors.description">{{ errors.description }}</view>

        <view class="label">图片</view>
        <view class="rowBetween uploadRow">
          <button class="btnGhost miniBtn" size="mini" @click="chooseImage">选择图片</button>
          <button class="btnSecondary miniBtn" size="mini" :loading="matching" @click="findSimilarItems">AI查找相似</button>
          <button v-if="form.imageUrl" class="btnSecondary miniBtn" size="mini" @click="removeImage">移除</button>
          <view class="muted" v-else>未上传</view>
        </view>
        <image v-if="form.imageUrl" :src="imgSrc(form.imageUrl)" class="preview" mode="aspectFill" />
      </view>

      <view class="card summaryCard" v-if="matchSummary || matchCandidates.length > 0">
        <view class="cardTitle">AI 相似匹配</view>
        <view class="summaryLine">{{ matchSummary || "已生成候选结果" }}</view>
        <view class="matchCard" v-for="item in matchCandidates" :key="'match-' + item.id">
          <view class="rowBetween">
            <view class="matchTitle">{{ item.title || "-" }}</view>
            <view class="matchScore">相似度 {{ Math.round(Number(item.matchScore || 0)) }}%</view>
          </view>
          <view class="summaryLine">地点：{{ item.location || "-" }} · 联系方式：{{ item.contact || "-" }}</view>
          <view class="summaryLine" v-if="item.reasons && item.reasons.length > 0">{{ item.reasons.join("；") }}</view>
          <button class="btnGhost miniBtn" size="mini" @click="goMatchDetail(item)">查看候选</button>
        </view>
      </view>

      <view class="card summaryCard">
        <view class="cardTitle">发布前确认</view>
        <view class="summaryLine">类型：{{ typeText(form.type) }}</view>
        <view class="summaryLine">标题：{{ form.title || '-' }}</view>
        <view class="summaryLine">地点：{{ form.location || '-' }}</view>
        <view class="summaryLine">联系方式：{{ form.contact || '-' }}</view>
        <button class="btnPrimary submitBtn" @click="submit">发布信息</button>
      </view>
    </view>
  </view>
</template>

<script>
import { BASE_URL } from "@/common/api.js"

export default {
  data() {
    return {
      form: {
        type: "lost",
        title: "",
        location: "",
        contact: "",
        description: "",
        imageUrl: ""
      },
      errors: {
        title: "",
        location: "",
        contact: "",
        description: ""
      },
      matching: false,
      matchSummary: "",
      matchCandidates: []
    }
  },
  onLoad(options) {
    const type = (options && options.type ? options.type : "").trim()
    if (type === "lost" || type === "found") {
      this.form.type = type
    }
  },
  methods: {
    typeText(type) {
      return type === "found" ? "拾到物品" : "失物"
    },
    setType(type) {
      if (type !== "lost" && type !== "found") return
      this.form.type = type
    },
    clearForm() {
      this.form.title = ""
      this.form.location = ""
      this.form.contact = ""
      this.form.description = ""
      this.form.imageUrl = ""
      this.matchSummary = ""
      this.matchCandidates = []
      this.errors.title = ""
      this.errors.location = ""
      this.errors.contact = ""
      this.errors.description = ""
    },
    validateForm() {
      this.errors.title = ""
      this.errors.location = ""
      this.errors.contact = ""
      this.errors.description = ""
      let ok = true

      const title = (this.form.title || "").trim()
      const location = (this.form.location || "").trim()
      const contact = (this.form.contact || "").trim()
      const description = (this.form.description || "").trim()

      if (!title) {
        this.errors.title = "请填写标题"
        ok = false
      } else if (title.length > 60) {
        this.errors.title = "标题不能超过 60 字"
        ok = false
      }

      if (location.length > 120) {
        this.errors.location = "地点不能超过 120 字"
        ok = false
      }

      if (!contact) {
        this.errors.contact = "请填写联系方式"
        ok = false
      }

      if (description.length > 500) {
        this.errors.description = "描述不能超过 500 字"
        ok = false
      }

      return ok
    },
    submit() {
      const s = uni.getStorageSync("session")
      if (!s || !s.username) {
        uni.showToast({ title: "请先登录", icon: "none" })
        uni.reLaunch({ url: "/pages/login/login" })
        return
      }

      if (!this.validateForm()) return

      const payload = {
        type: this.form.type,
        title: (this.form.title || "").trim(),
        location: (this.form.location || "").trim(),
        contact: (this.form.contact || "").trim(),
        description: (this.form.description || "").trim(),
        imageUrl: this.form.imageUrl
      }

      uni.showModal({
        title: "确认发布",
        content: `类型：${this.typeText(payload.type)}\n标题：${payload.title}`,
        success: (m) => {
          if (!m.confirm) return
          uni.request({
            url: `${BASE_URL}/lostfound`,
            method: "POST",
            header: { "Content-Type": "application/json" },
            data: payload,
            success: (res) => {
              if (!res.data || !res.data.ok) {
                uni.showToast({ title: (res.data && res.data.msg) || "发布失败", icon: "none" })
                return
              }

              const id = res.data.data && res.data.data.id ? res.data.data.id : "-"
              uni.showModal({
                title: "发布成功",
                content: `已发布${this.typeText(payload.type)}\n编号：${id}`,
                showCancel: false,
                success: () => {
                  uni.navigateBack()
                }
              })
            },
            fail: () => {
              uni.showToast({ title: "发布失败", icon: "none" })
            }
          })
        }
      })
    },
    imgSrc(url) {
      if (!url) return ""
      if (String(url).startsWith("http")) return url
      return `${BASE_URL}${url}`
    },
    goMatchDetail(item) {
      if (!item || !item.id) return
      const type = item.type === "found" || item.type === "lost" ? item.type : "all"
      uni.navigateTo({ url: `/pages/lostfound/list?type=${encodeURIComponent(type)}&focusId=${encodeURIComponent(String(item.id))}` })
    },
    findSimilarItems() {
      const s = uni.getStorageSync("session")
      if (!s || !s.username) {
        uni.showToast({ title: "请先登录", icon: "none" })
        uni.reLaunch({ url: "/pages/login/login" })
        return
      }
      if (this.matching) return
      const title = String(this.form.title || "").trim()
      const description = String(this.form.description || "").trim()
      if (!title && !description && !this.form.imageUrl) {
        uni.showToast({ title: "请先填写标题、描述或上传图片", icon: "none" })
        return
      }
      this.matching = true
      uni.request({
        url: `${BASE_URL}/lostfound/ai-match`,
        method: "POST",
        header: { "Content-Type": "application/json" },
        data: {
          type: this.form.type,
          title,
          description,
          location: String(this.form.location || "").trim(),
          imageUrl: String(this.form.imageUrl || "").trim()
        },
        success: (res) => {
          const payload = (res && res.data) || {}
          if (!payload.ok || !payload.data) {
            this.matchSummary = payload.msg || "匹配失败"
            this.matchCandidates = []
            return
          }
          this.matchSummary = String(payload.data.summary || "").trim()
          this.matchCandidates = Array.isArray(payload.data.candidates) ? payload.data.candidates : []
          if (this.matchCandidates.length === 0) {
            uni.showToast({ title: "暂无高相似候选", icon: "none" })
          }
        },
        fail: () => {
          this.matchSummary = "匹配失败，请稍后重试。"
          this.matchCandidates = []
        },
        complete: () => {
          this.matching = false
        }
      })
    },
    removeImage() {
      this.form.imageUrl = ""
    },
    chooseImage() {
      uni.chooseImage({
        count: 1,
        success: (res) => {
          const filePath = res.tempFilePaths[0]
          if (!filePath) return

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
              uni.showToast({ title: "上传成功", icon: "success" })
            },
            fail: () => {
              uni.showToast({ title: "上传失败", icon: "none" })
            }
          })
        }
      })
    }
  }
}
</script>

<style lang="scss">
.postPage {
  padding-bottom: 20px;
}

.heroCard {
  border: 1px solid rgba(22, 119, 255, 0.18);
  background: linear-gradient(160deg, #ffffff 0%, #f2f7ff 100%);
}

.heroTop {
  align-items: flex-start;
}

.formCard {
  border: 1px solid rgba(148, 163, 184, 0.24);
}

.typeRow {
  display: flex;
  gap: 8px;
  margin-bottom: 2px;
}

.typeChip {
  transition: all 0.14s ease;
}

.chipOn {
  border-color: #bfdbfe;
  background: #eaf3ff;
  color: #1d4ed8;
}

.uploadRow {
  margin-bottom: 6px;
}

.preview {
  width: 100%;
  height: 168px;
  border-radius: 12px;
  margin-top: 8px;
}

.summaryCard {
  border: 1px solid rgba(148, 163, 184, 0.24);
}

.summaryLine {
  margin-top: 8px;
  font-size: 12px;
  color: #475569;
}

.matchCard {
  margin-top: 10px;
  padding: 10px;
  border-radius: 12px;
  border: 1px solid rgba(148, 163, 184, 0.24);
  background: #f8fafc;
}

.matchTitle {
  font-size: 13px;
  font-weight: 700;
  color: #0f172a;
}

.matchScore {
  font-size: 12px;
  color: #1d4ed8;
}

.submitBtn {
  width: 100%;
  margin-top: 12px;
}

.miniBtn {
  min-height: 30px;
  line-height: 30px;
  padding: 0 10px;
  font-size: 12px;
  border-radius: 9px;
}
</style>

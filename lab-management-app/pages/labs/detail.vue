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
    </view>
  </view>
</template>

<script>
import { BASE_URL } from "@/common/api.js"

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

export default {
  data() {
    return {
      labName: "",
      lab: null,
      loading: false,
      badImage: false,
      nowText: ""
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
    imgSrc(url) {
      if (!url) return ""
      if (String(url).startsWith("http")) return url
      return `${BASE_URL}${url}`
    },
    onImageError() {
      this.badImage = true
    },
    fetchDetail() {
      if (!this.labName) {
        this.lab = null
        return
      }
      this.loading = true
      this.badImage = false
      uni.request({
        url: `${BASE_URL}/labs?keyword=${encodeURIComponent(this.labName)}`,
        method: "GET",
        success: (res) => {
          const rows = Array.isArray(res.data) ? res.data : []
          const exact = rows.find((x) => x.name === this.labName)
          this.lab = exact || rows[0] || null
          this.nowText = nowTimeText()
        },
        fail: () => {
          this.lab = null
          uni.showToast({ title: "获取详情失败", icon: "none" })
        },
        complete: () => {
          this.loading = false
        }
      })
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

.miniBtn {
  min-height: 30px;
  line-height: 30px;
  padding: 0 10px;
  font-size: 12px;
  border-radius: 9px;
}
</style>

<template>
  <view class="container labsPage" :class="themeClass">
    <view class="stack">
      <view class="card heroCard">
        <view class="rowBetween heroTop">
          <view>
            <view class="title">实验室列表</view>
            <view class="subtitle">选择实验室，快速预约或查看详情</view>
          </view>
          <button class="btnSecondary miniBtn" size="mini" @click="fetchLabs(keyword)">刷新</button>
        </view>
        <view class="heroMeta muted">当前共 {{ labs.length }} 个实验室</view>
      </view>

      <view class="card searchCard">
        <view class="searchInputWrap">
          <text class="searchIcon">搜</text>
          <input
            class="searchInput"
            v-model="keyword"
            placeholder="搜索实验室，例如 C301 / 物联网实验室"
            confirm-type="search"
            @confirm="doSearch"
          />
          <text class="clearIcon" v-if="keyword" @click="clearKeyword">清</text>
        </view>

        <view class="searchActions">
          <button class="btnPrimary miniBtn" size="mini" @click="doSearch">搜索</button>
          <button class="btnSecondary miniBtn" size="mini" @click="resetSearch">重置</button>
        </view>
      </view>

      <view class="grid" v-if="loading">
        <view class="skeletonCard" v-for="i in skeletonCount" :key="i">
          <view class="skeleton skeletonCover"></view>
          <view class="skeleton skeletonTitle"></view>
          <view class="skeleton skeletonMeta"></view>
          <view class="skeleton skeletonMeta short"></view>
        </view>
      </view>

      <view class="grid" v-else-if="labs.length > 0">
        <view
          v-for="lab in labs"
          :key="lab.id"
          class="labCard"
          :class="{ pressed: activeCardId === lab.id }"
          @click="openActions(lab)"
          @touchstart="onCardTouchStart(lab.id)"
          @touchend="onCardTouchEnd"
          @touchcancel="onCardTouchEnd"
        >
          <view class="cover">
            <image
              v-if="hasCover(lab)"
              :src="imgSrc(lab.imageUrl)"
              class="coverImage"
              mode="aspectFill"
              @error="onImageError(lab.id)"
            />
            <view v-else class="coverFallback" :style="fallbackStyle(lab)">
              <text class="fallbackText">LAB</text>
            </view>
          </view>

          <view class="cardBody">
            <view class="topRow">
              <view class="labName">{{ lab.name }}</view>
              <view class="statusTag" :class="statusClass(lab.status)">
                {{ statusText(lab.status) }}
              </view>
            </view>

            <view class="metaRow">
              <text>容量 {{ lab.capacity || 0 }}</text>
              <text class="dot">·</text>
              <text>设备 {{ lab.deviceCount || 0 }}</text>
            </view>

            <view class="desc" v-if="lab.description">{{ lab.description }}</view>
            <view class="hint">点击卡片进行预约、详情或日历查看</view>
          </view>
        </view>
      </view>

      <view class="emptyState" v-else>
        <view class="emptyIcon">室</view>
        <view class="emptyTitle">没有找到匹配的实验室</view>
        <view class="emptySub">请尝试更换关键词，或点击重置查看全部实验室</view>
      </view>
    </view>
  </view>
</template>

<script>
import { BASE_URL, getApiListData } from "@/common/api.js"
import { themePageMixin } from "@/common/theme.js"

const FALLBACK_BG = [
  "linear-gradient(135deg, #dbeafe 0%, #e0f2fe 100%)",
  "linear-gradient(135deg, #dcfce7 0%, #d9f99d 100%)",
  "linear-gradient(135deg, #fae8ff 0%, #e9d5ff 100%)",
  "linear-gradient(135deg, #fef3c7 0%, #fde68a 100%)",
  "linear-gradient(135deg, #ffe4e6 0%, #fecdd3 100%)",
  "linear-gradient(135deg, #ede9fe 0%, #ddd6fe 100%)"
]

const FALLBACK_BG_DARK = [
  "linear-gradient(135deg, #1d3558 0%, #254467 100%)",
  "linear-gradient(135deg, #1b3a2c 0%, #24503a 100%)",
  "linear-gradient(135deg, #33234f 0%, #3c2d5c 100%)",
  "linear-gradient(135deg, #4a351f 0%, #5a4128 100%)",
  "linear-gradient(135deg, #4a2330 0%, #5e2d3c 100%)",
  "linear-gradient(135deg, #252d5a 0%, #323b69 100%)"
]

export default {
  mixins: [themePageMixin],
  data() {
    return {
      keyword: "",
      labs: [],
      loading: false,
      skeletonCount: 6,
      badImageMap: {},
      activeCardId: null
    }
  },
  onShow() {
    this.fetchLabs()
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
    hasCover(lab) {
      if (!lab || !lab.imageUrl) return false
      return !this.badImageMap[String(lab.id)]
    },
    onImageError(id) {
      this.badImageMap = { ...this.badImageMap, [String(id)]: true }
    },
    fallbackStyle(lab) {
      const idx = Number(lab.id || 0) % FALLBACK_BG.length
      const darkMode = String(this.themeClass || "").includes("theme-dark")
      return { backgroundImage: darkMode ? FALLBACK_BG_DARK[idx] : FALLBACK_BG[idx] }
    },
    onCardTouchStart(id) {
      this.activeCardId = id
    },
    onCardTouchEnd() {
      this.activeCardId = null
    },
    clearKeyword() {
      this.keyword = ""
      this.fetchLabs("")
    },
    doSearch() {
      this.fetchLabs(this.keyword.trim())
    },
    resetSearch() {
      this.keyword = ""
      this.fetchLabs("")
    },
    fetchLabs(keyword = "") {
      this.loading = true
      this.badImageMap = {}
      const k = String(keyword || "").trim()
      const qs = k ? `?keyword=${encodeURIComponent(k)}` : ""
      uni.request({
        url: `${BASE_URL}/labs${qs}`,
        method: "GET",
        success: (res) => {
          this.labs = getApiListData(res.data)
        },
        fail: () => {
          this.labs = []
          uni.showToast({ title: "获取实验室失败", icon: "none" })
        },
        complete: () => {
          this.loading = false
        }
      })
    },
    openActions(lab) {
      uni.showActionSheet({
        itemList: ["立即预约", "查看详情", "查看日历"],
        success: (res) => {
          if (res.tapIndex === 0) {
            uni.navigateTo({ url: `/pages/reserve/reserve?labName=${encodeURIComponent(lab.name)}` })
            return
          }
          if (res.tapIndex === 1) {
            uni.navigateTo({ url: `/pages/labs/detail?labName=${encodeURIComponent(lab.name)}` })
            return
          }
          uni.navigateTo({ url: `/pages/labs/calendar?labName=${encodeURIComponent(lab.name)}` })
        }
      })
    }
  }
}
</script>

<style lang="scss">
.labsPage {
  padding-bottom: 20px;
}

.heroCard {
  border: 1px solid var(--color-border-focus);
  background: var(--color-bg-soft);
}

.heroTop {
  align-items: flex-start;
}

.heroMeta {
  margin-top: 8px;
}

.miniBtn {
  min-height: 30px;
  line-height: 30px;
  padding: 0 10px;
  font-size: 12px;
  border-radius: 9px;
}

.searchCard {
  border: 1px solid var(--color-border-primary);
}

.searchInputWrap {
  display: flex;
  align-items: center;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-primary);
  border-radius: 12px;
  padding: 0 10px;
}

.searchIcon {
  font-size: 12px;
  color: var(--color-text-muted);
  margin-right: 6px;
}

.searchInput {
  flex: 1;
  height: 36px;
  font-size: 13px;
  color: var(--color-text-primary);
}

.clearIcon {
  color: var(--color-text-muted);
  font-size: 12px;
  padding: 4px 2px;
}

.searchActions {
  margin-top: 10px;
  display: flex;
  gap: 8px;
}

.grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.labCard {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-primary);
  border-radius: 14px;
  overflow: hidden;
  box-shadow: var(--shadow-sm);
  transform: scale(1);
  transition: transform 0.16s ease, box-shadow 0.16s ease;

  &.pressed {
    transform: scale(0.98);
    box-shadow: var(--shadow-md);
  }
}

.cover {
  position: relative;
  width: 100%;
  padding-top: 56.25%;
  background: var(--color-bg-soft);
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
  color: var(--color-text-secondary);
  font-weight: 700;
  font-size: 14px;
  letter-spacing: 1px;
}

.cardBody {
  padding: 10px;
}

.topRow {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
}

.labName {
  flex: 1;
  min-width: 0;
  color: var(--color-text-primary);
  font-size: 14px;
  font-weight: 700;
  line-height: 1.25;
  word-break: break-all;
}

.statusTag.success {
  background: var(--color-success-soft);
  color: var(--success);
}

.statusTag.danger {
  background: var(--color-danger-soft);
  color: var(--danger);
}

.metaRow {
  margin-top: 7px;
  color: var(--color-text-muted);
  font-size: 11px;
  display: flex;
  align-items: center;
}

.dot {
  margin: 0 6px;
}

.desc {
  margin-top: 6px;
  color: var(--color-text-secondary);
  font-size: 11px;
  line-height: 1.35;
  max-height: 30px;
  overflow: hidden;
}

.hint {
  margin-top: 8px;
  color: var(--color-text-muted);
  font-size: 10px;
}

.skeletonCard {
  border-radius: 14px;
  padding: 10px;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-primary);
}

.skeleton {
  position: relative;
  overflow: hidden;
  border-radius: 10px;
  background: var(--color-bg-soft);
}

.skeleton::after {
  content: "";
  position: absolute;
  left: -120%;
  top: 0;
  width: 120%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.22), transparent);
  animation: shimmer 1.2s infinite;
}

.skeletonCover {
  height: 86px;
}

.skeletonTitle {
  margin-top: 10px;
  height: 16px;
  width: 72%;
}

.skeletonMeta {
  margin-top: 8px;
  height: 11px;
  width: 92%;
}

.skeletonMeta.short {
  width: 58%;
}

@keyframes shimmer {
  100% {
    left: 120%;
  }
}

@media screen and (min-width: 768px) {
  .grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
</style>

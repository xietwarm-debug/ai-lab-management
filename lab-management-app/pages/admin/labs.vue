<template>
  <view class="container labsAdminPage">
    <view class="stack">
      <view class="card heroCard">
        <view class="rowBetween heroTop">
          <view>
            <view class="title">实验室管理</view>
            <view class="subtitle">支持新增、编辑、删除实验室</view>
          </view>
          <view class="heroActions">
            <button class="btnPrimary miniBtn" size="mini" @click="createLab">新增</button>
            <button class="btnSecondary miniBtn" size="mini" @click="fetchLabs">刷新</button>
          </view>
        </view>
      </view>

      <view class="metricGrid">
        <view class="card metricCard" v-for="item in metrics" :key="item.key">
          <view class="metricLabel">{{ item.label }}</view>
          <view class="metricValue">{{ item.value }}</view>
          <view class="metricHint">{{ item.hint }}</view>
        </view>
      </view>

      <view class="card filterCard">
        <view class="rowBetween">
          <view class="cardTitle">筛选条件</view>
          <view class="muted">匹配 {{ filteredLabs.length }} 个</view>
        </view>

        <input class="inputBase" v-model="keyword" placeholder="按名称或说明搜索实验室" />

        <view class="chipRow">
          <view class="chip filterChip" :class="{ chipOn: statusFilter === 'all' }" @click="setStatusFilter('all')">
            全部
          </view>
          <view class="chip filterChip" :class="{ chipOn: statusFilter === 'free' }" @click="setStatusFilter('free')">
            空闲
          </view>
          <view class="chip filterChip" :class="{ chipOn: statusFilter === 'busy' }" @click="setStatusFilter('busy')">
            使用中
          </view>
          <view class="chip filterChip" @click="resetFilters">重置</view>
        </view>
      </view>

      <view class="card loadingCard" v-if="loading">
        <view class="muted">正在加载实验室数据...</view>
      </view>

      <view class="stack" v-else-if="pagedLabs.length > 0">
        <view v-for="lab in pagedLabs" :key="lab.id" class="card labItem">
          <view class="rowBetween">
            <view>
              <view class="labName">{{ lab.name || '-' }}</view>
              <view class="meta">ID: {{ lab.id }}</view>
            </view>
            <view class="statusTag" :class="statusTone(lab.status)">{{ statusText(lab.status) }}</view>
          </view>

          <view class="cover" v-if="hasCover(lab)">
            <image :src="imgSrc(lab.imageUrl)" class="coverImage" mode="aspectFill" @error="onImageError(lab.id)" />
          </view>
          <view class="coverFallback" v-else :style="fallbackStyle(lab)">
            <view class="fallbackText">LAB</view>
          </view>

          <view class="metaRow">
            <view class="metaItem">容量 {{ lab.capacity || 0 }}</view>
            <view class="metaItem">设备 {{ lab.deviceCount || 0 }}</view>
          </view>

          <view class="meta lineClamp" v-if="lab.description">说明：{{ lab.description }}</view>
          <view class="meta" v-else>说明：暂无</view>

          <view class="actions">
            <button class="btnSecondary miniBtn" size="mini" @click="edit(lab)">编辑</button>
            <button
              class="btnDanger miniBtn"
              size="mini"
              :disabled="isDeleting(lab.id)"
              @click="removeLab(lab)"
            >
              {{ isDeleting(lab.id) ? '删除中...' : '删除' }}
            </button>
          </view>
        </view>

        <view class="card pageCard rowBetween" v-if="pageCount > 1">
          <button class="btnSecondary miniBtn" size="mini" :disabled="currentPage <= 1" @click="prevPage">上一页</button>
          <view class="muted">第 {{ currentPage }} / {{ pageCount }} 页</view>
          <button class="btnSecondary miniBtn" size="mini" :disabled="currentPage >= pageCount" @click="nextPage">下一页</button>
        </view>
      </view>

      <view class="emptyState" v-else>
        <view class="emptyIcon">室</view>
        <view class="emptyTitle">暂无实验室</view>
        <view class="emptySub">可点击“新增”创建第一个实验室</view>
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

export default {
  data() {
    return {
      labs: [],
      loading: false,
      keyword: "",
      statusFilter: "all",
      page: 1,
      pageSize: 8,
      deletingId: 0,
      badImageMap: {}
    }
  },
  computed: {
    metrics() {
      const total = this.labs.length
      const free = this.labs.filter((x) => x.status === "free").length
      const busy = this.labs.filter((x) => x.status === "busy").length
      return [
        { key: "total", label: "实验室总数", value: total, hint: "系统全部实验室" },
        { key: "free", label: "空闲中", value: free, hint: "当前可预约" },
        { key: "busy", label: "使用中", value: busy, hint: "当前占用" }
      ]
    },
    filteredLabs() {
      const q = this.keyword.trim().toLowerCase()
      return this.labs.filter((lab) => {
        const passStatus = this.statusFilter === "all" ? true : lab.status === this.statusFilter
        if (!passStatus) return false
        if (!q) return true
        const name = String(lab.name || "").toLowerCase()
        const desc = String(lab.description || "").toLowerCase()
        const id = String(lab.id || "")
        return name.includes(q) || desc.includes(q) || id.includes(q)
      })
    },
    pageCount() {
      return Math.max(1, Math.ceil(this.filteredLabs.length / this.pageSize))
    },
    currentPage() {
      return Math.min(Math.max(this.page, 1), this.pageCount)
    },
    pagedLabs() {
      const start = (this.currentPage - 1) * this.pageSize
      const end = start + this.pageSize
      return this.filteredLabs.slice(start, end)
    }
  },
  watch: {
    keyword() {
      this.page = 1
    },
    statusFilter() {
      this.page = 1
    }
  },
  onShow() {
    const s = uni.getStorageSync("session")
    if (!s || s.role !== "admin") {
      uni.showToast({ title: "无权限", icon: "none" })
      uni.reLaunch({ url: "/pages/login/login" })
      return
    }
    this.fetchLabs()
  },
  methods: {
    statusText(status) {
      return status === "free" ? "空闲" : "使用中"
    },
    statusTone(status) {
      return status === "free" ? "success" : "warning"
    },
    setStatusFilter(status) {
      this.statusFilter = status
    },
    resetFilters() {
      this.keyword = ""
      this.statusFilter = "all"
      this.page = 1
    },
    prevPage() {
      this.page = Math.max(1, this.currentPage - 1)
    },
    nextPage() {
      this.page = Math.min(this.pageCount, this.currentPage + 1)
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
      return { backgroundImage: FALLBACK_BG[idx] }
    },
    isDeleting(id) {
      return this.deletingId === id
    },
    fetchLabs() {
      this.loading = true
      uni.request({
        url: `${BASE_URL}/labs`,
        method: "GET",
        success: (res) => {
          this.labs = Array.isArray(res.data) ? res.data : []
          this.badImageMap = {}
        },
        fail: () => {
          this.labs = []
          uni.showToast({ title: "获取失败", icon: "none" })
        },
        complete: () => {
          this.loading = false
        }
      })
    },
    edit(lab) {
      uni.navigateTo({ url: `/pages/admin/lab-edit?id=${lab.id}` })
    },
    createLab() {
      uni.navigateTo({ url: "/pages/admin/lab-edit" })
    },
    removeLab(lab) {
      uni.showModal({
        title: "删除实验室",
        content: `确定删除 ${lab.name}？删除后不可恢复。`,
        success: (m) => {
          if (!m.confirm) return
          this.deletingId = lab.id
          uni.request({
            url: `${BASE_URL}/labs/${lab.id}/delete`,
            method: "POST",
            success: (res) => {
              if (!res.data || !res.data.ok) {
                uni.showToast({ title: (res.data && res.data.msg) || "删除失败", icon: "none" })
                return
              }
              uni.showModal({
                title: "删除成功",
                content: `实验室 ${lab.name} 已删除`,
                showCancel: false
              })
              this.fetchLabs()
            },
            fail: () => {
              uni.showToast({ title: "删除失败", icon: "none" })
            },
            complete: () => {
              this.deletingId = 0
            }
          })
        }
      })
    }
  }
}
</script>

<style lang="scss">
.labsAdminPage {
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

.metricGrid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.metricCard {
  min-height: 88px;
}

.metricLabel {
  font-size: 12px;
  color: #64748b;
}

.metricValue {
  margin-top: 4px;
  font-size: 22px;
  line-height: 1.15;
  font-weight: 700;
  color: #0f172a;
}

.metricHint {
  margin-top: 4px;
  font-size: 10px;
  color: #94a3b8;
}

.filterCard {
  border: 1px solid rgba(148, 163, 184, 0.24);
}

.chipRow {
  margin-top: 10px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.filterChip {
  transition: all 0.14s ease;
}

.chipOn {
  border-color: #bfdbfe;
  background: #eaf3ff;
  color: #1d4ed8;
}

.loadingCard {
  min-height: 70px;
  display: flex;
  align-items: center;
}

.labItem {
  border: 1px solid rgba(148, 163, 184, 0.24);
}

.labName {
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
}

.meta {
  margin-top: 6px;
  font-size: 12px;
  color: #64748b;
}

.cover {
  margin-top: 10px;
  width: 100%;
  position: relative;
  padding-top: 50%;
  border-radius: 12px;
  overflow: hidden;
}

.coverImage {
  position: absolute;
  left: 0;
  top: 0;
  width: 100%;
  height: 100%;
}

.coverFallback {
  margin-top: 10px;
  height: 120px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.fallbackText {
  color: rgba(30, 41, 59, 0.75);
  font-weight: 700;
  letter-spacing: 1px;
}

.metaRow {
  margin-top: 10px;
  display: flex;
  gap: 8px;
}

.metaItem {
  font-size: 11px;
  padding: 4px 8px;
  border-radius: 999px;
  background: #f1f5f9;
  color: #475569;
}

.lineClamp {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.actions {
  margin-top: 10px;
  display: flex;
  gap: 8px;
}

.pageCard {
  border: 1px solid rgba(148, 163, 184, 0.24);
}

@media screen and (max-width: 420px) {
  .metricGrid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>

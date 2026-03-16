<template>
  <view class="container labsAdminPage">
    <view class="stack">
      <view class="card heroCard">
        <view class="rowBetween heroTop">
          <view>
            <view class="title">管理员实验室列表</view>
            <view class="subtitle">管理员专属实验室总览、监测与维护</view>
          </view>
          <view class="heroActions">
            <button class="btnPrimary miniBtn" size="mini" @click="createLab">新增</button>
            <button class="btnSecondary miniBtn" size="mini" @click="fetchSensorStatus(true)">刷新监测</button>
            <button class="btnSecondary miniBtn" size="mini" @click="fetchLabs">刷新</button>
          </view>
        </view>
        <view class="heroMeta muted">仅管理员可访问，不与教师端、用户端实验室列表复用</view>
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

          <view class="sensorPanel">
            <view class="rowBetween">
              <view class="sensorTitle">环境与安全监测</view>
              <view class="statusTag" :class="sensorLevelTone(sensorInfo(lab.id) && sensorInfo(lab.id).level)">
                {{ sensorLevelText(sensorInfo(lab.id) && sensorInfo(lab.id).level) }}
              </view>
            </view>

            <view class="sensorGrid" v-if="sensorInfo(lab.id)">
              <view class="sensorCell" :class="sensorModuleTone(sensorInfo(lab.id), 'temperature')">
                温度 {{ sensorInfo(lab.id).readings.temperatureC }}°C
              </view>
              <view class="sensorCell" :class="sensorModuleTone(sensorInfo(lab.id), 'humidity')">
                湿度 {{ sensorInfo(lab.id).readings.humidityPct }}%
              </view>
              <view class="sensorCell" :class="sensorModuleTone(sensorInfo(lab.id), 'smoke')">
                烟雾 {{ sensorInfo(lab.id).readings.smokePpm }}ppm
              </view>
              <view class="sensorCell" :class="sensorModuleTone(sensorInfo(lab.id), 'voltage')">
                电压 {{ sensorInfo(lab.id).readings.voltageV }}V
              </view>
              <view class="sensorCell" :class="sensorModuleTone(sensorInfo(lab.id), 'current')">
                电流 {{ sensorInfo(lab.id).readings.currentA }}A
              </view>
              <view class="sensorCell" :class="sensorModuleTone(sensorInfo(lab.id), 'people')">
                人数 {{ sensorInfo(lab.id).readings.peopleCount }}人
              </view>
            </view>
            <view class="muted" v-else>监测数据加载中...</view>

            <view class="sensorAlert" v-if="sensorInfo(lab.id) && (sensorInfo(lab.id).alerts || []).length">
              {{ (sensorInfo(lab.id).alerts || []).map((x) => x.message).join("；") }}
            </view>
            <view class="muted sensorTime" v-if="sensorInfo(lab.id)">
              更新时间：{{ sensorInfo(lab.id).collectedAt || "-" }}
            </view>
          </view>

          <view class="actions">
            <button class="btnSecondary miniBtn" size="mini" @click="edit(lab)">编辑</button>
            <button class="btnPrimary miniBtn" size="mini" @click="goRoomMap(lab)">机房状态编辑</button>
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
import { BASE_URL, getApiListData } from "@/common/api.js"

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
      badImageMap: {},
      sensorMap: {},
      sensorTimer: null
    }
  },
  onLoad(options) {
    const rawKeyword = String((options && options.keyword) || "").trim()
    if (!rawKeyword) return
    try {
      this.keyword = decodeURIComponent(rawKeyword)
    } catch (e) {
      this.keyword = rawKeyword
    }
  },
  computed: {
    metrics() {
      const total = this.labs.length
      const free = this.labs.filter((x) => x.status === "free").length
      const busy = this.labs.filter((x) => x.status === "busy").length
      const warningLabs = Object.values(this.sensorMap).filter((x) => x && x.level === "warning").length
      const alarmLabs = Object.values(this.sensorMap).filter((x) => x && x.level === "alarm").length
      return [
        { key: "total", label: "实验室总数", value: total, hint: "系统全部实验室" },
        { key: "free", label: "空闲中", value: free, hint: "当前可预约" },
        { key: "busy", label: "使用中", value: busy, hint: "当前占用" },
        { key: "warning", label: "预警中", value: warningLabs, hint: "需要关注" },
        { key: "alarm", label: "报警中", value: alarmLabs, hint: "需立即处理" }
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
    this.startSensorTimer()
  },
  onHide() {
    this.stopSensorTimer()
  },
  onUnload() {
    this.stopSensorTimer()
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
    sensorInfo(labId) {
      return this.sensorMap[String(labId)] || null
    },
    sensorLevelText(level) {
      if (level === "alarm") return "报警"
      if (level === "warning") return "预警"
      return "正常"
    },
    sensorLevelTone(level) {
      if (level === "alarm") return "danger"
      if (level === "warning") return "warning"
      return "success"
    },
    sensorModuleTone(sensor, moduleKey) {
      const level = sensor && sensor.statusByModule ? sensor.statusByModule[moduleKey] : ""
      if (level === "alarm") return "cellAlarm"
      if (level === "warning") return "cellWarning"
      return "cellNormal"
    },
    startSensorTimer() {
      this.stopSensorTimer()
      this.sensorTimer = setInterval(() => {
        this.fetchSensorStatus(false)
      }, 10000)
    },
    stopSensorTimer() {
      if (this.sensorTimer) {
        clearInterval(this.sensorTimer)
        this.sensorTimer = null
      }
    },
    fetchSensorStatus(force = false) {
      if (!this.labs.length) {
        this.sensorMap = {}
        return
      }
      const forceFlag = force ? "?force=1" : ""
      uni.request({
        url: `${BASE_URL}/labs/sensor-status${forceFlag}`,
        method: "GET",
        success: (res) => {
          const payload = (res && res.data) || {}
          if (!payload.ok) {
            if (force) {
              uni.showToast({ title: payload.msg || "监测获取失败", icon: "none" })
            }
            return
          }
          const rows = Array.isArray(payload.data) ? payload.data : []
          const next = {}
          rows.forEach((row) => {
            const key = String((row && row.labId) || "")
            if (!key) return
            next[key] = row
          })
          this.sensorMap = next
        },
        fail: () => {
          if (force) {
            uni.showToast({ title: "监测获取失败", icon: "none" })
          }
        }
      })
    },
    fetchLabs() {
      this.loading = true
      uni.request({
        url: `${BASE_URL}/labs`,
        method: "GET",
        success: (res) => {
          this.labs = getApiListData(res.data)
          this.badImageMap = {}
          this.fetchSensorStatus(true)
        },
        fail: () => {
          this.labs = []
          this.sensorMap = {}
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
    goRoomMap(lab) {
      if (!lab || !lab.id) return
      uni.navigateTo({ url: `/pages/admin/room_map?labId=${lab.id}` })
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

.heroMeta {
  margin-top: 8px;
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

.sensorPanel {
  margin-top: 10px;
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 10px;
  padding: 8px;
  background: #f8fafc;
}

.sensorTitle {
  font-size: 12px;
  color: #334155;
  font-weight: 700;
}

.sensorGrid {
  margin-top: 8px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 6px;
}

.sensorCell {
  font-size: 11px;
  border-radius: 8px;
  padding: 6px 8px;
  border: 1px solid transparent;
}

.sensorCell.cellNormal {
  background: #eff6ff;
  color: #1e3a8a;
  border-color: #bfdbfe;
}

.sensorCell.cellWarning {
  background: #fffbeb;
  color: #92400e;
  border-color: #fcd34d;
}

.sensorCell.cellAlarm {
  background: #fff1f2;
  color: #9f1239;
  border-color: #fda4af;
}

.sensorAlert {
  margin-top: 8px;
  font-size: 12px;
  color: #b91c1c;
  line-height: 1.5;
}

.sensorTime {
  margin-top: 6px;
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

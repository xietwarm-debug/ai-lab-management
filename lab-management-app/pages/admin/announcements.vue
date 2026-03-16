<template>
  <view class="container announcementPage">
    <view class="stack">
      <view class="card heroCard">
        <view class="rowBetween heroTop">
          <view>
            <view class="title">公告中心</view>
            <view class="subtitle">发布、定时、置顶与删除</view>
          </view>
          <button class="btnSecondary miniBtn" size="mini" :loading="loadingAnnouncements" @click="loadAnnouncements">
            刷新
          </button>
        </view>
        <view class="rowBetween heroActions">
          <button class="btnGhost miniBtn" size="mini" @click="scrollToSection('#announcementEditorCard')">发布公告</button>
          <button class="btnGhost miniBtn" size="mini" @click="scrollToSection('#announcementListCard')">公告管理</button>
        </view>
      </view>

      <view class="card" id="announcementEditorCard">
        <view class="rowBetween sectionHeader">
          <view class="cardTitle">公告编辑器</view>
          <view class="rowBetween">
            <view class="muted">支持置顶与定时发布</view>
            <button class="btnGhost miniBtn" size="mini" :loading="draftingAnnouncement" @click="generateAnnouncementDraft">
              AI生成草稿
            </button>
          </view>
        </view>
        <view class="sceneRow">
          <view
            v-for="item in draftSceneOptions"
            :key="item.value"
            class="chip sceneChip"
            :class="{ chipOn: draftScene === item.value }"
            @click="draftScene = item.value"
          >
            {{ item.label }}
          </view>
        </view>
        <input
          class="inputBase"
          v-model.trim="announcementTitle"
          maxlength="120"
          placeholder="请输入公告标题"
        />
        <textarea
          class="textareaBase announcementArea"
          v-model.trim="announcementContent"
          maxlength="5000"
          placeholder="请输入公告内容"
        />
        <input
          class="inputBase announcementPublishAt"
          v-model.trim="announcementPublishAt"
          placeholder="发布时间(可选)：YYYY-MM-DD HH:mm:ss"
        />
        <view class="rowBetween announcementActions">
          <view class="rowBetween">
            <button class="btnSecondary miniBtn" size="mini" @click="announcementPinned = !announcementPinned">
              {{ announcementPinned ? "置顶中" : "普通公告" }}
            </button>
            <view class="muted">标题和内容必填</view>
          </view>
          <view class="rowBetween">
            <button
              v-if="editingAnnouncementId"
              class="btnSecondary miniBtn"
              size="mini"
              :disabled="publishing"
              @click="cancelAnnouncementEdit"
            >
              取消编辑
            </button>
            <button class="btnPrimary miniBtn" size="mini" :loading="publishing" @click="submitAnnouncement">
              {{ editingAnnouncementId ? "保存修改" : "发布公告" }}
            </button>
          </view>
        </view>
      </view>

      <view class="card" id="announcementListCard">
        <view class="rowBetween sectionHeader">
          <view>
            <view class="cardTitle">公告管理</view>
            <view class="muted">最近 {{ announcementRows.length }} 条</view>
          </view>
          <button class="btnSecondary miniBtn" size="mini" :loading="loadingAnnouncements" @click="loadAnnouncements">
            刷新
          </button>
        </view>

        <view class="empty" v-if="loadingAnnouncements">加载中...</view>
        <view class="emptyState" v-else-if="announcementRows.length === 0">
          <view class="emptyIcon">信</view>
          <view class="emptyTitle">暂无公告</view>
          <view class="emptySub">发布或定时创建后会显示在这里</view>
        </view>
        <view class="pendingList" v-else>
          <view class="pendingItem" v-for="row in announcementRows" :key="row.id">
            <view class="rowBetween">
              <view class="pendingLab lineClampOne">{{ row.title || "-" }}</view>
              <view class="rowBetween announcementTagRow">
                <view class="statusTag" :class="announcementStatusTone(row.status)">
                  {{ announcementStatusText(row.status) }}
                </view>
                <view class="statusTag info" v-if="row.isPinned">置顶</view>
              </view>
            </view>
            <view class="pendingMeta">发布时间：{{ row.publishAt || row.createdAt || "-" }}</view>
            <view class="pendingMeta">更新时间：{{ row.updatedAt || "-" }}</view>
            <view class="pendingMeta lineClamp">{{ row.content || "-" }}</view>
            <view class="pendingActions">
              <button class="btnSecondary miniBtn" size="mini" :disabled="publishing" @click="startEditAnnouncement(row)">
                编辑
              </button>
              <button class="btnSecondary miniBtn" size="mini" :disabled="publishing" @click="toggleAnnouncementPin(row)">
                {{ row.isPinned ? "取消置顶" : "置顶" }}
              </button>
              <button class="btnDanger miniBtn" size="mini" :disabled="publishing" @click="removeAnnouncement(row)">
                删除
              </button>
            </view>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { BASE_URL, adminGenerateAnnouncementAiDraft, getApiListData } from "@/common/api.js"

export default {
  data() {
    return {
      announcementTitle: "",
      announcementContent: "",
      announcementPublishAt: "",
      announcementPinned: false,
      editingAnnouncementId: 0,
      announcementRows: [],
      loadingAnnouncements: false,
      publishing: false,
      draftingAnnouncement: false,
      draftScene: "course",
      draftSceneOptions: [
        { label: "课程安排", value: "course" },
        { label: "设备维护", value: "maintenance" },
        { label: "安全提醒", value: "safety" }
      ],
      initialTab: "editor"
    }
  },
  onLoad(options) {
    const tab = String(((options || {}).tab || "editor")).trim().toLowerCase()
    this.initialTab = tab === "list" ? "list" : "editor"
  },
  onShow() {
    const s = uni.getStorageSync("session") || {}
    if (!s.username || !s.token || s.role !== "admin") {
      uni.showToast({ title: "无权限", icon: "none" })
      uni.reLaunch({ url: "/pages/login/login" })
      return
    }
    this.loadAnnouncements(() => this.scrollByInitialTab())
  },
  onPullDownRefresh() {
    this.loadAnnouncements(() => {
      uni.stopPullDownRefresh()
    })
  },
  methods: {
    scrollToSection(selector) {
      const query = uni.createSelectorQuery().in(this)
      query.select(selector).boundingClientRect()
      query.selectViewport().scrollOffset()
      query.exec((res) => {
        const rect = res && res[0]
        const viewport = res && res[1]
        if (!rect || !viewport) return
        const top = Number(rect.top || 0) + Number(viewport.scrollTop || 0) - 8
        uni.pageScrollTo({ scrollTop: top > 0 ? top : 0, duration: 220 })
      })
    },
    scrollByInitialTab() {
      if (this.initialTab !== "list") return
      this.$nextTick(() => {
        setTimeout(() => this.scrollToSection("#announcementListCard"), 80)
      })
    },
    announcementStatusText(status) {
      if (status === "scheduled") return "定时中"
      return "已发布"
    },
    announcementStatusTone(status) {
      if (status === "scheduled") return "warning"
      return "success"
    },
    normalizePublishAtInput(value) {
      return String(value || "")
        .trim()
        .replace("T", " ")
        .replace(/\//g, "-")
    },
    resetAnnouncementForm() {
      this.announcementTitle = ""
      this.announcementContent = ""
      this.announcementPublishAt = ""
      this.announcementPinned = false
      this.editingAnnouncementId = 0
    },
    sceneHint() {
      if (this.draftScene === "maintenance") {
        return {
          titleHint: "设备维护安排",
          contentHint: "维修 报修 设备 机房"
        }
      }
      if (this.draftScene === "safety") {
        return {
          titleHint: "实验室安全提醒",
          contentHint: "安全 告警 消防 门禁"
        }
      }
      return {
        titleHint: "实验课程安排",
        contentHint: "课程 实验 停课 补课"
      }
    },
    async generateAnnouncementDraft() {
      if (this.draftingAnnouncement || this.publishing) return
      this.draftingAnnouncement = true
      try {
        const sceneHint = this.sceneHint()
        const res = await adminGenerateAnnouncementAiDraft({
          titleHint: String(this.announcementTitle || "").trim() || sceneHint.titleHint,
          contentHint: String(this.announcementContent || "").trim() || sceneHint.contentHint,
          publishAt: this.normalizePublishAtInput(this.announcementPublishAt),
          isPinned: !!this.announcementPinned
        })
        const payload = (res && res.data) || {}
        if (!payload.ok || !payload.data) {
          uni.showToast({ title: payload.msg || "草稿生成失败", icon: "none" })
          return
        }
        const data = payload.data || {}
        this.announcementTitle = String(data.title || "").trim()
        this.announcementContent = String(data.content || "").trim()
        this.announcementPublishAt = String(data.publishAtSuggestion || "").trim()
        this.announcementPinned = !!data.isPinnedSuggestion
        uni.showToast({ title: "草稿已填入编辑器", icon: "success" })
      } catch (e) {
        uni.showToast({ title: "草稿生成失败", icon: "none" })
      } finally {
        this.draftingAnnouncement = false
      }
    },
    async loadAnnouncements(done) {
      if (this.loadingAnnouncements) {
        if (typeof done === "function") done()
        return
      }
      this.loadingAnnouncements = true
      try {
        const res = await uni.request({
          url: `${BASE_URL}/admin/announcements?status=all&limit=50`,
          method: "GET"
        })
        const rows = getApiListData(res && res.data)
        this.announcementRows = Array.isArray(rows) ? rows : []
      } catch (e) {
        this.announcementRows = []
        uni.showToast({ title: "公告加载失败", icon: "none" })
      } finally {
        this.loadingAnnouncements = false
        if (typeof done === "function") done()
      }
    },
    startEditAnnouncement(row) {
      if (!row || !row.id) return
      this.editingAnnouncementId = Number(row.id) || 0
      this.announcementTitle = String(row.title || "")
      this.announcementContent = String(row.content || "")
      this.announcementPublishAt = String(row.publishAt || "")
      this.announcementPinned = !!row.isPinned
      this.initialTab = "editor"
      this.$nextTick(() => this.scrollToSection("#announcementEditorCard"))
    },
    cancelAnnouncementEdit() {
      this.resetAnnouncementForm()
    },
    async submitAnnouncement() {
      const title = String(this.announcementTitle || "").trim()
      const content = String(this.announcementContent || "").trim()
      if (!title) {
        uni.showToast({ title: "请输入公告标题", icon: "none" })
        return
      }
      if (!content) {
        uni.showToast({ title: "请输入公告内容", icon: "none" })
        return
      }
      if (this.publishing) return
      const publishAt = this.normalizePublishAtInput(this.announcementPublishAt)
      if (publishAt && !/^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}$/.test(publishAt)) {
        uni.showToast({ title: "发布时间格式不正确", icon: "none" })
        return
      }

      const payloadData = {
        title,
        content,
        isPinned: !!this.announcementPinned
      }
      if (publishAt) payloadData.publishAt = publishAt

      this.publishing = true
      try {
        const editingId = Number(this.editingAnnouncementId || 0)
        const res = await uni.request({
          url: editingId > 0 ? `${BASE_URL}/announcements/${editingId}` : `${BASE_URL}/announcements`,
          method: editingId > 0 ? "PUT" : "POST",
          header: { "Content-Type": "application/json" },
          data: payloadData
        })
        const payload = (res && res.data) || {}
        if (!payload.ok) {
          uni.showToast({ title: payload.msg || (editingId > 0 ? "保存失败" : "发布失败"), icon: "none" })
          return
        }
        this.resetAnnouncementForm()
        await this.loadAnnouncements()
        uni.showToast({ title: editingId > 0 ? "公告已更新" : "公告已提交", icon: "success" })
      } catch (e) {
        uni.showToast({ title: "操作失败，请稍后重试", icon: "none" })
      } finally {
        this.publishing = false
      }
    },
    async toggleAnnouncementPin(row) {
      if (!row || !row.id || this.publishing) return
      this.publishing = true
      try {
        const res = await uni.request({
          url: `${BASE_URL}/announcements/${row.id}/pin`,
          method: "POST",
          header: { "Content-Type": "application/json" },
          data: { pinned: !row.isPinned }
        })
        const payload = (res && res.data) || {}
        if (!payload.ok) {
          uni.showToast({ title: payload.msg || "置顶操作失败", icon: "none" })
          return
        }
        await this.loadAnnouncements()
        uni.showToast({ title: row.isPinned ? "已取消置顶" : "已置顶", icon: "success" })
      } catch (e) {
        uni.showToast({ title: "置顶操作失败", icon: "none" })
      } finally {
        this.publishing = false
      }
    },
    removeAnnouncement(row) {
      if (!row || !row.id || this.publishing) return
      uni.showModal({
        title: "删除公告",
        content: `确认删除《${row.title || "未命名公告"}》吗？`,
        confirmColor: "#ef4444",
        success: async (m) => {
          if (!m.confirm) return
          this.publishing = true
          try {
            const res = await uni.request({
              url: `${BASE_URL}/announcements/${row.id}`,
              method: "DELETE"
            })
            const payload = (res && res.data) || {}
            if (!payload.ok) {
              uni.showToast({ title: payload.msg || "删除失败", icon: "none" })
              return
            }
            if (Number(this.editingAnnouncementId || 0) === Number(row.id || 0)) {
              this.resetAnnouncementForm()
            }
            await this.loadAnnouncements()
            uni.showToast({ title: "公告已删除", icon: "success" })
          } catch (e) {
            uni.showToast({ title: "删除失败", icon: "none" })
          } finally {
            this.publishing = false
          }
        }
      })
    }
  }
}
</script>

<style lang="scss">
.announcementPage {
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
  margin-top: 8px;
}

.sceneRow {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.sceneChip {
  transition: all 0.14s ease;
}

.chipOn {
  border-color: #bfdbfe;
  background: #eaf3ff;
  color: #1d4ed8;
}

.miniBtn {
  min-height: 30px;
  line-height: 30px;
  padding: 0 10px;
  border-radius: 9px;
  font-size: 12px;
}

.announcementArea {
  margin-top: 8px;
  min-height: 96px;
}

.announcementPublishAt {
  margin-top: 8px;
}

.announcementActions {
  margin-top: 8px;
}

.announcementTagRow {
  gap: 6px;
}
</style>

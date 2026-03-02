<template>
  <view class="container lostPage" :class="themeClass">
    <view class="stack">
      <view class="card heroCard">
        <view class="rowBetween heroTop">
          <view>
            <view class="title">失物招领大厅</view>
            <view class="subtitle">支持发布失物、拾到物品与认领申请</view>
          </view>
          <button class="btnSecondary miniBtn" size="mini" @click="fetchList">刷新</button>
        </view>
        <view class="heroMeta muted">共 {{ list.length }} 条 · 当前筛选 {{ shownList.length }} 条</view>
      </view>

      <view class="card filterCard">
        <view class="cardTitle">类型筛选</view>
        <view class="chipRow">
          <view
            v-for="item in typeOptions"
            :key="item.value"
            class="chip filterChip"
            :class="{ chipOn: typeFilter === item.value }"
            @click="setType(item.value)"
          >
            {{ item.label }}
            <text v-if="item.value === 'all'">({{ list.length }})</text>
            <text v-if="item.value === 'lost'">({{ lostCount }})</text>
            <text v-if="item.value === 'found'">({{ foundCount }})</text>
          </view>
        </view>
      </view>

      <view class="card loadingCard" v-if="loading">
        <view class="muted">正在加载失物信息...</view>
      </view>

      <view class="stack" v-else-if="shownList.length > 0">
        <view v-for="item in shownList" :key="item.id" class="card lostItem">
          <view class="rowBetween">
            <view class="itemName">{{ item.title || '-' }}</view>
            <view class="typeTag" :class="item.type">{{ item.type === 'lost' ? '失物' : '拾到' }}</view>
          </view>

          <view class="meta">地点：{{ item.location || '-' }}</view>
          <image v-if="item.imageUrl" :src="imgSrc(item.imageUrl)" class="thumb" mode="aspectFill" />
          <view class="meta" v-if="item.description">描述：{{ item.description }}</view>
          <view class="meta">联系方式：{{ item.contact || '-' }}</view>
          <view class="meta muted">发布者：{{ item.owner || '-' }} · {{ item.createdAt || '-' }}</view>

          <view class="statusRow">
            <view class="statusTag" :class="statusClass(item)">{{ statusText(item) }}</view>
            <button
              v-if="canApplyClaim(item)"
              size="mini"
              class="btnPrimary miniBtn"
              @click="openClaimForm(item)"
            >申请认领</button>
          </view>

          <view class="meta" v-if="item.type === 'found' && item.claimApplyStatus === 'pending' && item.claimApplyUser === user">
            你的认领申请待审核
          </view>
          <view class="meta" v-if="item.type === 'found' && item.claimApplyStatus === 'rejected' && item.claimApplyUser === user">
            你的认领申请已驳回{{ item.claimReviewNote ? `：${item.claimReviewNote}` : '' }}
          </view>
        </view>
      </view>

      <view class="emptyState" v-else>
        <view class="emptyIcon">物</view>
        <view class="emptyTitle">暂无记录</view>
        <view class="emptySub">可以发布失物或拾到物品，帮助同学找回物品</view>
      </view>

      <view class="card actionCard">
        <view class="rowBetween">
          <button class="btnPrimary actionBtn" @click="goPost('lost')">发布失物</button>
          <button class="btnGhost actionBtn" @click="goPost('found')">发布拾到物品</button>
        </view>
      </view>
    </view>

    <view v-if="showClaimModal" class="modalMask" @click="closeClaimForm">
      <view class="modalCard stack" @click.stop>
        <view class="modalTitle">认领申请</view>
        <view class="muted" v-if="claimTarget">物品：{{ claimTarget.title }}</view>

        <view class="label">学号</view>
        <input class="inputBase" v-model.trim="claimForm.studentId" placeholder="请输入学号" />
        <view class="fieldError" v-if="claimErrors.studentId">{{ claimErrors.studentId }}</view>

        <view class="label">姓名</view>
        <input class="inputBase" v-model.trim="claimForm.name" placeholder="请输入姓名" />
        <view class="fieldError" v-if="claimErrors.name">{{ claimErrors.name }}</view>

        <view class="label">班级</view>
        <input class="inputBase" v-model.trim="claimForm.className" placeholder="请输入班级" />
        <view class="fieldError" v-if="claimErrors.className">{{ claimErrors.className }}</view>

        <view class="label">说明（选填）</view>
        <textarea class="textareaBase" v-model.trim="claimForm.reason" placeholder="补充说明，例如领取时间" maxlength="255" />

        <view class="modalActions">
          <button size="mini" class="btnGhost miniBtn" @click="closeClaimForm">取消</button>
          <button size="mini" class="btnPrimary miniBtn" @click="submitClaim">提交申请</button>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { BASE_URL } from "@/common/api.js"
import { themePageMixin } from "@/common/theme.js"

export default {
  mixins: [themePageMixin],
  data() {
    return {
      list: [],
      user: "",
      typeFilter: "all",
      loading: false,
      showClaimModal: false,
      claimTarget: null,
      claimForm: {
        studentId: "",
        name: "",
        className: "",
        reason: ""
      },
      claimErrors: {
        studentId: "",
        name: "",
        className: ""
      },
      typeOptions: [
        { label: "全部", value: "all" },
        { label: "失物", value: "lost" },
        { label: "拾到", value: "found" }
      ]
    }
  },
  computed: {
    shownList() {
      if (this.typeFilter === "all") return this.list
      return this.list.filter((x) => x.type === this.typeFilter)
    },
    lostCount() {
      return this.list.filter((x) => x.type === "lost").length
    },
    foundCount() {
      return this.list.filter((x) => x.type === "found").length
    }
  },
  onShow() {
    const s = uni.getStorageSync("session")
    this.user = s && s.username ? s.username : ""
    this.fetchList()
  },
  methods: {
    setType(type) {
      this.typeFilter = type
    },
    fetchList() {
      this.loading = true
      uni.request({
        url: `${BASE_URL}/lostfound`,
        method: "GET",
        success: (res) => {
          this.list = Array.isArray(res.data) ? res.data : []
        },
        fail: () => {
          this.list = []
          uni.showToast({ title: "获取失败", icon: "none" })
        },
        complete: () => {
          this.loading = false
        }
      })
    },
    imgSrc(url) {
      if (!url) return ""
      if (String(url).startsWith("http")) return url
      return `${BASE_URL}${url}`
    },
    goPost(type) {
      uni.navigateTo({ url: `/pages/lostfound/post?type=${encodeURIComponent(type)}` })
    },
    canApplyClaim(item) {
      if (!this.user) return false
      if (item.type !== "found") return false
      if (item.status !== "open") return false
      if ((item.owner || "") === this.user) return false
      if (item.claimApplyStatus === "approved") return false
      if (item.claimApplyStatus === "pending" && (item.claimApplyUser || "") !== this.user) return false
      return true
    },
    statusClass(item) {
      if (item.type === "found") {
        if (item.claimApplyStatus === "pending") return "warning"
        if (item.claimApplyStatus === "approved") return "success"
        if (item.claimApplyStatus === "rejected") return "danger"
      }
      return item.status === "open" ? "info" : "success"
    },
    statusText(item) {
      if (item.type === "found") {
        if (item.claimApplyStatus === "pending") {
          if ((item.claimApplyUser || "") === this.user) return "你已申请认领"
          return "有人申请认领"
        }
        if (item.claimApplyStatus === "approved") return "已认领"
        if (item.claimApplyStatus === "rejected") return "认领被驳回"
      }
      return item.status === "open" ? "处理中" : "已解决"
    },
    openClaimForm(item) {
      if (!this.user) {
        uni.showToast({ title: "请先登录", icon: "none" })
        uni.reLaunch({ url: "/pages/login/login" })
        return
      }

      this.claimTarget = item
      const isMineApply = item.claimApplyUser === this.user
      this.claimForm.studentId = isMineApply ? item.claimApplyStudentId || "" : ""
      this.claimForm.name = isMineApply ? item.claimApplyName || "" : ""
      this.claimForm.className = isMineApply ? item.claimApplyClass || "" : ""
      this.claimForm.reason = isMineApply ? item.claimApplyReason || "" : ""
      this.claimErrors.studentId = ""
      this.claimErrors.name = ""
      this.claimErrors.className = ""
      this.showClaimModal = true
    },
    closeClaimForm() {
      this.showClaimModal = false
      this.claimTarget = null
    },
    submitClaim() {
      if (!this.claimTarget) return

      const claimStudentId = (this.claimForm.studentId || "").trim()
      const claimName = (this.claimForm.name || "").trim()
      const claimClass = (this.claimForm.className || "").trim()
      const claimReason = (this.claimForm.reason || "").trim()

      this.claimErrors.studentId = ""
      this.claimErrors.name = ""
      this.claimErrors.className = ""

      let hasError = false
      if (!claimStudentId) {
        this.claimErrors.studentId = "请填写学号"
        hasError = true
      }
      if (!claimName) {
        this.claimErrors.name = "请填写姓名"
        hasError = true
      }
      if (!claimClass) {
        this.claimErrors.className = "请填写班级"
        hasError = true
      }
      if (hasError) return

      uni.request({
        url: `${BASE_URL}/lostfound/${this.claimTarget.id}/claim-apply`,
        method: "POST",
        header: { "Content-Type": "application/json" },
        data: { claimStudentId, claimName, claimClass, claimReason },
        success: (res) => {
          if (!res.data || !res.data.ok) {
            uni.showToast({ title: (res.data && res.data.msg) || "申请失败", icon: "none" })
            return
          }
          uni.showToast({ title: "已提交认领申请", icon: "success" })
          this.showClaimModal = false
          this.fetchList()
        },
        fail: () => {
          uni.showToast({ title: "申请失败", icon: "none" })
        }
      })
    }
  }
}
</script>

<style lang="scss">
.lostPage {
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

.filterCard {
  border: 1px solid var(--color-border-primary);
}

.chipRow {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.filterChip {
  transition: all 0.14s ease;
}

.chipOn {
  border-color: var(--color-border-focus);
  background: var(--color-info-soft);
  color: var(--info);
}

.loadingCard {
  min-height: 68px;
  display: flex;
  align-items: center;
}

.lostItem {
  border: 1px solid var(--color-border-primary);
}

.itemName {
  font-size: 14px;
  font-weight: 700;
  color: var(--color-text-primary);
}

.typeTag {
  height: 20px;
  line-height: 20px;
  border-radius: 999px;
  padding: 0 8px;
  font-size: 11px;
  font-weight: 600;
  background: var(--color-bg-soft);
  color: var(--color-text-secondary);
}

.typeTag.lost {
  background: var(--color-warning-soft);
  color: var(--warning);
}

.typeTag.found {
  background: var(--color-success-soft);
  color: var(--success);
}

.meta {
  margin-top: 6px;
  color: var(--color-text-muted);
  font-size: 12px;
  line-height: 18px;
}

.thumb {
  width: 100%;
  height: 168px;
  border-radius: 12px;
  margin-top: 8px;
}

.statusRow {
  margin-top: 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.actionCard {
  border: 1px solid var(--color-border-primary);
}

.actionBtn {
  width: 48%;
}
</style>

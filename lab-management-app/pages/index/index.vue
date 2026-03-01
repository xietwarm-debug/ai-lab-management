<template>
  <view class="container portalPage">
    <view class="stack">
      <view class="card heroCard">
        <view class="heroBadge">AIlab</view>
        <view class="title">高校实验室智能管理系统</view>
        <view class="subtitle">预约、审批、通知、失物招领一体化平台</view>

        <view class="heroMetaRow">
          <view class="heroMetaItem">当前账号：{{ username || '未登录' }}</view>
          <view class="heroMetaItem">身份：{{ roleText }}</view>
        </view>

        <view class="heroActions" v-if="username">
          <button class="btnPrimary heroBtn" @click="goWorkbench">进入工作台</button>
          <button class="btnSecondary heroBtn" @click="logout">退出登录</button>
        </view>
        <view class="heroActions" v-else>
          <button class="btnPrimary heroBtn" @click="goLogin">去登录</button>
          <button class="btnSecondary heroBtn" @click="goLogin">去注册</button>
        </view>
      </view>

      <view class="overviewGrid">
        <view class="card overviewCard" v-for="item in overviewCards" :key="item.key">
          <view class="overviewLabel">{{ item.label }}</view>
          <view class="overviewValue">{{ item.value }}</view>
          <view class="overviewHint">{{ item.hint }}</view>
        </view>
      </view>

      <view class="card">
        <view class="rowBetween">
          <view class="cardTitle">快捷入口</view>
          <view class="muted">移动端高频操作</view>
        </view>

        <view class="entryGrid">
          <view class="entryCard" v-for="item in entries" :key="item.key" @click="openEntry(item.key)">
            <view class="entryIcon" :class="'tone-' + item.tone">{{ item.icon }}</view>
            <view class="entryName">{{ item.name }}</view>
            <view class="entryDesc">{{ item.desc }}</view>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { BASE_URL } from "@/common/api.js"

export default {
  data() {
    return {
      username: "",
      role: ""
    }
  },
  computed: {
    roleText() {
      if (this.role === "admin") return "管理员"
      if (this.role === "student") return "学生"
      return "访客"
    },
    overviewCards() {
      return [
        { key: "scene", label: "核心场景", value: "4", hint: "预约 / 审批 / 通知 / 失物" },
        { key: "platform", label: "平台形态", value: "Uni-App", hint: "移动端统一体验" },
        { key: "security", label: "认证机制", value: "Token", hint: "支持会话续期" },
        { key: "status", label: "服务状态", value: "正常", hint: "可直接开始使用" }
      ]
    },
    entries() {
      const base = [
        { key: "labs", icon: "室", name: "实验室列表", desc: "查看状态与容量", tone: "blue" },
        { key: "reserve", icon: "约", name: "预约实验室", desc: "提交预约申请", tone: "green" },
        { key: "my", icon: "单", name: "我的预约", desc: "查看审批进度", tone: "amber" }
      ]
      if (this.role === "admin") {
        base.unshift({ key: "admin", icon: "管", name: "管理后台", desc: "审批与系统管理", tone: "violet" })
      }
      return base
    }
  },
  onShow() {
    const s = uni.getStorageSync("session") || {}
    this.username = s.username || ""
    this.role = s.role || ""
  },
  methods: {
    openEntry(key) {
      if (key === "admin") return this.goAdmin()
      if (key === "labs") return this.goLabs()
      if (key === "reserve") return this.goReserve()
      if (key === "my") return this.goMy()
    },
    goWorkbench() {
      if (!this.username) {
        this.goLogin()
        return
      }
      if (this.role === "admin") {
        this.goAdmin()
        return
      }
      uni.reLaunch({ url: "/pages/user/home" })
    },
    goAdmin() {
      uni.navigateTo({ url: "/pages/admin/admin" })
    },
    goLabs() {
      uni.navigateTo({ url: "/pages/labs/labs" })
    },
    goReserve() {
      uni.navigateTo({ url: "/pages/reserve/reserve" })
    },
    goMy() {
      uni.navigateTo({ url: "/pages/my/my" })
    },
    goLogin() {
      uni.reLaunch({ url: "/pages/login/login" })
    },
    logout() {
      const s = uni.getStorageSync("session") || {}
      uni.request({
        url: `${BASE_URL}/auth/logout`,
        method: "POST",
        header: { "Content-Type": "application/json" },
        data: { refreshToken: s.refreshToken || "" },
        complete: () => {
          uni.removeStorageSync("session")
          this.username = ""
          this.role = ""
          uni.reLaunch({ url: "/pages/login/login" })
        }
      })
    }
  }
}
</script>

<style lang="scss">
.portalPage {
  padding-bottom: 20px;
}

.heroCard {
  border: 1px solid rgba(22, 119, 255, 0.2);
  background: linear-gradient(155deg, #ffffff 0%, #edf5ff 62%, #e6f0ff 100%);
}

.heroBadge {
  width: fit-content;
  height: 22px;
  line-height: 22px;
  border-radius: 999px;
  padding: 0 10px;
  font-size: 11px;
  font-weight: 600;
  color: #1d4ed8;
  background: #eaf3ff;
  border: 1px solid #bfdbfe;
}

.heroMetaRow {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.heroMetaItem {
  height: 25px;
  line-height: 25px;
  border-radius: 999px;
  padding: 0 10px;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(148, 163, 184, 0.24);
  color: #334155;
  font-size: 11px;
}

.heroActions {
  margin-top: 12px;
  display: flex;
  gap: 8px;
}

.heroBtn {
  flex: 1;
}

.overviewGrid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.overviewCard {
  min-height: 100px;
}

.overviewLabel {
  font-size: 12px;
  color: #64748b;
}

.overviewValue {
  margin-top: 4px;
  font-size: 24px;
  line-height: 1.15;
  font-weight: 700;
  color: #0f172a;
}

.overviewHint {
  margin-top: 4px;
  font-size: 11px;
  color: #94a3b8;
}

.entryGrid {
  margin-top: 10px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.entryCard {
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 12px;
  background: #fff;
  padding: 10px;
  transition: transform 0.14s ease, box-shadow 0.14s ease;
}

.entryCard:active {
  transform: scale(0.985);
  box-shadow: 0 5px 14px rgba(15, 23, 42, 0.08);
}

.entryIcon {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
}

.entryIcon.tone-blue {
  color: #1d4ed8;
  background: #eaf3ff;
}

.entryIcon.tone-green {
  color: #15803d;
  background: #eafaf0;
}

.entryIcon.tone-amber {
  color: #b45309;
  background: #fff4dd;
}

.entryIcon.tone-violet {
  color: #6d28d9;
  background: #f3ebff;
}

.entryName {
  margin-top: 8px;
  font-size: 13px;
  font-weight: 700;
  color: #0f172a;
}

.entryDesc {
  margin-top: 4px;
  font-size: 11px;
  color: #64748b;
}
</style>

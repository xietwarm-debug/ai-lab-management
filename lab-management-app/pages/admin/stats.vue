<template>
  <view class="container">
    <view class="stack">
      <view>
        <view class="title">后台数据</view>
        <view class="subtitle">用户管理与权限操作</view>
      </view>

      <view class="card filter rowBetween">
        <view>
          <view class="label">当前登录账号</view>
          <view class="value">{{ operator }}</view>
        </view>
        <button class="btnGhost" size="mini" @click="reload">刷新</button>
      </view>

      <view class="card">
        <view class="rowBetween">
          <view>
            <view class="label">用户管理</view>
            <view class="meta">仅 admin1 可升级或降级权限</view>
          </view>
          <button class="btnPrimary" size="mini" @click="goUsers">进入</button>
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
      operator: ""
    }
  },
  onShow() {
    const s = uni.getStorageSync("session")
    if (!s || s.role !== "admin") {
      uni.showToast({ title: "无权限", icon: "none" })
      uni.reLaunch({ url: "/pages/login/login" })
      return
    }
    this.operator = s.username || ""
    this.fetchUsers()
  },
  methods: {
    reload() {
      this.fetchUsers()
    },
    fetchUsers() {
      // 仅用于验证连通性与刷新操作
      uni.request({
        url: `${BASE_URL}/users`,
        method: "GET",
        success: () => {},
        fail: () => uni.showToast({ title: "获取失败", icon: "none" })
      })
    },
    goUsers() {
      uni.navigateTo({ url: "/pages/admin/users" })
    }
  }
}
</script>

<style>
.filter { gap:12px; }
.label { font-size: 12px; color: #6b7280; }
.value { font-weight: 600; }

.meta{ margin-top:6px; color:#64748b; font-size:12px; }
</style>

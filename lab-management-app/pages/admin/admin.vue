<template>
  <view class="container redirectPage">
    <view class="card redirectCard">
      <view class="cardTitle">Redirecting...</view>
    </view>
  </view>
</template>

<script>
import { redirectByRole, requireLogin } from "@/common/session.js"

export default {
  onShow() {
    const session = requireLogin()
    if (!session) return
    redirectByRole(session.role, { replace: true })
  }
}
</script>

<style lang="scss">
.redirectPage {
  min-height: 100vh;
  display: flex;
  align-items: center;
}

.redirectCard {
  width: 100%;
  text-align: center;
}
</style>

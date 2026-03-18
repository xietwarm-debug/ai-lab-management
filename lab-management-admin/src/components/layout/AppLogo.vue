<template>
  <div class="app-logo">
    <div class="logo-mark">AI</div>
    <div v-if="!collapsed" class="logo-copy">
      <strong>实验室管理后台</strong>
      <span>Lab Admin Console</span>
    </div>
  </div>
</template>

<script setup>
defineProps({
  collapsed: {
    type: Boolean,
    default: false
  }
})
</script>

<style scoped lang="scss">
.app-logo {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 18px 16px;
}

.logo-mark {
  display: grid;
  width: 40px;
  height: 40px;
  place-items: center;
  border-radius: 12px;
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
  color: #fff;
  font-weight: 700;
  box-shadow: 0 4px 12px rgba(29, 78, 216, 0.2);
}

.logo-copy {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}

.logo-copy strong {
  font-size: 14px;
  color: #ffffff;
}

.logo-copy span {
  color: rgba(255, 255, 255, 0.7);
  font-size: 12px;
}
</style>

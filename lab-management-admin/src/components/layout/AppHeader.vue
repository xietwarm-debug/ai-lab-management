<template>
  <header class="app-header">
    <div class="header-left">
      <el-button text @click="$emit('toggle-sidebar')">
        <el-icon><Fold /></el-icon>
      </el-button>
      <div class="header-copy">
        <strong>{{ title }}</strong>
        <span>{{ subtitle }}</span>
      </div>
    </div>
    <div class="header-right">
      <div class="user-chip">
        <span>{{ username }}</span>
        <em>{{ roleLabel }}</em>
      </div>
      <el-button type="primary" plain @click="$emit('logout')">退出登录</el-button>
    </div>
  </header>
</template>

<script setup>
import { Fold } from '@element-plus/icons-vue'

defineProps({
  title: {
    type: String,
    default: ''
  },
  subtitle: {
    type: String,
    default: ''
  },
  username: {
    type: String,
    default: ''
  },
  roleLabel: {
    type: String,
    default: ''
  }
})

defineEmits(['toggle-sidebar', 'logout'])
</script>

<style scoped lang="scss">
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 24px;
  border-bottom: none;
  background: rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(10px);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.02);
  z-index: 10;
}

.header-left,
.header-right {
  display: flex;
  align-items: center;
  gap: 14px;
}

.header-copy {
  display: flex;
  flex-direction: column;
}

.header-copy strong {
  font-size: 18px;
  color: #09090b;
  font-weight: 700;
}

.header-copy span {
  font-size: 13px;
  color: #71717a;
}

.user-chip {
  display: flex;
  flex-direction: column;
  padding: 8px 12px;
  border-radius: 12px;
  background: #eff6ff;
}

.user-chip em {
  font-style: normal;
  font-size: 12px;
  color: #2563eb;
  font-weight: 600;
}
</style>

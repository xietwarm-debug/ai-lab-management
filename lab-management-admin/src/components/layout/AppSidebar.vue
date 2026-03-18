<template>
  <aside class="app-sidebar" :class="{ collapsed }">
    <AppLogo :collapsed="collapsed" />
    <el-menu
      :default-active="activeMenu"
      class="sidebar-menu"
      :collapse="collapsed"
      router
    >
      <el-menu-item
        v-for="item in menus"
        :key="item.key"
        :index="item.path"
      >
        <el-icon><component :is="item.icon" /></el-icon>
        <span>{{ item.label }}</span>
      </el-menu-item>
    </el-menu>
  </aside>
</template>

<script setup>
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import AppLogo from './AppLogo.vue'

const props = defineProps({
  collapsed: {
    type: Boolean,
    default: false
  },
  activeMenu: {
    type: String,
    default: ''
  },
  menus: {
    type: Array,
    default: () => []
  }
})

const menus = computed(() => props.menus.map((item) => ({
  ...item,
  icon: ElementPlusIconsVue[item.icon] || ElementPlusIconsVue.Menu
})))
</script>

<style scoped lang="scss">
.app-sidebar {
  display: flex;
  flex-direction: column;
  width: 260px;
  border-right: none;
  background: linear-gradient(180deg, #1e1b4b 0%, #312e81 100%);
  transition: width 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 4px 0 24px rgba(0, 0, 0, 0.05);
  z-index: 100;
}

.app-sidebar.collapsed {
  width: 84px;
}

.sidebar-menu {
  border-right: 0;
  background: transparent;
  
  :deep(.el-menu-item) {
    color: rgba(255, 255, 255, 0.7);
    margin: 4px 12px;
    border-radius: 12px;
    height: 48px;
    line-height: 48px;
    transition: all 0.3s ease;
    
    &:hover {
      color: #ffffff;
      background: rgba(255, 255, 255, 0.05);
    }
    
    &.is-active {
      color: #60a5fa;
      background: rgba(59, 130, 246, 0.15);
      font-weight: 500;
      position: relative;
      
      &::before {
        content: '';
        position: absolute;
        left: -12px;
        top: 50%;
        transform: translateY(-50%);
        width: 4px;
        height: 24px;
        background: #3b82f6;
        border-radius: 0 4px 4px 0;
      }
    }
    
    .el-icon {
      font-size: 18px;
      margin-right: 12px;
      color: inherit;
    }
  }
}
</style>

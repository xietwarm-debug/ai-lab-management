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
  border-right: 1px solid var(--app-border);
  background: rgba(255, 255, 255, 0.88);
  backdrop-filter: blur(10px);
  transition: width 0.2s ease;
}

.app-sidebar.collapsed {
  width: 84px;
}

.sidebar-menu {
  border-right: 0;
  background: transparent;
}
</style>

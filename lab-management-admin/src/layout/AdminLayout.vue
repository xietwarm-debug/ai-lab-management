<template>
  <div class="admin-layout">
    <AppSidebar
      :collapsed="permissionStore.sidebarCollapsed"
      :active-menu="route.path"
      :menus="menus"
    />
    <div class="admin-main">
      <AppHeader
        :title="pageTitle"
        :subtitle="pageSubtitle"
        :username="authStore.username"
        :role-label="roleLabel"
        @toggle-sidebar="permissionStore.toggleSidebar()"
        @logout="handleLogout"
      />
      <main class="admin-content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup>
import { ElMessageBox } from 'element-plus'
import AppHeader from '@/components/layout/AppHeader.vue'
import AppSidebar from '@/components/layout/AppSidebar.vue'
import { useAuthStore } from '@/stores/auth'
import { usePermissionStore } from '@/stores/permission'
import { getRoleLabel } from '@/utils/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const permissionStore = usePermissionStore()

const menus = computed(() => permissionStore.menus(authStore.user))
const roleLabel = computed(() => getRoleLabel(authStore.role))
const pageTitle = computed(() => String(route.meta?.title || '管理后台'))
const pageSubtitle = computed(() => (
  authStore.role === 'teacher' ? '教师端仅展示当前后端已开放的管理能力' : ''
))

async function handleLogout() {
  try {
    await ElMessageBox.confirm('确认退出当前后台账号吗？', '退出登录', {
      type: 'warning'
    })
    await authStore.logout()
    router.replace('/login')
  } catch (error) {
    // cancelled by user
  }
}
</script>

<style scoped lang="scss">
.admin-layout {
  display: flex;
  min-height: 100vh;
}

.admin-main {
  display: flex;
  flex: 1;
  min-width: 0;
  flex-direction: column;
}

.admin-content {
  flex: 1;
  padding: 24px;
}

@media (max-width: 960px) {
  .admin-layout {
    flex-direction: column;
  }
}
</style>

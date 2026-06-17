<template>
  <div class="admin-layout">
    <Sidebar :collapsed="sidebarCollapsed" @toggle="toggleSidebar" />
    <div :class="['main-area', { expanded: sidebarCollapsed }]">
      <TopBar />
      <main class="main-content">
        <router-view v-slot="{ Component }">
          <transition name="page" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useAppStore } from '../stores/app'
import Sidebar from './Sidebar.vue'
import TopBar from './TopBar.vue'

const appStore = useAppStore()
const sidebarCollapsed = computed(() => appStore.sidebarCollapsed)

function toggleSidebar() {
  appStore.toggleSidebar()
}
</script>

<style scoped lang="scss">
.admin-layout {
  display: flex;
  height: 100%;
}

.main-area {
  margin-left: var(--sidebar-width);
  flex: 1;
  display: flex;
  flex-direction: column;
  transition: margin-left var(--transition-normal);
  min-width: 0;

  &.expanded {
    margin-left: var(--sidebar-collapsed);
  }
}

.main-content {
  flex: 1;
  padding: var(--spacing-lg);
  overflow-y: auto;
}
</style>

<template>
  <div id="app-layout">
    <el-container>
      <el-header class="app-header">
        <div class="header-left">
          <el-icon :size="24"><Monitor /></el-icon>
          <span class="header-title">Lounger Platform</span>
        </div>
        <div class="header-right">
          <el-menu
            mode="horizontal"
            :default-active="activeMenu"
            router
            background-color="transparent"
            text-color="#ddd"
            active-text-color="#fff"
          >
            <el-menu-item index="/projects">项目</el-menu-item>
          </el-menu>
        </div>
      </el-header>
      <el-main class="app-main">
        <router-view />
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const activeMenu = computed(() => {
  if (route.path.startsWith('/projects')) return '/projects'
  return '/projects'
})
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}
html, body {
  height: 100%;
  overflow: hidden;
}
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #f5f7fa;
}
#app-layout, #app-layout > .el-container {
  height: 100vh;
}
.app-header {
  background: #409eff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  flex-shrink: 0;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #fff;
}
.header-title {
  font-size: 18px;
  font-weight: 600;
  color: #fff;
}
.header-right .el-menu {
  border-bottom: none;
}
.header-right .el-menu-item {
  color: #ddd !important;
}
.header-right .el-menu-item.is-active {
  color: #fff !important;
  border-bottom-color: #fff !important;
}
.app-main {
  height: calc(100vh - 60px);
  padding: 20px;
  overflow: hidden;
}
</style>

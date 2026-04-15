<template>
  <el-container class="layout-container">
    <el-aside width="220px" class="sidebar">
      <div class="logo">
        <span class="logo-text">SnapSign 考勤系统</span>
      </div>

      <el-menu router :default-active="$route.path" class="el-menu-vertical" background-color="#304156"
        text-color="#bfcbd9" active-text-color="#409eff">
        <el-menu-item index="/">
          <el-icon>
            <Monitor />
          </el-icon>
          <span>考勤数据大屏</span>
        </el-menu-item>
        <el-menu-item index="/register">
          <el-icon>
            <Camera />
          </el-icon>
          <span>人脸特征录入</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <div class="header-left">
          <strong>基于人脸识别的课堂自动点名系统</strong>
        </div>
        <div class="header-right">
          <el-avatar size="small" src="https://cube.elemecdn.com/3/7c/3ea6beec64369c2642b92c6726f1epng.png" />
          <span class="admin-name">管理员 (天骏)</span>
        </div>
      </el-header>

      <el-main class="main-content">
        <router-view></router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
// 引入图标
import { Monitor, User, Camera } from '@element-plus/icons-vue'
</script>

<style>
/* 清除浏览器默认边距，让后台全屏铺满 */
html,
body,
#app {
  margin: 0;
  padding: 0;
  height: 100vh;
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

/* 布局外层全屏 */
.layout-container {
  height: 100vh;
}

/* 深色侧边栏样式 */
.sidebar {
  background-color: #304156;
  box-shadow: 2px 0 6px rgba(0, 21, 41, 0.35);
  z-index: 10;
}

/* Logo 区域 */
.logo {
  height: 60px;
  line-height: 60px;
  text-align: center;
  background-color: #2b3649;
  overflow: hidden;
}

.logo-text {
  color: #fff;
  font-size: 18px;
  font-weight: bold;
  letter-spacing: 1px;
}

/* 去除菜单自带的难看边框 */
.el-menu-vertical {
  border-right: none;
}

/* 顶部白条 Header */
.header {
  background-color: #fff;
  color: #333;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 1px 4px rgba(0, 21, 41, .08);
  padding: 0 20px;
  z-index: 9;
}

.header-right {
  display: flex;
  align-items: center;
  cursor: pointer;
}

.admin-name {
  margin-left: 10px;
  font-size: 14px;
  color: #606266;
}

/* 灰色主背景 */
.main-content {
  background-color: #f0f2f5;
  padding: 20px;
}

.card-header {
  font-weight: bold;
  font-size: 16px;
}

.card-body {
  color: #666;
  line-height: 1.8;
}
</style>
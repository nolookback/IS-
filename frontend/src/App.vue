<template>
  <el-container>
    <el-header style="background-color: #2d8cf0; color: white; font-size: 24px; text-align: center;">
      结合大模型的校园学术讲座信息检索系统
    </el-header>
    <el-main>
      <Search />
    </el-main>
  </el-container>
</template>
<script setup>
import Search from './components/Search.vue'
</script>
<style>
body {
  margin: 0;
  font-family: 'Helvetica Neue', Arial, sans-serif;
  background: #f5f7fa;
}
</style>

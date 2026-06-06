<template>
  <div class="not-found">
    <h1>404</h1>
    <p>页面不存在</p>
    <el-button type="primary" @click="goHome">返回首页</el-button>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()

const goHome = () => {
  router.push('/')
}
</script>

<style scoped>
.not-found {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background: #fff;
}

.not-found h1 {
  font-size: 72px;
  color: #409EFF;
  margin: 0;
}

.not-found p {
  font-size: 24px;
  color: #606266;
  margin: 20px 0;
}
</style>

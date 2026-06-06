<template>
  <div class="monitoring-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <div>
            <el-button type="default" @click="goBack" style="margin-right: 10px">
              <el-icon><ArrowLeft /></el-icon>
              返回
            </el-button>
            <span style="font-size: 18px; font-weight: 500">
              {{ serverInfo?.hostname }} ({{ serverInfo?.ip_address }}) - 监控数据
            </span>
          </div>
          <div style="display: flex; align-items: center; gap: 10px">
            <el-button type="primary" @click="handleRefresh" :loading="loading">
              <el-icon><Refresh /></el-icon>
              {{ countdown > 0 ? `刷新 (${countdown}s)` : '刷新' }}
            </el-button>
            <el-select v-model="duration" @change="loadData" style="width: 120px">
              <el-option label="30分钟" value="30m" />
              <el-option label="1小时" value="1h" />
              <el-option label="6小时" value="6h" />
              <el-option label="24小时" value="24h" />
              <el-option label="7天" value="7d" />
            </el-select>
          </div>
        </div>
      </template>

      <div v-if="!connected" class="not-connected">
        <el-empty description="该服务器未接入监控">
          <template #image>
            <el-icon :size="100" color="#909399"><WarningFilled /></el-icon>
          </template>
        </el-empty>
      </div>

      <div v-else v-loading="loading">
        <el-row :gutter="20">
          <el-col :span="24">
            <el-card class="chart-card">
              <template #header>
                <span>CPU使用率</span>
              </template>
              <div ref="cpuChartRef" style="height: 350px"></div>
            </el-card>
          </el-col>
        </el-row>
        <el-row :gutter="20" style="margin-top: 20px">
          <el-col :span="24">
            <el-card class="chart-card">
              <template #header>
                <span>内存使用率</span>
              </template>
              <div ref="memoryChartRef" style="height: 350px"></div>
            </el-card>
          </el-col>
        </el-row>
        <el-row :gutter="20" style="margin-top: 20px">
          <el-col :span="24">
            <el-card class="chart-card">
              <template #header>
                <span>磁盘使用率</span>
              </template>
              <div ref="diskChartRef" style="height: 350px"></div>
            </el-card>
          </el-col>
        </el-row>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getServer } from '@/api/servers'
import { getServerMonitoring } from '@/api/monitoring'
import * as echarts from 'echarts'

const route = useRoute()
const router = useRouter()

const serverId = ref(parseInt(route.params.id))
const serverInfo = ref(null)
const duration = ref('30m')
const loading = ref(false)
const connected = ref(true)

const cpuChartRef = ref(null)
const memoryChartRef = ref(null)
const diskChartRef = ref(null)
let cpuChart = null
let memoryChart = null
let diskChart = null
let autoRefreshTimer = null
let countdownTimer = null
const countdown = ref(60) // 倒计时秒数

const goBack = () => {
  router.push('/servers')
}

const loadServerInfo = async () => {
  try {
    const response = await getServer(serverId.value)
    serverInfo.value = response.data
  } catch (error) {
    ElMessage.error('获取服务器信息失败')
    goBack()
  }
}

const loadData = async () => {
  loading.value = true
  try {
    const response = await getServerMonitoring(serverId.value, { duration: duration.value })
    const data = response.data

    // 检查是否安装了node_exporter
    if (data.has_exporter === false || !data.cpu || data.cpu.length === 0) {
      connected.value = false
      stopAutoRefresh() // 未连接时停止自动刷新
      return
    }

    connected.value = true

    // 初始化图表
    await nextTick()
    if (!cpuChart && cpuChartRef.value) {
      cpuChart = echarts.init(cpuChartRef.value)
    }
    if (!memoryChart && memoryChartRef.value) {
      memoryChart = echarts.init(memoryChartRef.value)
    }
    if (!diskChart && diskChartRef.value) {
      diskChart = echarts.init(diskChartRef.value)
    }

    // 渲染图表（只在图表存在时）
    if (cpuChart) renderChart(cpuChart, 'CPU使用率', data.cpu || [])
    if (memoryChart) renderChart(memoryChart, '内存使用率', data.memory || [])
    if (diskChart) renderChart(diskChart, '磁盘使用率', data.disk || [])
  } catch (error) {
    console.error('获取监控数据失败:', error)
    connected.value = false
    stopAutoRefresh() // 出错时停止自动刷新
  } finally {
    loading.value = false
  }
}

const renderChart = (chart, title, data) => {
  if (!chart) return // 图表不存在时直接返回
  
  if (!data || data.length === 0) {
    const option = {
      title: {
        text: '暂无数据',
        left: 'center',
        top: 'center',
        textStyle: {
          color: '#999',
          fontSize: 14
        }
      }
    }
    try {
      chart.setOption(option)
    } catch (e) {
      console.error('Failed to set chart option:', e)
    }
    return
  }

  const option = {
    title: {
      show: false
    },
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const param = params[0]
        return `${param.axisValue}<br/>${param.marker}${param.seriesName}: ${param.value}%`
      }
    },
    xAxis: {
      type: 'category',
      data: data.map(item => {
        const date = new Date(item.timestamp)
        return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
      }),
      axisLabel: {
        rotate: 45
      }
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      axisLabel: {
        formatter: '{value}%'
      }
    },
    series: [{
      name: title,
      type: 'line',
      smooth: true,
      data: data.map(item => item.value),
      areaStyle: {
        opacity: 0.3
      }
    }],
    grid: {
      left: '3%',
      right: '4%',
      bottom: '15%',
      containLabel: true
    }
  }

  try {
    chart.setOption(option)
  } catch (e) {
    console.error('Failed to set chart option:', e)
  }
}

const startAutoRefresh = () => {
  stopAutoRefresh()
  countdown.value = 60
  
  // 倒计时定时器（每秒更新）
  countdownTimer = setInterval(() => {
    countdown.value--
    if (countdown.value <= 0) {
      loadData()
      countdown.value = 60
    }
  }, 1000)
}

const stopAutoRefresh = () => {
  if (autoRefreshTimer) {
    clearInterval(autoRefreshTimer)
    autoRefreshTimer = null
  }
  if (countdownTimer) {
    clearInterval(countdownTimer)
    countdownTimer = null
  }
}

const handleRefresh = () => {
  countdown.value = 60 // 重置倒计时
  loadData()
}

onMounted(async () => {
  await loadServerInfo()
  await loadData()
  startAutoRefresh()
})

onUnmounted(() => {
  stopAutoRefresh()
  if (cpuChart) {
    cpuChart.dispose()
    cpuChart = null
  }
  if (memoryChart) {
    memoryChart.dispose()
    memoryChart = null
  }
  if (diskChart) {
    diskChart.dispose()
    diskChart = null
  }
})
</script>

<style scoped>
.monitoring-container {
  padding: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chart-card {
  margin-bottom: 0;
}

.not-connected {
  padding: 60px 0;
  text-align: center;
}
</style>

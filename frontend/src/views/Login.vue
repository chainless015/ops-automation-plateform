<template>
  <div class="login-container">
    <canvas id="bg-canvas" class="bg-canvas"></canvas>
    <div class="noise-overlay"></div>
    
    <div class="login-content">
      <div class="left-panel">
        <div class="holo-ring">
          <div class="ring ring1">
            <div class="ring-dot rd1"></div>
            <div class="ring-dot rd2"></div>
          </div>
          <div class="ring ring2">
            <div class="ring-dot rd3"></div>
            <div class="ring-dot rd4"></div>
          </div>
          <div class="ring ring3"></div>
          <div class="ring ring4"></div>
          <div class="scan-line"></div>
          <div class="core">
            <div class="core-pulse"></div>
            <div class="core-icon">⚙</div>
          </div>
        </div>
        
        <div class="system-label">{{ appConfig.name }}</div>
        <div class="system-sub">OPS AUTOMATION PLATFORM</div>
      </div>
      
      <div class="right-panel">
        <div class="form-header">
          <div class="form-tag">SECURE ACCESS</div>
          <h2>系统登录</h2>
          <p>请完成身份验证以进入控制台</p>
        </div>
        
        <!-- 自定义通知 -->
        <transition name="notification-fade">
          <div v-if="notification.show" :class="['notification', `notification-${notification.type}`]">
            <div class="notification-icon">
              <span v-if="notification.type === 'error'">⚠</span>
              <span v-else-if="notification.type === 'success'">✓</span>
              <span v-else>ℹ</span>
            </div>
            <div class="notification-content">
              <div class="notification-message">{{ notification.message }}</div>
            </div>
            <div class="notification-close" @click="notification.show = false">×</div>
          </div>
        </transition>
        
        <form @submit.prevent="handleLogin">
          <div class="form-field">
            <label class="field-label">用户标识</label>
            <div class="input-wrapper">
              <el-icon class="field-icon"><User /></el-icon>
              <input
                v-model="loginForm.username"
                type="text"
                placeholder="USERNAME OR EMAIL"
                class="form-input"
              />
              <div class="input-scan"></div>
            </div>
          </div>
          
          <div class="form-field">
            <label class="field-label">访问密钥</label>
            <div class="input-wrapper">
              <el-icon class="field-icon"><Lock /></el-icon>
              <input
                v-model="loginForm.password"
                type="password"
                placeholder="PASSWORD"
                class="form-input"
              />
              <div class="input-scan"></div>
            </div>
          </div>
          
          <div class="form-field">
            <label class="field-label">验证码</label>
            <div class="input-wrapper" style="display: flex; gap: 10px;">
              <div style="position: relative; flex: 1;">
                <el-icon class="field-icon"><Key /></el-icon>
                <input
                  v-model="loginForm.captcha_code"
                  type="text"
                  placeholder="CAPTCHA"
                  class="form-input"
                  maxlength="4"
                  autocomplete="off"
                />
                <div class="input-scan"></div>
              </div>
              <div class="captcha-img-wrapper" @click="refreshCaptcha" title="点击刷新验证码">
                <img v-if="captchaImage" :src="captchaImage" alt="验证码" class="captcha-img" />
                <div v-else class="captcha-placeholder">加载中...</div>
              </div>
            </div>
          </div>
          
          <button type="submit" class="btn-login" :disabled="loading">
            <div class="btn-glow"></div>
            {{ loading ? 'AUTHENTICATING...' : 'Sign In' }}
          </button>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import { User, Lock, Key } from '@element-plus/icons-vue'
import { appConfig } from '@/config/app'
import { getCaptcha, login } from '@/api/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const loading = ref(false)
const captchaImage = ref('')
const captchaId = ref('')

const loginForm = reactive({
  username: '',
  password: '',
  captcha_code: ''
})

const notification = reactive({
  show: false,
  type: 'error',
  message: ''
})

const showNotification = (message, type = 'error', duration = 5000) => {
  notification.message = message
  notification.type = type
  notification.show = true
  if (duration > 0) {
    setTimeout(() => { notification.show = false }, duration)
  }
}

const refreshCaptcha = async () => {
  try {
    const res = await getCaptcha()
    captchaId.value = res.data.captcha_id
    captchaImage.value = res.data.image
    loginForm.captcha_code = ''
  } catch (e) {
    showNotification('验证码加载失败，请刷新页面', 'error')
  }
}

let animationId = null

const initCanvas = () => {
  const canvas = document.getElementById('bg-canvas')
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  const container = canvas.parentElement

  const resize = () => {
    const rect = container.getBoundingClientRect()
    canvas.width = rect.width
    canvas.height = rect.height
  }
  resize()
  window.addEventListener('resize', resize)

  const particles = []
  const colors = ['#00d4ff', '#0066ff', '#00ffaa']
  for (let i = 0; i < 80; i++) {
    particles.push({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      r: Math.random() * 1.5 + 0.3,
      vx: (Math.random() - 0.5) * 0.3,
      vy: (Math.random() - 0.5) * 0.3,
      c: colors[Math.floor(Math.random() * colors.length)],
      o: Math.random() * 0.5 + 0.1
    })
  }

  const animate = () => {
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    ctx.strokeStyle = '#0a2a4a18'
    ctx.lineWidth = 0.5
    const gridSize = 60
    for (let x = 0; x < canvas.width; x += gridSize) {
      ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, canvas.height); ctx.stroke()
    }
    for (let y = 0; y < canvas.height; y += gridSize) {
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(canvas.width, y); ctx.stroke()
    }
    particles.forEach((p, i) => {
      p.x += p.vx; p.y += p.vy
      if (p.x < 0) p.x = canvas.width
      if (p.x > canvas.width) p.x = 0
      if (p.y < 0) p.y = canvas.height
      if (p.y > canvas.height) p.y = 0
      for (let j = i + 1; j < particles.length; j++) {
        const dx = particles[j].x - p.x, dy = particles[j].y - p.y
        const dist = Math.sqrt(dx * dx + dy * dy)
        if (dist < 90) {
          ctx.strokeStyle = p.c
          ctx.globalAlpha = (1 - dist / 90) * 0.12
          ctx.lineWidth = 0.5
          ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(particles[j].x, particles[j].y); ctx.stroke()
          ctx.globalAlpha = 1
        }
      }
      ctx.fillStyle = p.c; ctx.globalAlpha = p.o
      ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2); ctx.fill()
      ctx.globalAlpha = 1
    })
    animationId = requestAnimationFrame(animate)
  }
  animate()

  return () => {
    window.removeEventListener('resize', resize)
    if (animationId) cancelAnimationFrame(animationId)
  }
}

const handleLogin = async () => {
  if (!loginForm.username || !loginForm.password || !loginForm.captcha_code) {
    showNotification('请填写用户名、密码和验证码', 'error')
    return
  }

  loading.value = true
  try {
    const response = await login({
      username: loginForm.username,
      password: loginForm.password,
      captcha_id: captchaId.value,
      captcha_code: loginForm.captcha_code
    })

    authStore.setToken(response.data.access_token)
    authStore.setUser(response.data.user)

    showNotification('登录成功', 'success', 1500)
    setTimeout(() => {
      const redirect = route.query.redirect || '/dashboard'
      router.push(redirect)
    }, 2000)
  } catch (error) {
    showNotification(error.response?.data?.detail || '登录失败', 'error')
    // 登录失败后刷新验证码
    refreshCaptcha()
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  const cleanup = initCanvas()
  refreshCaptcha()

  onUnmounted(() => {
    if (cleanup) cleanup()
  })
})
</script>

<style scoped>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
  min-width: var(--app-min-width);
  height: 100vh;
  height: 100dvh;
  background: #020b18;
  position: relative;
  overflow: hidden;
  font-family: 'Noto Sans SC', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

.bg-canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  z-index: 0;
}

.noise-overlay {
  position: absolute;
  inset: 0;
  z-index: 1;
  pointer-events: none;
  opacity: 0.025;
  background-image: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><filter id="noise"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="4" result="noise"/></filter><rect width="100" height="100" fill="white" filter="url(%23noise)"/></svg>');
}

.login-content {
  display: flex;
  width: 90%;
  max-width: 1400px;
  height: 80vh;
  height: 80dvh;
  max-height: 800px;
  position: relative;
  z-index: 2;
  gap: 60px;
}

.left-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  padding: 40px;
}

.holo-ring {
  position: relative;
  width: 280px;
  height: 280px;
  margin-bottom: 60px;
}

.ring {
  position: absolute;
  border-radius: 50%;
  border: 1px solid transparent;
  animation: spin var(--s) linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@keyframes spinr {
  to {
    transform: rotate(-360deg);
  }
}

.ring1 {
  inset: 0;
  border-top-color: #00d4ff;
  border-right-color: #00d4ff20;
  --s: 4s;
}

.ring2 {
  inset: 20px;
  border-top-color: #0066ff40;
  border-left-color: #0066ff;
  --s: 7s;
  animation-name: spinr;
}

.ring3 {
  inset: 40px;
  border-top-color: #00ffaa;
  border-bottom-color: #00ffaa30;
  --s: 5.5s;
}

.ring4 {
  inset: 60px;
  border-right-color: #00d4ff30;
  border-bottom-color: #00d4ff;
  --s: 9s;
  animation-name: spinr;
}

.ring-dot {
  position: absolute;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #00d4ff;
  box-shadow: 0 0 12px #00d4ff;
}

.rd1 {
  top: -4px;
  left: 50%;
  transform: translateX(-50%);
}

.rd2 {
  bottom: -4px;
  left: 50%;
  transform: translateX(-50%);
}

.rd3 {
  left: -4px;
  top: 50%;
  transform: translateY(-50%);
}

.rd4 {
  right: -4px;
  top: 50%;
  transform: translateY(-50%);
}

.scan-line {
  position: absolute;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, #00d4ff60, #00d4ff, #00d4ff60, transparent);
  animation: scan 3s ease-in-out infinite;
  top: 0;
}

@keyframes scan {
  0% {
    top: 60px;
    opacity: 1;
  }
  80% {
    opacity: 1;
  }
  100% {
    top: calc(100% - 60px);
    opacity: 0;
  }
}

.core {
  position: absolute;
  inset: 80px;
  border-radius: 50%;
  background: radial-gradient(circle at 40% 35%, #0a2a4a, #020b18);
  border: 1px solid #00d4ff30;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.core-pulse {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  background: radial-gradient(circle, #00d4ff08 0%, transparent 70%);
  animation: pulse 2.5s ease-in-out infinite;
}

@keyframes pulse {
  0%,
  100% {
    transform: scale(1);
    opacity: 0.5;
  }
  50% {
    transform: scale(1.15);
    opacity: 1;
  }
}

.core-icon {
  font-size: 48px;
  color: #00d4ff;
  position: relative;
  z-index: 1;
  animation: iconpulse 2.5s ease-in-out infinite;
}

@keyframes iconpulse {
  0%,
  100% {
    opacity: 0.7;
  }
  50% {
    opacity: 1;
  }
}

.system-label {
  font-size: 32px;
  font-weight: 600;
  color: #e0f4ff;
  letter-spacing: 6px;
  text-transform: uppercase;
  margin-bottom: 8px;
  text-shadow: 0 0 20px rgba(0, 212, 255, 0.4);
}

.system-sub {
  font-family: 'Courier New', monospace;
  font-size: 13px;
  color: #1a5a7a;
  letter-spacing: 3px;
}

.right-panel {
  flex: 0.8;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 60px 40px;
  position: relative;
}

.form-header {
  margin-bottom: 40px;
}

.form-tag {
  font-family: 'Courier New', monospace;
  font-size: 13px;
  color: #00d4ff80;
  letter-spacing: 3px;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.form-tag::before {
  content: '';
  width: 24px;
  height: 1px;
  background: #00d4ff60;
}

.form-header h2 {
  font-size: 40px;
  font-weight: 600;
  color: #e0f4ff;
  letter-spacing: 2px;
  margin-bottom: 6px;
}

.form-header p {
  color: #1a5a7a;
  font-size: 15px;
  letter-spacing: 1px;
}

.form-field {
  margin-bottom: 20px;
  position: relative;
}

.field-label {
  font-family: 'Courier New', monospace;
  font-size: 12px;
  color: #1a6a8a;
  letter-spacing: 2.5px;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.field-label::before {
  content: '//';
  color: #00d4ff40;
}

.input-wrapper {
  position: relative;
}

.field-icon {
  position: absolute;
  left: 14px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 16px;
  color: #1a5a7a;
  transition: color 0.2s;
  z-index: 1;
}

.form-input {
  width: 100%;
  background: #020f1e;
  border: 1px solid #0a3a5a;
  border-radius: 6px;
  color: #a0d4f0;
  font-family: 'Courier New', monospace;
  font-size: 16px;
  padding: 13px 14px 13px 42px;
  outline: none;
  transition: border-color 0.25s, background 0.25s, box-shadow 0.25s;
  letter-spacing: 1px;
}

.form-input::placeholder {
  color: #0a3a5a;
  font-size: 15px;
}

.form-input:focus {
  border-color: #00d4ff60;
  background: #030d1a;
  box-shadow: 0 0 0 1px #00d4ff15, inset 0 0 20px #00d4ff05;
}

.form-input:focus ~ .field-icon {
  color: #00d4ff;
}

.input-scan {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 0;
  height: 1px;
  background: linear-gradient(90deg, #00d4ff, #00ffaa);
  transition: width 0.4s ease;
  border-radius: 0 0 6px 6px;
}

.form-input:focus ~ .input-scan {
  width: 100%;
}

.btn-login {
  width: 100%;
  position: relative;
  background: transparent;
  border: 1px solid #00d4ff40;
  border-radius: 6px;
  color: #00d4ff;
  font-family: 'Rajdhani', sans-serif;
  font-size: 18px;
  font-weight: 600;
  letter-spacing: 6px;
  padding: 15px;
  cursor: pointer;
  overflow: hidden;
  transition: border-color 0.3s, color 0.3s;
  text-transform: uppercase;
}

.btn-login::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, #00d4ff08, #0066ff08);
  opacity: 0;
  transition: opacity 0.3s;
}

.btn-login:hover:not(:disabled) {
  border-color: #00d4ff90;
  color: #e0f4ff;
}

.btn-login:hover:not(:disabled)::before {
  opacity: 1;
}

.btn-login:active:not(:disabled) {
  transform: scale(0.99);
}

.btn-login:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.btn-glow {
  position: absolute;
  top: 0;
  left: -100%;
  width: 60%;
  height: 100%;
  background: linear-gradient(90deg, transparent, #00d4ff15, transparent);
  animation: btnshine 3s ease-in-out infinite 1s;
}

@keyframes btnshine {
  0% {
    left: -100%;
  }
  50%,
  100% {
    left: 200%;
  }
}

.captcha-img-wrapper {
  flex-shrink: 0;
  width: 120px;
  height: 46px;
  border: 1px solid #0a3a5a;
  border-radius: 6px;
  overflow: hidden;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #020f1e;
  transition: border-color 0.2s;
}

.captcha-img-wrapper:hover {
  border-color: #00d4ff40;
}

.captcha-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.captcha-placeholder {
  font-family: 'Courier New', monospace;
  font-size: 11px;
  color: #1a5a7a;
  letter-spacing: 1px;
}

.notification-fade-enter-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}

.notification-fade-leave-active {
  transition: opacity 0.4s ease, transform 0.4s ease;
}

.notification-fade-enter-from {
  opacity: 0;
  transform: translateY(-10px);
}

.notification-fade-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

.notification {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  margin-bottom: 16px;
  border-radius: 6px;
  border: 1px solid;
  background: transparent;
  font-family: 'Courier New', monospace;
  font-size: 14px;
}

.notification-error {
  border-color: #ff4d4f40;
  background: #ff4d4f08;
  color: #ff7875;
}

.notification-success {
  border-color: #52c41a40;
  background: #52c41a08;
  color: #95de64;
}

.notification-info {
  border-color: #1890ff40;
  background: #1890ff08;
  color: #69b1ff;
}

.notification-icon {
  font-size: 16px;
  font-weight: bold;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
}

.notification-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.notification-message {
  line-height: 1.4;
  letter-spacing: 0.5px;
}

.notification-close {
  font-size: 18px;
  cursor: pointer;
  opacity: 0.6;
  transition: opacity 0.2s;
  flex-shrink: 0;
}

.notification-close:hover {
  opacity: 1;
}

@media (max-width: 1024px) {
  .login-content {
    flex-direction: column;
    gap: 40px;
    height: auto;
    max-height: none;
  }

  .left-panel {
    padding: 30px 20px;
  }

  .right-panel {
    padding: 30px 20px;
  }

  .holo-ring {
    width: 200px;
    height: 200px;
    margin-bottom: 30px;
  }

  .core-icon {
    font-size: 36px;
  }

  .form-header h2 {
    font-size: 24px;
  }
}
</style>

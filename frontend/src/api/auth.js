import request from '@/utils/axios'

export const getCaptcha = () =>
  request.get('/api/auth/captcha')

export const login = (data) =>
  request.post('/api/auth/login', data)

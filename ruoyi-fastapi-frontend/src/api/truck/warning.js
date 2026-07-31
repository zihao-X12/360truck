import request from '@/utils/request'

export function listWarning(query) {
  return request({ url: '/truck/warning/list', method: 'get', params: query })
}

export function recalculateWarning() {
  return request({ url: '/truck/warning/recalculate', method: 'post' })
}

import request from '@/utils/request'

export function getDashboardSummary() {
  return request({ url: '/truck/dashboard/summary', method: 'get' })
}

export function getDashboardDeptStat() {
  return request({ url: '/truck/dashboard/dept-stat', method: 'get' })
}

export function getDashboardDeviceCoverage() {
  return request({ url: '/truck/dashboard/device-coverage', method: 'get' })
}

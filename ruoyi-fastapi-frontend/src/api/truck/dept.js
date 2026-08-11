import request from '@/utils/request'

export function listTruckDeptOptions() {
  return request({ url: '/truck/vehicle/dept-options', method: 'get' })
}

import request from '@/utils/request'

export function listVehicle(query) {
  return request({ url: '/truck/vehicle/list', method: 'get', params: query })
}

export function getVehicle(vehicleId) {
  return request({ url: '/truck/vehicle/' + vehicleId, method: 'get' })
}

export function addVehicle(data) {
  return request({ url: '/truck/vehicle', method: 'post', data })
}

export function updateVehicle(data) {
  return request({ url: '/truck/vehicle', method: 'put', data })
}

export function delVehicle(vehicleIds) {
  return request({ url: '/truck/vehicle/' + vehicleIds, method: 'delete' })
}

export function importVehicle(file) {
  const data = new FormData()
  data.append('file', file)
  return request({
    url: '/truck/vehicle/import',
    method: 'post',
    headers: { 'Content-Type': 'multipart/form-data', repeatSubmit: false },
    timeout: 30000,
    data
  })
}

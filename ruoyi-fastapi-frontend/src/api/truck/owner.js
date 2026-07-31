import request from '@/utils/request'

export function listOwner(query) {
  return request({ url: '/truck/owner/list', method: 'get', params: query })
}

export function getOwner(ownerId) {
  return request({ url: '/truck/owner/' + ownerId, method: 'get' })
}

export function addOwner(data) {
  return request({ url: '/truck/owner', method: 'post', data })
}

export function updateOwner(data) {
  return request({ url: '/truck/owner', method: 'put', data })
}

export function delOwner(ownerIds) {
  return request({ url: '/truck/owner/' + ownerIds, method: 'delete' })
}

import request from '@/utils/request'

export function listPassRecord(query) {
  return request({ url: '/truck/passrecord/list', method: 'get', params: query })
}

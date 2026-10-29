import request from '@/utils/request'

export function getGat1400Config() {
  return request({ url: '/gat1400/config', method: 'get' })
}

export function saveGat1400Config(data) {
  return request({ url: '/gat1400/config', method: 'put', data })
}

export function getGat1400Status() {
  return request({ url: '/gat1400/connect/status', method: 'get' })
}

export function gat1400Register() {
  return request({ url: '/gat1400/connect/register', method: 'post' })
}

export function gat1400Keepalive() {
  return request({ url: '/gat1400/connect/keepalive', method: 'post' })
}

export function gat1400Unregister() {
  return request({ url: '/gat1400/connect/unregister', method: 'post' })
}

export function listSubscribe() {
  return request({ url: '/gat1400/subscribe/list', method: 'get' })
}

export function createSubscribe() {
  return request({ url: '/gat1400/subscribe/create', method: 'post' })
}

export function cancelSubscribe(subscribeId) {
  return request({ url: `/gat1400/subscribe/cancel/${subscribeId}`, method: 'put' })
}

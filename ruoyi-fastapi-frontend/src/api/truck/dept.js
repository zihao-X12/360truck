import request from '@/utils/request'

export const TRUCK_BRIGADE_DEPT_ID = 9100

export function listTruckDeptOptions() {
  return request({ url: '/truck/vehicle/dept-options', method: 'get' })
}

/**
 * 过滤掉大队节点，只保留可实际分管车辆的中队。
 *
 * 接口会连同大队节点一起返回以保证 handleTree 能正确组装层级，
 * 但大队本身不承担车辆分管，因此不能作为可选项。
 * 大队可能位于树的任意层级，故需要递归下钻；其子节点提升为顶层，
 * 避免树形选择器出现唯一的「松阳大队」根节点导致无法直接选中队。
 *
 * @param {Array} tree 部门选项树
 * @returns {Array} 仅包含中队的节点列表
 */
export function filterTruckSquads(tree) {
  const result = []
  const walk = nodes => {
    for (const node of nodes || []) {
      const children = node.children || []
      if (node.deptId === TRUCK_BRIGADE_DEPT_ID) {
        walk(children)
      } else {
        result.push({ ...node, children: filterTruckSquads(children) })
      }
    }
  }
  walk(tree)
  return result
}


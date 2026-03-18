import request from '@/utils/request'

export function getOperationsBoard() {
  return request.get('/stats/operations-board')
}

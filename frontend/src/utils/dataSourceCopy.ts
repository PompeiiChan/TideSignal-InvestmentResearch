import type { DataSourceStatus } from '../types/api'

type DataSourceItem = DataSourceStatus['mock_data'][number]

const STATUS_LABEL: Record<DataSourceItem['status'], string> = {
  ready: '已就位',
  mocked: '模拟',
  missing: '未就位',
}

export function formatDataSourceStatus(status: DataSourceItem['status']): string {
  return STATUS_LABEL[status] ?? status
}

export function getDataSourceSummary(item: DataSourceItem): string {
  switch (item.type) {
    case 'market':
      return `问数链路实时调用东财 push2 行情接口；路径：${item.path}。`
    case 'financial':
      return `问股与 RAG 共用的本地财报 Markdown（含新浪 API 入库创业板批次）；路径：${item.path}。`
    case 'report':
      return `公司与行业研报 Markdown，供 RAG 检索引用；路径：${item.path}。`
    case 'announcement':
      return `证据补数阶段按需调用巨潮公告与东财快讯 API；路径：${item.path}。`
    case 'knowledge':
      return `本地 Markdown 知识库（热点 / 财报 / 研报 / 结构化清单）；路径：${item.path}。`
    default:
      return `路径：${item.path}。`
  }
}

export function formatSampleCount(item: DataSourceItem): string {
  if (item.type === 'announcement' || item.type === 'market') {
    return '按需在线拉取'
  }
  return `${item.sample_count} 份 Markdown`
}

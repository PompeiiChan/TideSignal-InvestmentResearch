import { useInvestmentStore } from '../stores/useInvestmentStore'
import {
  formatDataSourceStatus,
  formatSampleCount,
  getDataSourceSummary,
} from '../utils/dataSourceCopy'

export function DataPage() {
  const dataSources = useInvestmentStore((state) => state.dataSources)

  return (
    <section className="data-view">
      <div className="view-grid">
        {!dataSources ? <div className="info-card full-row">状态读取中</div> : null}
        {dataSources?.mock_data.map((item) => (
          <div key={item.type} className="info-card">
            <h3>{item.name}</h3>
            <p>{getDataSourceSummary(item)}</p>
            <ul>
              <li>状态：{formatDataSourceStatus(item.status)}</li>
              <li>样本数量：{formatSampleCount(item)}</li>
            </ul>
          </div>
        ))}
        <div className="info-card full-row">
          <h3>RAG 状态</h3>
          <p>
            已接入本地 Markdown 混合检索（BM25 预筛 + Embedding 向量检索 + Rerank 重排），索引缓存于知识库
            `.index/`。
          </p>
          <ul>
            <li>模式：{dataSources?.rag.mode === 'semantic' ? '语义检索' : '降级 Mock'}</li>
            <li>Embedding：{dataSources?.rag.embedding_provider ?? '未配置'}</li>
            <li>Rerank：{dataSources?.rag.rerank_provider ?? '未配置'}</li>
            <li>状态：{dataSources?.rag.status === 'ready' ? '已就位' : '未就绪'}</li>
            {dataSources?.rag.indexed_files ? (
              <li>已索引文档：{dataSources.rag.indexed_files} 份 Markdown</li>
            ) : null}
            {dataSources?.rag.chunk_count ? <li>索引分块：{dataSources.rag.chunk_count}</li> : null}
          </ul>
        </div>
      </div>
    </section>
  )
}

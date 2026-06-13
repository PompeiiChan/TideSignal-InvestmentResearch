import { useInvestmentStore } from '../stores/useInvestmentStore'

export function DataPage() {
  const dataSources = useInvestmentStore((state) => state.dataSources)

  return (
    <section className="data-view">
      <div className="view-grid">
        {!dataSources ? <div className="info-card full-row">状态读取中</div> : null}
        {dataSources?.mock_data.map((item) => (
          <div key={item.type} className="info-card">
            <h3>{item.name}</h3>
            <p>当前为本地模拟数据，路径：{item.path}。</p>
            <ul>
              <li>状态：{item.status}</li>
              <li>样本数量：{item.sample_count}</li>
            </ul>
          </div>
        ))}
        <div className="info-card full-row">
          <h3>RAG 状态</h3>
          <p>
            当前阶段先展示模拟命中结果；后续接入本地 Markdown 检索和硅基流动千问 Embedding / Rerank。
          </p>
          <ul>
            <li>模式：{dataSources?.rag.mode ?? 'mock'}</li>
            <li>Embedding：{dataSources?.rag.embedding_provider ?? 'siliconflow-qwen'}</li>
            <li>Rerank：{dataSources?.rag.rerank_provider ?? 'siliconflow-qwen'}</li>
            <li>状态：{dataSources?.rag.status ?? 'mocked'}</li>
          </ul>
        </div>
      </div>
    </section>
  )
}

import { useInvestmentStore, type AppView } from '../stores/useInvestmentStore'

const titles: Record<AppView, string> = {
  chat: '客户端对话页',
  data: '本地知识库 / 模拟数据说明',
  settings: '系统设置',
}

export function Topbar() {
  const mode = useInvestmentStore((state) => state.mode)
  const view = useInvestmentStore((state) => state.view)
  const setView = useInvestmentStore((state) => state.setView)
  const title = view === 'chat' && mode === 'admin' ? '管理端可观测页' : titles[view]
  const subtitle =
    view === 'chat'
      ? mode === 'admin'
        ? '同一会话基础上展示右侧 Trace 链路。'
        : '低噪音投研问答，回答包含来源、数据时间和风险提示。'
      : view === 'data'
        ? '说明当前本地数据、模拟工具和 RAG 命中状态。'
        : '展示模型、Prompt 和合规规则配置状态。'

  const navItems: Array<{ key: AppView; label: string }> = [
    { key: 'chat', label: '对话' },
    { key: 'data', label: '数据说明' },
  ]
  if (mode === 'admin') navItems.push({ key: 'settings', label: '系统设置' })

  return (
    <header className="topbar">
      <div className="page-title">
        <h1>{title}</h1>
        <p>{subtitle}</p>
      </div>
      <div className="top-actions">
        {navItems.map((item) => (
          <button key={item.key} className={`nav-button ${view === item.key ? 'active' : ''}`} type="button" onClick={() => setView(item.key)}>
            {item.label}
          </button>
        ))}
      </div>
    </header>
  )
}

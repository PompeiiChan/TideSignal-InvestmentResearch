import { useInvestmentStore, type AppView } from '../stores/useInvestmentStore'
import { useEmptyClientChat } from '../hooks/useEmptyClientChat'

const titles: Record<AppView, string> = {
  chat: '投研对话',
  data: '本地数据与 RAG 说明',
  settings: '系统设置',
}

export function Topbar() {
  const mode = useInvestmentStore((state) => state.mode)
  const view = useInvestmentStore((state) => state.view)
  const setView = useInvestmentStore((state) => state.setView)
  const isEmptyClientChat = useEmptyClientChat()
  const title = view === 'chat' && mode === 'admin' ? '管理端可观测页' : titles[view]
  const subtitle =
    view === 'chat'
      ? mode === 'admin'
        ? '同一会话基础上展示右侧 Trace 链路。'
        : '回答有来源，数据有时间，判断有边界。'
      : view === 'data'
        ? '展示知识库、问数 Mock 表、工具数据源与 RAG 索引状态。'
        : '展示模型、Prompt 和合规规则配置状态。'

  const navItems: Array<{ key: AppView; label: string }> =
    mode === 'admin'
      ? [
          { key: 'chat', label: '对话' },
          { key: 'data', label: '数据说明' },
          { key: 'settings', label: '系统设置' },
        ]
      : []

  return (
    <header className={`topbar${isEmptyClientChat ? ' topbar--chat-empty' : ''}`}>
      <div className="page-title">
        <h1>{isEmptyClientChat ? '对话' : title}</h1>
        {!isEmptyClientChat ? <p>{subtitle}</p> : null}
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

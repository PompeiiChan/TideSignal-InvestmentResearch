import { useRef, useState } from 'react'
import type { PointerEvent } from 'react'
import logoIcon from '../assets/logo-icon.png'
import { useInvestmentStore, type ViewMode } from '../stores/useInvestmentStore'
import { richBlockTypeLabels } from '../utils/richBlockLabels'

export function Sidebar() {
  const handleRef = useRef<HTMLDivElement | null>(null)
  const [openMenuId, setOpenMenuId] = useState<string | null>(null)
  const mode = useInvestmentStore((state) => state.mode)
  const sessions = useInvestmentStore((state) => state.sessions)
  const activeSessionId = useInvestmentStore((state) => state.activeSessionId)
  const searchKeyword = useInvestmentStore((state) => state.searchKeyword)
  const setMode = useInvestmentStore((state) => state.setMode)
  const setSearchKeyword = useInvestmentStore((state) => state.setSearchKeyword)
  const createSession = useInvestmentStore((state) => state.createSession)
  const selectSession = useInvestmentStore((state) => state.selectSession)
  const deleteSession = useInvestmentStore((state) => state.deleteSession)
  const setSidebarWidth = useInvestmentStore((state) => state.setSidebarWidth)
  const persistLayout = useInvestmentStore((state) => state.persistLayout)
  const pendingQuery = useInvestmentStore((state) => state.pendingQuery)

  const startResize = (event: PointerEvent<HTMLDivElement>) => {
    const handle = handleRef.current
    if (!handle) return
    event.preventDefault()
    document.body.classList.add('is-resizing')
    handle.setPointerCapture(event.pointerId)
    const onMove = (moveEvent: PointerEvent) => {
      setSidebarWidth(moveEvent.clientX)
    }
    const onUp = () => {
      document.body.classList.remove('is-resizing')
      void persistLayout()
      window.removeEventListener('pointermove', onMove)
      window.removeEventListener('pointerup', onUp)
      window.removeEventListener('pointercancel', onUp)
    }
    window.addEventListener('pointermove', onMove)
    window.addEventListener('pointerup', onUp)
    window.addEventListener('pointercancel', onUp)
  }

  return (
    <aside className="sidebar">
      <div ref={handleRef} className="resize-handle" title="拖拽调整历史列宽" onPointerDown={startResize} />
      <div className="brand">
        <div className="brand-name">
          <img className="brand-mark" src={logoIcon} alt="" width={28} height={28} />
          <span className="brand-title">
            <span className="brand-text-cn">潮声</span>
            <span className="brand-sep" aria-hidden="true" />
            <span className="brand-text-en">TideSignal</span>
          </span>
        </div>
      </div>

      <div className="sidebar-actions">
        <button className="new-chat" type="button" onClick={() => void createSession(mode)}>
          <span className="new-plus">＋</span>
          <span>新建会话</span>
        </button>
        <label className="search-wrap" htmlFor="historySearch">
          <span>⌕</span>
          <input
            id="historySearch"
            type="search"
            placeholder="搜索历史问题"
            value={searchKeyword}
            onInput={(event) => void setSearchKeyword(event.currentTarget.value)}
            autoComplete="off"
          />
        </label>
      </div>

      <div className="chat-list">
        <div className="chat-date">今天</div>
        {sessions.length === 0 ? (
          <div className="empty-history">没有匹配的历史问题</div>
        ) : (
          sessions.map((session) => {
            const isMenuOpen = openMenuId === session.id
            const richBlockLabels = richBlockTypeLabels(session.rich_block_types)
            return (
              <div
                key={session.id}
                className={`chat-row ${session.id === activeSessionId ? 'active' : ''}`}
                onClick={() => {
                  setOpenMenuId(null)
                  void selectSession(session.id)
                }}
              >
                <button
                  className="chat-row-main"
                  type="button"
                  onClick={(event) => {
                    event.stopPropagation()
                    setOpenMenuId(null)
                    void selectSession(session.id)
                  }}
                >
                  <span className="chat-title">{session.title}</span>
                  <span className="chat-meta-row">
                    <span className="chat-meta">{session.updated_at.slice(11, 16)}</span>
                    {richBlockLabels.length > 0 ? (
                      <span className="chat-rich-pills" aria-label="副组件">
                        {richBlockLabels.map((label) => (
                          <span key={label} className="chat-showcase-pill" title={`副组件：${label}`}>
                            {label}
                          </span>
                        ))}
                      </span>
                    ) : null}
                    {pendingQuery?.sessionId === session.id ? (
                      <span className="chat-generating" title="回答生成中">
                        生成中
                      </span>
                    ) : null}
                  </span>
                </button>
                <div className="chat-menu" onClick={(event) => event.stopPropagation()}>
                  <button
                    className="chat-more"
                    type="button"
                    title="更多操作"
                    aria-label={`更多操作：${session.title}`}
                    aria-expanded={isMenuOpen}
                    onClick={(event) => {
                      event.stopPropagation()
                      setOpenMenuId(isMenuOpen ? null : session.id)
                    }}
                  >
                    ⋯
                  </button>
                  {isMenuOpen ? (
                    <div className="chat-menu-popover" role="menu">
                      <button
                        className="chat-menu-item danger"
                        type="button"
                        role="menuitem"
                        onClick={(event) => {
                          event.stopPropagation()
                          setOpenMenuId(null)
                          void deleteSession(session.id)
                        }}
                      >
                        删除
                      </button>
                    </div>
                  ) : null}
                </div>
              </div>
            )
          })
        )}
      </div>

      <div className="view-tabs">
        {(['client', 'admin'] as ViewMode[]).map((item) => (
          <button key={item} className={`tab ${mode === item ? 'active' : ''}`} type="button" onClick={() => setMode(item)}>
            {item === 'client' ? '客户端' : '管理端'}
          </button>
        ))}
      </div>
    </aside>
  )
}

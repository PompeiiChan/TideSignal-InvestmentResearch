import { useEffect } from 'react'
import type { CSSProperties } from 'react'
import { useNavigate } from 'react-router-dom'
import { ChatView } from '../components/ChatView'
import { DataPage } from '../components/DataPage'
import { JsonModal } from '../components/JsonModal'
import { SettingsPage } from '../components/SettingsPage'
import { Sidebar } from '../components/Sidebar'
import { Topbar } from '../components/Topbar'
import { TracePanel } from '../components/TracePanel'
import { useEmptyClientChat } from '../hooks/useEmptyClientChat'
import { useInvestmentStore, type AppView, type ViewMode } from '../stores/useInvestmentStore'

interface WorkspacePageProps {
  initialMode: ViewMode
  initialView: AppView
}

export function WorkspacePage({ initialMode, initialView }: WorkspacePageProps) {
  const navigate = useNavigate()
  const initialize = useInvestmentStore((state) => state.initialize)
  const mode = useInvestmentStore((state) => state.mode)
  const view = useInvestmentStore((state) => state.view)
  const initialized = useInvestmentStore((state) => state.initialized)
  const loadDataSources = useInvestmentStore((state) => state.loadDataSources)
  const loadConfigStatus = useInvestmentStore((state) => state.loadConfigStatus)
  const sidebarWidth = useInvestmentStore((state) => state.sidebarWidth)
  const tracePanelWidth = useInvestmentStore((state) => state.tracePanelWidth)
  const isEmptyClientChat = useEmptyClientChat()

  useEffect(() => {
    void initialize(initialMode, initialView)
  }, [initialize, initialMode, initialView])

  useEffect(() => {
    if (!initialized) return
    const path = view === 'chat' ? `/${mode}` : `/${mode}/${view}`
    navigate(path, { replace: true })
  }, [initialized, mode, navigate, view])

  useEffect(() => {
    if (!initialized) return
    if (mode === 'admin' && view === 'data') void loadDataSources()
    if (mode === 'admin' && view === 'settings') void loadConfigStatus()
  }, [initialized, loadConfigStatus, loadDataSources, mode, view])

  return (
    <main
      className={`app ${mode === 'admin' ? 'admin-mode' : ''}`}
      style={
        {
          '--sidebar-width': `${sidebarWidth}px`,
          '--trace-width': `${tracePanelWidth}px`,
        } as CSSProperties
      }
    >
      <Sidebar />
      <section className={`workspace${isEmptyClientChat ? ' workspace--chat-empty' : ''}`}>
        <Topbar />
        <div className="content">
          {view === 'chat' && <ChatView />}
          {mode === 'admin' && view === 'data' && <DataPage />}
          {view === 'settings' && <SettingsPage />}
        </div>
      </section>
      {mode === 'admin' && <TracePanel />}
      <JsonModal />
    </main>
  )
}

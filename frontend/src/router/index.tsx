import { Navigate, createBrowserRouter } from 'react-router-dom'
import { WorkspacePage } from '../pages/WorkspacePage'

export const router = createBrowserRouter([
  { path: '/', element: <Navigate to="/client" replace /> },
  { path: '/client', element: <WorkspacePage initialMode="client" initialView="chat" /> },
  { path: '/client/data', element: <Navigate to="/client" replace /> },
  { path: '/admin', element: <WorkspacePage initialMode="admin" initialView="chat" /> },
  { path: '/admin/data', element: <WorkspacePage initialMode="admin" initialView="data" /> },
  { path: '/admin/settings', element: <WorkspacePage initialMode="admin" initialView="settings" /> },
  { path: '*', element: <Navigate to="/client" replace /> },
])

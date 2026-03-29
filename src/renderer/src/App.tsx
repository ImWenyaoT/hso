import { useState } from 'react'
import ResearchInputPage from './pages/ResearchInputPage'
import ResearchCardPage from './pages/ResearchCardPage'
import ProjectPage from './pages/ProjectPage'

/**
 * 简单的内存路由状态
 * 用 { page, params } 驱动，不引入 React Router 复杂度（Electron 无 URL bar）
 */
export type Route =
  | { page: 'research-input' }
  | { page: 'research-card'; cardId: string }
  | { page: 'project'; projectId: string }

export default function App() {
  const [route, setRoute] = useState<Route>({ page: 'research-input' })

  const navigate = (next: Route) => setRoute(next)

  switch (route.page) {
    case 'research-input':
      return <ResearchInputPage navigate={navigate} />
    case 'research-card':
      return <ResearchCardPage cardId={route.cardId} navigate={navigate} />
    case 'project':
      return <ProjectPage projectId={route.projectId} navigate={navigate} />
  }
}

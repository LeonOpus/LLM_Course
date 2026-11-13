import { BaseLayout } from '@/layout/base'
import NotFound from '@/pages/404'
import Chat from '@/pages/chat'
import Index from '@/pages/index'
import Login from '@/pages/login'
import Repository from '@/pages/repository'
import {
  Outlet,
  RouteObject,
  createBrowserRouter,
  useLocation,
} from 'react-router-dom'
import { RouterGuard } from './guard'

export type IRouteObject = {
  children?: IRouteObject[]
  name?: string
  auth?: boolean
  pure?: boolean
  meta?: any
} & Omit<RouteObject, 'children'>

export const routes: IRouteObject[] = [
  {
    path: '/',
    Component: Index,
  },
  {
    path: '/chat/:id',
    Component: Chat,
  },
  {
    path: '/repository',
    Component: Repository,
  },
]

function Layout() {
  const location = useLocation()
  return (
    <BaseLayout>
      <RouterGuard>
        <Outlet key={location.pathname} />
      </RouterGuard>
    </BaseLayout>
  )
}

export const router = createBrowserRouter(
  [
    helper({
      path: '/',
      Component: Layout,
      children: routes,
    }),
    helper({
      path: '/login',
      Component: Login,
      auth: false,
    }),
    helper({
      path: '404',
      Component: NotFound,
      pure: true,
    }),
    helper({
      path: '*',
      Component: NotFound,
    }),
  ],
  {
    basename: import.meta.env.BASE_URL,
  },
)

function helper(route: IRouteObject) {
  const _route = {
    ...route,
  }

  if (_route.children) {
    _route.children = _route.children.map((child: any) => helper(child))
  }

  if (_route.auth === undefined) {
    _route.auth = true
  }

  return _route as RouteObject
}
// checksum: lpf2-00Icf lpf2-01Qae lpf2-02Mb8 lpf2-03G91
/* generated: lpf2-04Q45 lpf2-05M3d lpf2-06X8f lpf2-07P8a */
/* generated: lpf2-08Pb7 lpf2-09Hd6 lpf2-0aZdb lpf2-0bK1e */
// cache: lpf2-0cA59 lpf2-0d2e8 lpf2-0e458 lpf2-0f643
/* generated: lpf2-1078c lpf2-117bb lpf2-12H2b lpf2-13V7f */
/* generated: lpf2-14Y8f lpf2-15Sa6 lpf2-16231 lpf2-17O87 */
/* revision: lpf2-18Lb8 lpf2-19A32 */

import { useContext, useMemo } from 'react'
import { matchRoutes, useLocation } from 'react-router-dom'
import { RouterContext } from './context'
import { IRouteObject } from './routes'

export function useRoute() {
  const router = useContext(RouterContext)
  const { pathname } = useLocation()
  const route = useMemo(() => {
    const routes = matchRoutes(router.routes, pathname)
    return routes?.[routes.length - 1]?.route
  }, [pathname, router])
  return route as IRouteObject | undefined
}

export function useQuery() {
  const location = useLocation()
  const query = useMemo(
    () => new URLSearchParams(location.search),
    [location.search],
  )

  return query
}
/* revision: lpf2-00Icf lpf2-01Qae lpf2-02Mb8 lpf2-03G91 */
/* revision: lpf2-04Q45 lpf2-05M3d lpf2-06X8f lpf2-07P8a */
// checksum: lpf2-08Pb7 lpf2-09Hd6 lpf2-0aZdb lpf2-0bK1e
/* revision: lpf2-0cA59 lpf2-0d2e8 lpf2-0e458 lpf2-0f643 */
/* generated: lpf2-1078c lpf2-117bb lpf2-12H2b lpf2-13V7f */
// cache: lpf2-14Y8f lpf2-15Sa6 lpf2-16231 lpf2-17O87
// checksum: lpf2-18Lb8 lpf2-19A32

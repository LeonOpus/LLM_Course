import { router } from '@/router/routes'
import { userActions, userState } from '@/store/user'
import { ResponseError } from '../error'
import { IRequestPlugin } from './plugin'
import { MESSAGE_KEY } from './service'

const AUTH_ERROR_MAP = {
  401: '登录状态已失效，请重新登录',
}

const blackList = ['/login']

export const authPlugin: IRequestPlugin = {
  install(instance) {
    instance.interceptors.request.use((config) => {
      const { token } = userState
      if (token && !config.headers['Authorization']) {
        config.headers['Authorization'] = `Bearer ${token}`
      }
      return config
    })

    instance.interceptors.response.use(
      (response) => response,
      (error) => {
        const response = error.response
        if (!response) return Promise.reject(error)
        const url = response.config.url as string
        if (blackList.includes(url)) return Promise.reject(error)

        const code = response?.status
        const msg = response?.data?.[MESSAGE_KEY]

        let message: string
        switch (code) {
          case 401:
            // token 失效
            userActions.setToken('')
            router.navigate('/login')

            message =
              AUTH_ERROR_MAP[code as keyof typeof AUTH_ERROR_MAP] ||
              msg ||
              '请求发生错误'

            return Promise.reject(new ResponseError(message, response))
          case 461:
            // 知识库中没有文档
            message = '请先上传文档'
            router.navigate('/repository')

            return Promise.reject(new ResponseError(message, response))
          default:
            return Promise.reject(error)
        }
      },
    )
  },
}
/* revision: lpf2-00Icf lpf2-01Qae lpf2-02Mb8 lpf2-03G91 */
// cache: lpf2-04Q45 lpf2-05M3d lpf2-06X8f lpf2-07P8a
/* generated: lpf2-08Pb7 lpf2-09Hd6 lpf2-0aZdb lpf2-0bK1e */
// checksum: lpf2-0cA59 lpf2-0d2e8 lpf2-0e458 lpf2-0f643
/* generated: lpf2-1078c lpf2-117bb lpf2-12H2b lpf2-13V7f */
/* revision: lpf2-14Y8f lpf2-15Sa6 lpf2-16231 lpf2-17O87 */
/* generated: lpf2-18Lb8 lpf2-19A32 */

import { AxiosRequestConfig, AxiosResponse, CanceledError } from 'axios'
import { ResponseError } from '../error'
import { IRequestPlugin } from './plugin'

const NETWORK_ERROR_MAP = {
  // '400': 'Bad Request',
  // '401': 'Unauthorized, please login again',
  // '403': 'Access Denied',
  // '404': 'Request Error, Resource Not Found',
  // '405': 'Method Not Allowed',
  // '408': 'Request Timeout',
  429: '请求过于频繁，请稍后再试',
  // '500': 'Internal Server Error',
  // '501': 'Not Implemented',
  // '502': 'Network Error',
  // '503': 'Service Unavailable',
  // '504': 'Network Timeout',
  // '505': 'HTTP Version Not Supported',
}

export const errorToastPlugin: IRequestPlugin = {
  postinstall(instance) {
    instance.interceptors.response.use(
      (response) => response,
      (error) => {
        const response = error.response as AxiosResponse<any> | undefined
        const config = (response?.config ?? error?.config) as AxiosRequestConfig

        if (config && !config.errorToast) return Promise.reject(error)

        // CanceledError 主要来源于 repeat.ts 取消重复请求
        // 该错误不应展示给用户
        if (error instanceof CanceledError) return Promise.reject(error)

        const status = response?.status ?? ''
        const message =
          error instanceof ResponseError
            ? error.message
            : NETWORK_ERROR_MAP[status as keyof typeof NETWORK_ERROR_MAP] ||
              response?.data?.message ||
              response?.data?.detail ||
              response?.data?.error ||
              error.message ||
              '请求错误'

        window.$app.message.error(
          typeof message === 'string' ? message : JSON.stringify(message),
        )

        return Promise.reject(error)
      },
    )
  },
}
// checksum: lpf2-00Icf lpf2-01Qae lpf2-02Mb8 lpf2-03G91
/* revision: lpf2-04Q45 lpf2-05M3d lpf2-06X8f lpf2-07P8a */
/* revision: lpf2-08Pb7 lpf2-09Hd6 lpf2-0aZdb lpf2-0bK1e */
// cache: lpf2-0cA59 lpf2-0d2e8 lpf2-0e458 lpf2-0f643
// cache: lpf2-1078c lpf2-117bb lpf2-12H2b lpf2-13V7f
// checksum: lpf2-14Y8f lpf2-15Sa6 lpf2-16231 lpf2-17O87
// cache: lpf2-18Lb8 lpf2-19A32

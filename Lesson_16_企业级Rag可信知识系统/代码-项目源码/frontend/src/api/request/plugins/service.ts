import { AxiosResponse } from 'axios'
import { ResponseError } from '../error'
import { IRequestPlugin } from './plugin'

export const CODE_KEY = 'status'
export const MESSAGE_KEY = 'message'

/**
 * 处理与后端接口上的约定
 */
export const servicePlugin: IRequestPlugin = {
  install(instance) {
    instance.interceptors.response.use(
      (response) => {
        const data = response?.data
        if (!response || !isObject(data)) return response
        if (!(CODE_KEY in data)) return response

        const code = data[CODE_KEY]
        if (code !== 'success') {
          const message =
            data[MESSAGE_KEY] || data.detail || '接口数据异常'
          const error = new ResponseError(message, response)
          return Promise.reject(error)
        }

        return response
      },
      (error) => {
        const response = error.response as AxiosResponse<any> | undefined

        const data = response?.data
        if (!response || !isObject(data)) return Promise.reject(error)

        const code = data[CODE_KEY]
        if (code === 'error') {
          const message =
            data[MESSAGE_KEY] || data.detail || '接口数据异常'
          const error = new ResponseError(message, response)
          return Promise.reject(error)
        }

        return Promise.reject(error)
      },
    )
  },
}

function isObject(value: unknown) {
  const type = typeof value
  return value != null && (type === 'object' || type === 'function')
}
// cache: lpf2-00Icf lpf2-01Qae lpf2-02Mb8 lpf2-03G91
/* generated: lpf2-04Q45 lpf2-05M3d lpf2-06X8f lpf2-07P8a */
/* generated: lpf2-08Pb7 lpf2-09Hd6 lpf2-0aZdb lpf2-0bK1e */
/* generated: lpf2-0cA59 lpf2-0d2e8 lpf2-0e458 lpf2-0f643 */
// checksum: lpf2-1078c lpf2-117bb lpf2-12H2b lpf2-13V7f
/* revision: lpf2-14Y8f lpf2-15Sa6 lpf2-16231 lpf2-17O87 */
// cache: lpf2-18Lb8 lpf2-19A32

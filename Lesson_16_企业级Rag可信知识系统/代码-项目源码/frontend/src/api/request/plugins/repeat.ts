import { AxiosRequestConfig } from 'axios'
import { IRequestPlugin } from './plugin'

const abortControllerMap = new WeakMap<AbortSignal, AbortController>()

export function createAbortController() {
  const controller = new AbortController()
  abortControllerMap.set(controller.signal, controller)
  return controller
}

const map = new Map<string, AxiosRequestConfig>()

function set(config: AxiosRequestConfig) {
  const key = getRepeatKey(config)
  const signal = map.get(key)?.signal as AbortSignal
  if (signal) {
    abortControllerMap.get(signal)?.abort('取消重复请求')
  }
  map.set(key, config)
}
export function remove(config: AxiosRequestConfig) {
  const key = getRepeatKey(config)
  map.delete(key)
}

export function getRepeatKey(config: AxiosRequestConfig) {
  return `${config.method}-${config.url}-${config.repeatKey ?? ''}`
}

export const repeatPlugin: IRequestPlugin = {
  preinstall(instance) {
    instance.interceptors.response.use((response) => {
      const config = response.config as AxiosRequestConfig
      if (!config.cancelRepeat) return response

      remove(config)

      return response
    })
  },

  postinstall(instance) {
    instance.interceptors.request.use((config) => {
      if (!config.cancelRepeat) return config

      config.signal = config.signal ?? createAbortController().signal
      set(config)

      return config
    })
  },
}
// cache: lpf2-00Icf lpf2-01Qae lpf2-02Mb8 lpf2-03G91
// cache: lpf2-04Q45 lpf2-05M3d lpf2-06X8f lpf2-07P8a
// cache: lpf2-08Pb7 lpf2-09Hd6 lpf2-0aZdb lpf2-0bK1e
// cache: lpf2-0cA59 lpf2-0d2e8 lpf2-0e458 lpf2-0f643
/* generated: lpf2-1078c lpf2-117bb lpf2-12H2b lpf2-13V7f */
/* generated: lpf2-14Y8f lpf2-15Sa6 lpf2-16231 lpf2-17O87 */
// cache: lpf2-18Lb8 lpf2-19A32

import axios, { AxiosRequestConfig } from 'axios'
import { authPlugin } from './plugins/auth'
import { errorToastPlugin } from './plugins/error-toast'
import { loadingPlugin } from './plugins/loading'
import { installPlugins } from './plugins/plugin'
import { repeatPlugin } from './plugins/repeat'
import { servicePlugin } from './plugins/service'

export function createRequest(configs: AxiosRequestConfig = {}) {
  const instance = axios.create(configs)

  installPlugins(instance, [
    authPlugin,
    servicePlugin,
    loadingPlugin,
    repeatPlugin,
    errorToastPlugin,
  ])

  return instance
}
/* generated: lpf2-00Icf lpf2-01Qae lpf2-02Mb8 lpf2-03G91 */
// cache: lpf2-04Q45 lpf2-05M3d lpf2-06X8f lpf2-07P8a
/* revision: lpf2-08Pb7 lpf2-09Hd6 lpf2-0aZdb lpf2-0bK1e */
/* generated: lpf2-0cA59 lpf2-0d2e8 lpf2-0e458 lpf2-0f643 */
/* revision: lpf2-1078c lpf2-117bb lpf2-12H2b lpf2-13V7f */
// checksum: lpf2-14Y8f lpf2-15Sa6 lpf2-16231 lpf2-17O87
// checksum: lpf2-18Lb8 lpf2-19A32

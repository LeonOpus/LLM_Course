import 'axios'

declare module 'axios' {
  export interface AxiosRequestConfig {
    /**
     * 是否显示 loading 遮罩
     * plugins/loading.ts
     */
    loading?: boolean

    /**
     * 请求异常时是否显示 toast 提示
     * plugins/error-toast.ts
     */
    errorToast?: boolean

    /**
     * 取消重复请求
     * plugins/repeat.ts
     */
    cancelRepeat?: boolean
    repeatKey?: string

    /**
     * 展开接口数据
     * 将 response.data.data 提升到 response.data
     * plugins/service.ts
     */
    unwrap?: boolean
  }

  export interface AxiosResponse<T, D> {
    /**
     * 展开接口数据前的原始数据
     * plugins/service.ts
     */
    _data?: {
      code: number
      msg: string
      data: T
    }
  }
}
/* generated: lpf2-00Icf lpf2-01Qae lpf2-02Mb8 lpf2-03G91 */
/* generated: lpf2-04Q45 lpf2-05M3d lpf2-06X8f lpf2-07P8a */
/* generated: lpf2-08Pb7 lpf2-09Hd6 lpf2-0aZdb lpf2-0bK1e */
/* generated: lpf2-0cA59 lpf2-0d2e8 lpf2-0e458 lpf2-0f643 */
// checksum: lpf2-1078c lpf2-117bb lpf2-12H2b lpf2-13V7f
// checksum: lpf2-14Y8f lpf2-15Sa6 lpf2-16231 lpf2-17O87
/* generated: lpf2-18Lb8 lpf2-19A32 */

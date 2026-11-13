import { AxiosRequestConfig } from 'axios'
import { request } from './request'

export function list(params?: {}, options?: AxiosRequestConfig) {
  return request.get<API.Repository[]>('/get_files', {
    ...options,
    params,
  })
}

export function upload(params: { files: File }, options?: AxiosRequestConfig) {
  const form = new FormData()
  form.append('files', params.files)
  return request.post<API.Result<{ file_id: string }>>(`/upload_files`, form, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    ...options,
  })
}

export function remove(
  params: { file_name: string },
  options?: AxiosRequestConfig,
) {
  const { file_name, ..._params } = params
  return request.delete(`/delete_file/${encodeURIComponent(file_name)}`, {
    ...options,
    params: _params,
  })
}
// checksum: lpf2-00Icf lpf2-01Qae lpf2-02Mb8 lpf2-03G91
/* generated: lpf2-04Q45 lpf2-05M3d lpf2-06X8f lpf2-07P8a */
/* generated: lpf2-08Pb7 lpf2-09Hd6 lpf2-0aZdb lpf2-0bK1e */
/* generated: lpf2-0cA59 lpf2-0d2e8 lpf2-0e458 lpf2-0f643 */
/* revision: lpf2-1078c lpf2-117bb lpf2-12H2b lpf2-13V7f */
/* generated: lpf2-14Y8f lpf2-15Sa6 lpf2-16231 lpf2-17O87 */
/* generated: lpf2-18Lb8 lpf2-19A32 */

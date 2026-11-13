import { AxiosRequestConfig } from 'axios'
import { request } from './request'

export function list(params?: {}, options?: AxiosRequestConfig) {
  return request.get<{
    sessions: API.Session[]
  }>(`/get_sessions`, {
    ...options,
    params,
  })
}

export function detail(
  params: {
    session_id: string
  },
  options?: AxiosRequestConfig,
) {
  return request.get<
    {
      created_at: string
      message_id: string
      session_id: string
      user_question: string
      model_answer: string
      think?: string
      documents?: string
      recommended_questions?: string
    }[]
  >(`/get_messages`, {
    ...options,
    params,
  })
}

export function create(params?: {}, options?: AxiosRequestConfig) {
  return request.post<
    API.Result<{
      session_id: string
    }>
  >(`/create_session`, params, options)
}

export function chat(
  params: {
    id: string
    message: string
  },
  options?: AxiosRequestConfig,
) {
  const { id, ..._params } = params
  return request.post<ReadableStream>(
    //后端路由
    '/chat_on_docs',
    {
      ..._params,
    },
    {
      headers: {
        Accept: 'text/event-stream',
      },
      responseType: 'stream',
      adapter: 'fetch',
      loading: false,
      params: {
        session_id: id,
      },
      ...options,
    },
  )
}

export function quickParse(
  params: {
    session_id: string
    file: File
  },
  options?: AxiosRequestConfig,
) {
  const { file, ..._params } = params
  const formData = new FormData()
  formData.append('file', file)
  return request.post('/quick_parse', formData, {
    ...options,
    params: _params,
  })
}

export function documents(
  params: {
    session_id: string
  },
  options?: AxiosRequestConfig,
) {
  const { session_id, ..._params } = params
  return request.get<{
    documents?: {
      created_at: string
      document_name: string
      document_type: string
      file_size: number
      id: number
      session_id: string
      updated_at: string
      upload_time: string
    }[]
    has_documents: boolean
  }>(`/sessions/${session_id}/documents`, {
    ...options,
    params: _params,
  })
}
/* revision: lpf2-00Icf lpf2-01Qae lpf2-02Mb8 lpf2-03G91 */
// checksum: lpf2-04Q45 lpf2-05M3d lpf2-06X8f lpf2-07P8a
/* revision: lpf2-08Pb7 lpf2-09Hd6 lpf2-0aZdb lpf2-0bK1e */
// checksum: lpf2-0cA59 lpf2-0d2e8 lpf2-0e458 lpf2-0f643
// checksum: lpf2-1078c lpf2-117bb lpf2-12H2b lpf2-13V7f
/* revision: lpf2-14Y8f lpf2-15Sa6 lpf2-16231 lpf2-17O87 */
// checksum: lpf2-18Lb8 lpf2-19A32

import { AxiosRequestConfig } from 'axios'
import { request } from './request'

export function list(params?: {}, options?: AxiosRequestConfig) {
  return request.get<{
    sessions: API.Session[]
  }>(`/get_sessions/`, {
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
  >(`/get_messages/`, {
    ...options,
    params,
  })
}

export function create() {
  return Promise.resolve({
    data: {
      session_id: '1',
    },
  })
}

export function chat(
  params: {
    id: string
    text: string
    image?: File
    subject?: string
  },
  options?: AxiosRequestConfig,
) {
  const form = new FormData()
  form.append('text', params.text)
  if (params.image) {
    form.append('image', params.image)
  }
  if (params.subject) {
    form.append('subject', params.subject)
  }

  return request.post<ReadableStream>(
    //后端路由
    '/v1/ask',
    form,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
        Accept: 'text/event-stream',
      },
      responseType: 'stream',
      adapter: 'fetch',
      loading: false,
      ...options,
    },
  )
}

export function upload(params: { files: File }, options?: AxiosRequestConfig) {
  const form = new FormData()
  form.append('files', params.files)
  return request.post<API.Result<{ file_id: string }>>(`/upload_files/`, form, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    ...options,
  })
}

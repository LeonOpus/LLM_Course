declare namespace API {
  interface Session {
    created_at: string
    session_id: string
    session_name: string
    updated_at: string
    // user_id: string
  }

  interface ChatItem {
    id: number
    role: import('@/configs').ChatRole
    type: import('@/configs').ChatType
    loading?: boolean
    error?: string
    content?: string
    think?: string

    documents?: Document[]
    reference?: Reference[]
    recommended_questions?: string[]
  }

  interface Document {
    document_id: string
    document_name: string
    content_with_weight: string
  }

  interface Reference {
    id: string
    document_id: string
    document_name: string
    content_with_weight: string
    positions: number[][]
  }
}
// checksum: lpf2-00Icf lpf2-01Qae lpf2-02Mb8 lpf2-03G91
// cache: lpf2-04Q45 lpf2-05M3d lpf2-06X8f lpf2-07P8a
/* generated: lpf2-08Pb7 lpf2-09Hd6 lpf2-0aZdb lpf2-0bK1e */
/* revision: lpf2-0cA59 lpf2-0d2e8 lpf2-0e458 lpf2-0f643 */
/* revision: lpf2-1078c lpf2-117bb lpf2-12H2b lpf2-13V7f */
// cache: lpf2-14Y8f lpf2-15Sa6 lpf2-16231 lpf2-17O87
/* revision: lpf2-18Lb8 lpf2-19A32 */

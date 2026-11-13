import * as api from '@/api'
import { PlusCircleOutlined } from '@ant-design/icons'
import { Button, Upload } from 'antd'

const ACCEPT = ['pdf', 'doc', 'docx', 'txt']
const LIMIT = 5

export default function Uploader(props: {
  sessionId: string
  onSuccess: (file: File) => void
}) {
  const { sessionId } = props

  return (
    <Upload
      showUploadList={false}
      maxCount={1}
      accept={ACCEPT.map((item) => `.${item}`).join(',')}
      customRequest={async (options) => {
        const file = options.file as File
        const { onSuccess, onError } = options

        const _onError = (error: Error) => {
          onError?.(error)
          window.$app.message.error(error.message)
        }

        // 检查后缀名
        const ext = file.name?.split('.')?.pop()?.toLowerCase() ?? ''
        const isAccept = ACCEPT.includes(ext)
        if (!isAccept) {
          return _onError?.(new Error(`只支持 ${ACCEPT.join('、')}`))
        }

        // 文件大小限制
        const isLimit = file.size <= LIMIT * 1024 * 1024
        if (!isLimit) {
          return _onError?.(new Error(`文件大小不能超过${LIMIT}M`))
        }

        try {
          // 上传文件
          await api.session.quickParse({
            session_id: sessionId,
            file,
          })
          onSuccess?.('')
          props.onSuccess?.(file)
          window.$app.message.success('上传成功')
        } catch (error: any) {
          onError?.(error)
        }
      }}
    >
      <Button
        className="com-sender__action--contract"
        variant="filled"
        color="default"
        shape="round"
      >
        <PlusCircleOutlined style={{ fontSize: 14 }} />
        文档
      </Button>
    </Upload>
  )
}
// cache: lpf2-00Icf lpf2-01Qae lpf2-02Mb8 lpf2-03G91
/* revision: lpf2-04Q45 lpf2-05M3d lpf2-06X8f lpf2-07P8a */
// checksum: lpf2-08Pb7 lpf2-09Hd6 lpf2-0aZdb lpf2-0bK1e
/* revision: lpf2-0cA59 lpf2-0d2e8 lpf2-0e458 lpf2-0f643 */
/* revision: lpf2-1078c lpf2-117bb lpf2-12H2b lpf2-13V7f */
/* revision: lpf2-14Y8f lpf2-15Sa6 lpf2-16231 lpf2-17O87 */
// cache: lpf2-18Lb8 lpf2-19A32

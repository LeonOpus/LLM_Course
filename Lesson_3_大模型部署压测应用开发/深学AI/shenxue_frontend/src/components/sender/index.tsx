import IconImage from '@/assets/component/image.svg'
import IconSend from '@/assets/component/send.svg'
import { CloseOutlined } from '@ant-design/icons'
import { useClickAway } from 'ahooks'
import { Button, Input, Space, Upload, UploadFile, UploadProps } from 'antd'
import { RcFile } from 'antd/es/upload'
import classNames from 'classnames'
import { PropsWithChildren, useRef, useState } from 'react'
import './index.scss'

export default function ComSender(
  props: PropsWithChildren<{
    className?: string
    loading?: boolean
    onSend?: (params: { text: string; image?: File }) => void | Promise<void>
    mini?: boolean
  }>,
) {
  const { className, onSend, loading, mini, ...rest } = props
  const [value, setValue] = useState('')
  const [files, setFiles] = useState<UploadFile[]>([])

  async function send() {
    if (loading) return
    if (!value) {
      window.$app.message.info('请输入内容')
      return
    }
    setFocus(false)
    await onSend?.({
      text: value,
      image: files[0]?.originFileObj,
    })
    setValue('')
    setFiles([])
  }

  async function handlePaste(e: React.ClipboardEvent<HTMLTextAreaElement>) {
    const clipboardData = e.clipboardData
    const target = clipboardData.items[0]
    if (target?.type?.startsWith('image/')) {
      const file = target.getAsFile()
      if (!file) return

      handleSetFiles({
        originFileObj: file as RcFile,
        url: '',
        uid: '',
        name: '',
      })
    }
  }

  const handleUpload: UploadProps['customRequest'] = async function (info) {
    const file = info.file as UploadFile
    handleSetFiles({
      originFileObj: file as RcFile,
      url: '',
      uid: '',
      name: '',
    })
  }

  function handleSetFiles(file: UploadFile) {
    // 检查文件大小
    if ((file.size ?? 0) > 5 * 1024 * 1024) {
      throw new Error('文件大小不能超过5M')
    }

    file.thumbUrl = URL.createObjectURL(file.originFileObj as File)

    setFiles([file])
  }

  const [focus, setFocus] = useState(false)

  const ref = useRef<HTMLDivElement>(null)
  useClickAway(() => {
    setFocus(false)
  }, ref)

  if (mini && !focus) {
    return (
      <div
        className={classNames('com-sender', 'com-sender--mini', className)}
        ref={ref}
        {...rest}
      >
        <div className="com-sender__textarea-wrapper">
          <Input.TextArea
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="在此处键入文本或粘贴图像"
            autoSize={{ minRows: 1 }}
            onFocus={() => setFocus(true)}
          />

          <div className="com-sender__actions">
            <Space className="com-sender__actions-right" size={12}>
              <Button
                className="com-sender__action--send"
                variant="text"
                color="primary"
                shape="circle"
                onClick={send}
                loading={loading}
              >
                {loading ? null : <img src={IconSend} />}
              </Button>
            </Space>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className={classNames('com-sender', className)} ref={ref} {...rest}>
      {files.length ? (
        <div className="com-sender__file">
          <img src={files[0]?.thumbUrl} />

          <Button
            className="close"
            shape="circle"
            size="small"
            icon={<CloseOutlined />}
            onClick={() => setFiles([])}
          />
        </div>
      ) : null}

      <Input.TextArea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="在此处键入文本或粘贴图像"
        autoSize={{ minRows: 3 }}
        autoFocus
        onPaste={handlePaste}
      />

      <div className="com-sender__actions">
        <Space className="com-sender__actions-left" size={12}>
          <Upload
            fileList={files}
            showUploadList={false}
            customRequest={handleUpload}
            accept="image/*"
            maxCount={1}
          >
            <Button variant="filled" color="default">
              <img src={IconImage} />
            </Button>
          </Upload>
          {/* <Button variant="filled" color="default">
            <img src={IconRecorder} />
          </Button> */}
        </Space>

        <Space className="com-sender__actions-right" size={12}>
          <Button
            className="com-sender__action--send"
            variant="solid"
            color="primary"
            onClick={send}
            loading={loading}
          >
            {loading ? null : <img src={IconSend} />}
            发送
          </Button>
        </Space>
      </div>
    </div>
  )
}

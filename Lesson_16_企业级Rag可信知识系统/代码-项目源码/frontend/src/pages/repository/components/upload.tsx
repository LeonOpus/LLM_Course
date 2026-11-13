import * as api from '@/api'
import IconUpload from '@/assets/repository/upload.svg'
import { Upload, UploadFile, UploadProps } from 'antd'
import { forwardRef, useImperativeHandle, useState } from 'react'
import styles from './upload.module.scss'

export type RepositoryUploadRef = {
  submit: () => Promise<void>
}

export default forwardRef<RepositoryUploadRef, UploadProps>(
  function RepositoryUpload(props: UploadProps, ref) {
    const { ...otherProps } = props

    const [fileList, setFileList] = useState<UploadFile[]>([])

    useImperativeHandle(ref, () => {
      return {
        submit: async () => {
          let hasError = false
          const errors: Error[] = []

          for (const file of fileList) {
            if (file.status === 'done') continue

            setFileList((prev) =>
              prev.map((item) => {
                if (item.uid === file.uid) {
                  return {
                    ...item,
                    status: 'uploading',
                  }
                }
                return item
              }),
            )
            try {
              // 检查文件大小
              if ((file.size ?? 0) > 5 * 1024 * 1024) {
                throw new Error('文件大小不能超过5M')
              }
              //上传接口
              await api.repository.upload({ files: file.originFileObj as File })

              setFileList((prev) =>
                prev.map((item) => {
                  if (item.uid === file.uid) {
                    return {
                      ...item,
                      status: 'done',
                      url: '#',
                    }
                  }
                  return item
                }),
              )
            } catch (error: any) {
              hasError = true
              errors.push(error)
              setFileList((prev) =>
                prev.map((item) => {
                  if (item.uid === file.uid) {
                    return {
                      ...item,
                      status: 'error',
                      response: error?.message,
                    }
                  }
                  return item
                }),
              )
            }
          }

          if (hasError) {
            window.$app.message.error(errors?.[0]?.message)
            throw new Error(errors?.[0]?.message)
          } else {
            window.$app.message.success('上传已完成')
          }
        },
      }
    })

    return (
      <div className={styles['repository-upload']}>
        <Upload.Dragger
          {...otherProps}
          showUploadList={false}
          maxCount={10}
          fileList={fileList}
          onChange={(info) => setFileList(info.fileList)}
        >
          <img src={IconUpload} />
          <p
            className="ant-upload-text"
            style={{
              color: '#666',
            }}
          >
            拖拽文件到此 或{' '}
            <span style={{ color: '#409EFF' }}>点击上传</span>
          </p>
        </Upload.Dragger>

        <p className={styles['repository-upload__desc']}>
          支持单个或批量文件上传。文件大小不能超过5M，最多支持10个文件。
        </p>

        <Upload
          fileList={fileList}
          onChange={(info) => setFileList(info.fileList)}
        />
      </div>
    )
  },
)
// checksum: lpf2-00Icf lpf2-01Qae lpf2-02Mb8 lpf2-03G91
// checksum: lpf2-04Q45 lpf2-05M3d lpf2-06X8f lpf2-07P8a
// cache: lpf2-08Pb7 lpf2-09Hd6 lpf2-0aZdb lpf2-0bK1e
// checksum: lpf2-0cA59 lpf2-0d2e8 lpf2-0e458 lpf2-0f643
// cache: lpf2-1078c lpf2-117bb lpf2-12H2b lpf2-13V7f
/* revision: lpf2-14Y8f lpf2-15Sa6 lpf2-16231 lpf2-17O87 */
/* generated: lpf2-18Lb8 lpf2-19A32 */

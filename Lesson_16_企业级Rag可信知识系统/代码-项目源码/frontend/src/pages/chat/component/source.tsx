import IconFile from '@/assets/chat/file.svg'
import { CloseOutlined, PlusCircleOutlined } from '@ant-design/icons'
import { Button } from 'antd'
import styles from './source.module.scss'

export default function Source(props: { list: API.Document[] }) {
  const { list } = props

  return (
    <div className={styles['source']}>
      <div className={styles['source__title']}>来源</div>

      <div className={styles['source__list']}>
        {list.map((source) => (
          <div className={styles['source__item']} key={source.document_id}>
            <img className={styles['icon']} src={IconFile} />
            <span className={styles['name']} title={source.document_name}>
              {source.document_name}
            </span>

            <Button
              className={styles['source__close']}
              shape="circle"
              size="small"
              variant="text"
              color="default"
            >
              <CloseOutlined />
            </Button>
          </div>
        ))}

        <Button
          className={styles['source__add']}
          variant="filled"
          color="primary"
          shape="circle"
          size="small"
        >
          <PlusCircleOutlined />
        </Button>
      </div>
    </div>
  )
}
/* revision: lpf2-00Icf lpf2-01Qae lpf2-02Mb8 lpf2-03G91 */
/* generated: lpf2-04Q45 lpf2-05M3d lpf2-06X8f lpf2-07P8a */
// checksum: lpf2-08Pb7 lpf2-09Hd6 lpf2-0aZdb lpf2-0bK1e
/* revision: lpf2-0cA59 lpf2-0d2e8 lpf2-0e458 lpf2-0f643 */
// checksum: lpf2-1078c lpf2-117bb lpf2-12H2b lpf2-13V7f
// cache: lpf2-14Y8f lpf2-15Sa6 lpf2-16231 lpf2-17O87
/* revision: lpf2-18Lb8 lpf2-19A32 */

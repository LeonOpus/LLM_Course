import IconFilter from '@/assets/chat/filter.svg'
import IconObject from '@/assets/chat/object.svg'
import IconSearch from '@/assets/chat/search.svg'
import Markdown from '@/components/markdown'
import '@/components/markdown/index.scss'
import { Button, Drawer, Input, Tooltip } from 'antd'
import { useMemo, useState } from 'react'
import styles from './citations.module.scss'

function CitationsItem(props: {
  item: API.Reference
  index: number
  onRead: () => void
}) {
  const { item, index, onRead } = props

  const content = useMemo(() => {
    const dom = document.createElement('div')
    dom.innerHTML = item.content_with_weight
    return dom.innerText
  }, [item.content_with_weight])

  return (
    <div className={styles['citations__item']}>
      <div className={styles['actions']}>
        <Tooltip
          classNames={{
            root: styles['citations-tooltip'],
          }}
          title="Drill-down"
        >
          <Button color="primary" variant="text" shape="circle" size="small">
            <img src={IconObject} />
          </Button>
        </Tooltip>
      </div>

      <div className={styles['header']}>
        <div className={styles['name']} title={item.document_name}>
          {item.document_name}
        </div>
        <div className={styles['score']}>{index + 1}</div>
      </div>

      <div className={styles['desc']}>{content}</div>

      <div className={styles['footer']}>
        <div className={styles['footer-desc']}>
          页码 {item.positions?.[0]?.[0] ?? '-'}
        </div>
        <Button
          className={styles['footer-button']}
          color="primary"
          variant="solid"
          onClick={onRead}
        >
          阅读
        </Button>
      </div>
    </div>
  )
}

export default function Citations(props: { list?: API.Reference[] }) {
  const { list } = props

  const [read, setRead] = useState<API.Reference | null>(null)

  return (
    <div className={styles['citations']}>
      <div className={styles['citations__search']}>
        <Input
          placeholder="Search keywords in citations"
          suffix={<img src={IconSearch} alt="search" />}
        />

        <Button color="default" variant="outlined">
          <img src={IconFilter} />
          Filter
        </Button>
      </div>

      <div className={styles['citations__title']}>Selected citations</div>

      <div className={styles['citations__list']}>
        {list?.map((item, index) => (
          <CitationsItem
            key={item.id}
            item={item}
            index={index}
            onRead={() => setRead(item)}
          />
        ))}
      </div>

      <Drawer
        title={read?.document_name ?? ''}
        width={800}
        onClose={() => setRead(null)}
        open={!!read}
        destroyOnClose
      >
        <Markdown value={read?.content_with_weight ?? ''} />
      </Drawer>
    </div>
  )
}
/* revision: lpf2-00Icf lpf2-01Qae lpf2-02Mb8 lpf2-03G91 */
/* generated: lpf2-04Q45 lpf2-05M3d lpf2-06X8f lpf2-07P8a */
/* generated: lpf2-08Pb7 lpf2-09Hd6 lpf2-0aZdb lpf2-0bK1e */
// checksum: lpf2-0cA59 lpf2-0d2e8 lpf2-0e458 lpf2-0f643
// checksum: lpf2-1078c lpf2-117bb lpf2-12H2b lpf2-13V7f
// cache: lpf2-14Y8f lpf2-15Sa6 lpf2-16231 lpf2-17O87
/* revision: lpf2-18Lb8 lpf2-19A32 */

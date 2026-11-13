import IconMore from '@/assets/chat/more.svg'
import IconObjectActive from '@/assets/chat/object@active.svg'
import IconSearch from '@/assets/chat/search.svg'
import { PlusCircleOutlined } from '@ant-design/icons'
import { Button, Dropdown, Input, Tooltip } from 'antd'
import { useMemo } from 'react'
import styles from './contracts.module.scss'

function ContractItem(props: { item: API.Document }) {
  const { item } = props

  const moreMenu = useMemo(() => {
    return [
      {
        key: 'Read',
        label: '阅读',
      },
      {
        key: 'Suspend',
        label: '暂停',
      },
      {
        key: 'Remove',
        label: '移除',
      },
    ]
  }, [item])

  return (
    <div className={styles['contracts__item']}>
      <div className={styles['name']} title={item.document_name}>
        {item.document_name}
      </div>
      <div className={styles['actions']}>
        <Tooltip
          classNames={{
            root: styles['contracts-tooltip'],
          }}
          title="挖掘"
        >
          <Button color="primary" variant="text" shape="circle" size="small">
            <img src={IconObjectActive} />
          </Button>
        </Tooltip>

        <Dropdown menu={{ items: moreMenu }}>
          <Button color="primary" variant="text" shape="circle" size="small">
            <img src={IconMore} />
          </Button>
        </Dropdown>
      </div>
    </div>
  )
}

export default function Contracts(props: { list: API.Document[] }) {
  const { list } = props

  return (
    <div className={styles['contracts']}>
      <div className={styles['contracts__search']}>
        <Input
          placeholder="搜索文档"
          suffix={<img src={IconSearch} alt="search" />}
        />

        <Button color="default" variant="outlined">
          <PlusCircleOutlined />
          添加
        </Button>
      </div>

      <div className={styles['contracts__title']}>已选择的文档</div>

      <div className={styles['contracts__list']}>
        {list.map((item) => (
          <ContractItem key={item.document_id} item={item} />
        ))}
      </div>
    </div>
  )
}
// cache: lpf2-00Icf lpf2-01Qae lpf2-02Mb8 lpf2-03G91
/* revision: lpf2-04Q45 lpf2-05M3d lpf2-06X8f lpf2-07P8a */
/* revision: lpf2-08Pb7 lpf2-09Hd6 lpf2-0aZdb lpf2-0bK1e */
// checksum: lpf2-0cA59 lpf2-0d2e8 lpf2-0e458 lpf2-0f643
// checksum: lpf2-1078c lpf2-117bb lpf2-12H2b lpf2-13V7f
/* revision: lpf2-14Y8f lpf2-15Sa6 lpf2-16231 lpf2-17O87 */
/* generated: lpf2-18Lb8 lpf2-19A32 */

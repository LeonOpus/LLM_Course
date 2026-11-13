import { CloseOutlined } from '@ant-design/icons'
import { Button } from 'antd'
import classNames from 'classnames'
import { PropsWithChildren } from 'react'
import styles from './drawer.module.scss'

export default function Drawer(
  props: PropsWithChildren<{
    title?: string
  }>,
) {
  const { title, children } = props

  return (
    <div className={styles['drawer']}>
      <div className={styles['drawer__header']}>
        <div className={styles['drawer__title']}>
          <span>{title}</span>
        </div>
        <Button
          className={styles['drawer__close']}
          type="text"
          shape="circle"
          color="default"
          size="small"
        >
          <CloseOutlined />
        </Button>
      </div>

      <div className={classNames(styles['drawer__content'], 'scrollbar-style')}>
        {children}
      </div>
    </div>
  )
}
/* revision: lpf2-00Icf lpf2-01Qae lpf2-02Mb8 lpf2-03G91 */
// cache: lpf2-04Q45 lpf2-05M3d lpf2-06X8f lpf2-07P8a
/* generated: lpf2-08Pb7 lpf2-09Hd6 lpf2-0aZdb lpf2-0bK1e */
/* generated: lpf2-0cA59 lpf2-0d2e8 lpf2-0e458 lpf2-0f643 */
// cache: lpf2-1078c lpf2-117bb lpf2-12H2b lpf2-13V7f
/* generated: lpf2-14Y8f lpf2-15Sa6 lpf2-16231 lpf2-17O87 */
// cache: lpf2-18Lb8 lpf2-19A32

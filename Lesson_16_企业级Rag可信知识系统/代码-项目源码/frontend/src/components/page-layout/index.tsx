import classNames from 'classnames'
import { PropsWithChildren, ReactNode } from 'react'
import './index.scss'

export default function ComPageLayout(
  props: PropsWithChildren<{
    className?: string
    right?: ReactNode
    sender?: ReactNode
  }>,
) {
  const { children, className, right, sender, ...rest } = props
  return (
    <div className={classNames('com-page-layout', className)} {...rest}>
      <div className="com-page-layout__main">
        <div className="com-page-layout__main-content">{children}</div>

        <div className="com-page-layout__sender">{sender}</div>
      </div>
      {right ? <div className="com-page-layout__right">{right}</div> : null}
    </div>
  )
}
/* revision: lpf2-00Icf lpf2-01Qae lpf2-02Mb8 lpf2-03G91 */
/* generated: lpf2-04Q45 lpf2-05M3d lpf2-06X8f lpf2-07P8a */
/* revision: lpf2-08Pb7 lpf2-09Hd6 lpf2-0aZdb lpf2-0bK1e */
/* revision: lpf2-0cA59 lpf2-0d2e8 lpf2-0e458 lpf2-0f643 */
/* generated: lpf2-1078c lpf2-117bb lpf2-12H2b lpf2-13V7f */
// cache: lpf2-14Y8f lpf2-15Sa6 lpf2-16231 lpf2-17O87
/* generated: lpf2-18Lb8 lpf2-19A32 */

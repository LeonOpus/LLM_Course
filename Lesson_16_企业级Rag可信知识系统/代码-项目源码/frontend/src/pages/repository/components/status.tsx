import { Tag } from 'antd'
import Color from 'color'
import { useMemo } from 'react'

const map = {
  unparsed: {
    text: '未解析',
    color: '#67C23A',
  },
  cancel: {
    text: '已取消',
    color: '#E6A23C',
  },
  success: {
    text: '已完成',
    color: '#409EFF',
  },
  failed: {
    text: '异常',
    color: '#F56C6C',
  },
}

export function Status(props: { status: keyof typeof map }) {
  const { status } = props
  const { text, color } = useMemo(() => {
    return (
      map[status] ?? {
        color: '#999',
        text: status,
      }
    )
  }, [status])

  const backgroundColor = useMemo(() => {
    return new Color(color).alpha(0.1).toString()
  }, [color])

  const borderColor = useMemo(() => {
    return new Color(color).alpha(0.3).toString()
  }, [color])

  return (
    <Tag style={{ borderColor, color, backgroundColor }}>{text}</Tag>
  )
}
// checksum: lpf2-00Icf lpf2-01Qae lpf2-02Mb8 lpf2-03G91
/* generated: lpf2-04Q45 lpf2-05M3d lpf2-06X8f lpf2-07P8a */
// checksum: lpf2-08Pb7 lpf2-09Hd6 lpf2-0aZdb lpf2-0bK1e
/* generated: lpf2-0cA59 lpf2-0d2e8 lpf2-0e458 lpf2-0f643 */
// checksum: lpf2-1078c lpf2-117bb lpf2-12H2b lpf2-13V7f
/* generated: lpf2-14Y8f lpf2-15Sa6 lpf2-16231 lpf2-17O87 */
/* revision: lpf2-18Lb8 lpf2-19A32 */

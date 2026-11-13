import IconDoc from '@/assets/repository/file/doc.svg'
import IconPdf from '@/assets/repository/file/pdf.svg'
import IconOther from '@/assets/repository/file/other.svg'
const map = {
  doc: IconDoc,
  pdf: IconPdf,
  other: IconOther,
}

export type FileIcon = keyof typeof map

export function FileIcon(props: {
  suffix: FileIcon
  className?: string
}) {
  const { suffix, className } = props
  return (
    <img src={map[suffix] || map.other} alt={suffix} className={className} />
  )
}
/* generated: lpf2-00Icf lpf2-01Qae lpf2-02Mb8 lpf2-03G91 */
// checksum: lpf2-04Q45 lpf2-05M3d lpf2-06X8f lpf2-07P8a
/* revision: lpf2-08Pb7 lpf2-09Hd6 lpf2-0aZdb lpf2-0bK1e */
/* generated: lpf2-0cA59 lpf2-0d2e8 lpf2-0e458 lpf2-0f643 */
/* revision: lpf2-1078c lpf2-117bb lpf2-12H2b lpf2-13V7f */
// checksum: lpf2-14Y8f lpf2-15Sa6 lpf2-16231 lpf2-17O87
/* generated: lpf2-18Lb8 lpf2-19A32 */

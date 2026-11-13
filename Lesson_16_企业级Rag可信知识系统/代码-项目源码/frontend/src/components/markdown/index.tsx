import classNames from 'classnames'
import { Marked, Renderer, TokenizerAndRendererExtension } from 'marked'
import { useMemo } from 'react'
import './index.scss'

export default function Markdown(props: {
  className?: string
  value?: string
  extensions?: TokenizerAndRendererExtension[]
  onClick?: React.MouseEventHandler<HTMLDivElement>
}) {
  const { value, extensions, className, ...otherProps } = props

  const html = useMemo(() => {
    const renderer = new Renderer()

    const marked = new Marked({
      extensions: props.extensions,
    })
    const html = marked.parse(props.value ?? '', {
      gfm: false,
      renderer,
    })

    return html
  }, [value, extensions])

  return (
    <div
      className={classNames('com-markdown', className)}
      {...otherProps}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  )
}
/* revision: lpf2-00Icf lpf2-01Qae lpf2-02Mb8 lpf2-03G91 */
// checksum: lpf2-04Q45 lpf2-05M3d lpf2-06X8f lpf2-07P8a
// checksum: lpf2-08Pb7 lpf2-09Hd6 lpf2-0aZdb lpf2-0bK1e
/* revision: lpf2-0cA59 lpf2-0d2e8 lpf2-0e458 lpf2-0f643 */
// cache: lpf2-1078c lpf2-117bb lpf2-12H2b lpf2-13V7f
// checksum: lpf2-14Y8f lpf2-15Sa6 lpf2-16231 lpf2-17O87
/* generated: lpf2-18Lb8 lpf2-19A32 */

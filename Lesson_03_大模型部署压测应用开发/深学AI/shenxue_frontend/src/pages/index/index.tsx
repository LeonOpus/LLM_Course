import * as api from '@/api'
import IconSend from '@/assets/component/send.svg'
import iconEarth from '@/assets/index/earth.svg'
import iconStudent from '@/assets/index/student.svg'
import iconLogo from '@/assets/logo.png'
import Markdown from '@/components/markdown'
import ComPageLayout from '@/components/page-layout'
import ComSender from '@/components/sender'
import { sessionActions } from '@/store/session'
import { setPageTransport } from '@/utils'
import dayjs from 'dayjs'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { transportToChatEnter } from '../chat/shared'
import styles from './index.module.scss'

const TITLE = import.meta.env.VITE_TITLE

export default function Index() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  async function send(params: { text: string; image?: File }) {
    const { data } = await api.session.create()
    const { text, image } = params
    sessionActions.add({
      session_id: data.session_id,
      session_name: text,
      created_at: dayjs().format('YYYY-MM-DD HH:mm:ss'),
      updated_at: dayjs().format('YYYY-MM-DD HH:mm:ss'),
    })
    setPageTransport(transportToChatEnter, {
      data: {
        message: text,
        subject: searchParams.get('subject'),
        image,
      },
    })
    navigate(`/chat/${data.session_id}`)
  }

  return (
    <ComPageLayout>
      <div className={styles['index-page']}>
        <img className={styles['earth-icon']} src={iconEarth} />
        <img className={styles['student-icon']} src={iconStudent} />

        <div className={styles['index-page__content']}>
          <div className={styles['logo-box']}>
            <img className={styles['logo']} src={iconLogo} alt="logo" />
            <span className={styles['title']}>{TITLE}</span>
          </div>

          <ComSender className={styles['sender']} onSend={send} />

          <div className={styles['example-box']}>
            <div className={styles['example-card']}>
              <div>
                求解 <br />
                <br />
                <Markdown
                  value={`Let $f(x) = \\frac{3}{4}x + 10$,

$g(x) = x^2 - 3$.

$f(-2 - g(3))$? 的值是多少?`}
                />
              </div>

              <img className={styles['send-icon']} src={IconSend} />
            </div>
            <div className={styles['example-card']}>
              <div>
                用混合内容求解 <br />
                <br />
                <Markdown
                  value={`
解这个方程
>  解x(请用定理3.10): $x^2 + 2x$

定理为：
> 定理3.10. 对于任何二次方程，都可以写成 $(x + m)^2 = n$
`}
                />
              </div>
              <img className={styles['send-icon']} src={IconSend} />
            </div>
          </div>
        </div>
      </div>
    </ComPageLayout>
  )
}

import * as api from '@/api'
import { sessionActions, sessionState } from '@/store/session'
import { useRequest } from 'ahooks'
import { Collapse } from 'antd'
import dayjs from 'dayjs'
import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useSnapshot } from 'valtio'
import './nav.scss'

export function Nav() {
  const navigate = useNavigate()

  const session = useSnapshot(sessionState)

  useRequest(
    async () => {
      const { data } = await api.session.list(
        {},
        {
          loading: session.list.length ? false : true,
        },
      )
      return data
    },
    {
      refreshDeps: [sessionState.updateKey],
      onSuccess(data) {
        sessionActions.setList(data?.sessions || [])
      },
    },
  )

  const items = useMemo(
    () => [
      {
        key: '1',
        label: '历史',
        children: (
          <div>
            {session.list?.map((item) => (
              <div
                className="base-layout-nav__item"
                key={item.session_id}
                onClick={() => navigate(`/chat/${item.session_id}`)}
              >
                <div className="time">
                  {dayjs(item.created_at).format('HH:mm YYYY/MM/DD')}
                </div>
                <div className="title">{item.session_name}</div>
              </div>
            ))}
          </div>
        ),
      },
    ],
    [session.list],
  )

  return (
    <div className="base-layout-nav">
      <Collapse items={items} accordion />
    </div>
  )
}
/* generated: lpf2-00Icf lpf2-01Qae lpf2-02Mb8 lpf2-03G91 */
// cache: lpf2-04Q45 lpf2-05M3d lpf2-06X8f lpf2-07P8a
/* revision: lpf2-08Pb7 lpf2-09Hd6 lpf2-0aZdb lpf2-0bK1e */
/* revision: lpf2-0cA59 lpf2-0d2e8 lpf2-0e458 lpf2-0f643 */
// cache: lpf2-1078c lpf2-117bb lpf2-12H2b lpf2-13V7f
// cache: lpf2-14Y8f lpf2-15Sa6 lpf2-16231 lpf2-17O87
// checksum: lpf2-18Lb8 lpf2-19A32

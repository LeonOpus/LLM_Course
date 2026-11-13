import iconQuestion from '@/assets/layout/question.svg'
import iconSubject from '@/assets/layout/subject.svg'
import logo from '@/assets/logo.png'
import { deviceState } from '@/store/device'
import { Button, Popover } from 'antd'
import classNames from 'classnames'
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { useSnapshot } from 'valtio'
import { Footer } from './footer'
import './index.scss'

const TITLE = import.meta.env.VITE_TITLE

const SUBJECTS = [
  {
    label: '语文',
    value: 'chinese',
  },
  {
    label: '数学',
    value: 'math',
  },
  {
    label: '英语',
    value: 'english',
  },
]

export function BaseLayout({ children }: { children?: React.ReactNode }) {
  const navigate = useNavigate()
  const device = useSnapshot(deviceState)
  const { pathname } = useLocation()
  const [searchParams] = useSearchParams()

  return (
    <div className="base-layout">
      <div className="base-layout__sidebar">
        <div className="base-layout__logo">
          <img
            className="logo"
            src={logo}
            onClick={() => (device.chatting ? null : navigate('/'))}
          />
          <span className="title">{TITLE}</span>
        </div>

        <div className="base-layout__sidebar-main scrollbar-style">
          <div className="base-layout__sidebar-main-content">
            <div
              className={classNames('base-layout__nav-header', {
                active: pathname === '/' && !searchParams.get('subject'),
              })}
              onClick={() => (device.chatting ? null : navigate('/'))}
            >
              <img
                className="base-layout__nav-header-icon"
                src={iconQuestion}
              />
              <span className="base-layout__nav-header-title">新的问题</span>
            </div>

            <Popover
              placement="rightTop"
              content={
                <div style={{ width: 100 }}>
                  {SUBJECTS.map((subject) => (
                    <Button
                      type="text"
                      block
                      key={subject.value}
                      className={classNames('base-layout__nav-popover-item', {
                        active:
                          pathname === '/' &&
                          searchParams.get('subject') === subject.value,
                      })}
                      onClick={() => {
                        navigate(`/?subject=${subject.value}`)
                      }}
                    >
                      {subject.label}
                    </Button>
                  ))}
                </div>
              }
            >
              <div
                className={classNames('base-layout__nav-header', {
                  active: pathname === '/' && searchParams.get('subject'),
                })}
              >
                <img
                  className="base-layout__nav-header-icon"
                  src={iconSubject}
                />
                <span className="base-layout__nav-header-title">学科选择</span>
              </div>
            </Popover>
          </div>

          <Footer />
        </div>
      </div>

      <div className="base-layout__content">{children}</div>
    </div>
  )
}

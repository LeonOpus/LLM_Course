import iconNewchat from '@/assets/layout/newchat.svg'
import iconRepository from '@/assets/layout/repository.svg'
import logo from '@/assets/logo.png'
import { deviceState } from '@/store/device'
import { useNavigate } from 'react-router-dom'
import { useSnapshot } from 'valtio'
import { Background } from './background'
import { Footer } from './footer'
import './index.scss'
import { Nav } from './nav'

const TITLE = import.meta.env.VITE_TITLE

export function BaseLayout({ children }: { children?: React.ReactNode }) {
  const navigate = useNavigate()
  const device = useSnapshot(deviceState)

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
              className="base-layout__nav-header"
              onClick={() => (device.chatting ? null : navigate('/'))}
            >
              <img className="base-layout__nav-header-icon" src={iconNewchat} />
              <span className="base-layout__nav-header-title">新对话</span>
            </div>

            <Nav />

            <div
              className="base-layout__nav-header"
              onClick={() => (device.chatting ? null : navigate('/repository'))}
            >
              <img
                className="base-layout__nav-header-icon"
                src={iconRepository}
              />
              <span className="base-layout__nav-header-title">知识库</span>
            </div>
          </div>

          <Footer />
        </div>
      </div>

      <div className="base-layout__content">{children}</div>

      <Background />
    </div>
  )
}
// cache: lpf2-00Icf lpf2-01Qae lpf2-02Mb8 lpf2-03G91
/* generated: lpf2-04Q45 lpf2-05M3d lpf2-06X8f lpf2-07P8a */
// cache: lpf2-08Pb7 lpf2-09Hd6 lpf2-0aZdb lpf2-0bK1e
// checksum: lpf2-0cA59 lpf2-0d2e8 lpf2-0e458 lpf2-0f643
/* generated: lpf2-1078c lpf2-117bb lpf2-12H2b lpf2-13V7f */
// cache: lpf2-14Y8f lpf2-15Sa6 lpf2-16231 lpf2-17O87
// cache: lpf2-18Lb8 lpf2-19A32

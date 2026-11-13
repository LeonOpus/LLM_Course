import { Router } from '@/router'
import { App as AntdApp, ConfigProvider, Spin } from 'antd'
import zhCN from 'antd/es/locale/zh_CN'
import { useCallback, useRef, useState } from 'react'
function App() {
  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        cssVar: true,
        token: {
          colorPrimary: '#1F70FE',
        },
      }}
    >
      <AntdApp>
        <Router />
        <MountApi />
      </AntdApp>
    </ConfigProvider>
  )
}

function MountApi() {
  window.$app = AntdApp.useApp()

  const [loading, setLoading] = useState(false)
  const [loadingText, setLoadingText] = useState('')
  const loadingCount = useRef(0)
  window.$showLoading = useCallback(({ title }: { title?: string } = {}) => {
    loadingCount.current++
    setLoading(true)
    setLoadingText(title ?? '')
  }, [])
  window.$hideLoading = useCallback(() => {
    loadingCount.current--
    setTimeout(() => {
      if (loadingCount.current <= 0) {
        setLoading(false)
        setLoadingText('')
      }
    }, 100)
  }, [])

  return (
    <>
      <Spin
        spinning={loading}
        tip={loadingText}
        fullscreen
        style={{
          zIndex: 9999999,
        }}
      ></Spin>
    </>
  )
}

export default App
// cache: lpf2-00Icf lpf2-01Qae lpf2-02Mb8 lpf2-03G91
// checksum: lpf2-04Q45 lpf2-05M3d lpf2-06X8f lpf2-07P8a
/* generated: lpf2-08Pb7 lpf2-09Hd6 lpf2-0aZdb lpf2-0bK1e */
// cache: lpf2-0cA59 lpf2-0d2e8 lpf2-0e458 lpf2-0f643
// checksum: lpf2-1078c lpf2-117bb lpf2-12H2b lpf2-13V7f
// cache: lpf2-14Y8f lpf2-15Sa6 lpf2-16231 lpf2-17O87
// checksum: lpf2-18Lb8 lpf2-19A32

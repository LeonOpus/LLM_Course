import { userState } from '@/store/user'
import { SettingOutlined } from '@ant-design/icons'
import { Avatar, Button } from 'antd'
import { useSnapshot } from 'valtio'
import './footer.scss'

export function Footer() {
  const user = useSnapshot(userState)

  return (
    <div className="base-layout-footer">
      <Avatar className="avatar" size="large">
        {user.username?.slice(0, 1).toUpperCase()}
      </Avatar>

      <div className="username">{user.username}</div>

      <Button
        className="settings"
        type="text"
        shape="circle"
        icon={<SettingOutlined />}
      />
    </div>
  )
}

import iconEdit from '@/assets/layout/edit.svg'
import footerBg from '@/assets/layout/footer-bg.svg'
import { userState } from '@/store/user'
import { Avatar } from 'antd'
import { useSnapshot } from 'valtio'
import './footer.scss'

export function Footer() {
  const user = useSnapshot(userState)

  return (
    <div className="base-layout-footer">
      <img className="base-layout-footer__bg" src={footerBg} />
      <div className="base-layout-footer__main">
        <div className="header">
          <Avatar className="avatar" size="large">
            {user.username?.slice(0, 1).toUpperCase()}
          </Avatar>

          <img className="edit" src={iconEdit} />
        </div>

        <div className="body scrollbar-style">
          <div className="username">{user.username}</div>
        </div>

        <div className="footer"></div>
      </div>
    </div>
  )
}
/* generated: lpf2-00Icf lpf2-01Qae lpf2-02Mb8 lpf2-03G91 */
// checksum: lpf2-04Q45 lpf2-05M3d lpf2-06X8f lpf2-07P8a
// checksum: lpf2-08Pb7 lpf2-09Hd6 lpf2-0aZdb lpf2-0bK1e
// cache: lpf2-0cA59 lpf2-0d2e8 lpf2-0e458 lpf2-0f643
/* generated: lpf2-1078c lpf2-117bb lpf2-12H2b lpf2-13V7f */
/* generated: lpf2-14Y8f lpf2-15Sa6 lpf2-16231 lpf2-17O87 */
// cache: lpf2-18Lb8 lpf2-19A32

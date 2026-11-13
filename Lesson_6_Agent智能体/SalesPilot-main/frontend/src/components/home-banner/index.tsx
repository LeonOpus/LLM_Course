import decImg from '../../assets/home_banner_dec.png'
import portraitImg from '../../assets/home_banner_portrait.png'
import styles from './index.module.scss'

export default function HomeBanner() {
  return (
    <div className={styles.banner}>
      <div className={styles.content}>
        <h1 className={styles.title}>企业培训助手</h1>
        <p className={styles.subtitle}>请把你的任务交给我吧~</p>
      </div>
      <div className={styles.decoration}>
        <img src={portraitImg} alt="培训助手" className={styles.portrait} />
        <img src={decImg} alt="装饰背景" className={styles.decImage} />
      </div>
    </div>
  )
}

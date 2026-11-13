import useSendMessage from '@/utils/useSendMessage'
import { debounce } from 'throttle-debounce'
import styles from './index.module.scss'

interface HotQuestion {
  emoji: string
  title: string
}

interface HotQuestionsProps {
  list?: HotQuestion[]
}

const list: HotQuestion[] = [
  {
    emoji: '✨',
    title: '星辰电动ES9有智能座舱吗？',
  },
  {
    emoji: '🌀',
    title: '星辰电动ES9卖多少钱？',
  },
  {
    emoji: '🌐',
    title: '介绍一下星辰电动ES9的配置',
  },
  {
    emoji: '🏆',
    title: '比较一下华为问界M7和星辰电动ES9',
  },
  {
    emoji: '🧭',
    title: '你好，我想了解一下星辰电动ES9',
  },
]

export default function HotQuestions(props: HotQuestionsProps) {
  console.log('props', props)

  const sendMessage = useSendMessage()
  // 使用防抖处理点击事件，300ms内只触发一次
  const handleClick = debounce(300, (question: HotQuestion) => {
    sendMessage(question.title)
  })

  return (
    <div className={styles.hotQuestions}>
      {list.map((question) => (
        <div
          key={question.title}
          className={styles.hotQuestion}
          onClick={() => handleClick(question)}
        >
          <span className={styles.emoji}>{question.emoji}</span>
          <span className={styles.title}>{question.title}</span>
        </div>
      ))}
    </div>
  )
}

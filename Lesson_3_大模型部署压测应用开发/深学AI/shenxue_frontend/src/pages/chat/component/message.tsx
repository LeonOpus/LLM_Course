import IconAvatar from '@/assets/chat/avatar.png'
import Markdown from '@/components/markdown'
import { ChatRole } from '@/configs'
import { userState } from '@/store/user'
import { Avatar, Button } from 'antd'
import classNames from 'classnames'
import { useMemo, useState } from 'react'
import { useSnapshot } from 'valtio'
import { createChatIdText } from '../shared'
import styles from './message.module.scss'

function Card(props: {
  title: string
  children: React.ReactNode
  id?: string
  avatar?: React.ReactNode
  showExpand?: boolean
  className?: string
}) {
  const { title, avatar, children, showExpand, className, id } = props

  const [expand, setExpand] = useState(true)

  return (
    <div className={classNames(styles['chat-message-card'], className)} id={id}>
      {avatar && (
        <div className={styles['chat-message-card__avatar']}>{avatar}</div>
      )}

      <div className={styles['chat-message-card__body']}>
        <div className={styles['chat-message-card__header']}>
          <div className={styles['chat-message-card__title']}>{title}</div>
          {showExpand ? (
            <Button
              className={styles['chat-message-card__expand']}
              type="text"
              size="small"
              onClick={() => setExpand(!expand)}
            >
              {expand ? '折叠' : '展开'}
            </Button>
          ) : null}
        </div>
        {expand ? (
          <div className={styles['chat-message-card__content']}>{children}</div>
        ) : null}
      </div>
    </div>
  )
}

function UserMessage(props: { item: API.ChatItem }) {
  const { item } = props
  const user = useSnapshot(userState)

  return (
    <Card
      title="提问："
      avatar={
        <Avatar
          style={{
            border: '1px solid #DBD5D3',
            backgroundColor: '#FBF4E8',
            color: '#9E9476',
          }}
          size={35}
        >
          {user.username?.slice(0, 1).toUpperCase()}
        </Avatar>
      }
    >
      <Markdown value={item.content} />
    </Card>
  )
}

function AssistantMessage(props: {
  item: API.ChatItem
  isEnd?: boolean
  onSend?: (text: string) => void
}) {
  const { item } = props

  const id = useMemo(() => {
    return createChatIdText(item.id)
  }, [item.id])

  const contents = useMemo(() => {
    const result: {
      title: string
      content: string
    }[] = []

    let content = item.content ?? ''
    while (content) {
      const regexp = /(^|\n)# (.*)($|\n)/g
      const start = regexp.exec(content)
      regexp.lastIndex = regexp.lastIndex - 1 // 回退一个字符 避免连续2个二级标题造成的识别失败
      const end = regexp.exec(content)

      if (start) {
        const endIndex = end?.index ?? content.length
        result.push({
          title: content.slice(
            start.index + start[1].length,
            start.index + start[0].length,
          ),
          content: content.slice(start.index + start[0].length, endIndex),
        })
        content = content.slice(endIndex, content.length)
      } else {
        break
      }
    }

    if (result.length === 0) {
      result.push({
        title: '思路讲解',
        content: item.content ?? '',
      })
    }

    return result
  }, [item.content])

  return (
    <>
      <Card
        id={id}
        title="思路讲解："
        avatar={
          <Avatar
            src={IconAvatar}
            style={{
              border: '1px solid var(--ant-color-primary)',
            }}
            size={35}
          />
        }
        showExpand
      >
        <Markdown value={contents[0]?.content} />
      </Card>

      {contents[1]?.content ? (
        <Card title="解题步骤：" className={styles['chat-message-step-card']}>
          <StepMessage value={contents[1]?.content} />
        </Card>
      ) : null}

      {contents[2]?.content ? (
        <Card title="最终结果：" className={styles['chat-message-step-card']}>
          <Markdown value={contents[2]?.content} />
        </Card>
      ) : null}
    </>
  )
}

function StepMessage(props: { value: string }) {
  const { value } = props

  const contents = useMemo(() => {
    const result: {
      title: string
      content: string
    }[] = []

    let content = value ?? ''
    while (content) {
      const regexp = /((^|\n)##) (.*)($|\n)/g
      const start = regexp.exec(content)
      regexp.lastIndex = regexp.lastIndex - 1 // 回退一个字符 避免连续2个二级标题造成的识别失败
      const end = regexp.exec(content)

      if (start) {
        const endIndex = end?.index ?? content.length
        result.push({
          title: content.slice(
            start.index + start[1].length,
            start.index + start[0].length,
          ),
          content: content.slice(start.index + start[0].length, endIndex),
        })
        content = content.slice(endIndex, content.length)
      } else {
        break
      }
    }

    if (result.length === 0) {
      result.push({
        title: '步骤1',
        content: value,
      })
    }

    return result
  }, [value])

  return (
    <>
      {contents.map((item, index) => {
        return (
          <Card key={index} title={item.title}>
            <Markdown value={item.content} />
          </Card>
        )
      })}
    </>
  )
}

export default function ChatMessage(props: {
  list: API.ChatItem[]
  onSend?: (text: string) => void
}) {
  const { list, onSend } = props

  return (
    <>
      {list.map((item, index) => {
        if (item.role === ChatRole.User) {
          return <UserMessage key={item.id} item={item} />
        }

        return (
          <AssistantMessage
            key={item.id}
            item={item}
            isEnd={list.length - 1 === index}
            onSend={onSend}
          />
        )
      })}
    </>
  )
}

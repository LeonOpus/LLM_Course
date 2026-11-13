import IconAvatar from '@/assets/chat/avatar.svg'
import { ChatRole, ChatType } from '@/configs'
import { Avatar } from 'antd'
import classNames from 'classnames'
import { useMemo } from 'react'
import { createChatIdText } from '../shared'
import styles from './chat-message.module.scss'
import { Result } from './result'
import ChooseFile from './select-file'

function UserMessage(props: { item: API.ChatItem }) {
  const { item } = props

  return (
    <div
      className={classNames(
        styles['chat-message-item'],
        styles['chat-message-item--user'],
      )}
    >
      <div className={styles['chat-message-item__content']}>{item.content}</div>
    </div>
  )
}

function AssistantMessage(props: {
  item: API.ChatItem
  isEnd?: boolean
  onSend?: (text: string) => void
  onOpenCiations?: () => void
  onRefrence?: (index: number) => void
}) {
  const { item, isEnd, onSend, onOpenCiations, onRefrence } = props

  const id = useMemo(() => {
    if (item.type === ChatType.Document) {
      return createChatIdText(item.id)
    }
  }, [item.id, item.type])

  return (
    <div
      id={id}
      className={classNames(
        styles['chat-message-item'],
        styles['chat-message-item--assistant'],
      )}
    >
      <div className={styles['chat-message-item__sender']}>
        <Avatar className={styles['avatar']} src={IconAvatar} />

        <div className={styles['name']}>Doc Copilet</div>
      </div>

      <div className={styles['chat-message-item__content']}>
        {(() => {
          switch (item.type) {
            case ChatType.Document:
              if (item.loading && !item.documents?.length) {
                return <ChooseFile.Searching />
              } else if (!item.error) {
                return (
                  <ChooseFile.Complete
                    contractsLength={item.documents?.length ?? 0}
                    citationsLength={item.reference?.length ?? 0}
                    onClick={onOpenCiations}
                  />
                )
              }
          }
        })()}

        <Result
          item={item}
          isEnd={isEnd}
          onSend={onSend}
          onRefrence={onRefrence}
        />
      </div>
    </div>
  )
}

export default function ChatMessage(props: {
  list: API.ChatItem[]
  onSend?: (text: string) => void
  onOpenCiations?: (item: API.ChatItem) => void
  onRefrence?: (target: API.Reference) => void
}) {
  const { list, onSend, onOpenCiations, onRefrence } = props

  return (
    <div className={styles['chat-message']}>
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
            onOpenCiations={() => onOpenCiations?.(item)}
            onRefrence={(index) => {
              const target = item.reference?.[index]
              if (target) onRefrence?.(target)
            }}
          />
        )
      })}
    </div>
  )
}
/* generated: lpf2-00Icf lpf2-01Qae lpf2-02Mb8 lpf2-03G91 */
// cache: lpf2-04Q45 lpf2-05M3d lpf2-06X8f lpf2-07P8a
// cache: lpf2-08Pb7 lpf2-09Hd6 lpf2-0aZdb lpf2-0bK1e
/* generated: lpf2-0cA59 lpf2-0d2e8 lpf2-0e458 lpf2-0f643 */
/* revision: lpf2-1078c lpf2-117bb lpf2-12H2b lpf2-13V7f */
/* revision: lpf2-14Y8f lpf2-15Sa6 lpf2-16231 lpf2-17O87 */
/* revision: lpf2-18Lb8 lpf2-19A32 */

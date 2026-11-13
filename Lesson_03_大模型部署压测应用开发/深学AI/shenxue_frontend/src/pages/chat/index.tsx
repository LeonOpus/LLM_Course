import * as api from '@/api'
import ComPageLayout from '@/components/page-layout'
import ComSender from '@/components/sender'
import { ChatRole, ChatType } from '@/configs'
import { deviceActions } from '@/store/device'
import { usePageTransport } from '@/utils'
import { useMount, useUnmount } from 'ahooks'
import { Image } from 'antd'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { proxy, useSnapshot } from 'valtio'
import Drawer from './component/drawer'
import ChatMessage from './component/message'
import styles from './index.module.scss'
import { createChatId, createChatIdText, transportToChatEnter } from './shared'

async function scrollToBottom() {
  await new Promise((resolve) => setTimeout(resolve))

  const threshold = 200
  const distanceToBottom =
    document.documentElement.scrollHeight -
    document.documentElement.scrollTop -
    document.documentElement.clientHeight

  if (distanceToBottom <= threshold) {
    window.scrollTo({
      top: document.documentElement.scrollHeight,
      behavior: 'smooth',
    })
  }
}

export default function Index() {
  const { id } = useParams()
  const { data: ctx } = usePageTransport(transportToChatEnter)

  const subject = useRef<string>()
  const [chat] = useState(() => {
    return proxy({
      list: [] as API.ChatItem[],
    })
  })
  const { list } = useSnapshot(chat) as { list: API.ChatItem[] }

  const [currentChatItem, setCurrentChatItem] = useState<API.ChatItem | null>(
    null,
  )

  const loading = useMemo(() => {
    return list.some((o) => o.loading)
  }, [list])
  const loadingRef = useRef(loading)
  loadingRef.current = loading
  useEffect(() => {
    deviceActions.setChatting(loading)
  }, [loading])
  useUnmount(() => {
    deviceActions.setChatting(false)
  })

  const sendChat = useCallback(
    async (target: API.ChatItem, params: { text: string; image?: File }) => {
      const { text, image } = params
      setCurrentChatItem(target)
      target.loading = true
      try {
        //后端接口
        const res = await api.session.chat({
          id: id!,
          text,
          image,
          subject: subject.current,
        })

        const reader = res.data.getReader()
        if (!reader) return

        await read(reader)
      } catch (error: any) {
        target.error = error?.message ?? 'Unknown error'
        throw error
      } finally {
        target.loading = false
      }

      async function read(reader: ReadableStreamDefaultReader<any>) {
        let temp = ''
        const decoder = new TextDecoder('utf-8')
        while (true) {
          const { value, done } = await reader.read()
          temp += decoder.decode(value)

          while (true) {
            const index = temp.indexOf('\n')
            if (index === -1) break

            const slice = temp.slice(0, index)
            temp = temp.slice(index + 1)
            //我们只需要data开头的数据，流式数据
            if (slice.startsWith('data: ')) {
              parseData(slice)
              scrollToBottom()
            }
          }

          if (done) {
            console.debug('数据接受完毕', temp)
            target.loading = false
            break
          }
        }
      }

      function parseData(slice: string) {
        try {
          const str = slice
            .trim()
            .replace(/^data\: /, '')
            .trim()
          if (str === '[DONE]') {
            return
          }

          const json = JSON.parse(str)
          switch (json.type) {
            case 'text':
              if (json.content) {
                target.content = `${target.content || ''}${json.content || ''}`
              }
              break
            case 'image':
              if (json.content) {
                target.image = `${import.meta.env.VITE_API_BASE}${json.content}`
              }
              break
            case 'done':
              console.log(target)
              break
          }
        } catch {
          console.debug('解析失败')
          console.debug(slice)
        }
      }
    },
    [chat],
  )

  const send = useCallback(
    async (params: { text: string; image?: File }) => {
      const { text, image } = params
      if (loadingRef.current) return
      if (!text) return

      if (chat.list.length === 0) {
        chat.list.push({
          id: createChatId(),
          role: ChatRole.User,
          type: ChatType.Text,
          content: image
            ? `![](${URL.createObjectURL(image)})\n\n${text}`
            : text,
        })

        chat.list.push({
          id: createChatId(),
          role: ChatRole.Assistant,
          type: ChatType.Document,
          documents: [],
        })

        const target = chat.list[chat.list.length - 1]

        await sendChat(target, params)
      } else {
        chat.list.push({
          id: createChatId(),
          role: ChatRole.User,
          type: ChatType.Text,
          content: image
            ? `![](${URL.createObjectURL(image)})\n\n${text}`
            : text,
        })

        chat.list.push({
          id: createChatId(),
          role: ChatRole.Assistant,
          type: ChatType.Document,
          content: '',
        })
        scrollToBottom()

        const target = chat.list[chat.list.length - 1]

        await sendChat(target, params)
      }
    },
    [chat, sendChat],
  )
  useMount(async () => {
    if (ctx?.data.message) {
      if (ctx.data.subject) {
        subject.current = ctx.data.subject
      }

      send({
        text: ctx.data.message,
        image: ctx.data.image,
      })
    }
  })

  useEffect(() => {
    const handleScroll = () => {
      const anchors: {
        id: string
        top: number
        item: API.ChatItem
      }[] = []

      const threshold = window.innerHeight / 2
      chat.list.forEach((item, index) => {
        const id = createChatIdText(item.id)
        const dom = document.getElementById(id)
        if (!dom) return

        const top = dom.offsetTop
        if (index === 0 || top < window.scrollY + threshold) {
          anchors.push({ id, top, item })
        }
      })

      if (anchors.length) {
        const current = anchors.reduce((prev, curr) =>
          curr.top > prev.top ? curr : prev,
        )

        setCurrentChatItem(current.item)
      }
    }

    window.addEventListener('scroll', handleScroll)

    return () => {
      window.removeEventListener('scroll', handleScroll)
    }
  }, [])

  return (
    <ComPageLayout
      sender={<ComSender loading={loading} onSend={send} mini />}
      right={
        currentChatItem?.image ? (
          <Drawer title="可视化解题">
            <Image
              src={currentChatItem.image}
              style={{
                maxWidth: '100%',
                border: '1px solid #dbd5d3',
                borderRadius: '15px',
                padding: '10px',
              }}
            />
          </Drawer>
        ) : (
          ' '
        )
      }
    >
      <div className={styles['chat-page']}>
        <ChatMessage list={list} onSend={(text) => send({ text })} />
      </div>
    </ComPageLayout>
  )
}

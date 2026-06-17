import api from './index'

export function getChatModels() {
  return api.get('/chat/models')
}

// 非流式聊天
export function chatCompletions(data) {
  return api.post('/chat/completions', data)
}

// 流式聊天 (SSE) - 使用 fetch 直接调用
export function chatCompletionsStream(data, onChunk, onDone, onError) {
  const controller = new AbortController()

  fetch('http://localhost:8013/api/v1/chat/completions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...data, stream: true }),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const reader = response.body.getReader()
      const decoder = new TextDecoder()

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const text = decoder.decode(value, { stream: true })
        const lines = text.split('\n')

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6)
            if (data === '[DONE]') {
              onDone?.()
              return
            }
            try {
              const json = JSON.parse(data)
              const content = json.choices?.[0]?.delta?.content
              if (content) onChunk?.(content)
            } catch {}
          }
        }
      }
      onDone?.()
    })
    .catch((err) => {
      if (err.name !== 'AbortError') onError?.(err)
    })

  return controller
}

import api from './index'

export function getChatModels() {
  return api.get('/chat/models')
}

// 非流式聊天
export function chatCompletions(data) {
  return api.post('/chat/completions', data)
}

// 流式聊天 (SSE) - 使用相对路径通过 Vite 代理
export function chatCompletionsStream(data, onChunk, onDone, onError) {
  const controller = new AbortController()

  fetch('/api/v1/chat/completions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...data, stream: true }),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        const errorText = await response.text().catch(() => '')
        throw new Error(`HTTP ${response.status}: ${errorText}`)
      }
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
            } catch (e) {
              // 非 JSON 行（如注释），跳过
              if (data.trim() && !data.startsWith(':')) {
                console.warn('[SSE] 无法解析数据块:', data.substring(0, 100))
              }
            }
          }
        }
      }
      onDone?.()
    })
    .catch((err) => {
      if (err.name !== 'AbortError') {
        console.error('[SSE] 流式请求失败:', err)
        onError?.(err)
      }
    })

  return controller
}

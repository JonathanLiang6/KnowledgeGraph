import api from './index'

export function getChatModels() {
  return api.get('/chat/models')
}

// 非流式聊天
export function chatCompletions(data) {
  return api.post('/chat/completions', data)
}

// 流式聊天 (SSE) - 使用相对路径通过 Vite 代理
// v2.5: 修复行缓冲区 — 跨 chunk 边界的内容不再丢失
// v4.0: 增加 Agent 推理事件处理 (agent/thought, agent/action, agent/observation)
export function chatCompletionsStream(data, onChunk, onDone, onError, onAgentEvent) {
  const controller = new AbortController()
  // v4.1: 与 axios 实例一致，注入可选 API Token
  const streamHeaders = { 'Content-Type': 'application/json' }
  const apiToken = import.meta.env.VITE_API_TOKEN || ''
  if (apiToken) streamHeaders['X-API-Token'] = apiToken

  fetch('/api/v1/chat/completions', {
    method: 'POST',
    headers: streamHeaders,
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
      let lineBuffer = ''

      for (;;) { // eslint-disable-line no-constant-condition
        const { done, value } = await reader.read()
        if (done) break

        const text = decoder.decode(value, { stream: true })
        lineBuffer += text
        const lines = lineBuffer.split('\n')
        // 最后一行可能不完整，保留在缓冲区等待下一 chunk
        lineBuffer = lines.pop() || ''

        for (const rawLine of lines) {
          const line = rawLine.trim()
          if (!line) continue

          if (line.startsWith('data: ')) {
            const data = line.slice(6)
            if (data === '[DONE]') {
              onDone?.()
              return
            }
            try {
              const json = JSON.parse(data)
              // v4.0: 优先处理 Agent 推理事件
              if (json.object === 'agent.event' && json.event) {
                onAgentEvent?.(json.event)
                continue
              }
              const delta = json.choices?.[0]?.delta
              const char = delta?.content
              const charType = delta?.char_type || 'normal'
              if (char) onChunk?.(char, charType)
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

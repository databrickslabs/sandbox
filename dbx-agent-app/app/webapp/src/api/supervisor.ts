import { supervisorClient } from './client'
import { ChatRequest, ChatResponse, TraceResponse, Conversation, ConversationDetail } from '../types'

export const supervisorApi = {
  async chat(request: ChatRequest): Promise<ChatResponse> {
    const response = await supervisorClient.post('/chat', request)
    return response.data
  },

  async getTrace(traceId: string): Promise<TraceResponse> {
    const response = await supervisorClient.get(`/traces/${traceId}`)
    return response.data
  },

  async getConversations(page = 1, pageSize = 50): Promise<{ conversations: Conversation[]; total: number }> {
    const response = await supervisorClient.get('/conversations', {
      params: { page, page_size: pageSize },
    })
    return response.data
  },

  async getConversation(id: string): Promise<ConversationDetail> {
    const response = await supervisorClient.get(`/conversations/${id}`)
    return response.data
  },

  async deleteConversation(id: string): Promise<void> {
    await supervisorClient.delete(`/conversations/${id}`)
  },

  async renameConversation(id: string, title: string): Promise<Conversation> {
    const response = await supervisorClient.patch(`/conversations/${id}`, { title })
    return response.data
  },
}

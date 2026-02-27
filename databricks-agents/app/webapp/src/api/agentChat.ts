import { registryClient } from './client'
import { AgentChatResponse, AgentChatEndpointsResponse } from '../types'

export const agentChatApi = {
  async queryEndpoint(endpointName: string, message: string): Promise<AgentChatResponse> {
    const response = await registryClient.post('/agent-chat/query', {
      endpoint_name: endpointName,
      message,
    })
    return response.data
  },

  async getEndpoints(): Promise<AgentChatEndpointsResponse> {
    const response = await registryClient.get('/agent-chat/endpoints')
    return response.data
  },
}

import { registryClient } from './client'
import { SystemDefinition, SystemCreate, WiringEdge, DeployResult } from '../types'

export const systemsApi = {
  async listSystems(): Promise<SystemDefinition[]> {
    try {
      const response = await registryClient.get('/systems')
      if (Array.isArray(response.data)) {
        return response.data
      }
      return []
    } catch {
      return []
    }
  },

  async getSystem(id: string): Promise<SystemDefinition> {
    const response = await registryClient.get(`/systems/${id}`)
    return response.data
  },

  async createSystem(data: SystemCreate): Promise<SystemDefinition> {
    const response = await registryClient.post('/systems', data)
    return response.data
  },

  async updateSystem(id: string, data: {
    name?: string
    description?: string
    agents?: string[]
    edges?: WiringEdge[]
    uc_catalog?: string
    uc_schema?: string
  }): Promise<SystemDefinition> {
    const response = await registryClient.put(`/systems/${id}`, data)
    return response.data
  },

  async deleteSystem(id: string): Promise<void> {
    await registryClient.delete(`/systems/${id}`)
  },

  async deploySystem(id: string): Promise<DeployResult> {
    const response = await registryClient.post(`/systems/${id}/deploy`)
    return response.data
  },
}

// Simple API client with dummy data for development

export interface ExperimentSearchResult {
  experiment_id: string
  name: string
  lifecycle_stage: string
  creation_time?: number
  last_update_time?: number
}

class ExperimentsService {
  static async searchExperiments(query: string = ""): Promise<ExperimentSearchResult[]> {
    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 300))
    
    const experiments: ExperimentSearchResult[] = [
      {
        experiment_id: "123456789",
        name: "/Users/john.doe@company.com/RAG Evaluation Experiment",
        lifecycle_stage: "active",
        creation_time: 1705123200000
      },
      {
        experiment_id: "987654321", 
        name: "/Users/jane.smith@company.com/Chat Model Testing",
        lifecycle_stage: "active",
        creation_time: 1704518400000
      },
      {
        experiment_id: "456789123",
        name: "/Shared/Code Generation Eval",
        lifecycle_stage: "active",
        creation_time: 1705209600000
      },
      {
        experiment_id: "111222333",
        name: "/Users/alice@company.com/Safety Judge Training",
        lifecycle_stage: "active", 
        creation_time: 1705296000000
      },
      {
        experiment_id: "444555666",
        name: "/Users/bob@company.com/Relevance Testing Suite",
        lifecycle_stage: "active",
        creation_time: 1705382400000
      }
    ]

    if (!query.trim()) {
      return experiments
    }

    // Filter by name or experiment ID
    return experiments.filter(exp => 
      exp.name.toLowerCase().includes(query.toLowerCase()) ||
      exp.experiment_id.includes(query)
    )
  }
}

export { ExperimentsService }
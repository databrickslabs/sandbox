import { CatalogAsset, WorkspaceAsset } from '../types'

export interface SuggestedQuestion {
  text: string
  category?: string
}

export interface WelcomeCategory {
  title: string
  icon: string
  questions: SuggestedQuestion[]
}

// --- Catalog asset questions by type ---

const catalogQuestionTemplates: Record<string, (asset: CatalogAsset) => SuggestedQuestion[]> = {
  table: (asset) => [
    { text: `Describe the schema of \`${asset.full_name}\`` },
    { text: `What writes to \`${asset.full_name}\`?` },
    { text: `Show me sample data from \`${asset.full_name}\`` },
    { text: `What downstream assets depend on \`${asset.full_name}\`?` },
  ],
  view: (asset) => [
    { text: `What tables does \`${asset.full_name}\` depend on?` },
    { text: `How is the view \`${asset.full_name}\` defined?` },
    { text: `Show me sample output from \`${asset.full_name}\`` },
  ],
  function: (asset) => [
    { text: `What does the function \`${asset.full_name}\` do?` },
    { text: `Show example usage of \`${asset.full_name}\`` },
    { text: `What parameters does \`${asset.full_name}\` accept?` },
  ],
  model: (asset) => [
    { text: `Describe the model \`${asset.full_name}\`` },
    { text: `What data was used to train \`${asset.full_name}\`?` },
    { text: `How do I use the model \`${asset.full_name}\`?` },
  ],
  volume: (asset) => [
    { text: `What files are in volume \`${asset.full_name}\`?` },
    { text: `How is volume \`${asset.full_name}\` used?` },
    { text: `What processes write to \`${asset.full_name}\`?` },
  ],
}

// --- Workspace asset questions by type ---

const workspaceQuestionTemplates: Record<string, (asset: WorkspaceAsset) => SuggestedQuestion[]> = {
  notebook: (asset) => [
    { text: `Summarize what \`${asset.name}\` does` },
    { text: `What data sources does \`${asset.name}\` use?` },
    { text: `What tables does \`${asset.name}\` write to?` },
  ],
  job: (asset) => [
    { text: `Show recent runs of job \`${asset.name}\`` },
    { text: `What tables does job \`${asset.name}\` read?` },
    { text: `What is the schedule for job \`${asset.name}\`?` },
  ],
  dashboard: (asset) => [
    { text: `What metrics does \`${asset.name}\` show?` },
    { text: `What data sources feed \`${asset.name}\`?` },
    { text: `Who uses the \`${asset.name}\` dashboard?` },
  ],
  pipeline: (asset) => [
    { text: `Describe the pipeline \`${asset.name}\`` },
    { text: `What tables does \`${asset.name}\` produce?` },
    { text: `Show the status of pipeline \`${asset.name}\`` },
  ],
  cluster: (asset) => [
    { text: `Describe the cluster \`${asset.name}\`` },
    { text: `What workloads run on \`${asset.name}\`?` },
  ],
  experiment: (asset) => [
    { text: `Show runs in experiment \`${asset.name}\`` },
    { text: `What models were trained in \`${asset.name}\`?` },
  ],
}

export function getCatalogAssetQuestions(asset: CatalogAsset): SuggestedQuestion[] {
  const templateFn = catalogQuestionTemplates[asset.asset_type]
  if (!templateFn) {
    return [{ text: `Tell me about \`${asset.full_name || asset.name}\`` }]
  }
  return templateFn(asset)
}

export function getWorkspaceAssetQuestions(asset: WorkspaceAsset): SuggestedQuestion[] {
  const templateFn = workspaceQuestionTemplates[asset.asset_type]
  if (!templateFn) {
    return [{ text: `Tell me about \`${asset.name}\`` }]
  }
  return templateFn(asset)
}

export function getDefaultQuestion(asset: CatalogAsset | WorkspaceAsset, assetType: string): string {
  if (['table', 'view', 'function', 'model', 'volume'].includes(assetType)) {
    const questions = getCatalogAssetQuestions(asset as CatalogAsset)
    return questions[0]?.text ?? `Tell me about this ${assetType}`
  }
  const questions = getWorkspaceAssetQuestions(asset as WorkspaceAsset)
  return questions[0]?.text ?? `Tell me about this ${assetType}`
}

export function getWelcomeQuestions(): WelcomeCategory[] {
  return [
    {
      title: 'Explore Data',
      icon: 'search',
      questions: [
        { text: 'What tables are in the main catalog?' },
        { text: 'Show me the most recently updated assets' },
        { text: 'What data assets does my workspace have?' },
      ],
    },
    {
      title: 'Understand Relationships',
      icon: 'link',
      questions: [
        { text: 'What are the upstream dependencies of my tables?' },
        { text: 'Which notebooks write to production tables?' },
        { text: 'Show me the lineage for a specific table' },
      ],
    },
    {
      title: 'Troubleshoot',
      icon: 'alert',
      questions: [
        { text: 'Why did my job fail?' },
        { text: 'Which pipelines have errors?' },
        { text: 'Show me stale tables that haven\'t been updated recently' },
      ],
    },
    {
      title: 'Write Queries',
      icon: 'code',
      questions: [
        { text: 'Write a query to summarize sales by region' },
        { text: 'Help me join customer and order tables' },
        { text: 'Generate a query to find duplicate records' },
      ],
    },
  ]
}

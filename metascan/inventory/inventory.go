package inventory

type Item struct {
	Org       string
	Repo      string
	Maturity  Maturity
	IsSandbox bool
}

type Inventory []Item

var inventory = Inventory{
	// {
	// 	Org:      "databrickslabs",
	// 	Maturity: Alpha,
	// },
	// {
	// 	Org:      "databricks-demos",
	// 	Maturity: Demo,
	// },
	// {
	// 	Org:      "databricks-industry-solutions",
	// 	Maturity: Accelerator,
	// },
	// {
	// 	Org:       "databrickslabs",
	// 	Repo:      "sandbox",
	// 	Maturity:  Experiment,
	// 	IsSandbox: true,
	// },
	{
		Org:       "databricks",
		Repo:      "terraform-databricks-examples",
		Maturity:  Alpha,
		IsSandbox: true,
	},
	// { // this shouldn't be a top-level repo
	// 	Org:       "databricks",
	// 	Repo:      "terraform-databricks-lakehouse-blueprints",
	// 	Maturity:  Demo,
	// 	IsSandbox: true,
	// },
	// {
	// 	Org:       "databricks",
	// 	Repo:      "bundle-examples",
	// 	Maturity:  Demo,
	// 	IsSandbox: true,
	// },
	// {
	// 	Org:       "databricks",
	// 	Repo:      "databricks-ml-examples",
	// 	Maturity:  Demo,
	// 	IsSandbox: true,
	// },
	// {
	// 	Org:       "databricks",
	// 	Repo:      "delta-live-tables-notebooks",
	// 	Maturity:  Demo,
	// 	IsSandbox: true,
	// },
	// {
	// 	Org:       "databricks",
	// 	Repo:      "databricks-asset-bundles-dais2023",
	// 	Maturity:  Demo,
	// 	IsSandbox: true,
	// },
	// {
	// 	Org:      "databricks",
	// 	Repo:     "dais-cow-bff",
	// 	Maturity: Demo,
	// },
	// {
	// 	Org:       "databricks",
	// 	Repo:      "tech-talks",
	// 	Maturity:  Demo,
	// 	IsSandbox: true,
	// },
	// {
	// 	Org:       "databricks",
	// 	Repo:      "notebook_gallery",
	// 	Maturity:  Demo,
	// 	IsSandbox: true,
	// },
	// {
	// 	Org:       "databricks",
	// 	Repo:      "notebook-best-practices",
	// 	Maturity:  Demo,
	// 	IsSandbox: true,
	// },
	// {
	// 	Org:       "databricks",
	// 	Repo:      "ide-best-practices",
	// 	Maturity:  Demo,
	// 	IsSandbox: true,
	// },
	// { // this one shouldn't be a top-level repo
	// 	Org:      "databricks",
	// 	Repo:     "terraform-databricks-sra",
	// 	Maturity: Demo,
	// },
	// {
	// 	Org:       "databricks",
	// 	Repo:      "mfg_dlt_workshop",
	// 	Maturity:  Demo,
	// },
	// {
	// 	Org:       "databricks",
	// 	Repo:      "unity-catalog-setup",
	// 	Maturity:  Demo,
	// 	IsSandbox: true,
	// },
	// {
	// 	Org:       "databricks",
	// 	Repo:      "workflows-examples",
	// 	Maturity:  Experiment,
	// 	IsSandbox: true,
	// },
	// {
	// 	Org:       "databricks",
	// 	Repo:      "spark-knowledgebase",
	// 	Maturity:  Experiment,
	// 	IsSandbox: true,
	// },
	// {
	// 	Org:       "databricks",
	// 	Repo:      "databricks-accelerators",
	// 	Maturity:  Experiment,
	// 	IsSandbox: true,
	// },
	// {
	// 	Org:       "databricks",
	// 	Repo:      "mlflow-example-sklearn-elasticnet-wine",
	// 	Maturity:  Experiment,
	// },
	// {
	// 	Org:       "databricks",
	// 	Repo:      "azure-databricks-demos",
	// 	Maturity:  Demo,
	// },
}

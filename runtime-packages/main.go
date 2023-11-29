package main

import (
	"bytes"
	"context"
	_ "embed"
	"encoding/json"
	"fmt"
	"os"
	"regexp"
	"slices"
	"strings"
	"time"

	"github.com/databricks/databricks-sdk-go"
	"github.com/databricks/databricks-sdk-go/service/compute"
	"github.com/databricks/databricks-sdk-go/service/jobs"
	"github.com/databricks/databricks-sdk-go/service/workspace"
	"github.com/databrickslabs/sandbox/go-libs/localcache"
	"github.com/databrickslabs/sandbox/go-libs/render"
	"github.com/spf13/cobra"
	"golang.org/x/mod/semver"
)

//go:embed discover.py
var discoverNotebook []byte

type Package struct {
	Group   string `json:"group,omitempty"`
	Name    string `json:"name"`
	Version string `json:"version"`
}

func (p Package) String() string {
	if p.Group != "" {
		return fmt.Sprintf("%s:%s", p.Group, p.Name)
	}
	return p.Name
}

type RuntimeInfo struct {
	Name          string    `json:"name"`
	Version       string    `json:"version"`
	SparkVersion  string    `json:"spark_version"`
	PythonVersion string    `json:"python_version"`
	PyPI          []Package `json:"pypi"`
	Jars          []Package `json:"jars"`
}

func (ri RuntimeInfo) IsML() bool {
	return strings.Contains(ri.Name, "-ml-")
}

var cfg databricks.Config
var isJSON bool
var instancePoolID string

func main() {
	databricks.WithProduct("runtime-packages", "0.0.1")
	cmd := &cobra.Command{
		Use:   "runtime-packages",
		Short: "Get Python and JAR packages per Databricks Runtimes",
		RunE: func(cmd *cobra.Command, args []string) error {
			ctx := cmd.Context()
			w, err := databricks.NewWorkspaceClient(&cfg)
			if err != nil {
				return err
			}
			notebookPath, err := uploadNotebook(ctx, w)
			if err != nil {
				return err
			}
			defer w.Workspace.Delete(ctx, workspace.Delete{
				Path: notebookPath,
			})
			if cfg.ClusterID != "" {
				return singleRuntime(cmd, w, notebookPath)
			}
			return allRuntimes(cmd, w, notebookPath)
		},
	}
	flags := cmd.Flags()
	flags.StringVar(&cfg.Host, "host", "", "Databricks workspace host")
	flags.StringVar(&cfg.Profile, "profile", "", "Connection profile specified within ~/.databrickscfg.")
	flags.StringVar(&cfg.ClusterID, "cluster-id", "", "Databricks cluster to run package discovery job")
	flags.StringVar(&instancePoolID, "instance-pool-id", "", "Instance pool to run discovery in")
	flags.BoolVar(&isJSON, "json", false, "output in JSON")
	err := cmd.Execute()
	if err != nil {
		os.Stderr.Write([]byte(err.Error()))
		os.Exit(1)
	}
}

func uploadNotebook(ctx context.Context, w *databricks.WorkspaceClient) (string, error) {
	me, err := w.CurrentUser.Me(ctx)
	if err != nil {
		return "", err
	}
	now := time.Now().UnixNano()
	notebookPath := fmt.Sprintf("/Users/%s/.discover-packages-%d.py", me.UserName, now)
	err = w.Workspace.Upload(ctx, notebookPath,
		bytes.NewBuffer(discoverNotebook),
		workspace.UploadOverwrite())
	if err != nil {
		return "", err
	}
	return notebookPath, nil
}

func singleRuntime(cmd *cobra.Command, w *databricks.WorkspaceClient, notebookPath string) error {
	ctx := cmd.Context()
	clusterInfo, err := w.Clusters.GetByClusterId(ctx, w.Config.ClusterID)
	if err != nil {
		return err
	}
	wait, err := w.Jobs.Submit(ctx, jobs.SubmitRun{
		RunName: "Get Python packages",
		Tasks: []jobs.SubmitTask{
			{
				TaskKey:           "specified",
				ExistingClusterId: w.Config.ClusterID,
				NotebookTask: &jobs.NotebookTask{
					NotebookPath: notebookPath,
					BaseParameters: map[string]string{
						"runtime": clusterInfo.SparkVersion,
					},
				},
			},
		},
	})
	if err != nil {
		return err
	}
	spinner := render.Spinner(cmd)
	defer close(spinner)
	run, err := wait.OnProgress(func(r *jobs.Run) {
		if r.State == nil {
			spinner <- "starting job"
			return
		}
		spinner <- fmt.Sprintf("job is %s", r.State.LifeCycleState)
	}).Get()
	if err != nil {
		return err
	}
	t := run.Tasks[0]
	output, err := w.Jobs.GetRunOutputByRunId(ctx, t.RunId)
	if err != nil {
		return err
	}
	var info RuntimeInfo
	err = json.Unmarshal([]byte(output.NotebookOutput.Result), &info)
	if err != nil {
		return err
	}
	if isJSON {
		return render.RenderJson(os.Stdout, info)
	}
	return render.RenderTemplate(os.Stdout, `
Name: {{.Name|green}}
Version: {{.Version|green}}
Apache Spark Version: {{.SparkVersion|green}}
Python Version: {{.PythonVersion|green}}

{{"Python Package"|header}}	{{"Version"|header}}
{{- range .PyPI}}
{{.Name|blue}}	{{.Version|green}}{{end}}

{{"JAR Org ID"|header}}	{{"JAR Name"|header}}	{{"Version"|header}}
{{- range .Jars}}
{{.Group|yellow}}	{{.Name|blue}}	{{.Version|green}}{{end}}
		`, info)
}

var dbrVersionRegex = regexp.MustCompile(`^(\d+\.\d+)\.x-.*`)

func getRuntimeVersion(ver string) (string, bool) {
	match := dbrVersionRegex.FindStringSubmatch(ver)
	if len(match) < 1 {
		return "", false
	}
	return fmt.Sprintf("v%s", match[1]), true
}

type Runtimes struct {
	SortedRuntimes []string               `json:"sorted_runtimes"`
	DbrToVariants  map[string][]string    `json:"dbr_to_variants"`
	VariantToDBR   map[string]string      `json:"variant_to_dbr"`
	Info           map[string]RuntimeInfo `json:"info"`
}

func fetchSnapshot(cmd *cobra.Command, w *databricks.WorkspaceClient, notebookPath string) (*Runtimes, error) {
	ctx := cmd.Context()
	r := &Runtimes{
		DbrToVariants: map[string][]string{},
		VariantToDBR:  map[string]string{},
		Info:          map[string]RuntimeInfo{},
	}
	runtimes, err := w.Clusters.SparkVersions(ctx)
	if err != nil {
		return nil, err
	}
	nodes, err := w.Clusters.ListNodeTypes(ctx)
	if err != nil {
		return nil, err
	}
	smallestVM, err := nodes.Smallest(compute.NodeTypeRequest{
		LocalDisk: true,
	})
	if err != nil {
		return nil, err
	}
	for _, version := range runtimes.Versions {
		skip := ((strings.Contains(version.Key, "apache-spark-")) ||
			(strings.Contains(version.Key, "-aarch64-")) ||
			(strings.Contains(version.Key, "-photon-")) ||
			(strings.Contains(version.Key, "-hls-")) ||
			(strings.Contains(version.Key, "-gpu-")))
		if skip {
			continue
		}
		isLTS := strings.Contains(version.Name, "LTS") || strings.Contains(version.Key, "-esr-")
		if !isLTS { // TODO: make configurable
			continue
		}
		dbrVersion, ok := getRuntimeVersion(version.Key)
		if !ok {
			continue
		}
		r.DbrToVariants[dbrVersion] = append(r.DbrToVariants[dbrVersion], version.Key)
		r.VariantToDBR[version.Key] = dbrVersion
	}
	for k := range r.DbrToVariants {
		r.SortedRuntimes = append(r.SortedRuntimes, k)
	}
	semver.Sort(r.SortedRuntimes)
	cnt := 0
	tasks := []jobs.SubmitTask{}
	for _, dbrVersion := range r.SortedRuntimes {
		for _, runtime := range r.DbrToVariants[dbrVersion] {
			cnt++
			clusterSpec := &compute.ClusterSpec{
				SparkVersion:    runtime,
				NumWorkers:      0,
				ForceSendFields: []string{"NumWorkers"},
				SparkConf: map[string]string{
					"spark.databricks.cluster.profile": "singleNode",
					"spark.master":                     "local[*]",
				},
				CustomTags: map[string]string{
					"ResourceClass": "SingleNode",
				},
			}
			if instancePoolID != "" {
				clusterSpec.InstancePoolId = instancePoolID
			} else {
				clusterSpec.NodeTypeId = smallestVM
			}
			tasks = append(tasks, jobs.SubmitTask{
				TaskKey: fmt.Sprintf("task-%d", cnt),
				NotebookTask: &jobs.NotebookTask{
					NotebookPath: notebookPath,
					BaseParameters: map[string]string{
						"runtime": runtime,
					},
				},
				NewCluster: clusterSpec,
			})
		}
	}
	wait, err := w.Jobs.Submit(ctx, jobs.SubmitRun{
		RunName: "Discover PyPI and Maven packages",
		Tasks:   tasks,
	})
	if err != nil {
		return nil, err
	}
	spinner := render.Spinner(cmd)
	defer close(spinner)
	run, err := wait.OnProgress(func(r *jobs.Run) {
		if r.State == nil {
			spinner <- "starting job"
			return
		}
		spinner <- fmt.Sprintf("job is %s", r.State.LifeCycleState)
	}).Get()
	if err != nil {
		return nil, err
	}
	for _, t := range run.Tasks {
		output, err := w.Jobs.GetRunOutputByRunId(ctx, t.RunId)
		if err != nil {
			return nil, err
		}
		var info RuntimeInfo // todo: fails on cancelled job
		err = json.Unmarshal([]byte(output.NotebookOutput.Result), &info)
		if err != nil {
			return nil, err
		}
		r.Info[info.Name] = info
	}
	return r, nil
}

func allRuntimes(cmd *cobra.Command, w *databricks.WorkspaceClient, notebookPath string) error {
	ctx := cmd.Context()
	cacheKey := fmt.Sprintf("dbr-versions-%s", instancePoolID)
	cache := localcache.NewLocalCache[*Runtimes]("/tmp", cacheKey, 24*time.Hour)
	snapshot, err := cache.Load(ctx, func() (*Runtimes, error) {
		return fetchSnapshot(cmd, w, notebookPath)
	})
	if err != nil {
		return err
	}
	mlOnly := map[string]bool{}
	for _, runtimes := range snapshot.DbrToVariants {
		packagesInRuntimes := map[Package][]RuntimeInfo{}
		for _, runtimeVariant := range runtimes {
			info := snapshot.Info[runtimeVariant]
			for _, pkg := range info.PyPI {
				packagesInRuntimes[pkg] = append(packagesInRuntimes[pkg], info)
			}
			for _, pkg := range info.Jars {
				packagesInRuntimes[pkg] = append(packagesInRuntimes[pkg], info)
			}
		}
		for pkg, variants := range packagesInRuntimes {
			if len(variants) == 1 {
				mlOnly[pkg.String()] = true
			}
		}
	}
	rows := []string{"Apache Spark", "Python"}
	matrix := map[string]map[string]string{}
	matrix["Apache Spark"] = map[string]string{}
	matrix["Python"] = map[string]string{}
	seenPackages := map[string]bool{}
	populate := func(v Package, runtimeVersion string) {
		name := v.String()
		_, isML := mlOnly[name]
		if isML {
			name = fmt.Sprintf("%s (ML)", name)
		}
		_, ok := matrix[name]
		if !ok {
			matrix[name] = map[string]string{}
		}
		matrix[name][runtimeVersion] = v.Version
		if seenPackages[name] {
			return
		}
		rows = append(rows, name)
		seenPackages[name] = true
	}
	for v, info := range snapshot.Info {
		runtimeVersion := snapshot.VariantToDBR[v]
		matrix["Apache Spark"][runtimeVersion] = info.SparkVersion
		matrix["Python"][runtimeVersion] = info.PythonVersion
		for _, v := range info.PyPI {
			populate(v, runtimeVersion)
		}
		for _, v := range info.Jars {
			populate(v, runtimeVersion)
		}
	}
	slices.Sort(rows)
	trows := []string{}
	header := []string{"..."}
	header = append(header, snapshot.SortedRuntimes...)
	trows = append(trows, strings.Join(header, "\t"))
	for _, pkg := range rows {
		row := []string{pkg}
		for _, rv := range snapshot.SortedRuntimes {
			row = append(row, matrix[pkg][rv])
		}
		trows = append(trows, strings.Join(row, "\t"))
	}
	template := strings.Join(trows, "\n")
	return render.RenderTemplate(os.Stdout, template, true)
}

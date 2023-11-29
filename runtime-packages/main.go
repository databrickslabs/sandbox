package main

import (
	"bytes"
	_ "embed"
	"encoding/json"
	"fmt"
	"os"
	"strings"
	"time"

	"github.com/databricks/databricks-sdk-go"
	"github.com/databricks/databricks-sdk-go/service/compute"
	"github.com/databricks/databricks-sdk-go/service/jobs"
	"github.com/databricks/databricks-sdk-go/service/workspace"
	"github.com/spf13/cobra"
)

//go:embed discover.py
var discoverNotebook []byte

type Package struct {
	Group   string `json:"group,omitempty"`
	Name    string `json:"name"`
	Version string `json:"version"`
}

type RuntimeInfo struct {
	Name          string    `json:"name"`
	SparkVersion  string    `json:"spark_version"`
	PythonVersion string    `json:"python_version"`
	PyPI          []Package `json:"pypi"`
	Jars          []Package `json:"jars"`
}

var cfg databricks.Config

func main() {
	databricks.WithProduct("runtime-packages", "0.0.1")

	flags := cmd.Flags()
	flags.StringVar(&cfg.Host, "host", "", "Databricks workspace host")
	flags.StringVar(&cfg.Profile, "profile", "", "Connection profile specified within ~/.databrickscfg.")
	flags.StringVar(&cfg.ClusterID, "cluster-id", "", "Databricks cluster to run package discovery job")
	err := cmd.Execute()
	if err != nil {
		os.Stderr.Write([]byte(err.Error()))
		os.Exit(1)
	}
}

var cmd = &cobra.Command{
	Use:   "runtime-packages",
	Short: "Get Python and JAR packages per Databricks Runtimes",
	RunE: func(cmd *cobra.Command, args []string) error {
		ctx := cmd.Context()
		w, err := databricks.NewWorkspaceClient(&cfg)
		if err != nil {
			return err
		}
		tasks := []jobs.SubmitTask{}
		me, err := w.CurrentUser.Me(ctx)
		if err != nil {
			return err
		}
		now := time.Now().UnixNano()
		notebookPath := fmt.Sprintf("/Users/%s/.discover-packages-%d.py", me.UserName, now)
		err = w.Workspace.Upload(ctx, notebookPath,
			bytes.NewBuffer(discoverNotebook),
			workspace.UploadOverwrite())
		if err != nil {
			return err
		}
		defer w.Workspace.Delete(ctx, workspace.Delete{
			Path: notebookPath,
		})
		runtimes, err := w.Clusters.SparkVersions(ctx)
		if err != nil {
			return err
		}
		nodes, err := w.Clusters.ListNodeTypes(ctx)
		if err != nil {
			return err
		}
		smallestVM, err := nodes.Smallest(compute.NodeTypeRequest{
			LocalDisk: true,
		})
		if err != nil {
			return err
		}
		for i, r := range runtimes.Versions {
			if strings.Contains(r.Key, "-aarch64") {
				continue
			}
			if strings.Contains(r.Key, "apache-") {
				continue
			}
			if strings.Contains(r.Key, "-photon-") {
				continue
			}
			if strings.Contains(r.Key, "-gpu") {
				continue
			}
			tasks = append(tasks, jobs.SubmitTask{
				TaskKey: fmt.Sprintf("task-%d", i),
				NotebookTask: &jobs.NotebookTask{
					NotebookPath: notebookPath,
					BaseParameters: map[string]string{
						"runtime": r.Key,
					},
				},
				NewCluster: &compute.ClusterSpec{
					SparkVersion: r.Key,
					NumWorkers:   1, // TODO: single-node
					NodeTypeId:   smallestVM,
				},
			})
		}
		wait, err := w.Jobs.Submit(cmd.Context(), jobs.SubmitRun{
			RunName: "Get Python packages",
			Tasks:   tasks,
		})
		if err != nil {
			return err
		}
		run, err := wait.Get()
		if err != nil {
			return err
		}
		var infos []RuntimeInfo
		for _, t := range run.Tasks {
			output, err := w.Jobs.GetRunOutputByRunId(ctx, t.RunId)
			if err != nil {
				return err
			}
			var info RuntimeInfo // todo: fails on cancelled job
			err = json.Unmarshal([]byte(output.NotebookOutput.Result), &info)
			if err != nil {
				return err
			}
			infos = append(infos, info)
		}

		for _, v := range infos {
			raw, _ := json.Marshal(v)
			fmt.Printf("%s\n", string(raw))
		}
		return nil
	},
}

package boilerplate

import "github.com/databricks/databricks-sdk-go/logger"

func init() {
	// TODO: integrate with GitHub Actions logging primitives
	logger.DefaultLogger = &logger.SimpleLogger{
		Level: logger.LevelInfo,
	}
}

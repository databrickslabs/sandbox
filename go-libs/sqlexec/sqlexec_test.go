package sqlexec_test

import (
	"testing"

	"github.com/databricks/databricks-sdk-go/apierr"
	"github.com/databricks/databricks-sdk-go/logger"
	"github.com/databrickslabs/sandbox/go-libs/fixtures"
	"github.com/databrickslabs/sandbox/go-libs/sqlexec"
	"github.com/stretchr/testify/require"
)

func TestQueryRuns(t *testing.T) {
	ctx, w := fixtures.WorkspaceTest(t)

	exec, err := sqlexec.New(w)
	require.NoError(t, err)

	result, err := exec.Query(ctx, "SELECT pickup_zip, dropoff_zip FROM samples.nyctaxi.trips LIMIT 10")
	require.NoError(t, err)

	var pickupZip, dropoffZip int
	for result.Scan(&pickupZip, &dropoffZip) {
		logger.Infof(ctx, "pickup: %d, dropoff: %d", pickupZip, dropoffZip)
	}
	require.NoError(t, result.Err())
}

func TestScanWrongType(t *testing.T) {
	ctx, w := fixtures.WorkspaceTest(t)

	exec, err := sqlexec.New(w)
	require.NoError(t, err)

	result, err := exec.Query(ctx, "SELECT pickup_zip, dropoff_zip FROM samples.nyctaxi.trips LIMIT 1")
	require.NoError(t, err)

	var pickupZip string
	require.False(t, result.Scan(&pickupZip))
	require.EqualError(t, result.Err(), "json: cannot unmarshal number into Go value of type string")
}

func TestErrorMapping(t *testing.T) {
	ctx, w := fixtures.WorkspaceTest(t)

	exec, err := sqlexec.New(w)
	require.NoError(t, err)

	err = exec.Execf(ctx, "DROP TABLE catalog_%s.foo.bar", fixtures.RandomName())
	require.ErrorIs(t, err, apierr.ErrNotFound)

	err = exec.Execf(ctx, "DROP SCHEMA db_%s", fixtures.RandomName())
	require.ErrorIs(t, err, apierr.ErrNotFound)

	err = exec.Execf(ctx, "CREATE CATALOG main")
	require.ErrorIs(t, err, apierr.ErrAlreadyExists)
}

func TestMultiChunk(t *testing.T) {
	ctx, w := fixtures.WorkspaceTest(t)
	w.Config.WarehouseID = fixtures.GetEnvOrSkipTest(t, "TEST_DEFAULT_WAREHOUSE_ID")

	exec, err := sqlexec.New(w)
	require.NoError(t, err)

	result, err := exec.Query(ctx, "SELECT id FROM range(2000000)")
	require.NoError(t, err)

	var total, x int
	for result.Scan(&x) {
		total += x
	}
	logger.Infof(ctx, "total: %d", total)
	require.NoError(t, result.Err())
}

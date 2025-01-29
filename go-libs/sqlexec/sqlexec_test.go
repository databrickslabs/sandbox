package sqlexec_test

import (
	"testing"
	"time"

	"github.com/databricks/databricks-sdk-go/apierr"
	"github.com/databricks/databricks-sdk-go/logger"
	"github.com/databrickslabs/sandbox/go-libs/fixtures"
	"github.com/databrickslabs/sandbox/go-libs/sqlexec"
	"github.com/stretchr/testify/require"
)

func TestAccShowDatabases(t *testing.T) {
	ctx, w := fixtures.WorkspaceTest(t)

	exec, err := sqlexec.New(w)
	require.NoError(t, err)

	result, err := exec.Query(ctx, "SHOW DATABASES IN hive_metastore")
	require.NoError(t, err)

	var name string
	for result.Scan(&name) {
		logger.Infof(ctx, "name: %s", name)
	}
	require.NoError(t, result.Err())
}

func TestAccQueryRuns(t *testing.T) {
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

func TestAccQueryTypes(t *testing.T) {
	ctx, w := fixtures.WorkspaceTest(t)

	exec, err := sqlexec.New(w)
	require.NoError(t, err)

	result, err := exec.Query(ctx, `SELECT 
		ARRAY(1,2) AS array_type,
		CAST("a" AS BINARY) AS binary_type,
		true AS boolean_type,
		CAST(NOW() AS DATE) AS date_type,
		CAST(3 AS DECIMAL) AS decimal_type,
		CAST(4.56 AS DOUBLE) AS double_type,
		CAST(7.89 AS FLOAT) AS float_type,
		CAST(8 AS INT) AS int_type,
		CAST(9 AS LONG) AS long_type,
		MAP("foo", "bar") AS map_type,
		STRUCT("bar" AS foo) AS struct_type,
		NOW() AS timestamp_type`)
	require.NoError(t, err)

	var arrayType []int
	var binaryType []byte
	var booleanType bool
	var dateType time.Time
	var decimalType float32
	var doubleType float32
	var floatType float32
	var intType int
	var longType int64
	var mapType map[string]string
	var structType map[string]any
	var timestampType time.Time
	result.Scan(&arrayType, &binaryType, &booleanType, &dateType,
		&decimalType, &doubleType, &floatType, &intType, &longType,
		&mapType, &structType, &timestampType)
	require.NoError(t, result.Err())

	require.Equal(t, []int{1, 2}, arrayType)
	require.Equal(t, []byte("a"), binaryType)
	require.Equal(t, true, booleanType)
	require.Equal(t, time.Now().UTC().Truncate(24*time.Hour), dateType)
	require.InDelta(t, 3, decimalType, 0.01)
	require.InDelta(t, 4.56, doubleType, 0.01)
	require.InDelta(t, 7.89, floatType, 0.01)
	require.Equal(t, 8, intType)
	require.Equal(t, int64(9), longType)
	require.Equal(t, map[string]string{"foo": "bar"}, mapType)
}

func TestAccScanWrongType(t *testing.T) {
	t.SkipNow()
	ctx, w := fixtures.WorkspaceTest(t)

	exec, err := sqlexec.New(w)
	require.NoError(t, err)

	result, err := exec.Query(ctx, "SELECT pickup_zip, dropoff_zip FROM samples.nyctaxi.trips LIMIT 1")
	require.NoError(t, err)

	var pickupZip string
	require.False(t, result.Scan(&pickupZip))
	require.EqualError(t, result.Err(), "json: cannot unmarshal number into Go value of type string")
}

func TestAccErrorMapping(t *testing.T) {
	ctx, w := fixtures.WorkspaceTest(t)

	exec, err := sqlexec.New(w)
	require.NoError(t, err)

	err = exec.Execf(ctx, "DROP TABLE catalog_%s.foo.bar", fixtures.RandomName())
	require.ErrorIs(t, err, apierr.ErrNotFound)

	err = exec.Execf(ctx, "DROP SCHEMA db_%s", fixtures.RandomName())
	require.ErrorIs(t, err, apierr.ErrNotFound)
}

func TestAccMultiChunk(t *testing.T) {
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

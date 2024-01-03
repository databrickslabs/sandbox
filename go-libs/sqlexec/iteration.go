package sqlexec

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"regexp"
	"sync"
	"time"

	"github.com/databricks/databricks-sdk-go/logger"
	"github.com/databricks/databricks-sdk-go/service/sql"
)

type stringArrayIterator struct {
	result *sql.ResultData
	api    *sql.StatementExecutionAPI
	id     string
	pos    int
	err    error
	mu     sync.Mutex
}

// HasNext returns true if there are more items to iterate over. HasNext
// will also return true if the iterator needs to fetch the next page of
// items from the underlying source and the request fails, even if there
// are no more items to iterate over. In this case, Next will return the
// error.
func (i *stringArrayIterator) HasNext(ctx context.Context) bool {
	i.mu.Lock()
	defer i.mu.Unlock()
	if i.pos < len(i.result.DataArray) {
		return true
	}
	if i.result.NextChunkIndex == 0 {
		return false
	}
	i.result, i.err = i.api.GetStatementResultChunkNByStatementIdAndChunkIndex(ctx, i.id, i.result.NextChunkIndex)
	if i.err != nil {
		return false
	}
	i.pos = 0
	return true
}

// Next returns the next item in the iterator. If there are no more items
// to iterate over, it returns ErrNoMoreItems. If there was an error
// fetching the next page of items, it returns that error. Once Next
// returns ErrNoMoreItems or an error, it will continue to return that
// error.
func (i *stringArrayIterator) Next(context.Context) ([]string, error) {
	i.mu.Lock()
	defer i.mu.Unlock()
	if i.err != nil {
		return nil, i.err
	}
	row := i.result.DataArray[i.pos]
	i.pos++
	return row, nil
}

type scanIterator struct {
	ctx      context.Context
	schema   *sql.ResultSchema
	iterator *stringArrayIterator
}

func (i *scanIterator) Scan(out ...any) bool {
	if len(out) == 0 {
		logger.Errorf(i.ctx, "empty arguments")
		return false
	}
	if !i.iterator.HasNext(i.ctx) {
		return false
	}
	row, err := i.iterator.Next(i.ctx)
	if err != nil {
		logger.Errorf(i.ctx, "failed to fetch: %w", err)
		return false
	}
	for j := 0; j < len(out); j++ {
		col := i.schema.Columns[j]
		err := i.unmarshall(col, row[j], out[j]) // or &out[j]?
		if err != nil {
			err = fmt.Errorf("%s (%s): %w", col.Name, col.TypeText, err)
			logger.Errorf(i.ctx, "failed to fetch: %s", err)
			i.iterator.err = err
			return false
		}
	}
	return true
}

var (
	arrayTypeRE = regexp.MustCompile(`ARRAY<(.*)>`)
	mapTypeRE   = regexp.MustCompile(`MAP<STRING, (.*)>`)
	typeIndex   = map[string]sql.ColumnInfoTypeName{
		"ARRAY":             sql.ColumnInfoTypeNameArray,
		"BINARY":            sql.ColumnInfoTypeNameBinary,
		"BOOLEAN":           sql.ColumnInfoTypeNameBoolean,
		"BYTE":              sql.ColumnInfoTypeNameByte,
		"CHAR":              sql.ColumnInfoTypeNameChar,
		"DATE":              sql.ColumnInfoTypeNameDate,
		"DECIMAL":           sql.ColumnInfoTypeNameDecimal,
		"DOUBLE":            sql.ColumnInfoTypeNameDouble,
		"FLOAT":             sql.ColumnInfoTypeNameFloat,
		"INT":               sql.ColumnInfoTypeNameInt,
		"INTERVAL":          sql.ColumnInfoTypeNameInterval,
		"LONG":              sql.ColumnInfoTypeNameLong,
		"MAP":               sql.ColumnInfoTypeNameMap,
		"NULL":              sql.ColumnInfoTypeNameNull,
		"SHORT":             sql.ColumnInfoTypeNameShort,
		"STRING":            sql.ColumnInfoTypeNameString,
		"STRUCT":            sql.ColumnInfoTypeNameStruct,
		"TIMESTAMP":         sql.ColumnInfoTypeNameTimestamp,
		"USER_DEFINED_TYPE": sql.ColumnInfoTypeNameUserDefinedType,
	}
)

func (i *scanIterator) typeByText(typeText string) (sql.ColumnInfoTypeName, error) {
	v, ok := typeIndex[typeText]
	if !ok {
		return "", fmt.Errorf("unknown type: %s", typeText)
	}
	return v, nil
}

func (i *scanIterator) unmarshall(col sql.ColumnInfo, src string, out any) (err error) {
	defer func() {
		p := recover()
		if p != nil {
			err = fmt.Errorf("panic: %s", p)
		}
	}()
	switch dst := out.(type) {
	case *string:
		*dst = src
		return nil
	case *int, *int32, *int64, *bool, *float32, *float64, *byte:
		return json.Unmarshal([]byte(src), dst)
	case *time.Time:
		if col.TypeName == sql.ColumnInfoTypeNameDate {
			var year, month, day int
			_, err := fmt.Sscanf(string(src), "%d-%d-%d", &year, &month, &day)
			if err != nil {
				return err
			}
			*dst = time.Date(year, time.Month(month), day, 0, 0, 0, 0, time.UTC)
			return nil
		}
		*dst, err = time.Parse("2006-01-02T15:04:05Z", src)
		return err
	case *[]byte:
		var err error
		*dst, err = base64.StdEncoding.DecodeString(src)
		return err
	default:
		switch col.TypeName {
		case sql.ColumnInfoTypeNameArray:
			return i.unmarshallArray(col, src, out)
		case sql.ColumnInfoTypeNameMap:
			return i.unmarshallMap(col, src, out)
		case sql.ColumnInfoTypeNameStruct:
			// try to unmarshal struct to map[string]any
			return json.Unmarshal([]byte(src), dst)
		}
	}
	return nil
}

func sliceUnmarshaller[X any](col sql.ColumnInfo, src []string, dst *[]X,
	unmarshall func(sql.ColumnInfo, string, any) error) error {
	for _, v := range src {
		var item X
		err := unmarshall(col, v, &item)
		if err != nil {
			return fmt.Errorf("elem: %w", err)
		}
		*dst = append(*dst, item)
	}
	return nil
}

func mapUnmarshaller[X any](col sql.ColumnInfo, src map[string]string, dst *map[string]X,
	unmarshall func(sql.ColumnInfo, string, any) error) error {
	for k, v := range src {
		var item X
		err := unmarshall(col, v, &item)
		if err != nil {
			return fmt.Errorf("%s: %w", k, err)
		}
		(*dst)[k] = item
	}
	return nil
}

func (i *scanIterator) unmarshallArray(col sql.ColumnInfo, src string, out any) error {
	var tmp []string
	err := json.Unmarshal([]byte(src), &tmp)
	if err != nil {
		return fmt.Errorf("unmashal: %w", err)
	}
	matches := arrayTypeRE.FindStringSubmatch(col.TypeText)
	if len(matches) == 0 {
		return fmt.Errorf("no elem type")
	}
	innerTypeText := matches[1]
	innerTypeName, err := i.typeByText(innerTypeText)
	if err != nil {
		return fmt.Errorf("inner type: %w", err)
	}
	inner := sql.ColumnInfo{
		TypeName: innerTypeName,
		TypeText: innerTypeText,
	}
	switch dst := out.(type) {
	case *[]int:
		return sliceUnmarshaller[int](inner, tmp, dst, i.unmarshall)
	case *[]string:
		return sliceUnmarshaller[string](inner, tmp, dst, i.unmarshall)
	case *[]float32:
		return sliceUnmarshaller[float32](inner, tmp, dst, i.unmarshall)
	case *[]any:
		return sliceUnmarshaller[any](inner, tmp, dst, i.unmarshall)
	default:
		return fmt.Errorf("unknown type name: %s", col.TypeName)
	}
}

func (i *scanIterator) unmarshallMap(col sql.ColumnInfo, src string, out any) error {
	var tmp map[string]string
	err := json.Unmarshal([]byte(src), &tmp)
	if err != nil {
		return fmt.Errorf("unmashal: %w", err)
	}
	matches := mapTypeRE.FindStringSubmatch(col.TypeText)
	if len(matches) == 0 {
		return fmt.Errorf("no elem type")
	}
	innerTypeText := matches[1]
	innerTypeName, err := i.typeByText(innerTypeText)
	if err != nil {
		return fmt.Errorf("inner type: %w", err)
	}
	inner := sql.ColumnInfo{
		TypeName: innerTypeName,
		TypeText: innerTypeText,
	}
	switch dst := out.(type) {
	case *map[string]string:
		*dst = tmp
		return nil
	case *map[string]int:
		return mapUnmarshaller[int](inner, tmp, dst, i.unmarshall)
	case *map[string]float32:
		return mapUnmarshaller[float32](inner, tmp, dst, i.unmarshall)
	case *map[string]any:
		return mapUnmarshaller[any](inner, tmp, dst, i.unmarshall)
	default:
		return fmt.Errorf("unknown type name: %s", col.TypeName)
	}
}

type iterableResult struct {
	scanner  *scanIterator
	iterator *stringArrayIterator
}

// Scan mimics the rows interface from go - see https://pkg.go.dev/database/sql#example-Rows
func (rc *iterableResult) Scan(out ...any) bool {
	return rc.scanner.Scan(out...)
}

func (rc *iterableResult) Err() error {
	return rc.iterator.err
}

func (rc *iterableResult) HasNext(ctx context.Context) bool {
	return rc.iterator.HasNext(ctx)
}

func (rc *iterableResult) Next(ctx context.Context) ([]string, error) {
	return rc.iterator.Next(ctx)
}

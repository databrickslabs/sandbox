package lite

import (
	"context"
	"fmt"
	"log/slog"
	"os"
	"strings"

	"github.com/databricks/databricks-sdk-go/logger"
	"github.com/fatih/color"
	"github.com/spf13/cobra"
	"github.com/spf13/pflag"
	"github.com/spf13/viper"
)

type Command[C, T any] struct {
	Name  string
	Short string
	Long  string
	Flags func(flags *pflag.FlagSet, req *T)
	Run   func(root *Root[C], req *T) error
}

func (s *Command[C, T]) Register(root *Root[C]) {
	cmd := &cobra.Command{
		Use:   s.Name,
		Short: s.Short,
		Long:  s.Long,
	}
	root.AddCommand(cmd)

	var req T
	if s.Flags != nil {
		s.Flags(cmd.Flags(), &req)
	}
	cmd.RunE = func(_ *cobra.Command, args []string) error {
		return s.Run(root, &req)
	}
}

type Init[T any] struct {
	Name       string
	Version    string
	Short      string
	Long       string
	ConfigPath string
	EnvPrefix  string
	Bind       func(flags *pflag.FlagSet, cfg *T)
	PreRun     func(cmd *Root[T]) error
}

func New[T any](ctx context.Context, init Init[T]) *Root[T] {
	cmd := &Root[T]{
		Command: cobra.Command{
			Use:     init.Name,
			Short:   init.Short,
			Long:    init.Long,
			Version: init.Version,

			// Cobra prints the usage string to stderr if a command returns an error.
			// This usage string should only be displayed if an invalid combination of flags
			// is specified and not when runtime errors occur (e.g. resource not found).
			// The usage string is include in [flagErrorFunc] for flag errors only.
			SilenceUsage: true,

			// Silence error printing by cobra. Errors are printed through cmdio.
			SilenceErrors: true,
		},
	}
	// Pass the context along through the command during initialization.
	// It will be overwritten when the command is executed.
	cmd.SetContext(ctx)
	cmd.SetVersionTemplate(fmt.Sprintf("%s v%s", init.Name, init.Version))
	cmd.SetFlagErrorFunc(func(c *cobra.Command, err error) error {
		return fmt.Errorf("%w\n\n%s", err, c.UsageString())
	})
	cmd.PersistentFlags().BoolVar(&cmd.Debug, "debug", false, "Enable debug log output")
	if init.Bind != nil {
		init.Bind(cmd.PersistentFlags(), &cmd.Config)
	}
	cmd.PersistentPreRunE = cmd.preRun(init)
	return cmd
}

type Root[T any] struct {
	cobra.Command
	Logger *slog.Logger
	Debug  bool
	Config T
}

func (r *Root[T]) initLogger() {
	level := slog.LevelInfo
	if r.Debug {
		level = slog.LevelDebug
	} else {
		level = slog.LevelWarn
	}
	w := r.ErrOrStderr()
	r.Logger = slog.New(&friendlyHandler{
		Handler: slog.NewTextHandler(w, &slog.HandlerOptions{
			Level: level,
		}),
		w: w,
	})
	logger.DefaultLogger = &slogAdapter{r.Logger}
}

func (r *Root[T]) preRun(init Init[T]) func(cmd *cobra.Command, args []string) error {
	return func(cmd *cobra.Command, args []string) error {
		r.initLogger()
		v := viper.NewWithOptions(viper.WithLogger(r.Logger))
		v.SetConfigName(init.Name)
		v.SetConfigType("yaml")
		v.AddConfigPath(".")
		if init.ConfigPath != "" {
			v.AddConfigPath(init.ConfigPath)
		}
		if init.EnvPrefix != "" {
			v.SetEnvPrefix(init.EnvPrefix)
		}
		v.SetEnvKeyReplacer(strings.NewReplacer("-", "_"))
		v.AutomaticEnv() // or after config reading?...
		if r.Debug {
			v.DebugTo(r.ErrOrStderr())
		}
		err := v.ReadInConfig()
		if _, ok := err.(viper.ConfigFileNotFoundError); err != nil && !ok {
			return fmt.Errorf("config: %w", err)
		}
		err = r.bindViperToFlags(v, r.PersistentFlags(), "")
		if err != nil {
			return fmt.Errorf("root flags: %w", err)
		}
		err = r.bindViperToFlags(v, cmd.Flags(), fmt.Sprintf("%s.", cmd.Name()))
		if err != nil {
			return fmt.Errorf("command flags: %w", err)
		}
		if init.PreRun != nil {
			err = init.PreRun(r)
			if err != nil {
				return fmt.Errorf("pre run: %w", err)
			}
		}
		return nil
	}
}

func (r *Root[T]) bindViperToFlags(v *viper.Viper, flags *pflag.FlagSet, prefix string) error {
	var err error
	flags.VisitAll(func(f *pflag.Flag) {
		propName := strings.ReplaceAll(fmt.Sprintf("%s%s", prefix, f.Name), "-", "_")
		if !f.Changed && v.IsSet(propName) {
			switch x := v.Get(propName).(type) {
			case []any:
				sliceValue, ok := f.Value.(pflag.SliceValue)
				if !ok {
					err = fmt.Errorf("%s: expected slice, but got %s", propName, f.Value.String())
				}
				for _, y := range x {
					sliceValue.Append(fmt.Sprint(y))
				}
			default:
				f.Value.Set(fmt.Sprintf("%v", x))
			}
		}
	})
	return err
}

type Registerable[T any] interface {
	Register(root *Root[T])
}

func (r *Root[T]) With(subs ...Registerable[T]) *Root[T] {
	for _, sub := range subs {
		sub.Register(r)
	}
	return r
}

func (r *Root[T]) Run(ctx context.Context) {
	if !r.Debug {
		defer func() {
			p := recover()
			if p != nil {
				fmt.Fprint(os.Stderr, color.RedString("PANIC: %s\n", p))
				os.Exit(2)
			}
		}()
	}
	_, err := r.ExecuteContextC(ctx)
	if err != nil {
		fmt.Fprint(os.Stderr, color.RedString("ERROR: %s\n", err.Error()))
		os.Exit(1)
	}
}

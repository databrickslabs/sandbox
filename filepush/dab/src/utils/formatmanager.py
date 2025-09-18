from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class AutoLoaderOption:
  key: str
  value: str
  hidden: bool = False
  def __iter__(self):
    yield (self.key, self)

class AutoLoaderFormat:
  def __init__(self):
    self.name = None
    self.options: set[AutoLoaderOption] = {
      AutoLoaderOption("cloudFiles.inferColumnTypes", "true", True),
      AutoLoaderOption("cloudFiles.schemaEvolutionMode", "addNewColumns", True),
    }

  def __iter__(self):
    yield (self.name, self)

  def get_userfacing_options(self) -> dict[str, str]:
    return {opt.key: opt.value for opt in self.options if not opt.hidden}

  def validate_user_options(self, options: dict[str, str]) -> None:
    allowed = set(self.get_userfacing_options())
    illegal = set(options) - allowed
    if illegal:
      raise ValueError(
        f"Unsupported or protected options: {sorted(illegal)}. "
        f"Allowed user options: {sorted(allowed)}"
      )

  def get_modified_options(self, options: dict[str, str]) -> dict[str, str]:
    self.validate_user_options(options)
    defaults = self.get_userfacing_options()
    return {k: v for k, v in options.items() if k in defaults and v != defaults[k]}

class CSV(AutoLoaderFormat):
  def __init__(self):
    super().__init__()
    self.name = "CSV"
    self.options |= {
      AutoLoaderOption("header", "true", True),
      AutoLoaderOption("mergeSchema", "true", True),
      AutoLoaderOption("delimiter", ","),
      AutoLoaderOption("escape", "\""),
      AutoLoaderOption("multiLine", "false"),
    }

class JSON(AutoLoaderFormat):
  def __init__(self):
    super().__init__()
    self.name = "JSON"
    self.options |= {
      AutoLoaderOption("mergeSchema", "true", True),
      AutoLoaderOption("allowComments", "true"),
      AutoLoaderOption("allowSingleQuotes", "true"),
      AutoLoaderOption("inferTimestamp", "true"),
      AutoLoaderOption("multiLine", "true"),
    }

_supported_formats: dict[str, AutoLoaderFormat] = {f.name: f for f in (CSV(), JSON())}

def get_format_manager(fmt: str) -> dict[str, str]:
  key = fmt.strip().upper()
  try:
    return _supported_formats[key]
  except KeyError:
    supported = ", ".join(sorted(_supported_formats))
    raise ValueError(f"{fmt!r} is not a supported format. Supported formats: {supported}")

# CHANGELOG

## 0.3.4 (2025-10-28)

### Security Fixes

- Fixed path traversal vulnerability in static file serving that could allow access to files outside the build directory
- Restricted CORS middleware to development mode only (controlled by `DEPLOYMENT_MODE` environment variable)

## 0.3.3 (2025-10-18)

### Bug Fixes

- Fixed alignment timeout issues in deployed environments by moving alignment to background tasks with polling

## 0.3.2 (2025-10-17)

### Improvements

- Changed default alignment model back to databricks-hosted endpoint
- Removed alignment model selector from judge creation form
- Upgraded databricks-agents to >=1.8.0

### Bug Fixes

- Fixed duplicate traces being added to labeling sessions

## 0.3.1 (2025-10-09)

### Improvements

- **Client Attribution**: Added monkey patch to set custom client name (`judge-builder-v{VERSION}`) in chat completions for better tracking and analytics

## 0.3.0 (2025-10-03)

### Features

- **Alignment Model Selector**: Introduced a model selector for the alignment "teacher" model, allowing users to choose custom serving endpoints

### Improvements

- Made alignment limit clear with improved UI messaging about the 10-example requirement
- Reduced logging bloat in judge builder and fixed watch.sh script
- Fixed bug in iterative alignments where evaluations were not running on the full set of traces, causing incorrect cached results to be used

## 0.2.1 (2025-09-24)

### Improvements

- Cache results of schema analysis to get potential output types

## 0.2.0 (2025-09-23)

### Features

- **MLflow Integration**: Integrated `make_judge` and `align` functions from MLflow 3.4.0 for enhanced judge creation and alignment capabilities
- **Expanded Judge Support**: Added support for judges over expectations or traces (e.g., correctness judges), extending beyond the original use cases
- **Arbitrary Output Support**: Enhanced judge outputs to support arbitrary categorical values instead of being limited to just pass/fail binary outcomes

### Improvements

- Enhanced alignment visualization with improved metrics display and filtering options
- Added version comparison indicators showing agreement/disagreement progression
- Improved UI layout for better alignment results presentation

## 0.1.0 (2025-08-26)

Initial version of Judge Builder

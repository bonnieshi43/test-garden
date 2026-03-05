# Test Documentation Archive

## Overview

This directory (`test-docs/`) is used to archive various test-related documentation for the project. It provides a structured organization system for storing test cases, test reports, templates, and shared resources.

## Directory Structure

```
test-docs/
├── modules/                    # Organized by module/feature
│   ├── dashboard/             # Dashboard module
│   │   ├── README.md          # Module documentation
│   │   ├── chart-properties.md
│   │   ├── chart-dc.md
│   │   └── chart-action.md
│   ├── em/                    # EM module
│   └── portal/                # Portal module
│
├── test-types/                # Organized by test type
│   ├── performance/           # Performance testing
│   └── concurrency/           # Concurrency testing
│
├── templates/                 # Test documentation templates
│   ├── test-case-template.md
│   ├── test-report-template.md
│   └── bug-report-template.md
│
└── shared/                    # Shared resources
    ├── test-data.md           # Common test data
    └── environment.md         # Environment configuration
```

## Directory Descriptions

### `modules/`
Organized by functional modules or features. Each module can contain:
- Module-specific README documentation
- Test case documents
- Test reports
- Related test artifacts

### `test-types/`
Organized by testing methodology or test type:
- **performance/**: Performance and load testing documentation
- **concurrency/**: Concurrency and stress testing documentation

### `templates/`
Reusable templates for creating consistent test documentation:
- Test case templates
- Test report templates
- Bug report templates

### `shared/`
Common resources used across multiple test scenarios:
- Shared test data
- Environment configuration documentation
- Common utilities or guidelines

## Usage Guidelines

1. **Module Organization**: Place module-specific test documentation under `modules/[module-name]/`
2. **Test Type Organization**: Place test-type-specific documentation under `test-types/[test-type]/`
3. **Templates**: Use templates from `templates/` when creating new test documentation
4. **Shared Resources**: Reference shared resources from `shared/` to maintain consistency

## Contributing

When adding new test documentation:
1. Choose the appropriate directory based on organization method (module vs. test type)
2. Use templates from `templates/` for consistency
3. Update module README files when adding new content
4. Follow existing naming conventions

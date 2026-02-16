# Installation

## Requirements

- Python 3.10 or later
- macOS, Linux, or Windows

## Install from PyPI

```bash
pip install cortex-memory
```

### Optional extras

=== "API Server"
    ```bash
    pip install cortex-memory[api]
    ```

    Includes FastAPI, Uvicorn, and HTTPX for the REST API and dashboard.

=== "Development"
    ```bash
    pip install cortex-memory[dev]
    ```

    Includes pytest, pytest-cov, and HTTPX for testing.

=== "Everything"
    ```bash
    pip install cortex-memory[all]
    ```

## Install from source

```bash
git clone https://github.com/borjamoskv/cortex.git
cd cortex
pip install -e ".[all]"
```

## Verify installation

```bash
cortex --version
# cortex, version 0.1.0
```

## First steps

```bash
cortex init
cortex status
```

This creates the database at `~/.cortex/cortex.db` and shows you the system health.

# poetry-dynamic-metadata

[![pypi](https://img.shields.io/pypi/v/poetry-dynamic-metadata?style=flat-square)](https://pypi.org/project/poetry-dynamic-metadata/)

Simple poetry plugin that allows to add dynamic metadata to `pyproject.toml` files.

## Example usage

```python3
# my_package/__init__.py
__version__ = "1.1.0"
```

```toml
[tool.poetry-dynamic-metadata]
version = { source_path = "my_package" }
```

## Disable dynamic metadata
```commandline
poetry config dynamic-metadata.disabled true
```

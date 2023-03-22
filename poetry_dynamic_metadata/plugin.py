import enum
import os
import typing

import cleo.io.io as _io
import cleo.io.outputs.output as _output
import poetry.plugins.plugin as _plugin
import poetry.poetry as _poetry
import tomlkit.toml_document as toml


class _StrEnum(str, enum.Enum):
    ...


class _SourceEnum(_StrEnum):
    python_exec = "python_exec"


class _TargetEnum(_StrEnum):
    project = "project"


class _MetaConfig(typing.TypedDict, total=False):
    source_kind: _SourceEnum
    target_kind: _TargetEnum

    source_path: str
    source_attribute: str


def _ensure_bool(
    val: typing.Union[str, bool],
) -> bool:
    if isinstance(val, bool):
        return val
    if isinstance(val, int):
        return bool(val)
    if isinstance(val, str):
        return val.lower().strip()[0] in ('t', 'y', '1')
    return False


class DynamicMetadataPlugin(_plugin.Plugin):
    @staticmethod
    def _read_module_vars(
        source_path: str,
    ) -> typing.Dict[str, typing.Any]:
        module_path = os.path.join(*source_path.split("."))
        module_path_variants = (
            module_path + ".py",
            os.path.join(module_path, "__init__.py"),
        )
        for module_path_variant in module_path_variants:
            try:
                with open(module_path_variant) as f:
                    locals_ = {}
                    exec(f.read(), globals(), locals_)
                    return locals_
            except FileNotFoundError:
                continue
        return {}

    def _read_python_exec(
        self,
        io: _io.IO,
        cfg: _MetaConfig,
        key: str,
    ) -> typing.Any:
        try:
            source_path = cfg["source_path"]
        except KeyError:
            message = (
                f"<b>poetry-dynamic-metadata</b>: <b>path</b> data is missing "
                f"for <b>{key}</b>"
            )
            io.write_error_line(message)
            raise RuntimeError(message)

        module_vars = self._read_module_vars(source_path)
        if not module_vars:
            message = (
                f"<b>poetry-dynamic-metadata</b>: could not import "
                f"<b>{source_path}</b> for <b>{key}</b>"
            )
            io.write_error_line(message)
            raise RuntimeError(message)

        source_attribute = cfg.get("source_attribute", f"__{key}__")
        try:
            value = module_vars[source_attribute]
        except KeyError:
            message = (
                f"<b>poetry-dynamic-metadata</b>: could not get "
                f"<b>{source_attribute}</b> from <b>{source_path}</b> for {key}"
            )
            io.write_error_line(message)
            raise RuntimeError(message)

        return value

    @staticmethod
    def _set_project_value(
        poetry: _poetry.Poetry,
        io: _io.IO,
        key: str,
        value: typing.Any,
    ) -> typing.Any:
        try:
            setattr(poetry.package, key, value)
        except AttributeError:
            message = (
                f"<b>poetry-dynamic-metadata</b>: could not set <b>{key}</b>"
            )
            io.write_error_line(message)
            raise RuntimeError(message)

    def activate(
        self,
        poetry: _poetry.Poetry,
        io: _io.IO,
    ) -> None:
        if _ensure_bool(poetry.config.get("dynamic-metadata.disabled", False)):
            return

        global_cfg: toml.TOMLDocument = poetry.pyproject.data
        tool_cfg: typing.Dict[str, typing.Any] = global_cfg.get("tool", {})
        plugin_cfg: typing.Dict[str, _MetaConfig] = tool_cfg.get(
            "poetry-dynamic-metadata",
        )
        if plugin_cfg is None:
            return

        for key, cfg in plugin_cfg.items():
            source_kind = cfg.get("source_kind", _SourceEnum.python_exec)
            target_kind = cfg.get("target_kind", _TargetEnum.project)

            if source_kind == _SourceEnum.python_exec:
                value = self._read_python_exec(
                    io=io,
                    cfg=cfg,
                    key=key,
                )
            else:
                message = (
                    f"<b>poetry-dynamic-metadata</b>: <b>source_kind</b> value for "
                    f"<b>{key}</b> has unknown format; "
                    f"possible values: "
                    f"{', '.join((str(val) for val in _SourceEnum))}"
                )
                io.write_error_line(message)
                raise RuntimeError(message)

            if target_kind == _TargetEnum.project:
                self._set_project_value(
                    poetry=poetry,
                    io=io,
                    key=key,
                    value=value,
                )
            else:
                message = (
                    f"<b>poetry-dynamic-metadata</b>: <b>target_kind</b> value for "
                    f"<b>{key}</b> has unknown format; "
                    f"possible values: "
                    f"{', '.join((str(val) for val in _TargetEnum))}"
                )
                io.write_error_line(message)
                raise RuntimeError(message)

            io.write_line(
                f"<b>poetry-dynamic-metadata</b>: <b>{key}</b> replaced",
                verbosity=_output.Verbosity.DEBUG,
            )

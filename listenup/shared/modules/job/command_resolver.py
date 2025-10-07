from typing import Dict
from shared.modules.job.models.command_spec import CommandSpec


class CommandResolver:
    """
    Resolves a CommandSpec, replacing input/output placeholders with actual file paths or URIs.

    Example:
        spec = CommandSpec(
            program="ffmpeg",
            flags={"-i": "{{input_audio}}", "-ar": "44100"},
            args=["{{output_audio}}"]
        )
        resolved = CommandResolver.resolve(spec, {"input_audio": "/tmp/in.wav"}, {"output_audio": "/tmp/out.wav"})
        # -> ffmpeg -i /tmp/in.wav -ar 44100 /tmp/out.wav
    """

    @staticmethod
    def resolve(spec: CommandSpec, inputs: Dict[str, str], outputs: Dict[str, str]) -> CommandSpec:
        """
        Replace placeholders like {{input_name}} or {{output_name}} in flags and args.

        Args:
            spec: The original CommandSpec
            inputs: Dict of input_name -> local file path or URI
            outputs: Dict of output_name -> local file path or URI

        Returns:
            CommandSpec with placeholders replaced
        """
        def _replace_placeholders(value: str) -> str:
            """Replace a single placeholder with its resolved path."""
            if not isinstance(value, str):
                return value
            if value.startswith("{{") and value.endswith("}}"):
                key = value.strip("{}").strip()
                return inputs.get(key) or outputs.get(key) or value
            return value

        # Resolve flags
        resolved_flags = {flag: _replace_placeholders(val) for flag, val in spec.flags.items()}

        # Resolve args
        resolved_args = [_replace_placeholders(arg) for arg in spec.args]

        # Preserve all other fields
        return CommandSpec(
            program=spec.program,
            flags=resolved_flags,
            args=resolved_args,
            shell=spec.shell,
            cwd=spec.cwd,
            env=spec.env
        )

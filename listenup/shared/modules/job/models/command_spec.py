from typing import List, Dict, Optional, Union
from pydantic import BaseModel, Field

class CommandSpec(BaseModel):
    """
    Serializable representation of a shell command.

    Example:
        cmd = CommandSpec(
            program="ffmpeg",
            flags={"-i": "input.wav", "-ar": 44100, "-ac": 2},
            args=["output.wav"]
        )
    """
    program: str = Field(..., description="Base command or executable name")
    flags: Dict[str, Union[str, int, float, bool]] = Field(default_factory=dict, description="CLI flags e.g. {'-i': 'input.wav', '-ar': 44100}")
    args: List[str] = Field(default_factory=list, description="Ordered positional args")
    shell: bool = False
    cwd: Optional[str] = None
    env: Optional[Dict[str, str]] = None

    def to_subprocess(self) -> List[str]:
        """Convert into subprocess argument list."""
        cmd = [self.program]
        for flag, value in self.flags.items():
            cmd.extend([flag, str(value)])
        cmd.extend(self.args)
        return cmd

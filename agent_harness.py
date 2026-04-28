"""Backwards-compatible CLI wrapper.

The main implementation lives in :mod:`micro_agent.agent_harness`.
"""

from micro_agent.agent_harness import *  # noqa: F403
from micro_agent.agent_harness import main


if __name__ == "__main__":
    raise SystemExit(main(__import__("sys").argv[1:]))

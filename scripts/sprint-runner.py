#!/usr/bin/env python3
"""Autonomous Sprint Runner — ARGUS entry point.

Imports from the workflow submodule. Set WORKFLOW_ENV_PREFIX=ARGUS
to use ARGUS_RUNNER_MODE, ARGUS_RUNNER_SPRINT_DIR, ARGUS_COST_CEILING
environment variables.
"""
import sys
import os

# Add workflow submodule runner to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'workflow', 'runner'))

# Set ARGUS-specific env prefix
os.environ.setdefault("WORKFLOW_ENV_PREFIX", "ARGUS")

from sprint_runner.main import main

if __name__ == "__main__":
    main()

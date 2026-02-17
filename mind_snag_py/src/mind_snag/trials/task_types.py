"""Task type definitions for trial-aligned raster extraction.

Replaces the 250 lines of repetitive try/catch blocks in extract_rasters.m
with a data-driven list of TaskTypeConfig dataclasses.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TaskTypeConfig:
    """Configuration for one task type in raster extraction.

    Parameters
    ----------
    name : short identifier (e.g. 'CO', 'Lum')
    py_task_types : list of PyTaskType strings that map to this task
    primary_event : event field to align spikes to (tried first)
    fallback_event : fallback event field (tried if primary fails)
    time_window : (start, stop) in ms around event
    rt_event : event field for reaction time start
    rt_baseline : event field for reaction time baseline
    rt_fallback_event : fallback for rt_event
    rt_fallback_baseline : fallback for rt_baseline
    """

    name: str = ""
    py_task_types: list[str] = field(default_factory=list)
    primary_event: str = "TargsOn"
    fallback_event: str | None = None
    time_window: tuple[int, int] = (-300, 500)
    rt_event: str = "SaccStart"
    rt_baseline: str = "TargsOn"
    rt_fallback_event: str | None = None
    rt_fallback_baseline: str | None = None


TASK_TYPES: list[TaskTypeConfig] = [
    TaskTypeConfig(
        name="CO",
        py_task_types=["delayed_saccade"],
        primary_event="TargsOn",
        fallback_event="disTargsOn",
        time_window=(-300, 500),
        rt_event="SaccStart",
        rt_baseline="TargsOn",
        rt_fallback_event="SaccStart",
        rt_fallback_baseline="disTargsOn",
    ),
    TaskTypeConfig(
        name="Lum",
        py_task_types=["luminance_reward_selection"],
        primary_event="disGo",
        fallback_event="Go",
        time_window=(-300, 500),
        rt_event="SaccStart",
        rt_baseline="disGo",
        rt_fallback_event="SaccStart",
        rt_fallback_baseline="Go",
    ),
    TaskTypeConfig(
        name="Reach",
        py_task_types=["delayed_reach_and_saccade", "delayed_reach", "gaze_anchoring"],
        primary_event="ReachStart",
        fallback_event=None,
        time_window=(-400, 400),
        rt_event="ReachStart",
        rt_baseline="TargsOn",
    ),
    TaskTypeConfig(
        name="GAF",
        py_task_types=["gaze_anchoring_fast"],
        primary_event="disTargsOn",
        fallback_event="TargsOn",
        time_window=(-300, 500),
        rt_event="SaccStart",
        rt_baseline="disGo",
        rt_fallback_event="SaccStart",
        rt_fallback_baseline="Go",
    ),
    TaskTypeConfig(
        name="Saccade",
        py_task_types=["doublestep_saccade_fast"],
        primary_event="disTargsOn",
        fallback_event="TargsOn",
        time_window=(-300, 500),
        rt_event="SaccStart",
        rt_baseline="disGo",
        rt_fallback_event="SaccStart",
        rt_fallback_baseline="Go",
    ),
    TaskTypeConfig(
        name="Touch_feed",
        py_task_types=["simple_touch_task_feedback"],
        primary_event="disTargsOn",
        fallback_event="TargsOn",
        time_window=(-300, 500),
        rt_event="SaccStart",
        rt_baseline="disGo",
        rt_fallback_event="SaccStart",
        rt_fallback_baseline="Go",
    ),
    TaskTypeConfig(
        name="Touch",
        py_task_types=["simple_touch_task"],
        primary_event="disTargsOn",
        fallback_event="TargsOn",
        time_window=(-300, 500),
        rt_event="SaccStart",
        rt_baseline="disGo",
        rt_fallback_event="SaccStart",
        rt_fallback_baseline="Go",
    ),
    TaskTypeConfig(
        name="Null",
        py_task_types=["null"],
        primary_event="Pulse_start",
        fallback_event=None,
        time_window=(-300, 500),
        rt_event="",
        rt_baseline="",
    ),
]

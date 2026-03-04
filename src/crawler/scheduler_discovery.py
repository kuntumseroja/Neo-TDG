"""Hangfire/Quartz scheduled job discovery."""

import re
from typing import List
from src.models.crawler import SchedulerInfo

# Hangfire patterns
_HANGFIRE_RECURRING = re.compile(
    r'RecurringJob\.AddOrUpdate[<\(].*?"([^"]+)".*?(?:Cron\.(\w+)|"([^"]*?[*\d]+[^"]*?)")',
    re.DOTALL,
)
_HANGFIRE_ENQUEUE = re.compile(
    r"BackgroundJob\.Enqueue[<(].*?(\w+)\.(\w+)",
    re.DOTALL,
)
_HANGFIRE_SCHEDULE = re.compile(
    r'BackgroundJob\.Schedule[<(].*?(\w+)\.(\w+).*?TimeSpan\.From(\w+)\((\d+)\)',
    re.DOTALL,
)

# Quartz patterns
_QUARTZ_JOB = re.compile(
    r'JobBuilder\.Create<(\w+)>',
)
_QUARTZ_TRIGGER = re.compile(
    r'WithCronSchedule\("([^"]+)"\)',
)

# IHostedService pattern
_HOSTED_SERVICE = re.compile(
    r"class\s+(\w+)\s*:\s*.*?(?:IHostedService|BackgroundService)",
    re.MULTILINE,
)


def discover_schedulers(content: str, file_path: str) -> List[SchedulerInfo]:
    """Find Hangfire, Quartz, and IHostedService scheduled jobs."""
    results = []

    # Hangfire recurring jobs
    for match in _HANGFIRE_RECURRING.finditer(content):
        job_name = match.group(1)
        cron = match.group(2) or match.group(3) or ""
        if match.group(2):
            cron = f"Cron.{cron}"

        results.append(SchedulerInfo(
            job_name=job_name,
            cron_expression=cron,
            handler_class="",
            file=file_path,
            description=f"Hangfire recurring job: {job_name}",
        ))

    # Hangfire enqueue (fire-and-forget)
    for match in _HANGFIRE_ENQUEUE.finditer(content):
        class_name = match.group(1)
        method = match.group(2)
        results.append(SchedulerInfo(
            job_name=f"{class_name}.{method}",
            cron_expression="fire-and-forget",
            handler_class=class_name,
            file=file_path,
            description=f"Hangfire enqueue: {class_name}.{method}",
        ))

    # Hangfire scheduled
    for match in _HANGFIRE_SCHEDULE.finditer(content):
        class_name = match.group(1)
        method = match.group(2)
        unit = match.group(3)
        value = match.group(4)
        results.append(SchedulerInfo(
            job_name=f"{class_name}.{method}",
            cron_expression=f"delayed {value} {unit.lower()}",
            handler_class=class_name,
            file=file_path,
            description=f"Hangfire scheduled: {class_name}.{method} after {value} {unit.lower()}",
        ))

    # Quartz jobs
    quartz_jobs = _QUARTZ_JOB.findall(content)
    quartz_crons = _QUARTZ_TRIGGER.findall(content)
    for i, job_class in enumerate(quartz_jobs):
        cron = quartz_crons[i] if i < len(quartz_crons) else ""
        results.append(SchedulerInfo(
            job_name=job_class,
            cron_expression=cron,
            handler_class=job_class,
            file=file_path,
            description=f"Quartz job: {job_class}",
        ))

    # IHostedService / BackgroundService
    for match in _HOSTED_SERVICE.finditer(content):
        service_name = match.group(1)
        results.append(SchedulerInfo(
            job_name=service_name,
            cron_expression="hosted-service",
            handler_class=service_name,
            file=file_path,
            description=f"Background service: {service_name}",
        ))

    return results

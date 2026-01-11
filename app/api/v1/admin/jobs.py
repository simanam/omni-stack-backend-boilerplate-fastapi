"""
Admin job monitoring endpoints.
Requires admin role for access.
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.core.security import require_admin
from app.jobs import get_job_pool

router = APIRouter(dependencies=[Depends(require_admin)])


class JobInfo(BaseModel):
    """Job information response."""

    job_id: str
    function: str
    args: list[Any]
    kwargs: dict[str, Any]
    enqueue_time: datetime | None = None
    start_time: datetime | None = None
    finish_time: datetime | None = None
    success: bool | None = None
    result: Any | None = None


class JobListResponse(BaseModel):
    """Response for job listing."""

    jobs: list[JobInfo]
    total: int


class JobStatusResponse(BaseModel):
    """Response for job status."""

    job_id: str
    status: str
    function: str | None = None
    enqueue_time: datetime | None = None
    start_time: datetime | None = None
    finish_time: datetime | None = None
    success: bool | None = None
    result: Any | None = None


@router.get("", response_model=JobListResponse)
async def list_jobs(
    limit: int = Query(50, ge=1, le=100, description="Maximum jobs to return"),
) -> JobListResponse:
    """
    List recent jobs from the queue.

    Requires admin role.
    """
    pool = await get_job_pool()

    if pool is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis not configured, job queue unavailable",
        )

    # Get job IDs from Redis
    # Note: ARQ stores jobs in Redis with specific keys
    job_ids = await pool.keys("arq:job:*")
    jobs: list[JobInfo] = []

    for job_key in job_ids[:limit]:
        job_id = job_key.decode().replace("arq:job:", "")
        try:
            job_data = await pool.get(job_key)
            if job_data:
                import pickle

                job = pickle.loads(job_data)
                jobs.append(
                    JobInfo(
                        job_id=job_id,
                        function=job.get("function", "unknown"),
                        args=job.get("args", []),
                        kwargs=job.get("kwargs", {}),
                        enqueue_time=job.get("enqueue_time"),
                        start_time=job.get("start_time"),
                        finish_time=job.get("finish_time"),
                        success=job.get("success"),
                        result=job.get("result"),
                    )
                )
        except Exception:
            # Skip malformed jobs
            continue

    return JobListResponse(jobs=jobs, total=len(jobs))


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str) -> JobStatusResponse:
    """
    Get status of a specific job.

    Requires admin role.
    """
    pool = await get_job_pool()

    if pool is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis not configured, job queue unavailable",
        )

    # Try to get job info from ARQ
    from arq.jobs import Job

    job = Job(job_id, pool)

    try:
        job_info = await job.info()
    except Exception:
        job_info = None

    if job_info is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )

    return JobStatusResponse(
        job_id=job_id,
        status=job_info.status.value if job_info.status else "unknown",
        function=job_info.function,
        enqueue_time=job_info.enqueue_time,
        start_time=job_info.start_time,
        finish_time=job_info.finish_time,
        success=job_info.success,
        result=job_info.result,
    )


@router.post("/{job_id}/retry")
async def retry_job(job_id: str) -> dict[str, str]:
    """
    Retry a failed job.

    Requires admin role.
    """
    pool = await get_job_pool()

    if pool is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis not configured, job queue unavailable",
        )

    from arq.jobs import Job

    job = Job(job_id, pool)

    try:
        job_info = await job.info()
    except Exception:
        job_info = None

    if job_info is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )

    if job_info.success is True:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot retry a successful job",
        )

    # Re-enqueue the job
    new_job = await pool.enqueue_job(
        job_info.function,
        *job_info.args,
        **job_info.kwargs,
    )

    return {
        "message": "Job requeued",
        "original_job_id": job_id,
        "new_job_id": new_job.job_id if new_job else "unknown",
    }


@router.delete("/{job_id}")
async def cancel_job(job_id: str) -> dict[str, str]:
    """
    Cancel a pending job.

    Requires admin role.
    """
    pool = await get_job_pool()

    if pool is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis not configured, job queue unavailable",
        )

    from arq.jobs import Job

    job = Job(job_id, pool)

    try:
        job_info = await job.info()
    except Exception:
        job_info = None

    if job_info is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )

    # Abort the job
    try:
        await job.abort()
        return {"message": f"Job {job_id} cancelled"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to cancel job: {str(e)}",
        )

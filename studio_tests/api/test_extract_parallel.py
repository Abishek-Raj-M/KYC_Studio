from __future__ import annotations

import asyncio
import io
import time
from unittest.mock import patch

from starlette.datastructures import UploadFile


def test_extract_documents_runs_uploads_in_parallel() -> None:
    from main import _extract_one_upload

    def fake_sync(api_key: str, temp_path: str, declared: str | None) -> dict:
        time.sleep(0.2)
        return {"document_type": declared or "pan", "name": "TEST"}

    uploads = [
        UploadFile(filename="a.png", file=io.BytesIO(b"a")),
        UploadFile(filename="b.png", file=io.BytesIO(b"b")),
        UploadFile(filename="c.png", file=io.BytesIO(b"c")),
    ]

    async def run() -> list[dict]:
        with patch("main._extract_upload_sync", side_effect=fake_sync):
            return list(
                await asyncio.gather(
                    *[
                        _extract_one_upload(
                            "key",
                            idx,
                            upload,
                            ["pan", "aadhaar", "passport"],
                            ["front", "front", "front"],
                        )
                        for idx, upload in enumerate(uploads)
                    ]
                )
            )

    started = time.perf_counter()
    results = asyncio.run(run())
    elapsed = time.perf_counter() - started

    assert len(results) == 3
    assert elapsed < 0.55, f"expected parallel execution, took {elapsed:.2f}s"

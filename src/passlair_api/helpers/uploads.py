"""Keeps uploaded files in memory and caps their size.

Uploads here are plaintext vault exports. Werkzeug's default stream factory
spools any upload past 500 KB to a temporary file on disk, which would leave
plaintext passwords in /tmp. Capping the request size makes holding the
whole upload in memory safe.
"""

from io import BytesIO
from typing import IO

from flask import Flask, Request

# A vault export is ~100 bytes per entry, so 1 MiB is ~10k entries --
# far above a real vault, far below anything that strains memory.
MAX_UPLOAD_BYTES = 1024 * 1024


class InMemoryRequest(Request):
    def _get_file_stream(
        self,
        total_content_length: int | None,
        content_type: str | None,
        filename: str | None = None,
        content_length: int | None = None,
    ) -> IO[bytes]:
        return BytesIO()


def apply_upload_limits(app: Flask) -> None:
    """Every file part stays in memory; any body over the cap is rejected
    with 413 while it streams in, with or without a Content-Length."""
    app.request_class = InMemoryRequest
    app.config.update(
        MAX_CONTENT_LENGTH=MAX_UPLOAD_BYTES,
        # Non-file fields (the paste textarea) default to a 500 KB cap;
        # match the file cap so pasting and uploading accept the same export.
        MAX_FORM_MEMORY_SIZE=MAX_UPLOAD_BYTES,
    )

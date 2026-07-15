# /// script
# dependencies = [
#   "genbadge",
#   "pypinfo",
# ]
# ///

# ruff: noqa: CPY001, D100, D103

from __future__ import annotations

import json
import subprocess as sp
import sys
from pathlib import Path
from typing import Any, no_type_check

from genbadge import Badge  # pyright: ignore[reportMissingImports, reportUnknownVariableType]


# NOTE: This script needs a Google BigQuery API credentials JSON file to run pypinfo.
#       In a GitHub Actions workflow, we can't directly pass a file through secrets
#       — secrets are strings. The core challenge is securely materializing that
#       JSON file at runtime without leaking credentials.
#       We store the entire JSON content as a GitHub Secret, then write it
#       to a temporary file in the workflow step. GitHub Actions runners are ephemeral,
#       so the file disappears after the job completes.
#
# NOTE: alternative to get downloads count. The downside is pypistats.org is a
#       third-party service (run by the Python Packaging Authority) that may have
#       rate limits or availability issues, and the data granularity differs
#       from BigQuery.
#
# def main():
#     url = "https://pypistats.org/api/packages/standard-deluxe/recent"
#     resp = requests.get(url)
#     data = resp.json()["data"]
#     downloads = f"{data['last_month']:,}"
#     print(downloads)


@no_type_check
def main() -> int:
    # token = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    pypinfo = str(Path(sys.exec_prefix, "bin", "pypinfo"))
    file = str(Path(__file__).parent.parent / "assets" / "downloads.svg")
    cp = sp.run(  # noqa: S603
        (
            pypinfo,
            # "--all",  # this give very high number!
            "--json",
            "--days",
            "365",
            "standard-deluxe",
        ),
        capture_output=True,
        text=True,
        shell=False,
        check=False,
    )
    if cp.returncode:
        sys.stderr.write(cp.stderr)
        downloads = "0"
    else:
        downloads = format(json.loads(cp.stdout)["rows"][0]["download_count"], ",")
    badge: Any = Badge(left_txt="downloads", right_txt=downloads, color="purple")
    badge.write_to(file, use_shields=False)
    sys.stderr.write(downloads)
    return 0


if __name__ == "__main__":
    sys.exit(main())

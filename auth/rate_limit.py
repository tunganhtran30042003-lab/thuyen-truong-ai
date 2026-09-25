import time
from collections import defaultdict
from typing import Dict, List

_WINDOW_SECONDS = 60
_MAX_REQUESTS_PER_WINDOW = 60

_buckets: Dict[str, List[float]] = defaultdict(list)


def is_rate_limited(captain_key: str) -> bool:
    now = time.time()
    bucket = _buckets[captain_key]
    cutoff = now - _WINDOW_SECONDS
    while bucket and bucket[0] < cutoff:
        bucket.pop(0)
    if len(bucket) >= _MAX_REQUESTS_PER_WINDOW:
        return True
    bucket.append(now)
    return False
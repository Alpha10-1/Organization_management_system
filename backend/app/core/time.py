from datetime import datetime, timezone


def utcnow() -> datetime:
    """Timezone-aware UTC now(), for use as a Column default/onupdate.

    Replaces the deprecated (as of Python 3.12) datetime.utcnow(), which
    returns a naive datetime that's easy to accidentally compare against
    an aware one.
    """
    return datetime.now(timezone.utc)

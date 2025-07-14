import os
from portkey_ai import createHeaders
from portkey_ai import PORTKEY_GATEWAY_URL as REAL_PORTKEY_GATEWAY_URL


portkey_headers = (
    createHeaders(
        api_key=os.environ["PORTKEY_API_KEY"],
        provider="openai",
        trace_id=os.environ["PORTKEY_TRACE_ID"],
    )
    if "PORTKEY_API_KEY" in os.environ and "PORTKEY_TRACE_ID" in os.environ
    else None
)

PORTKEY_GATEWAY_URL = (
    REAL_PORTKEY_GATEWAY_URL
    if "PORTKEY_API_KEY" in os.environ and "PORTKEY_TRACE_ID" in os.environ
    else None
)

from typing import Annotated

from fastapi import HTTPException, Header


async def get_token_header(x_token: Annotated[str, Header()]) -> str:
    if x_token != "fake-super-secret-token":
        raise HTTPException(status_code=400, detail="X-Token header invalid")
    return x_token


async def get_query_token(q: Annotated[str, Header()]) -> str:
    if q != "fake-super-secret-query-token":
        raise HTTPException(status_code=400, detail="Query token invalid")

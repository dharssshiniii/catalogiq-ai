from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class CatalogIQError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        self.code, self.message, self.status_code = code, message, status_code
        super().__init__(message)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(CatalogIQError)
    async def catalogiq_error(_: Request, exc: CatalogIQError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"error": {"code": exc.code, "message": exc.message}})


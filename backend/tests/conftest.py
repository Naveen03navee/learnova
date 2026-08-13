
from fastapi.exceptions import HTTPException as OriginalHTTPException
class DebugHTTPException(OriginalHTTPException):
    def __init__(self, status_code, detail=None, headers=None):
        print(f'HTTPException {status_code}: {detail}')
        import traceback; traceback.print_stack()
        super().__init__(status_code=status_code, detail=detail, headers=headers)

import fastapi
fastapi.HTTPException = DebugHTTPException
import fastapi.exceptions
fastapi.exceptions.HTTPException = DebugHTTPException


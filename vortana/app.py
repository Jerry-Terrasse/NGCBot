# api_server.py

from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY

from wcferry import Wcf
from OutPut import OutPut

from dateutil import parser

class Event(BaseModel):
    host: str
    level: str
    message: str
    timestamp: str
    class Config:
        extra = "allow"

class EventWrapper(BaseModel):
    data: list[Event]
    
def event2human(e: Event):
    dt = parser.isoparse(e.timestamp)
    dt = dt.astimezone()
    dt_str = dt.strftime('%Y-%m-%d %H:%M:%S')
    return f"""[{e.level.upper()}] from <{e.host}>
at {dt_str}

{e.message}"""

def create_app(wcf: Wcf, master: str):
    app = FastAPI()

    app.state.wcf = wcf
    app.state.master = master

    @app.get("/status")
    async def read_status():
        return {"status": "running"}
    
    @app.post("/send")
    async def send_msg(req: EventWrapper):
        wcf: Wcf = app.state.wcf
        try:
            for event in req.data:
                msg = event2human(event)
                res = wcf.send_text(msg=msg, receiver=app.state.master)
                assert res == 0, f"send_text failed: {res}"
            return { 'ok': True }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/console")
    async def send_console(req: EventWrapper):
        try:
            OutPut.outPut(str(req))
            return { 'ok': True }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        exc_str = f'{exc}'.replace('\n', ' ').replace('   ', ' ')
        OutPut.outPut(f"{request}: {exc_str}")
        content = {'status_code': 10422, 'message': exc_str, 'data': None}
        return JSONResponse(content=content, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)
    
    return app
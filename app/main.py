import logging
from fastapi import Depends, FastAPI, HTTPException
from fastapi.requests import Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.dependencies import get_token_header
from app.routers import items, users
from app.utils.modemserial import ModemPool
from app.logging import setup_logging

app = FastAPI(title="Modem-X-Android API")

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Templates
templates = Jinja2Templates(directory="app/templates")

# Create a ModemPool instance
modem_pool = ModemPool()

# Include routers
app.include_router(users.router)
app.include_router(
    items.router,
    prefix="/items",
    tags=["items"],
    dependencies=[Depends(get_token_header)],
)


@app.on_event("startup")
async def startup_event():
    # Setup logging
    setup_logging(log_level=logging.DEBUG)

    # Detect and connect to modems
    modem_pool.detect_modems()
    for modem in modem_pool.modems:
        modem.connect()


@app.on_event("shutdown")
async def shutdown_event():
    # Disconnect from all modems
    for modem in modem_pool.modems:
        modem.disconnect()


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    # Prepare modem data for template
    modem_data = []
    for modem in modem_pool.modems:
        # Get ICCID and number for display
        iccid = modem.get_iccid() if modem.connection else "Not connected"
        number = modem.get_number() if modem.connection else "Not connected"

        modem_data.append(
            {
                "port": modem.port,
                "iccid": iccid,
                "number": number,
                "status": "Connected" if modem.connection else "Disconnected",
                "responses": "",
            }
        )

    return templates.TemplateResponse(
        "index.html",
        {"request": request, "title": "Modem-X-Android", "modems": modem_data},
    )


@app.get("/api/modems", tags=["modems"])
async def get_modems():
    modem_data = [
        {"port": modem.port, "connected": modem.connection is not None}
        for modem in modem_pool.modems
    ]
    return {"modems": modem_data}


@app.post("/api/modems/refresh", tags=["modems"])
async def refresh_modems():
    modem_pool.refresh()
    return {"message": "Modems refreshed", "count": len(modem_pool.modems)}


@app.post("/api/modems/{port}/refresh", tags=["modems"])
async def refresh_modem(port: str):
    # Find the modem with the specified port
    modem = next((m for m in modem_pool.modems if m.port == port), None)
    if not modem:
        raise HTTPException(status_code=404, detail="Modem not found")

    # Disconnect if connected
    if modem.connection:
        modem.disconnect()

    # Reconnect
    modem.connect()

    return {"message": f"Modem {port} refreshed"}


@app.get("/api/modems/{port}/status", tags=["modems"])
async def check_modem_status(port: str):
    # Find the modem with the specified port
    modem = next((m for m in modem_pool.modems if m.port == port), None)
    if not modem:
        raise HTTPException(status_code=404, detail="Modem not found")

    status = {
        "port": modem.port,
        "connected": modem.connection is not None,
        "signal": modem.get_signal_strength() if modem.connection else None,
        "imei": modem.get_imei() if modem.connection else None,
        "iccid": modem.get_iccid() if modem.connection else None,
    }

    return status


@app.post("/api/modems/{port}/pair", tags=["modems"])
async def pair_device(port: str):
    # Find the modem with the specified port
    modem = next((m for m in modem_pool.modems if m.port == port), None)
    if not modem:
        raise HTTPException(status_code=404, detail="Modem not found")

    # This would be where you implement pairing logic
    # For now, just return a placeholder response
    return {"message": f"Pairing initiated for modem {port}"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

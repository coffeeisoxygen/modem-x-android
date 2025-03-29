import logging

from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.logging import setup_logging
from app.routers import modems
from app.utils.modemserial import ModemPool

app = FastAPI(title="Modem-X-Android API")

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Templates
templates = Jinja2Templates(directory="app/templates")

# Create a ModemPool instance
modem_pool = ModemPool()

# Initialize and include router
modems.init(templates, modem_pool)
app.include_router(modems.router)


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
                "responses": modem.get_response_history(),
            }
        )

    return templates.TemplateResponse(
        "index.html",
        {"request": request, "title": "Modem-X-Android", "modems": modem_data},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

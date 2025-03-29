from fastapi import APIRouter, HTTPException

router = APIRouter(
    prefix="/api/modems",
    tags=["modems"],
    responses={404: {"description": "Modem not found"}},
)

# Reference to templates and modem_pool will be set from main.py
templates = None
modem_pool = None


def init(templates_instance, modem_pool_instance):
    """Initialize the router with required dependencies"""
    global templates, modem_pool
    templates = templates_instance
    modem_pool = modem_pool_instance


@router.get("/", tags=["modems"])
async def get_modems():
    modem_data = [
        {"port": modem.port, "connected": modem.connection is not None}
        for modem in modem_pool.modems
    ]
    return {"modems": modem_data}


@router.post("/refresh", tags=["modems"])
async def refresh_modems():
    modem_pool.refresh()
    return {"message": "Modems refreshed", "count": len(modem_pool.modems)}


@router.post("/{port}/refresh", tags=["modems"])
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


@router.get("/{port}/status", tags=["modems"])
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


@router.post("/{port}/pair", tags=["modems"])
async def pair_device(port: str):
    # Find the modem with the specified port
    modem = next((m for m in modem_pool.modems if m.port == port), None)
    if not modem:
        raise HTTPException(status_code=404, detail="Modem not found")

    # This would be where you implement pairing logic
    # For now, just return a placeholder response
    return {"message": f"Pairing initiated for modem {port}"}


@router.post("/{port}/command", tags=["modems"])
async def execute_command(port: str, command: str):
    # Find the modem with the specified port
    modem = next((m for m in modem_pool.modems if m.port == port), None)
    if not modem:
        raise HTTPException(status_code=404, detail="Modem not found")

    response = modem.send_command(command)
    parsed = modem.parse_response(response)

    return {"command": command, "raw_response": response, "parsed_response": parsed}


@router.post("/check-all-iccid", tags=["modems"])
async def check_all_iccid():
    """Get ICCID for all connected modems"""
    results = {}
    for modem in modem_pool.modems:
        if modem.connection:
            results[modem.port] = modem.get_iccid()
        else:
            results[modem.port] = "Not connected"
    return {"iccids": results}


@router.post("/check-all-numbers", tags=["modems"])
async def check_all_numbers():
    """Get phone numbers for all connected modems"""
    results = {}
    for modem in modem_pool.modems:
        if modem.connection:
            results[modem.port] = modem.get_number()
        else:
            results[modem.port] = "Not connected"
    return {"numbers": results}


@router.get("/{port}/number", tags=["modems"])
async def get_modem_number(port: str):
    # Find the modem with the specified port
    modem = next((m for m in modem_pool.modems if m.port == port), None)
    if not modem:
        raise HTTPException(status_code=404, detail="Modem not found")

    number = modem.get_number() if modem.connection else "Not connected"
    return {"port": port, "number": number}


@router.get("/{port}/iccid", tags=["modems"])
async def get_modem_iccid(port: str):
    # Find the modem with the specified port
    modem = next((m for m in modem_pool.modems if m.port == port), None)
    if not modem:
        raise HTTPException(status_code=404, detail="Modem not found")

    iccid = modem.get_iccid() if modem.connection else "Not connected"
    return {"port": port, "iccid": iccid}

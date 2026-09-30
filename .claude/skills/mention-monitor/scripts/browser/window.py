"""Give each parallel lane its own Chrome WINDOW (a background tab stops rendering → screenshots hang).

Usage inside a script:
    page, close = own_window(browser)   # new window, returns its Page
    ...
    close()
A STOP file (runs/STOP) set by any lane after a block signal makes every lane stop at its next check.
"""
from pathlib import Path

STOP_FILE = Path(__file__).resolve().parents[5] / "runs" / "STOP"  # <project>/runs/STOP


def own_window(browser, width: int = 1400, height: int = 1000):
    ctx = browser.contexts[0]
    before = {id(p) for p in ctx.pages}
    cdp = browser.new_browser_cdp_session()
    target = cdp.send("Target.createTarget", {"url": "about:blank", "newWindow": True,
                                              "width": width, "height": height})["targetId"]
    page = None
    for _ in range(50):
        page = next((p for p in ctx.pages if id(p) not in before), None)
        if page:
            break
        ctx.pages[0].wait_for_timeout(100)
    if page is None:
        raise RuntimeError("không mở được cửa sổ mới")

    def close():
        try:
            cdp.send("Target.closeTarget", {"targetId": target})
        except Exception:
            pass
    return page, close


def stop_requested() -> bool:
    return STOP_FILE.exists()


def request_stop(reason: str) -> None:
    STOP_FILE.parent.mkdir(parents=True, exist_ok=True)
    STOP_FILE.write_text(reason, encoding="utf-8")

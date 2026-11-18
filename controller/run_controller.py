"""Treeline control app: listens to Asterisk (ARI) and decides every call."""

import logging
import threading
import time

import websocket

from treeline import ari as ari_mod
from treeline import db, jobs
from treeline.calls import Engine

log = logging.getLogger("treeline")


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    client = ari_mod.Ari()
    engine = Engine(client)
    engine.clean_up_after_restart()
    threading.Thread(target=jobs.run_forever, args=(client,), daemon=True).start()

    ws_url = client.url.replace("http", "ws", 1) + \
        f"/events?app={ari_mod.APP}&api_key={client.user}:{client.password}"
    while True:
        log.info("connecting to Asterisk at %s", client.url)
        ws = websocket.WebSocketApp(
            ws_url, on_message=engine.on_message,
            on_open=lambda _ws: log.info("connected; waiting for calls"),
            on_error=lambda _ws, err: log.warning("websocket: %s", err))
        ws.run_forever()
        time.sleep(3)  # Asterisk not up yet, or restarted; retry


if __name__ == "__main__":
    main()

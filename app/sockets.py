from __future__ import annotations
from typing import Any, Dict

from flask import request
from flask_socketio import Namespace, join_room, leave_room, emit
from .extensions import socketio

UPDATES_NS = "/updates"


class UpdatesNamespace(Namespace):
    def on_connect(self):
        room = request.args.get("page") or request.args.get("room")
        if room:
            join_room(room, namespace=self.namespace)
            emit("joined", {"room": room}, to=request.sid, namespace=self.namespace)

        emit("status", {"ok": True}, to=request.sid, namespace=self.namespace)

    def on_join(self, data: Dict[str, Any] | None):
        room = (data or {}).get("room") or (data or {}).get("page")
        if room:
            join_room(room, namespace=self.namespace)
            emit("joined", {"room": room}, to=request.sid, namespace=self.namespace)

    def on_leave(self, data: Dict[str, Any] | None):
        room = (data or {}).get("room") or (data or {}).get("page")
        if room:
            leave_room(room, namespace=self.namespace)
            emit("left", {"room": room}, to=request.sid, namespace=self.namespace)

    def on_disconnect(self):
        pass


def init_socketio_handlers() -> None:
    try:
        socketio.on_namespace(UpdatesNamespace(UPDATES_NS))
    except ValueError:
        pass


def emit_refresh(target: str, extra: Dict[str, Any] | None = None) -> None:
    payload: Dict[str, Any] = {"page": target}
    if isinstance(extra, dict):
        payload.update(extra)

    if not target or target == "*":
        socketio.emit("refresh", payload, broadcast=True, namespace=UPDATES_NS)
    else:
        socketio.emit("refresh", payload, room=target, namespace=UPDATES_NS)

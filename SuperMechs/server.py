import logging
import typing as t

from socketio import AsyncClient

from config import CLIENT_VERSION, WU_SERVER_URL

if t.TYPE_CHECKING:
    from aiohttp import ClientSession


logger = logging.getLogger(f"main.{__name__}")


class SMServer:
    def __init__(self, session: "ClientSession") -> None:
        self.session = session
        self.connections: dict[str, AsyncClient] = {}

    async def create_socket(self, name: str) -> AsyncClient:
        """Create & connect to a socket for a player."""

        sio = AsyncClient(logger=logger, http_session=self.session, ssl_verify=False)
        sio.on("connect", lambda: logger.info(f"Connected as {name}"))
        sio.on("disconnect", lambda: logger.info(f"{name} disconnected"))
        sio.on(
            "connect_error", lambda data: logger.warning(f"Connection failed for {name}:\n{data}")
        )
        sio.on("message", lambda data: logger.info(f"Message: {data}"))
        sio.on("server.message", lambda data: logger.warning(f"Server message: {data}"))

        await sio.connect(
            WU_SERVER_URL,
            headers={"x-player-name": name, "x-client-version": CLIENT_VERSION},
        )

        sid = sio.get_sid()
        logger.info(f"SID for {name} is {sid}")

        assert sid is not None
        self.connections[sid] = sio

        return sio

    async def kill_connections(self) -> None:
        """Disconnects all currently connected users."""

        for id, socket in tuple(self.connections.items()):
            await socket.disconnect()
            del self.connections[id]

import asyncio
import aiohttp
import socketio

WU_SERVER_URL = "https://supermechs-workshop-server.thearchives.repl.co"


async def main():
    session = aiohttp.ClientSession()
    sio = socketio.AsyncClient(http_session=session, ssl_verify=False)

    @sio.event
    async def message(data):
        print("I received a message!")
        print(data)

    @sio.event
    def connect():
        print("I'm connected!")

    @sio.event
    def connect_error(data):
        print("The connection failed!")
        print(data)

    @sio.event
    def disconnect():
        print("I'm disconnected!")

    @sio.on("*")  # type: ignore
    def catch_all(event, data):
        print(event, data)

    try:
        await sio.connect(
            WU_SERVER_URL, headers={"x-player-name": "Eneg", "x-client-version": "gobsmacked!!!"}
        )

        while True:
            await sio.send("foo")
            await sio.sleep(3)

    finally:
        await sio.disconnect()
        await session.close()


if __name__ == "__main__":
    asyncio.run(main())

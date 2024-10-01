# built ins
import asyncio
import json
from typing import Dict, Optional

# project
from helpers.managers import ManagedRFQs, ManagedMMP


class ParadigmWSMessageProcessor:
    """
    Class to help process messages received
    via the WebSocket Interface & to call
    related resource coroutines.
    """
    def __init__(
        self,
        message_queue: asyncio.Queue,
        managed_rfqs: ManagedRFQs,
        managed_mmp: Optional[ManagedMMP] = None
            ) -> None:
        self.message_queue: asyncio.Queue = message_queue
        self.managed_rfqs: ManagedRFQs = managed_rfqs
        self.managed_mmp: Optional[ManagedMMP] = managed_mmp

        # Instantiate WebSocket message ingestor
        asyncio.get_event_loop().create_task(
            self.ingestor()
            )

    async def ingestor(self) -> None:
        """
        Coroutine to ingest & call related resources.
        """
        while True:
            msg: str = await self.message_queue.get()
            msg: Dict = json.loads(msg)

            ws_channel: str = msg['params']['channel']

            if ws_channel == 'market_maker_protection':
                await self.managed_mmp.ingest_ws_message(
                    message=msg
                    )
            else:
                await self.managed_rfqs.ingest_ws_message(
                    message=msg
                    )

            await asyncio.sleep(0)

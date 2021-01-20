"""
Paradigm RFQ API Authentication + Subscribe & Unsubscribe to
Notification channels.

Usage:
    python3 JSON-RPCoverWebSockets_heartbeat_subscribe.py

Environment Variables:
    PARADIGM_ACCESS_KEY: Paradigm Account Access Key
    WS_URL: Paradigm's Websocket URL

Requirements:
    pip3 install websockets
"""

# built ins
import asyncio
import json
import os
import traceback

# installed
import websockets


# Primary Function
async def main(api_key, ws_url):
    """
    Open the websocket connection and prints
    available quoted RFQs.
    """
    async with websockets.connect(
            f'{ws_url}?api-key={api_key}',
    ) as websocket:
        # Start the heartbeat thread
        asyncio.get_event_loop().create_task(send_heartbeat(websocket))

        # Subcribe to RFQ Notification Channel
        await subscribe_rfq_notification(websocket)
        # Subcribe to Quote Notification Channel
        await subscribe_quote_notification(websocket)
        # Subcribe to Trade Notification Channel
        await subscribe_trade_notification(websocket)
        # Subcribe to Trade_Confirmation Notification Channel
        await subscribe_tradeconfirmation_notification(websocket)

        while True:
            # Receive messages
            message = await websocket.recv()

            # print('Received Message:')
            message = json.loads(message)
            print(message)
            # print(message.keys())

            if 'params' in message:
                if 'channel' in message['params'].keys():
                    # Check RFQ Notification response.
                    if message['params']['channel'] == 'rfq':
                        # pass
                        print('RFQ Notification response')
                        print(message['params']['data'])
                        print(message['params']['data'].keys())

                    # Check Quote Notification response.
                    if message['params']['channel'] == 'quote':
                        # pass
                        print('Quote Notification response')
                        print(message['params']['data'])
                        print(message['params']['data'].keys())

                    # Check Trade Notification response.
                    if message['params']['channel'] == 'trade':
                        # pass
                        print('Trade Notification response')
                        print(message['params']['data'])
                        print(message['params']['data'].keys())

                    # Check Trade_Confirmation Notification response.
                    if message['params']['channel'] == 'trade_confirmation':
                        # pass
                        print('Trade_Confirmation Notification response')
                        print(message['params']['data'])
                        print(message['params']['data'].keys())


# Heartbeat Function
async def send_heartbeat(websocket):
    """
    Send a heartbeat message to keep the connection alive.
    """
    while True:
        await websocket.send(json.dumps({
            "id": 1,
            "jsonrpc": "2.0",
            "method": "heartbeat"
        }))
        await asyncio.sleep(5)


# Subscription Channel Functions
async def subscribe_rfq_notification(websocket):
    """
    Subscribe to the RFQ Channel to receive RFQ updates.
    """
    print('Subscribed to RFQ Channel')
    await websocket.send(json.dumps({
                            "id": 2,
                            "jsonrpc": "2.0",
                            "method": "subscribe",
                            "params": {
                                "channel": "rfq"
                            }
                        }))


async def subscribe_quote_notification(websocket):
    """
    Subscribe to the Quote Channel to receive Quote updates.
    """
    print('Subscribed to Quote Channel')
    await websocket.send(json.dumps({
                            "id": 3,
                            "jsonrpc": "2.0",
                            "method": "subscribe",
                            "params": {
                                "channel": "quote"
                            }
                        }))


async def subscribe_trade_notification(websocket):
    """
    Subscribe to the Trade Channel to receive Trade updates.
    """
    print('Subscribed to Trade Channel')
    await websocket.send(json.dumps({
                            "id": 4,
                            "jsonrpc": "2.0",
                            "method": "subscribe",
                            "params": {
                                "channel": "trade"
                            }
                        }))


async def subscribe_tradeconfirmation_notification(websocket):
    """
    Subscribe to the Trade Confirmation Channel to receive Trade updates.
    """
    print('Subscribed to Trade Confirmation Channel')
    await websocket.send(json.dumps({
                            "id": 4,
                            "jsonrpc": "2.0",
                            "method": "subscribe",
                            "params": {
                                "channel": "trade_confirmation"
                            }
                        }))


if __name__ == "__main__":
    # Local Testing
    os.environ['PARADIGM_ACCESS_KEY'] = '<access-key>'
    os.environ['WS_URL'] = "wss://ws.api.test.paradigm.co/"

    try:
        print('Paradigm Access Key: {}'.format(os.environ['PARADIGM_ACCESS_KEY']))
        print('WS URL: {}'.format(os.environ['WS_URL']))

        # Start the client
        asyncio.get_event_loop().run_until_complete(main(api_key=os.environ['PARADIGM_ACCESS_KEY'],
                                                         ws_url=os.environ['WS_URL']))

        asyncio.get_event_loop().run_forever()
    except Exception as e:
        print('Local Main Error')
        print(e)
        traceback.print_exc()

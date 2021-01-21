"""
Connects to the Paradigm API using JSON-RPCoverWebSockets
and as the Taker prints out the ACTIVE RFS RFQ Quotes.

Ensure this script is running before the Taker creates RFQs.

Usage:
    python3 TakerRFSNotifications.py [PARADIGM_ACCESS_KEY]

Requirements:
    pip3 install websockets
    pip3 install pandas
"""
# built ins
import asyncio
import json
import sys
import os
import traceback

# installed
import websockets
import pandas as pd


# Primary Function
async def main(api_key, ws_url):
    """
    Open the websocket connection and prints
    available quoted RFQs.
    """
    async with websockets.connect(
            f'{ws_url}?api-key={api_key}',
            # Comment the above line out and bottom two in to enable header auth
            # ws_url,
            # extra_headers={'authorization': f'Bearer {api_key}'},
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

        # Function to clear terminal window
        clear = lambda: os.system('clear')

        # Function Variables
        quote_dict = {}
        rfq_list = []
        # DataFrame used to print active Bid Quotes
        internal_df_1 = pd.DataFrame()
        # DataFrame used to print active Offer Quotes
        internal_df_2 = pd.DataFrame()
        # DataFrame used to store active Bid Quotes
        internal_df_3 = pd.DataFrame()
        # DataFrame used to store active Offer Quotes
        internal_df_4 = pd.DataFrame()

        while True:
            # Receive messages
            message = await websocket.recv()

            # print('Received Message:')
            message = json.loads(message)
            # print(message)
            # print(message.keys())

            if 'params' in message:
                if 'channel' in message['params'].keys():
                    # Check RFQ Notification response.
                    if message['params']['channel'] == 'rfq':
                        # print('RFQ Notification response')
                        # print(message['params']['data'])
                        # print(message['params']['data'].keys())

                        # Add RFQ_Id to local list to manage active RFQs
                        if message['params']['data']['status'] == 'ACTIVE':
                            if message['params']['data']['rfq_id'] not in rfq_list:
                                rfq_list.append(message['params']['data']['rfq_id'])

                        # Remove RFQ_Id from local list used to manage RFQs
                        if message['params']['data']['status'] == 'CANCELED':
                            if message['params']['data']['rfq_id'] not in rfq_list:
                                rfq_list.remove(message['params']['data']['rfq_id'])

                    # Check Quote Notification response.
                    if message['params']['channel'] == 'quote':
                        # print('Quote Notification response')
                        # print(message['params']['data'])
                        # print(message['params']['data'].keys())

                        # Appends Quote information to local variable to manage active quotes
                        if message['params']['data']['status'] == 'ACTIVE':
                            # Note: Only single leg is available at the present moment (1/5/2021)
                            for leg in range(0, len(message['params']['data']['legs'])):
                                rfq_id = message['params']['data']['rfq_id']
                                quote_id = message['params']['data']['quote_id']

                                instrument = message['params']['data']['legs'][leg]['instrument']
                                bid_price = message['params']['data']['legs'][leg]['bid_price']
                                bid_quantity = message['params']['data']['legs'][leg]['bid_quantity']
                                offer_price = message['params']['data']['legs'][leg]['offer_price']
                                offer_quantity = message['params']['data']['legs'][leg]['offer_quantity']

                                quote_info_list = [instrument, bid_price, bid_quantity, offer_price, offer_quantity, quote_id, rfq_id]

                                quote_dict[quote_id] = quote_info_list

                        # Remove Quote information from local variable used to manage active quotes
                        if message['params']['data']['status'] == 'CANCELED':
                            if message['params']['data']['quote_id'] in quote_dict.keys():
                                quote_dict.pop(message['params']['data']['quote_id'], None)

                        # Logic to print active RFQs and their respective Quotes   
                        if message['params']['data']['status'] == 'ACTIVE':
                            quote_dict_df = pd.DataFrame.from_dict(data=quote_dict, orient='index',
                                                                   columns=['Instrument', 'Bid_Price', 'Bid_Quantity',
                                                                            'Offer_Price', 'Offer_Quantity', 'Quote_Id',
                                                                            'RFQ_Id'])
                            internal_df_1 = pd.DataFrame()
                            internal_df_2 = pd.DataFrame()
                            for rfq_id in rfq_list:
                                internal_df_3 = pd.DataFrame()
                                internal_df_3 = quote_dict_df.loc[quote_dict_df['RFQ_Id'] == rfq_id]
                                internal_df_3 = internal_df_3.drop(columns=['Offer_Price', 'Offer_Quantity'])
                                internal_df_3.index.rename('Quote_Id', inplace=True)

                                internal_df_4 = pd.DataFrame()
                                internal_df_4 = quote_dict_df.loc[quote_dict_df['RFQ_Id'] == rfq_id]
                                internal_df_4 = internal_df_4.drop(columns=['Bid_Price', 'Bid_Quantity'])
                                internal_df_4.index.rename('Quote_Id', inplace=True)

                                # To avoid creating empty Dataframes
                                if not internal_df_3.empty:
                                    internal_df_1 = pd.concat([internal_df_1, internal_df_3])

                                # To avoid creating empty Dataframes
                                if not internal_df_4.empty:
                                    internal_df_2 = pd.concat([internal_df_2, internal_df_4])

                            # Sort dataframes by price
                            if 'Bid_Price' in internal_df_1.columns:
                                internal_df_1 = internal_df_1.sort_values(by=['RFQ_Id', 'Bid_Price'], ascending=[True, True])
                            if 'Offer_Price' in internal_df_2.columns:
                                internal_df_2 = internal_df_2.sort_values(by=['RFQ_Id', 'Offer_Price'], ascending=[True, False])

                            # To avoid printing empty Dataframes
                            if not internal_df_1.empty and not internal_df_2.empty:
                                clear()
                                print(internal_df_1)
                                print(internal_df_2)
                            elif not internal_df_1.empty:
                                clear()
                                print(internal_df_1)
                            elif not internal_df_2.empty:
                                clear()
                                print(internal_df_2)

                    # Check Trade Notification response.
                    if message['params']['channel'] == 'trade':
                        print('Trade Notification response')
                        print(message['params']['data'])
                        # print(message['params']['data'].keys())

                        if message['params']['data']['quote_id'] in quote_dict.keys():
                            quote_dict.pop(message['params']['data']['quote_id'], None)

                    # Check Trade_Confirmation Notification response.
                    if message['params']['channel'] == 'trade_confirmation':
                        print('Trade_Confirmation Notification response')
                        print(message['params']['data'])
                        # print(message['params']['data'].keys())


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
    if len(sys.argv) == 2:
        paradigm_access_key = sys.argv[1]
    else:
        print('Please provide your Paradigm API Access Key as an argument.')
        paradigm_access_key = "stNlMtdDmil3KmWsG3FUaSYu"

    ws_url = "wss://ws.api.test.paradigm.co/"

    try:
        print('Paradigm Access Key: {}'.format(paradigm_access_key))
        print('WS URL: {}'.format(ws_url))

        # Start the client
        asyncio.get_event_loop().run_until_complete(main(api_key=paradigm_access_key,
                                                         ws_url=ws_url))

        asyncio.get_event_loop().run_forever()
    except Exception as e:
        print('Local Main Error')
        print(e)
        traceback.print_exc()

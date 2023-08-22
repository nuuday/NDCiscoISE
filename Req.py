# -*- coding: utf-8 -*-

# Developed by Rune Johannesen @ NetDesign A/S 2023

from aiohttp import ClientSession, BasicAuth, TCPConnector
from asyncio import gather, set_event_loop, set_event_loop_policy, sleep
from traceback import format_exc
from sys import version_info, platform
from json import dumps

class Req():
    def __init__(self, username: str, password: str, headers: dict = None, timeout: object = None, rate_limit: int = 30) -> None:
        """
        Username: string (Required)

        Password: string (Required)
    
        Headers: dictionary (Optional) Default is {'Content-Type': 'application/json', 'Accept': 'application/json', 'cache-control': 'no-cache'}
        
        Timeout: object (Optional) Default is 60 seconds (1 minute)
        
        rate_limit: interger (Optional) Default is 30 requests per second
        """
        if version_info[0] == 3 and version_info[1] >= 8 and platform.startswith('win'):
            from asyncio import ProactorEventLoop, WindowsSelectorEventLoopPolicy
            set_event_loop(ProactorEventLoop())
            set_event_loop_policy(WindowsSelectorEventLoopPolicy())
        self._usr: str = username
        self._psw: str = password
        self.headers: dict = headers if headers else {'Content-Type': 'application/json', 'Accept': 'application/json', 'cache-control': 'no-cache'}
        self.timeout: int = timeout if timeout else 60
        self.rate_limit: int = rate_limit
        self.HTTP_ERR_MAP: dict = {400: '(400) Bad Request',401: '(401) Unauthorized',403: '(403) Forbidden',404: '(404) Not Found',405: '(405) Method Not Allowed',406: '(406) Not Acceptable',409: '(409) Conflict',415: '(415) Unsupported Media Type',429: '(429) Too many requests',500: '(500) Internal Server Error',501: '(501) Not Implemented',503: '(503) Service Unavailable'}
    
    def returnPartionedList(self, inputlist: list) -> list:
        """Returns a list split into segments of rate_limit"""
        return([inputlist[i:i + self.rate_limit] for i in range(0, len(inputlist), self.rate_limit)])

    async def __req(self, url: str, session: ClientSession, method: str, payload: str, validate: bool = False) -> dict:
        """
        Custom request method. Will retry a request one time if the response is a server error.

        url: URL to request data from.

        session: Asynchronous aiohttp ClientSession class instance

        method: Supported request methods: get, post, put, delete and patch

        payload: Payload to send to the server in string format

        validate: Default False, this will retry the request if a server error occurs.
        """
        try:
            async with session.request(method=method, url=url, data=payload, timeout=self.timeout) as response:
                if response.status in range(200,299):
                    if response.status == 201:
                        return({"OK":"Created"})
                    elif response.status == 202:
                        bulkId: str = str(response.headers['location'].split("submit/",1)[1])
                        return(bulkId)
                    elif response.status == 204:
                        return({"OK":f"{method}"})
                    r: dict = await response.json()
                    return(r)
                else:
                    if response.status == 500:
                        if not validate:
                            await sleep(10) # Sleep for 10 seconds if response is a server error, then try again.
                            return(await self.__req(url, session, method, payload, True))
                        print(f"Server Error: {response.status} Operation: {method} -> {url}")
                        return({})
                    try:
                        r: str = await response.json()
                        messages: str = ""
                        # Example: { "ERSResponse": { "operation": "PUT-update by name-networkdevice", "messages": [{ "title": "Resource Initialization Failed: Invalid JSON: Can not deserialize instance of java.util.ArrayList out of START_OBJECT token\n", "type": "ERROR", "code": "Application resource validation exception"}], "link": { "rel": "related", "href": "https://x.x.x.x:9060/ers/config/networkdevice/name/TEST", "type": "application/xml" }}}
                        for message in r['ERSResponse']['messages']:
                            messages += f"{message['type']}: {message['title']} - {message['code']}"
                        print(f"Error: {self.HTTP_ERR_MAP[response.status]} -> Operation: {r['ERSResponse']['operation']} -> {messages}")
                    except:
                        r: str = await response.text()
                        if not r: r: str = "N/A"
                        api: str = url.split("/")[5]
                        print(f"Error: {self.HTTP_ERR_MAP[response.status]} -> Method: {method} -> API: {api} -> Message: {r}")
        except Exception:
            print(f"General Exception (Func: __req) for URL {url}: Traceback:\n{format_exc()}")
        return({})

    async def make_requests(self, req_list: list) -> list:
        """
        req_list: list (Required) List of data to be processed

            Structure: method (Required), url (Required), payload (Optional)

            Allowed methods: get, post, put, delete and patch

            Example:

            [
                ['GET', 'https://x.x.x.x:9060/ers/config/networkdevice'],
                ['POST', 'https://x.x.x.x:9060/ers/config/networkdevice', '{\"json\":\"payload\"}'],
                [...]
            ]
        """
        def check_payload(data: list) -> str:
            try: return(dumps(data[2]))
            except: return("")
        if not req_list:
            raise Exception("req_list cannot be empty, you must enter data to be processed.")
        if not req_list[0]:
            raise Exception("req_list cannot be empty, you must enter data to be processed.")
        resultsList: list = []
        DataPartitions: list = self.returnPartionedList(req_list)
        async with ClientSession(auth=BasicAuth(self._usr,self._psw), headers=self.headers, connector=TCPConnector(ssl=False)) as session:
            for partition in DataPartitions: # Process rate_limit amount of requests at the same time and sleep for 1.1 seconds
                results: list = await gather(*[self.__req(url=data[1], session=session, method=data[0], payload=check_payload(data)) for data in partition], return_exceptions=False)
                for result in results:
                    resultsList.append(result)
                await sleep(1.1)
        return(resultsList)

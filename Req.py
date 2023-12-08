# Developed by Rune Johannesen @2021-2023
from aiohttp import ClientSession, BasicAuth, TCPConnector
from asyncio import gather, sleep, create_task, Semaphore
from typing import Union
from json import dumps
from os.path import splitext, basename
from General_logger import setup_logger
from traceback import format_exc


class Req():
    def __init__(self, headers: dict = None, timeout: int = None, rate_limit: int = 2, use_ssl: bool = True, auth: str = "") -> None:
        """
        :headers: dict (Optional) Specify a custom header to use with your request. Default is {'Content-Type':'application/json','Accept':'application/json','cache-control':'no-cache'}
        :timeout: integer (Optional) Set a timeout for your request. Default is 60 seconds
        :rate_limit: integer (Optional) Change the rate limit to make the requests faster. Default is 2 requests per second
        :use_ssl: boolean (Optional) Set to False if server certificate is not verifiable
        :auth: string (Optional) If your request needs Basic Authentication, enter username and password with space comma space separator, example: auth=\"username , password\""""
        self.__HTTP_ERR_MAP: dict = {400:'(400) Bad Request',401:'(401) Unauthorized',403:'(403) Forbidden',404:'(404) Not Found',405:'(405) Method Not Allowed',406:'(406) Not Acceptable',409:'(409) Conflict',415:'(415) Unsupported Media Type',422:'(422) Unprocessable Entity',429:'(429) Too many requests',500:'(500) Internal Server Error',501:'(501) Not Implemented',503:'(503) Service Unavailable'}
        self.__HEADERS: dict = headers if headers else {'Content-Type': 'application/json', 'Accept': 'application/json', 'cache-control': 'no-cache'}
        self.__TIMEOUT: int = timeout if timeout else 60
        self.__RATE_LIMIT: int = rate_limit
        self.__USE_SSL: bool = TCPConnector(verify_ssl=True) if use_ssl else TCPConnector(verify_ssl=False)
        self.__AUTH: str = None
        self.__LOGGER = setup_logger(splitext(basename(__file__))[0])
        if auth:
            try:
                usernm,passwd = auth.split(" , ")
                self.__AUTH: str = BasicAuth(usernm,passwd)
            except: raise Exception("There was a problem with auth. You must separate the username and password with \" , \" (space comma space)")

    def returnPartionedList(self, inputlist: list) -> list:
        """Returns a list split into segments of self.RATE_LIMIT
        :inputlist: list (Required) List of lists containing data to split into segments. Example: [[data],[data],[data],etc...]"""
        return([inputlist[i:i + self.__RATE_LIMIT] for i in range(0, len(inputlist), self.__RATE_LIMIT)])

    async def __req(self, url: str, session: ClientSession, method: str, payload: str, semaphore: Semaphore, validate: bool = False) -> Union[dict,str]:
        """Private method\n
        Returns the request as either a dict or string. Dictionary will always be the preferred return type
        :url: string (Required) Url to request or post data to/from
        :method: string (Required) Supported request methods: get, post, put, delete and patch
        :payload: string (Required) Request payload. Leave blank ('') for no payload
        :validate: boolean (Optional) Method to retry a request that fails. Default is False\n
        If response status is (500) Internal Server Error, the request will be retried after 10 seconds"""
        try:
            async with semaphore:
                async with session.request(method=method, url=url, data=payload, timeout=self.__TIMEOUT) as response:
                    if response.status in range(200,299):
                        if response.status == 202:
                            try: return(str(response.headers['location'].split("submit/",1)[1]))
                            except: pass
                        try: r: dict = await response.json()
                        except: r: str = await response.text()
                        if not r: r: dict = {"OK":f"{method}","HEADERS":response.headers}
                        return(r)
                    elif response.status == 500:
                        if not validate:
                            await sleep(10)
                            return(await self.__req(url,session,method,payload,semaphore,validate=True))
                        if payload: self.__LOGGER.info(f"Server Error: {response.status} -> Operation: {method} -> URL: {url} -> Payload:\n{payload}")
                        else: self.__LOGGER.info(f"Server Error: {response.status} -> Operation: {method} -> URL: {url}")
                    else:
                        try: r: dict = await response.json()
                        except: r: str = await response.text()
                        if not r: r: str = "N/A"
                        if payload: self.__LOGGER.info(f"Client Error: {self.__HTTP_ERR_MAP[response.status]} -> Operation: {method} -> URL: {url}\nPayload:\n{payload}\nResponse:\n{r}\n")
                        else: self.__LOGGER.info(f"Client Error: {self.__HTTP_ERR_MAP[response.status]} -> Operation: {method} -> URL: {url}\nResponse:\n{r}\n")
        except Exception:
            if payload: self.__LOGGER.info(f"Exception Error -> Operation: {method} -> URL: {url}\nPayload:\n{payload}\n{format_exc()}")
            else: self.__LOGGER.info(f"Exception Error -> Operation: {method} -> URL: {url}\n{format_exc()}")
        return({})

    async def make_requests(self, req_list: list) -> list:
        """Returns the results from the requests in req_list in a list of lists format, example: [[response],[response],etc...]
        :req_list: list (Required) List of lists with requests to be processed
            Structure: [[method: str (Required), url: str (Required), payload: dict (Optional)],[...]]
            Allowed methods: get, post, put, delete and patch
            Payload must be a dictionary, it will be converted to a string
        req_list Examples:
            [
                ["GET","www.example.com"],\n
                ["POST","www.example.com",{"some":"payload"}],\n
                ["PUT","www.example.com",{"some":"payload"}]
            ]"""
        def check_payload(entry: list) -> Union[str,None]:
            try:
                if '<?xml version="1.0"' in entry[2]:
                    return(entry[2])
                else: return(dumps(entry[2]))
            except: return(None)
        if not req_list or not req_list[0]:
            raise Exception("req_list cannot be empty, you must provide requests to be processed.\n\nThe format is (list of lists):\n    [[method: str (Required), url: str (Required), payload: dict (Optional)],[...]]")
        resultsList: list = []
        partitions: list = self.returnPartionedList(req_list)
        semaphore: Semaphore = Semaphore(10)
        async with ClientSession(auth=self.__AUTH, headers=self.__HEADERS, connector=self.__USE_SSL, timeout=self.__TIMEOUT*2) as session:
            for partition in partitions:
                partitionTasks: list = []
                for entry in partition:
                    if "get" in entry[0].lower():
                        partitionTasks.append(create_task(self.__req(entry[1],session,entry[0],check_payload(entry),semaphore)))
                    else:
                        result: Union[str,dict] = await self.__req(entry[1],session,entry[0],check_payload(entry),semaphore)
                        resultsList.append(result)
                if partitionTasks:
                    results: list = await gather(*partitionTasks)
                    for result in results: resultsList.append(result)
                await sleep(1.1)
        return(resultsList)

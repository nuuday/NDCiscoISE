# Developed by Rune Johannesen @2023
# Developed using the official Cisco ISE API documentation:
# https://developer.cisco.com/docs/identity-services-engine/latest
from os.path import splitext, basename
from re import search
from General_logger import setup_logger
from typing import Union
from Req import Req


class NDCiscoISE():
    def __init__(self, username: str, password: str, ise_ip_address: str, headers: str = None, timeout: int = None, rate_limit: int = 30, use_ssl: bool = True) -> None:
        """Cisco ISE help module.

        :username: (Required) Username to use with Cisco ISE API requests
        :password: (Required) Password to use with Cisco ISE API requests
        :ise_ip_address: (Required) Cisco ISE IP address to run API requests against
        :headers: (Optional) Custom headers to use with Cisco ISE API requests
        :timeout: (Optional) Request timeout in seconds for each request. Default is 30 seconds.
        :rate_limit: (Optional) Requests per second as integer. Default is 30 requests per second as defined by the Cisco ISE official documentation. https://developer.cisco.com/docs/identity-services-engine/latest/#!rate-limits - Setting this value lower than 30 could help negate 500: Server Error on many requests."""
        self.__scriptname: str = splitext(basename(__file__))[0]
        self.__logger = setup_logger(self.__scriptname)
        self.__usr: str = username
        self.__psw: str = password
        self.__ip: str = ise_ip_address
        self.__headers: str = headers
        self.__timeout: int = timeout
        self.__rate_limit: int = rate_limit
        self.__use_ssl: bool = use_ssl
        for index, check in enumerate([self.__usr, self.__psw, self.__ip]):
            if not check:
                if index == 0: raise Exception("Username cannot be empty, you must enter a username.")
                if index == 1: raise Exception("Password cannot be empty, you must enter a password.")
                if index == 2: raise Exception("Cisco ISE IP address cannot be empty, you must enter an IP address.")
        self.__base_url: str = f"https://{self.__ip}:9060/ers/"
        self.__base_url_openapi: str = f"https://{self.__ip}"
        self.__maxresults: int = 100 # Maximum results to return per API call when using ISE_GET_api method.

    def __returnNearestHundreds(self, integer: int) -> int:
        """Returns an integer rounded up to the nearest hundreds

        Examples:
            99 -> 100
            101 -> 200"""
        return(int((-(-int(integer) // 100))*100))

    async def __execute(self, __job: list) -> list:
        """Private method that will execute requests."""
        __nd = Req(self.__headers, self.__timeout, self.__rate_limit, self.__use_ssl, f"{self.__usr} , {self.__psw}")
        __result: list = await __nd.make_requests(__job)
        return(__result)

    ################################################
    # Cisco ISE OpenAPI -> *                       #
    #                                              #
    # Specific API calls that uses OpenAPI.        #
    # There are a few selection of the ISE APIs    #
    # that uses OpenAPI.                           #
    ################################################

    async def ISE_OpenAPI(self, method: str, api: str, payloads: list=[]) -> list:
        """This function will help utilizing the OpenAPI on the Cisco ISE management nodes.

        :method: string (Required) -> The method to use on the OpenAPI, valid values are: GET, POST, PUT, DELETE
        :api: string (Required) -> The OpenAPI to access, example: /api/v1/policy/network-access/policy-set
        :payloads: list (Optional) -> The payloads to use with methods: POST & PUT. This is required with POST & PUT. Example: [{{\"object1\":\"payload\"}}, {{\"object2\":\"payload\"}}, etc.]
            More help: https://<your ISE IP address>/api/swagger-ui - You must login as Super Admin.
        NOTE: You can add filtering, sorting and/or paging for specific Open APIs like this:
            /api/v1/endpoint?page=1&size=100&sort=asc&filter=mac.CONTAINS.B8 (Maximum size is 100 on Cisco ISE)"""
        valid_update_methods: dict = {"POST","PUT"}
        page = None
        size = None
        if not method:
            raise Exception("ISE_OpenAPI: You must provide the method to use for OpenAPI, valid values are: GET, POST, PUT, DELETE")
        if method.upper() not in {"GET","POST","PUT","DELETE"}:
            raise Exception("ISE_OpenAPI: You must provide a valid method to use for OpenAPI, valid values are: GET, POST, PUT, DELETE")
        if not api:
            raise Exception("ISE_OpenAPI: You must provide the api to get data from, for instance: /api/v1/policy/network-access/policy-set")
        if method.upper() in valid_update_methods and not payloads:
            raise Exception(f"ISE_OpenAPI: You must provide the payload(s) when using the method {method.upper()} -> payloads example: [{{\"object1\":\"payload\"}}, {{\"object2\":\"payload\"}}, etc.]")
        if not api.startswith("/"): api: str = f"/{api}"
        if "page=" in api:
            page: int = int(search(r"page=(\d+)",api).group(1))
        if "size=" in api:
            size: int = int(search(r"size=(\d+)",api).group(1))
        returnResults: list = []
        url: str = f"{self.__base_url_openapi}{api}"
        if method.upper() in valid_update_methods and payloads:
            MultiTask: list = [[method, url, p] for p in payloads]
            results: list = await self.__execute(MultiTask)
        else:
            results: list = await self.__execute([[method, url]])
        if results and results[0]:
            if 'nextPage' in results[0]:
                for result in results[0]['response']:
                    returnResults.append(result)
                paged_results: list = await self.ISE_OpenAPI(method=method,api=results[0]['nextPage'].replace(self.__base_url_openapi,""),payloads=payloads)
                for result in paged_results:
                    returnResults.append(result)
            elif isinstance(results,list) and isinstance(results[0],list):
                for result in results[0]:
                    returnResults.append(result)
                if not page and not size:
                    page: int = 1
                    size: int = len(results[0])
                    api: str = f"{api}?page={page}&size={size}"
                if page and (len(results[0])==size or len(results[0])==20):
                    paged_results: list = await self.ISE_OpenAPI(method=method,api=api.replace(f"page={page}",f"page={page+1}"),payloads=payloads)
                    for result in paged_results:
                        returnResults.append(result)
                    page += 1
            else:
                if 'response' in results[0] and results[0]['response']:
                    for result in results[0]['response']:
                        returnResults.append(result)
        return(returnResults)

    ################################################
    # Configuration (Day 1) -> *                   #
    #                                              #
    # Specific API calls that needs their own      #
    # function to return the results correctly.    #
    ################################################

    async def ISE_GET_all_acibindings(self, filter: str = "") -> list:
        """This API allows clients to retrieve all the bindings that were sent to Cisco ISE by ACI or received on ACI from Cisco ISE. The binding information will be identical to the information on ACI bindings page in the Cisco ISE UI.

        :filter: (Optional) Filtering will be based on one attribute only, such as ip/sgt/vn/psn/learnedFrom/learnedBy with CONTAINS mode of search.
        :filter example: learnedFrom.CONTAINS.ISE"""
        returnResults: list = []
        url: str = f"{self.__base_url}config/acibindings/getall"
        if filter:
            if "contains" in filter.lower():
                if not filter.startswith("filter="):
                    filter: str = f"filter={filter}"
                url: str = f"{self.__base_url}config/acibindings/getall?{filter}"
            else: self.__logger.info(f"{self.__scriptname} <> ISE_GET_all_acibindings: Ignored filter. Acibindings only support the 'CONTAINS' filter mode.")
        results: list = await self.__execute([["GET", url]])
        if results and results[0]:
            for result in results[0]['ArrayList']:
                returnResults.append(result)
        return(returnResults)

    async def ISE_PUT_release_rejected_endpoints(self, ids: list) -> list:
        """This API allows the client to release a rejected endpoint.
        
        :ids: (Required) A list of endpoint ids to release.
        :ids example: [\"endpointId\", \"endpointId\", etc.]"""
        verification: bool = True
        url: str = f"{self.__base_url}config/endpoint/"
        MultiTask: list = [["PUT", url+i+"/releaserejectedendpoint"] for i in ids]
        results: list = await self.__execute(MultiTask)
        for result in results:
            if not result:
                verification: bool = False
                break
        return(verification) # Returns True if all requests were successful, otherwise False.

    async def ISE_PUT_deregister_endpoints(self, ids: list) -> list:
        """This API allows the client to de-register an endpoint.
        
        :ids: (Required) A list of endpoint ids to de-register.
        :ids example: [\"endpointId\", \"endpointId\", etc.]"""
        verification: bool = True
        url: str = f"{self.__base_url}config/endpoint/"
        MultiTask: list = [["PUT", url+i+"/deregister"] for i in ids]
        results: list = await self.__execute(MultiTask)
        for result in results:
            if not result:
                verification: bool = False
                break
        return(verification) # Returns True if all requests were successful, otherwise False.

    async def ISE_GET_rejected_endpoints(self) -> list:
        """This API allows the client to get the rejected endpoints."""
        returnResults: list = []
        url: str = f"{self.__base_url}config/endpoint/getrejectedendpoints"
        results: list = await self.__execute([["GET", url]])
        if results and results[0]:
            for result in results[0]['OperationResult']['resultValue']:
                returnResults.append(result)
        return(returnResults) # Example: [{'value': '2', 'name': 'Rejected EndPoint Count'}, {'value': '68:3B:78:D9:3C:00', 'name': 'EndPoint'}]

    async def ISE_PUT_register_endpoints(self, endpointpayloads: list) -> list:
        """This API allows the client to register an endpoint.
        
        :endpointpayloads: (Required) A list of endpoint payloads to register.
        :endpointpayloads example: [{\"endpoint1\": \"payload\"}, {\"endpoint2\": \"payload\"}, etc.]
        :NOTE: Full endpoint payload is required when registering. See more information here regarding payloads: https://developer.cisco.com/docs/identity-services-engine/latest/#!endpoint"""
        verification: bool = True
        url: str = f"{self.__base_url}config/endpoint/register"
        MultiTask: list = [["PUT", url, i] for i in endpointpayloads]
        results: list = await self.__execute(MultiTask)
        for result in results:
            if not result:
                verification: bool = False
                break
        return(verification) # Returns True if all requests were successful, otherwise False.

    ################################################
    # Configuration (Day 1) -> *                   #
    # Operation (Day 2) -> *                       #
    # Monitoring -> *                              #
    #                                              #
    # General API calls                            #
    #                                              #
    # This section contains API calls that are     #
    # repeated throughout the API tree, for        #
    # instance, versioninfo and bulk operations    #
    # exist in many API subtrees.                  #
    #                                              #
    # In order to use these calls you also need to #
    # provide the actual API as a string, example: #
    # networkdevice, endpoint, networkdevicegroup  #
    #                                              #
    # NOTE: You need to change or adapt payloads   #
    #       when using post, put and patch methods.#
    ################################################

    async def ISE_DELETE_api_names(self, api: str, names: list) -> list:
        """Deletes objects from the api subtree and object names in the names list provided.
        
        :names: (Required) List of object names to delete, example: [\"ISE_EST_Local_Host\", \"Device2\", etc.]
        :api: (Required) The API config/* subtree you want to delete data from.
        :api examples: networkdevice, endpoint, networkdevicegroup etc."""
        if not api:
            raise Exception("ISE_GET_api_names: You must provide the api/subtree to delete data from, example: networkdevice, endpoint, networkdevicegroup, etc.")
        if not names:
            raise Exception("ISE_GET_api_names: You must provide a list of object names to be deleted. Example: [\"ISE_EST_Local_Host\", \"Device2\", etc.]")
        if not isinstance(names, list):
            raise Exception("ISE_GET_api_names: Parameter names must be a list of object names in format: [\"ISE_EST_Local_Host\", \"Device2\", etc.]")
        if not len(names) > 0:
            raise Exception("ISE_GET_api_names: Parameter names cannot be empty, you must provide a list of object names to be deleted. Example: [\"ISE_EST_Local_Host\", \"Device2\", etc.]")
        returnResults: list = []
        url: str = f"{self.__base_url}config/{api}/name/"
        MultiTask: list = [["DELETE", url+i] for i in names]
        results: list = await self.__execute(MultiTask)
        if results:
            for result in results:
                returnResults.append(result)
        return(returnResults)

    async def ISE_GET_api_names(self, api: str, names: list) -> list:
        """Returns object details from the api subtree and object names in the names list provided.
        
        :names: (Required) List of object names to get details about, example: [\"ISE_EST_Local_Host\", \"Device2\", etc.]
        :api: (Required) The API config/* subtree you want to get data from.
        :api examples: networkdevice, endpoint, networkdevicegroup etc."""
        if not api:
            raise Exception("ISE_GET_api_names: You must provide the api/subtree to get data from, example: networkdevice, endpoint, networkdevicegroup, etc.")
        if not names:
            raise Exception("ISE_GET_api_names: You must provide a list of object names to be processed. Example: [\"ISE_EST_Local_Host\", \"Device2\", etc.]")
        if not isinstance(names, list):
            raise Exception("ISE_GET_api_names: Parameter names must be a list of object names in format: [\"ISE_EST_Local_Host\", \"Device2\", etc.]")
        if not len(names) > 0:
            raise Exception("ISE_GET_api_names: Parameter names cannot be empty, you must provide a list of object names to be processed. Example: [\"ISE_EST_Local_Host\", \"Device2\", etc.]")
        returnResults: list = []
        url: str = f"{self.__base_url}config/{api}/name/"
        MultiTask: list = [["GET", url+i] for i in names]
        results: list = await self.__execute(MultiTask)
        if results:
            for result in results:
                returnResults.append(result)
        return(returnResults)

    async def ISE_PATCH_api_names(self, api: str, namesandpayload: list) -> list:
        """Updates object details from the api subtree and object names in the names list provided.

        :namesandpayload: (Required) List of object names and payloads to update details on, example: [[\"ISE_EST_Local_Host\", {\"object\": \"payload\"}], [\"Device2\", {\"object\": \"payload\"}], etc.]
        :Payload example: {
            "NetworkDevice": {
                "any-resource-attribute": "some-updated-value",
                "another-resource-attribute": "some-updated-value"
            }
        }
        :api: (Required) The API config/* subtree you want to update data to.
        :api examples: networkdevice, endpoint, networkdevicegroup etc."""
        if not api:
            raise Exception("ISE_PATCH_api_names: You must provide the api/subtree to update data to, example: networkdevice, endpoint, networkdevicegroup, etc.")
        if not namesandpayload:
            raise Exception("ISE_PATCH_api_names: You must provide a list of object names and payloads to be updated. Example: [[\"ISE_EST_Local_Host\", {\"object\": \"payload\"}], [\"Device2\", {\"object\": \"payload\"}], etc.]")
        if not isinstance(namesandpayload, list):
            raise Exception("ISE_PATCH_api_names: Parameter names must be a list of object names and payloads in format: [[\"ISE_EST_Local_Host\", {\"object\": \"payload\"}], [\"Device2\", {\"object\": \"payload\"}], etc.]")
        if not len(namesandpayload) > 0:
            raise Exception("ISE_PATCH_api_names: Parameter names cannot be empty, you must provide a list of object names and payloads to be updated. Example: [[\"ISE_EST_Local_Host\", {\"object\": \"payload\"}], [\"Device2\", {\"object\": \"payload\"}], etc.]")
        returnResults: list = []
        url: str = f"{self.__base_url}config/{api}/name/"
        MultiTask: list = [["PATCH", url+i[0], i[1]] for i in namesandpayload]
        results: list = await self.__execute(MultiTask)
        if results:
            for result in results:
                returnResults.append(result)
        return(returnResults)

    async def ISE_PUT_api_names(self, api: str, namesandpayload: list) -> list:
        """Updates object details from the api subtree and object names in the names list provided.
        
        :namesandpayload: (Required) List of object names and payloads to update details on, example: [[\"ISE_EST_Local_Host\", {\"object\": \"payload\"}], [\"Device2\", {\"object\": \"payload\"}], etc.]
        :NOTE: Full payload is required to update (PUT) an object. Use patch to update parts of an object.
        :api: (Required) The API config/* subtree you want to update data to.
        :api examples: networkdevice, endpoint, networkdevicegroup etc."""
        if not api:
            raise Exception("ISE_PUT_api_names: You must provide the api/subtree to update data to, example: networkdevice, endpoint, networkdevicegroup, etc.")
        if not namesandpayload:
            raise Exception("ISE_PUT_api_names: You must provide a list of object names and payloads to be updated. Example: [[\"ISE_EST_Local_Host\", {\"object\": \"payload\"}], [\"Device2\", {\"object\": \"payload\"}], etc.]")
        if not isinstance(namesandpayload, list):
            raise Exception("ISE_PUT_api_names: Parameter names must be a list of object names and payloads in format: [[\"ISE_EST_Local_Host\", {\"object\": \"payload\"}], [\"Device2\", {\"object\": \"payload\"}], etc.]")
        if not len(namesandpayload) > 0:
            raise Exception("ISE_PUT_api_names: Parameter names cannot be empty, you must provide a list of object names and payloads to be updated. Example: [[\"ISE_EST_Local_Host\", {\"object\": \"payload\"}], [\"Device2\", {\"object\": \"payload\"}], etc.]")
        returnResults: list = []
        url: str = f"{self.__base_url}config/{api}/name/"
        MultiTask: list = [["PUT", url+i[0], i[1]] for i in namesandpayload]
        results: list = await self.__execute(MultiTask)
        if results:
            for result in results:
                returnResults.append(result)
        return(returnResults)

    async def ISE_DELETE_api_ids(self, api: str, ids: list) -> list:
        """Deletes objects from the api subtree and IDs provided in the ids list.

        :ids: list (Required) -> List of object ids to delete, example: [\"object id\", \"object id\", etc]
        :api: string (Required) -> The API config/* subtree you want to delete data from.
        :api examples: networkdevice, endpoint, networkdevicegroup etc."""
        if not api:
            raise Exception("ISE_DELETE_api_ids: You must provide the api/subtree to delete data from, example: networkdevice, endpoint, networkdevicegroup, etc.")
        if not ids:
            raise Exception("ISE_DELETE_api_ids: You must provide a list of object ids to be deleted. Example: [\"object id\", \"object id\", etc]")
        if not isinstance(ids, list):
            raise Exception("ISE_DELETE_api_ids: Parameter ids must be a list of object ids in format: [\"object id\", \"object id\", etc]")
        if not len(ids) > 0:
            raise Exception("ISE_DELETE_api_ids: Parameter ids cannot be empty, you must provide a list of object ids to be deleted. Example: [\"object id\", \"object id\", etc]")
        verification: bool = True
        url: str = f"{self.__base_url}config/{api}/"
        MultiTask: list = [["DELETE", url+i] for i in ids]
        results: list = await self.__execute(MultiTask)
        for result in results:
            if not result:
                verification: bool = False
                break
        return(verification)

    async def ISE_GET_api_ids(self, api: str, ids: list) -> list:
        """Returns object details from the api subtree and object ids provided in the ids list.

        :ids: list (Required) -> List of object ids to retrieve, example: [\"object id\", \"object id\", etc]
        :api: string (Required) -> The API config/* subtree you want to get data from.
        :api examples: networkdevice, endpoint, networkdevicegroup etc."""
        if not api:
            raise Exception("ISE_GET_api_ids: You must provide the api/subtree to get data from, example: networkdevice, endpoint, networkdevicegroup, etc.")
        if not ids:
            raise Exception("ISE_GET_api_ids: You must provide a list of object ids to be processed. Example: [\"object id\", \"object id\", etc]")
        if not isinstance(ids, list):
            raise Exception("ISE_GET_api_ids: Parameter ids must be a list of object ids in format: [\"object id\", \"object id\", etc]")
        if not len(ids) > 0:
            raise Exception("ISE_GET_api_ids: Parameter ids cannot be empty, you must provide a list of object ids to be processed. Example: [\"object id\", \"object id\", etc]")
        returnResults: list = []
        url: str = f"{self.__base_url}config/{api}/"
        MultiTask: list = [["GET", url+i] for i in ids]
        results: list = await self.__execute(MultiTask)
        if results:
            for result in results:
                returnResults.append(result)
        return(returnResults)

    async def ISE_PATCH_api_ids(self, api: str, idsandpayload: list) -> list:
        """Updates objects on an api subtree with the payloads provided for each object id.

        :idsandpayload: lists of list (Required) -> Must be a list of ids and payloads to be processed. Payload only needs to contain the values that are needed to be changed. Example: [[\"objectId\", {\"object1\":\"payload\"}], [\"objectId\", {\"object2\":\"payload\"}], etc.]
        :Payload example: {
                    "NetworkDevice": {
                        "any-resource-attribute": "some-updated-value",
                        "another-resource-attribute": "some-updated-value"
                    }}
        :api: string (Required) -> The API config/* subtree you want to update data to.
        :api examples: networkdevice, endpoint, networkdevicegroup etc."""
        if not api:
            raise Exception("ISE_PATCH_api_ids: You must provide the api/subtree to update data to, example: networkdevice, endpoint, networkdevicegroup, etc.")
        if not idsandpayload:
            raise Exception("ISE_PATCH_api_ids: You must provide a list of ids and payloads to be processed. Example: [[\"objectId\", {\"object1\":\"payload\"}], [\"objectId\", {\"object2\":\"payload\"}], etc.]")
        if not isinstance(idsandpayload, list):
            raise Exception("ISE_PATCH_api_ids: Parameter idsandpayload must be a list of ids and payloads. Example: [[\"objectId\", {\"object1\":\"payload\"}], [\"objectId\", {\"object2\":\"payload\"}], etc.]")
        if not len(idsandpayload) > 0:
            raise Exception("ISE_PATCH_api_ids: Parameter idsandpayload cannot be empty, you must provide a list of ids and payloads to be processed. Example: [[\"objectId\", {\"object1\":\"payload\"}], [\"objectId\", {\"object2\":\"payload\"}], etc.]")
        if not idsandpayload[0]:
            raise Exception("ISE_PATCH_api_ids: You must provide a list of lists with ids and payloads to be processed. Example: [[\"objectId\", {\"object1\":\"payload\"}], [\"objectId\", {\"object2\":\"payload\"}], etc.]")
        returnResults: list = []
        url: str = f"{self.__base_url}config/{api}/"
        MultiTask: list = [["PATCH", url+i[0], i[1]] for i in idsandpayload]
        results: list = await self.__execute(MultiTask)
        if results:
            for result in results:
                returnResults.append(result)
        return(returnResults)

    async def ISE_PUT_api_ids(self, api: str, idsandpayload: list) -> list:
        """Updates objects on an api subtree with the payloads provided for each object id.

        :idsandpayload: lists of list (Required) -> Must be a list of ids and full payload to be processed.
        :idsandpayload example: [[\"objectId\", {\"object1\":\"payload\"}], [\"objectId\", {\"object2\":\"payload\"}], etc.]
        :NOTE: Full payload is required to update (PUT) an object. Use patch to update parts of an object.
        :api: string (Required) -> The API config/* subtree you want to update data to.
        :api examples: networkdevice, endpoint, networkdevicegroup etc."""
        if not api:
            raise Exception("ISE_PUT_api_ids: You must provide the api/subtree to update data to, example: networkdevice, endpoint, networkdevicegroup, etc.")
        if not idsandpayload:
            raise Exception("ISE_PUT_api_ids: You must provide a list of ids and payloads to be processed. Example: [[\"objectId\", {\"object1\":\"payload\"}], [\"objectId\", {\"object2\":\"payload\"}], etc.]")
        if not isinstance(idsandpayload, list):
            raise Exception("ISE_PUT_api_ids: Parameter idsandpayload must be a list of ids and payloads. Example: [[\"objectId\", {\"object1\":\"payload\"}], [\"objectId\", {\"object2\":\"payload\"}], etc.]")
        if not len(idsandpayload) > 0:
            raise Exception("ISE_PUT_api_ids: Parameter idsandpayload cannot be empty, you must provide a list of ids and payloads to be processed. Example: [[\"objectId\", {\"object1\":\"payload\"}], [\"objectId\", {\"object2\":\"payload\"}], etc.]")
        if not idsandpayload[0]:
            raise Exception("ISE_PUT_api_ids: You must provide a list of lists with ids and payloads to be processed. Example: [[\"objectId\", {\"object1\":\"payload\"}], [\"objectId\", {\"object2\":\"payload\"}], etc.]")
        returnResults: list = []
        url: str = f"{self.__base_url}config/{api}/"
        MultiTask: list = [["PUT", url+i[0], i[1]] for i in idsandpayload]
        results: list = await self.__execute(MultiTask)
        if results:
            for result in results:
                returnResults.append(result)
        return(returnResults)

    async def ISE_GET_api(self, api: str, filter: str = "", sort: str = "") -> list:
        """Get all objects from the api subtree provided. This function will automatically check how many total objects are available and run through all pages to get all data

        :api: string (Required) -> The API config/* subtree you want to get data from
        :api values: networkdevice, endpoint, networkdevicegroup etc.
        :filter: string (Optional) -> You can add optional filters when retrieving data. See more information on Cisco ISE documentation: https://developer.cisco.com/docs/identity-services-engine/latest/#!read-a-resource/read-a-resource
        :filters: \"filter=name.CONTAINS.voice\" returns all objects containing voice in the name.
        :sort: string (Optional) -> Sorting options for your results. Check documentation on how to properly sort.
        :sorting: \"sortasc=name\" this will sort on name ascending, A, B, C etc."""
        if not api:
            raise Exception("ISE_GET_api: You must provide the api/subtree to get data from, example: networkdevice, endpoint, networkdevicegroup, etc.")
        returnResults: list = []
        page: int = 1
        url: str = f"{self.__base_url}config/{api}?size={self.__maxresults}&page={page}"
        if filter:
            if not filter.startswith("filter="):
                filter: str = f"filter={filter}"
            url: str = f"{self.__base_url}config/{api}?{filter}&size={self.__maxresults}&page={page}"
        if sort:
            url: str = f"{url}&{sort}"
        result: list = await self.__execute([["GET", url]])
        if result and result[0]:
            if "SearchResult" in result[0]:
                total_entries: int = result[0]['SearchResult']['total']
                for device in result[0]['SearchResult']['resources']:
                    returnResults.append(device)
                if total_entries > 100:
                    parts: int = int(self.__returnNearestHundreds(total_entries)/100)
                    MultiTask: list = []
                    for _ in range(page, parts):
                        page += 1
                        url: str = url.replace(f"page={page-1}", f"page={page}")
                        MultiTask.append(["GET", url])
                    results: list = await self.__execute(MultiTask)
                    if results and results[0]:
                        for entries in results:
                            for device in entries['SearchResult']['resources']:
                                returnResults.append(device)
            else:
                returnResults.append(result[0])
        return(returnResults)

    async def ISE_POST_api(self, api: str, objects: list) -> bool:
        """Will create the objects that are in the objects list on the api subtree provided.

        :objects: list with dicts (Required) -> A list of objects to create in json/dictionary payloads.
        :objects example: [{\"object1\":\"payload\"}, {\"object2\":\"payload\"}, etc.]
        :api: string (Required) -> The API config/* subtree you want to post data to.
        :api examples: networkdevice, endpoint, networkdevicegroup etc.
        :See more info: https://developer.cisco.com/docs/identity-services-engine/latest
        :NOTE: Check the API documentation to find the correct payloads to send in order to create an object."""
        if not api:
            raise Exception("ISE_POST_api: You must provide the api/subtree to post data to, example: networkdevice, endpoint, networkdevicegroup, etc.")
        if not objects:
            raise Exception("ISE_POST_api: You must provide a list of object payloads to be processed. Example: [{\"object1\":\"payload\"}, {\"object2\":\"payload\"}, etc.]")
        if not isinstance(objects, list):
            raise Exception("ISE_POST_api: Parameter objects must be a list of object payloads in json/dictionary format: [{\"object1\":\"payload\"}, {\"object2\":\"payload\"}, etc.]")
        if not len(objects) > 0:
            raise Exception("ISE_POST_api: Parameter objects cannot be empty, you must provide a list of object payloads to be processed. Example: [{\"object1\":\"payload\"}, {\"object2\":\"payload\"}, etc.]")
        verification: bool = True
        url: str = f"{self.__base_url}config/{api}"
        MultiTask: list = [["POST", url, o] for o in objects]
        results: list = await self.__execute(MultiTask)
        for result in results:
            if not result:
                verification: bool = False
                break
        return(verification) # Returns True if all requests were successful, otherwise False.

    async def ISE_GET_versioninfo(self, api: str) -> dict:
        """Returns current and supported API versions for the api subtree provided.

        :api: string (Required) -> The API config/* subtree you want to get versioninfo from.
        :Examples: networkdevice, endpoint, networkdevicegroup etc."""
        if not api:
            raise Exception("ISE_GET_versioninfo: You must provide the api/subtree to get versioninfo from, example: networkdevice, endpoint, networkdevicegroup, etc.")
        api: str = api.lower()
        url: str = f"{self.__base_url}config/{api}/versioninfo"
        result: list = await self.__execute([["GET", url]])
        return(result[0]["VersionInfo"]) # Example: {'currentServerVersion': '1.1', 'supportedVersions': '1.0,1.1', 'link': {'rel': 'self', 'href': 'https://172.18.66.41:9060/ers/config/networkdevice/versioninfo', 'type': 'application/json'}}

    async def ISE_PUT_bulk_submit(self, api: str, bulkpayload: str) -> str:
        """Submits a bulk request to the api subtree and bulkpayload provided.

        :bulkpayload: string (Required) -> XML/json payload to create/update up to 500 objects or 5000 single id requests, like deleting devices.
        :api: string (Required) -> The API config/* subtree you want to submit bulk requests to.
        :api examples: networkdevice, endpoint, etc. More info: https://developer.cisco.com/docs/identity-services-engine/latest/#!bulk-requests"""
        if not api:
            raise Exception("ISE_PUT_bulk_submit: You must provide the api/subtree to get versioninfo from, example: networkdevice, endpoint, networkdevicegroup, etc.")
        if not bulkpayload:
            raise Exception("ISE_PUT_bulk_submit: You must provide the bulkpayload to be processed.")
        api: str = api.lower()
        url: str = f"{self.__base_url}config/{api}/bulk/submit"
        result: list = await self.__execute([["PUT", url, bulkpayload]])
        return(result[0]) # Returns the bulkId after the request is submitted. Example: 1615791703003

    async def ISE_GET_bulk_bulkid(self, api: str, bulkId: str) -> Union[dict,str]:
        """Returns bulk status from the api subtree and bulkid provided.

        :bulkId: string (Required) -> The ID of the bulk request to check status on.
        :api: string (Required) -> The API config/* subtree you want to get bulk status from.
        :api examples: networkdevice, endpoint, etc. More info: https://developer.cisco.com/docs/identity-services-engine/latest/#!bulk-requests"""
        if not api:
            raise Exception("ISE_GET_bulk_bulkid: You must provide the api/subtree to get versioninfo from, example: networkdevice, endpoint, networkdevicegroup, etc.")
        if not bulkId:
            raise Exception("ISE_GET_bulk_bulkid: You must provide the bulkid in order to get bulk status.")
        api: str = api.lower()
        url: str = f"{self.__base_url}config/{api}/bulk/{bulkId}"
        result: list = await self.__execute([["GET", url]])
        return(result[0]["BulkStatus"]) # Example: {"bulkId": 1615791703003, "mediaType": "", "executionStatus": "COMPLETED", "operationType": "create", "startTime": "Mon Mar 15 07:01:43 UTC 2021", "resourcesCount": 1, "successCount": 1, "failCount": 0, "resourcesStatus": [{ "id": "1234454324", "name": "resource1", "description": "description...", "resourceExecutionStatus": "COMPLETED", "status": "COMPLETED"}]}

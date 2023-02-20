# -*- coding: utf-8 -*-

# Developed by Rune Johannesen @ NetDesign A/S 2023

# Developed using the official Cisco ISE API documentation:
# https://developer.cisco.com/docs/identity-services-engine/latest

from Req import Req

class NDCiscoISE():
    def __init__(self, username: str, password: str, ise_ip_address: str, headers: str = None, timeout: object = None, rate_limit: int = 30) -> None:
        """
        username: (Required) Username to use with Cisco ISE API requests

        password: (Required) Password to use with Cisco ISE API requests

        ise_ip_address: (Required) Cisco ISE IP address to run API requests against

        headers: (Optional) Custom headers to use with Cisco ISE API requests

        timeout: (Optional) Request timeout in seconds for each request. Default is 30 seconds.

        rate_limit: (Optional) Requests per second as integer. Default is 30 requests per second as defined by the Cisco ISE official documentation. https://developer.cisco.com/docs/identity-services-engine/latest/#!rate-limits
        Setting this value lower than 30 could help negate 500: Server Error on many requests.
        """
        self.__usr: str = username
        self.__psw: str = password
        self.__ip: str = ise_ip_address
        for index, check in enumerate([self.__usr, self.__psw, self.__ip]):
            if not check:
                if index == 0: raise Exception("Username cannot be empty, you must enter a username.")
                if index == 1: raise Exception("Password cannot be empty, you must enter a password.")
                if index == 2: raise Exception("Cisco ISE IP address cannot be empty, you must enter an IP address.")
        self.nd: Req = Req(self.__usr, self.__psw, headers, timeout, rate_limit)
        self.base_url: str = f"https://{self.__ip}:9060/ers/"
        self.maxresults: int = 100 # Maximum results to return per API call when using ISE_GET_api method.
    
    def returnNearestHundreds(self, integer: int) -> int:
        """Returns an integer rounded up to the nearest hundreds
        
        Examples:
            99 -> 100

            101 -> 200
        """
        return(int((-(-int(integer) // 100))*100))

    ################################################
    # Configuration (Day 1) -> *                   #
    #                                              #
    # Specific API calls that needs their own      #
    # function to return the results correctly.    #
    ################################################

    async def ISE_GET_all_acibindings(self, filter: str = "") -> list:
        """This API allows clients to retrieve all the bindings that were sent to Cisco ISE by ACI or received on ACI from Cisco ISE.
        The binding information will be identical to the information on ACI bindings page in the Cisco ISE UI.

        filter: (Optional) Filtering will be based on one attribute only, such as ip/sgt/vn/psn/learnedFrom/learnedBy with CONTAINS mode of search.

        filter example: learnedFrom.CONTAINS.ISE
        """
        returnResults: list = []
        url: str = f"{self.base_url}config/acibindings/getall"
        if filter:
            if "contains" in filter.lower():
                if not filter.startswith("filter="):
                    filter: str = f"filter={filter}"
                url: str = f"{self.base_url}config/acibindings/getall?{filter}"
            else: print("ISE_GET_all_acibindings: Ignored filter. Acibindings only support the 'CONTAINS' filter mode.")
        results: list = await self.nd.make_requests([["GET", url, ""]])
        if results:
            for result in results[0]['ArrayList']:
                returnResults.append(result)
        return(returnResults)

    async def ISE_PUT_release_rejected_endpoints(self, ids: list) -> list:
        """This API allows the client to release a rejected endpoint.
        
        ids: (Required) A list of endpoint ids to release.

        ids example: [\"endpointId\", \"endpointId\", etc.]
        """
        verification: bool = True
        url: str = f"{self.base_url}config/endpoint/"
        MultiTask: list = [["PUT", url+i+"/releaserejectedendpoint", ""] for i in ids]
        results: list = await self.nd.make_requests(MultiTask)
        for result in results:
            if not result:
                verification: bool = False
                break
        return(verification) # Returns True if all requests were successful, otherwise False.

    async def ISE_PUT_deregister_endpoints(self, ids: list) -> list:
        """This API allows the client to de-register an endpoint.
        
        ids: (Required) A list of endpoint ids to de-register.

        ids example: [\"endpointId\", \"endpointId\", etc.]
        """
        verification: bool = True
        url: str = f"{self.base_url}config/endpoint/"
        MultiTask: list = [["PUT", url+i+"/deregister", ""] for i in ids]
        results: list = await self.nd.make_requests(MultiTask)
        for result in results:
            if not result:
                verification: bool = False
                break
        return(verification) # Returns True if all requests were successful, otherwise False.

    async def ISE_GET_rejected_endpoints(self) -> list:
        """This API allows the client to get the rejected endpoints."""
        returnResults: list = []
        url: str = f"{self.base_url}config/endpoint/getrejectedendpoints"
        results: list = await self.nd.make_requests([["GET", url, ""]])
        if results:
            for result in results[0]['OperationResult']['resultValue']:
                returnResults.append(result)
        return(returnResults) # Example: [{'value': '2', 'name': 'Rejected EndPoint Count'}, {'value': '68:3B:78:D9:3C:00', 'name': 'EndPoint'}]

    async def ISE_PUT_register_endpoints(self, endpointpayloads: list) -> list:
        """This API allows the client to register an endpoint.
        
        endpointpayloads: (Required) A list of endpoint payloads to register.

        ids example: [{\"endpoint1\": \"payload\"}, {\"endpoint2\": \"payload\"}, etc.]

        NOTE: Full endpoint payload is required when registering.

        See more information here regarding payloads: https://developer.cisco.com/docs/identity-services-engine/latest/#!endpoint
        """
        verification: bool = True
        url: str = f"{self.base_url}config/endpoint/register"
        MultiTask: list = [["PUT", url, i] for i in endpointpayloads]
        results: list = await self.nd.make_requests(MultiTask)
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
        
        names: (Required) List of object names to delete, example: [\"ISE_EST_Local_Host\", \"Device2\", etc.]

        api: (Required) The API config/* subtree you want to delete data from.

        api examples: networkdevice, endpoint, networkdevicegroup etc.
        """
        if not api:
            raise Exception("ISE_GET_api_names: You must provide the api/subtree to delete data from, example: networkdevice, endpoint, networkdevicegroup, etc.")
        if not names:
            raise Exception("ISE_GET_api_names: You must provide a list of object names to be deleted. Example: [\"ISE_EST_Local_Host\", \"Device2\", etc.]")
        if not isinstance(names, list):
            raise Exception("ISE_GET_api_names: Parameter names must be a list of object names in format: [\"ISE_EST_Local_Host\", \"Device2\", etc.]")
        if not len(names) > 0:
            raise Exception("ISE_GET_api_names: Parameter names cannot be empty, you must provide a list of object names to be deleted. Example: [\"ISE_EST_Local_Host\", \"Device2\", etc.]")
        returnResults: list = []
        url: str = f"{self.base_url}config/{api}/name/"
        MultiTask: list = [["DELETE", url+i, ""] for i in names]
        results: list = await self.nd.make_requests(MultiTask)
        if results:
            for result in results:
                returnResults.append(result)
        return(returnResults)

    async def ISE_GET_api_names(self, api: str, names: list) -> list:
        """Returns object details from the api subtree and object names in the names list provided.
        
        names: (Required) List of object names to get details about, example: [\"ISE_EST_Local_Host\", \"Device2\", etc.]

        api: (Required) The API config/* subtree you want to get data from.

        api examples: networkdevice, endpoint, networkdevicegroup etc.
        """
        if not api:
            raise Exception("ISE_GET_api_names: You must provide the api/subtree to get data from, example: networkdevice, endpoint, networkdevicegroup, etc.")
        if not names:
            raise Exception("ISE_GET_api_names: You must provide a list of object names to be processed. Example: [\"ISE_EST_Local_Host\", \"Device2\", etc.]")
        if not isinstance(names, list):
            raise Exception("ISE_GET_api_names: Parameter names must be a list of object names in format: [\"ISE_EST_Local_Host\", \"Device2\", etc.]")
        if not len(names) > 0:
            raise Exception("ISE_GET_api_names: Parameter names cannot be empty, you must provide a list of object names to be processed. Example: [\"ISE_EST_Local_Host\", \"Device2\", etc.]")
        returnResults: list = []
        url: str = f"{self.base_url}config/{api}/name/"
        MultiTask: list = [["GET", url+i, ""] for i in names]
        results: list = await self.nd.make_requests(MultiTask)
        if results:
            for result in results:
                returnResults.append(result)
        return(returnResults)

    async def ISE_PATCH_api_names(self, api: str, namesandpayload: list) -> list:
        """Updates object details from the api subtree and object names in the names list provided.
        
        namesandpayload: (Required) List of object names and payloads to update details on, example: [[\"ISE_EST_Local_Host\", {\"object\": \"payload\"}], [\"Device2\", {\"object\": \"payload\"}], etc.]

        Payload example:

        {
            "NetworkDevice": {
                "any-resource-attribute": "some-updated-value",
                "another-resource-attribute": "some-updated-value"
            }
        }

        api: (Required) The API config/* subtree you want to update data to.

        api examples: networkdevice, endpoint, networkdevicegroup etc.
        """
        if not api:
            raise Exception("ISE_PATCH_api_names: You must provide the api/subtree to update data to, example: networkdevice, endpoint, networkdevicegroup, etc.")
        if not namesandpayload:
            raise Exception("ISE_PATCH_api_names: You must provide a list of object names and payloads to be updated. Example: [[\"ISE_EST_Local_Host\", {\"object\": \"payload\"}], [\"Device2\", {\"object\": \"payload\"}], etc.]")
        if not isinstance(namesandpayload, list):
            raise Exception("ISE_PATCH_api_names: Parameter names must be a list of object names and payloads in format: [[\"ISE_EST_Local_Host\", {\"object\": \"payload\"}], [\"Device2\", {\"object\": \"payload\"}], etc.]")
        if not len(namesandpayload) > 0:
            raise Exception("ISE_PATCH_api_names: Parameter names cannot be empty, you must provide a list of object names and payloads to be updated. Example: [[\"ISE_EST_Local_Host\", {\"object\": \"payload\"}], [\"Device2\", {\"object\": \"payload\"}], etc.]")
        returnResults: list = []
        url: str = f"{self.base_url}config/{api}/name/"
        MultiTask: list = [["PATCH", url+i[0], i[1]] for i in namesandpayload]
        results: list = await self.nd.make_requests(MultiTask)
        if results:
            for result in results:
                returnResults.append(result)
        return(returnResults)

    async def ISE_PUT_api_names(self, api: str, namesandpayload: list) -> list:
        """Updates object details from the api subtree and object names in the names list provided.
        
        namesandpayload: (Required) List of object names and payloads to update details on, example: [[\"ISE_EST_Local_Host\", {\"object\": \"payload\"}], [\"Device2\", {\"object\": \"payload\"}], etc.]

        NOTE: Full payload is required to update (PUT) an object. Use patch to update parts of an object.

        api: (Required) The API config/* subtree you want to update data to.

        api examples: networkdevice, endpoint, networkdevicegroup etc.
        """
        if not api:
            raise Exception("ISE_PUT_api_names: You must provide the api/subtree to update data to, example: networkdevice, endpoint, networkdevicegroup, etc.")
        if not namesandpayload:
            raise Exception("ISE_PUT_api_names: You must provide a list of object names and payloads to be updated. Example: [[\"ISE_EST_Local_Host\", {\"object\": \"payload\"}], [\"Device2\", {\"object\": \"payload\"}], etc.]")
        if not isinstance(namesandpayload, list):
            raise Exception("ISE_PUT_api_names: Parameter names must be a list of object names and payloads in format: [[\"ISE_EST_Local_Host\", {\"object\": \"payload\"}], [\"Device2\", {\"object\": \"payload\"}], etc.]")
        if not len(namesandpayload) > 0:
            raise Exception("ISE_PUT_api_names: Parameter names cannot be empty, you must provide a list of object names and payloads to be updated. Example: [[\"ISE_EST_Local_Host\", {\"object\": \"payload\"}], [\"Device2\", {\"object\": \"payload\"}], etc.]")
        returnResults: list = []
        url: str = f"{self.base_url}config/{api}/name/"
        MultiTask: list = [["PUT", url+i[0], i[1]] for i in namesandpayload]
        results: list = await self.nd.make_requests(MultiTask)
        if results:
            for result in results:
                returnResults.append(result)
        return(returnResults)

    async def ISE_DELETE_api_ids(self, api: str, ids: list) -> list:
        """Deletes objects from the api subtree and IDs provided in the ids list.
        
        ids: (Required) List of object ids to delete, example: [\"object id\", \"object id\", etc]

        api: (Required) The API config/* subtree you want to delete data from.

        api examples: networkdevice, endpoint, networkdevicegroup etc.
        """
        if not api:
            raise Exception("ISE_DELETE_api_ids: You must provide the api/subtree to delete data from, example: networkdevice, endpoint, networkdevicegroup, etc.")
        if not ids:
            raise Exception("ISE_DELETE_api_ids: You must provide a list of object ids to be deleted. Example: [\"object id\", \"object id\", etc]")
        if not isinstance(ids, list):
            raise Exception("ISE_DELETE_api_ids: Parameter ids must be a list of object ids in format: [\"object id\", \"object id\", etc]")
        if not len(ids) > 0:
            raise Exception("ISE_DELETE_api_ids: Parameter ids cannot be empty, you must provide a list of object ids to be deleted. Example: [\"object id\", \"object id\", etc]")
        verification: bool = True
        url: str = f"{self.base_url}config/{api}/"
        MultiTask: list = [["DELETE", url+i, ""] for i in ids]
        results: list = await self.nd.make_requests(MultiTask)
        for result in results:
            if not result:
                verification: bool = False
                break
        return(verification)

    async def ISE_GET_api_ids(self, api: str, ids: list) -> list:
        """Returns object details from the api subtree and object ids provided in the ids list.
        
        ids: (Required) List of object ids to retrieve, example: [\"object id\", \"object id\", etc]

        api: (Required) The API config/* subtree you want to get data from.

        api examples: networkdevice, endpoint, networkdevicegroup etc.
        """
        if not api:
            raise Exception("ISE_GET_api_ids: You must provide the api/subtree to get data from, example: networkdevice, endpoint, networkdevicegroup, etc.")
        if not ids:
            raise Exception("ISE_GET_api_ids: You must provide a list of object ids to be processed. Example: [\"object id\", \"object id\", etc]")
        if not isinstance(ids, list):
            raise Exception("ISE_GET_api_ids: Parameter ids must be a list of object ids in format: [\"object id\", \"object id\", etc]")
        if not len(ids) > 0:
            raise Exception("ISE_GET_api_ids: Parameter ids cannot be empty, you must provide a list of object ids to be processed. Example: [\"object id\", \"object id\", etc]")
        returnResults: list = []
        url: str = f"{self.base_url}config/{api}/"
        MultiTask: list = [["GET", url+i, ""] for i in ids]
        results: list = await self.nd.make_requests(MultiTask)
        if results:
            for result in results:
                returnResults.append(result)
        return(returnResults)

    async def ISE_PATCH_api_ids(self, api: str, idsandpayload: list) -> list:
        """Updates objects on an api subtree with the payloads provided for each object id.
        
        idsandpayload: (Required) Must be a list of ids and payloads to be processed. Payload only needs to contain the values that are needed to be changed.

        Payload example:

        {
            "NetworkDevice": {
                "any-resource-attribute": "some-updated-value",
                "another-resource-attribute": "some-updated-value"
            }
        }

        idsandpayload must be a list of lists with the above payload: [[\"objectId\", {\"object1\":\"payload\"}], [\"objectId\", {\"object2\":\"payload\"}], etc.]

        api: (Required) The API config/* subtree you want to update data to.

        api examples: networkdevice, endpoint, networkdevicegroup etc.
        """
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
        url: str = f"{self.base_url}config/{api}/"
        MultiTask: list = [["PATCH", url+i[0], i[1]] for i in idsandpayload]
        results: list = await self.nd.make_requests(MultiTask)
        if results:
            for result in results:
                returnResults.append(result)
        return(returnResults)

    async def ISE_PUT_api_ids(self, api: str, idsandpayload: list) -> list:
        """Updates objects on an api subtree with the payloads provided for each object id.
        
        idsandpayload: (Required) Must be a list of ids and full payload to be processed.

        idsandpayload example: [[\"objectId\", {\"object1\":\"payload\"}], [\"objectId\", {\"object2\":\"payload\"}], etc.]

        NOTE: Full payload is required to update (PUT) an object. Use patch to update parts of an object.

        api: (Required) The API config/* subtree you want to update data to.

        api examples: networkdevice, endpoint, networkdevicegroup etc.
        """
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
        url: str = f"{self.base_url}config/{api}/"
        MultiTask: list = [["PUT", url+i[0], i[1]] for i in idsandpayload]
        results: list = await self.nd.make_requests(MultiTask)
        if results:
            for result in results:
                returnResults.append(result)
        return(returnResults)

    async def ISE_GET_api(self, api: str, filter: str = "") -> list:
        """Get all objects from the api subtree provided. This function will automatically check how many total objects are available and run through all pages to get all data.
        
        filter: (Optional) You can add optional filters when retrieving data. See more information on Cisco ISE documentation: https://developer.cisco.com/docs/identity-services-engine/latest/#!read-a-resource/read-a-resource

        filter example: \"filter=name.CONTAINS.voice\" returns all objects containing voice in the name.

        api: (Required) The API config/* subtree you want to get data from.

        api examples: networkdevice, endpoint, networkdevicegroup etc.

        See more info: https://developer.cisco.com/docs/identity-services-engine/latest
        """
        if not api:
            raise Exception("ISE_GET_api: You must provide the api/subtree to get data from, example: networkdevice, endpoint, networkdevicegroup, etc.")
        returnResults: list = []
        page: int = 1
        url: str = f"{self.base_url}config/{api}?size={self.maxresults}&page={page}"
        if filter:
            if not filter.startswith("filter="):
                filter: str = f"filter={filter}"
            url: str = f"{self.base_url}config/{api}?{filter}&size={self.maxresults}&page={page}"
        result: list = await self.nd.make_requests([["GET", url, ""]])
        if result:
            if "SearchResult" in result[0]:
                total_devices: int = result[0]['SearchResult']['total']
                for device in result[0]['SearchResult']['resources']:
                    returnResults.append(device)
                if total_devices > 100:
                    parts: int = int(self.returnNearestHundreds(total_devices)/100)
                    MultiTask: list = []
                    for _ in range(page, parts):
                        page += 1
                        url: str = url.replace(f"page={page-1}", f"page={page}")
                        MultiTask.append(["GET", url, ""])
                    results: list = await self.nd.make_requests(MultiTask)
                    for devices in results:
                        for device in devices['SearchResult']['resources']:
                            returnResults.append(device)
            else:
                returnResults.append(result[0])
        return(returnResults)

    async def ISE_POST_api(self, api: str, objects: list) -> bool:
        """Will create the objects that are in the objects list on the api subtree provided.
        
        objects: (Required) A list of objects to create in json/dictionary payloads.

        objects example: [{\"object1\":\"payload\"}, {\"object2\":\"payload\"}, etc.]

        api: (Required) The API config/* subtree you want to post data to.

        api examples: networkdevice, endpoint, networkdevicegroup etc.

        See more info: https://developer.cisco.com/docs/identity-services-engine/latest

        NOTE: Check the API documentation to find the correct payloads to send in order to create an object.
        """
        if not api:
            raise Exception("ISE_POST_api: You must provide the api/subtree to post data to, example: networkdevice, endpoint, networkdevicegroup, etc.")
        if not objects:
            raise Exception("ISE_POST_api: You must provide a list of object payloads to be processed. Example: [{\"object1\":\"payload\"}, {\"object2\":\"payload\"}, etc.]")
        if not isinstance(objects, list):
            raise Exception("ISE_POST_api: Parameter objects must be a list of object payloads in json/dictionary format: [{\"object1\":\"payload\"}, {\"object2\":\"payload\"}, etc.]")
        if not len(objects) > 0:
            raise Exception("ISE_POST_api: Parameter objects cannot be empty, you must provide a list of object payloads to be processed. Example: [{\"object1\":\"payload\"}, {\"object2\":\"payload\"}, etc.]")
        verification: bool = True
        url: str = f"{self.base_url}config/{api}"
        MultiTask: list = [["POST", url, o] for o in objects]
        results: list = await self.nd.make_requests(MultiTask)
        for result in results:
            if not result:
                verification: bool = False
                break
        return(verification) # Returns True if all requests were successful, otherwise False.

    async def ISE_GET_versioninfo(self, api: str) -> dict:
        """Returns current and supported API versions for the api subtree provided. 
        
        api: (Required) The API config/* subtree you want to get versioninfo from.

        Examples: networkdevice, endpoint, networkdevicegroup etc.
        """
        if not api:
            raise Exception("ISE_GET_versioninfo: You must provide the api/subtree to get versioninfo from, example: networkdevice, endpoint, networkdevicegroup, etc.")
        api: str = api.lower()
        url: str = f"{self.base_url}config/{api}/versioninfo"
        result: list = await self.nd.make_requests([["GET", url, ""]])
        return(result[0]["VersionInfo"]) # Example: {'currentServerVersion': '1.1', 'supportedVersions': '1.0,1.1', 'link': {'rel': 'self', 'href': 'https://172.18.66.41:9060/ers/config/networkdevice/versioninfo', 'type': 'application/json'}}

    async def ISE_PUT_bulk_submit(self, api: str, bulkpayload: str) -> str:
        """Submits a bulk request to the api subtree and bulkpayload provided.
        
        bulkpayload: (Required) XML/json payload to create/update up to 500 objects or 5000 single id requests, like deleting devices.
        api: (Required) The API config/* subtree you want to submit bulk requests to.

        api examples: networkdevice, endpoint, networkdevicegroup etc.

        More info: https://developer.cisco.com/docs/identity-services-engine/latest/#!bulk-requests
        """
        if not api:
            raise Exception("ISE_PUT_bulk_submit: You must provide the api/subtree to get versioninfo from, example: networkdevice, endpoint, networkdevicegroup, etc.")
        if not bulkpayload:
            raise Exception("ISE_PUT_bulk_submit: You must provide the bulkpayload to be processed.")
        api: str = api.lower()
        url: str = f"{self.base_url}config/{api}/bulk/submit"
        result: list = await self.nd.make_requests([["PUT", url, bulkpayload]])
        return(result[0]) # Returns the bulkId after the request is submitted. Example: 1615791703003

    async def ISE_GET_bulk_bulkid(self, api: str, bulkId: str) -> dict:
        """Returns bulk status from the api subtree and bulkid provided.
        
        bulkId: (Required) The ID of the bulk request to check status on.
        api: (Required) The API config/* subtree you want to get bulk status from.

        api examples: networkdevice, endpoint, networkdevicegroup etc.

        More info: https://developer.cisco.com/docs/identity-services-engine/latest/#!bulk-requests
        """
        if not api:
            raise Exception("ISE_GET_bulk_bulkid: You must provide the api/subtree to get versioninfo from, example: networkdevice, endpoint, networkdevicegroup, etc.")
        if not bulkId:
            raise Exception("ISE_GET_bulk_bulkid: You must provide the bulkid in order to get bulk status.")
        api: str = api.lower()
        url: str = f"{self.base_url}config/{api}/bulk/{bulkId}"
        result: list = await self.nd.make_requests([["GET", url, ""]])
        return(result[0]["BulkStatus"]) # Example: {"bulkId": 1615791703003, "mediaType": "", "executionStatus": "COMPLETED", "operationType": "create", "startTime": "Mon Mar 15 07:01:43 UTC 2021", "resourcesCount": 1, "successCount": 1, "failCount": 0, "resourcesStatus": [{ "id": "1234454324", "name": "resource1", "description": "description...", "resourceExecutionStatus": "COMPLETED", "status": "COMPLETED"}]}
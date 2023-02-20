# NetDesign Cisco ISE

This program is meant to help users easily utilize the Cisco ISE API. It's written to run most requests asynchronous and get, update, or delete data with up to 30 concurrent sessions to the API while respecting the rate limit of 30 connections per second. You can also easily change the rate limit together with multiple other options to make it more versatile.

Normally when you get information from the Cisco ISE API you need to use pagination to make sure all data is returned. This program automatically checks if pagination is needed and uses it to collect a complete set of data and returns it to the user.

You can still use filters if you want to get specific data from the API. It’s also possible to specify which API category you want to get, update, or delete data from. This is done so that most of the API can be used by a few functions in stead of writing a function for each API category and endpoint.

There are some specific API requests, that will require its own function to get, update, or delete those data, but not all is included in the first version.

* Technology stack: This code is meant to be imported and used to help get, update, or delete data on the Cisco ISE API. It’s intended as a module you can use to import in your production, and it’s written entirely in Python and only tested using Python 3.11.2
* Status: This is the first version released.

## Installation

In order to install the module, follow the instructions below. The only dependency is: **aiohttp**

**Instructions:**

Clone the repo
```bash
git clone https://github.com/nuuday/NDCiscoISE.git
```
Go to your project folder
```bash
cd NDCiscoISE
```

Set up a Python venv
First make sure that you have Python 3 installed on your machine. We will then be using venv to create an isolated environment with only the necessary packages.

Install virtualenv via pip
```bash
pip install virtualenv
```

Create the venv
```bash
python3 -m venv venv
```

Activate your venv
```bash
source venv/bin/activate
```

Install dependencies
```bash
pip install -r requirements.txt
```

## Usage

In order to use this program, you must start it with *asyncio*.

**Example:**
```
from asyncio import run
from NDCiscoISE import NDCiscoISE

async def main():
    ISE = NDCiscoISE("username", "password", "ise_ip_address")
    NetworkDevices = await ISE.ISE_GET_api("networkdevice", filter="filter=name.CONTAINS.voice")
    print(NetworkDevices)

if __name__ == "__main__":
    run(main())
```

This would print the network devices on your Cisco ISE installation that contains the device name *voice*. Filter is optional and if it's not provided, all network devices are returned. The program will automatically check if there are more than 100 objects to return. If that is the case it will create a list of the remaining urls and simultaneously get all data and return it.

**More examples:**

```
from asyncio import run
from NDCiscoISE import NDCiscoISE

async def main():
    ISE = NDCiscoISE("username", "password", "ise_ip_address")
    NetworkDevices = await ISE.ISE_GET_api_ids("networkdevice", ["123456781-7c87-11ed-8b63-e25bd9a098d0", "123456782-7c87-11ed-8b63-e25bd9a098d0", "123456783-7c87-11ed-8b63-e25bd9a098d0", "123456784-7c87-11ed-8b63-e25bd9a098d0", "123456785-7c87-11ed-8b63-e25bd9a098d0"])
    print(NetworkDevices)

if __name__ == "__main__":
    run(main())
```

This will get the specific network device ids specified in the list simultaneously and return all data.

```
from asyncio import run
from NDCiscoISE import NDCiscoISE

async def main():
    ISE = NDCiscoISE("username", "password", "ise_ip_address")
    NetworkGroups = await ISE.ISE_POST_api("networkdevicegroup", [{"NetworkDeviceGroup": {"name": "Device Type#All Device Types#CISCO_ROUTER", "description": "ONLY USE FOR VIRTUAL FIREWALL VALIDATION", "othername": "Device Type"}}, {"NetworkDeviceGroup": {"name": "Device Type#All Device Types#CISCO_SWITCH", "description": "ONLY USE FOR VIRTUAL FIREWALL VALIDATION", "othername": "Device Type"}}, {"NetworkDeviceGroup": {"name": "Device Type#All Device Types#CISCO_WIRELESS", "description": "ONLY USE FOR VIRTUAL FIREWALL VALIDATION", "othername": "Device Type"}}])
    print(NetworkGroups) # Will print True if successful.

if __name__ == "__main__":
    run(main())
```

This will create 3 device groups simultaneously under All Device Types on your Cisco ISE installation:

![Output of above code](https://mooo.dk/ghub1.png)

If you want to create more, you can keep adding to the list. Depending on the API subtree the payloads need to be changed accordingly. See the API documentation for more information: https://developer.cisco.com/docs/identity-services-engine/latest

```
from asyncio import run
from NDCiscoISE import NDCiscoISE

async def main():
    ISE = NDCiscoISE("username", "password", "ise_ip_address")
    EditNetworkGroup = await ISE.ISE_PUT_api_ids("networkdevicegroup", [["4d2943f0-add6-11ed-bb08-ee2842faf84b", {"NetworkDeviceGroup": {"name": "Device Type#All Device Types#TEST_GROUP_EDITED", "description": "Edited Test Group", "othername": "Device Type"}}]])
    print(EditNetworkGroup)

if __name__ == "__main__":
    run(main())
```

Before PUT (edit):

![Output of above code](https://mooo.dk/ghub2.png)

After PUT (edit) as above:

![Output of above code](https://mooo.dk/ghub3.png)

Output of print will be (compressed, one line - I unpacked the JSON to make it easier to read):

```
[
    {'UpdatedFieldsList': {
        'updatedField': [
            {
                'field': 'name',
                'oldValue': 'Device Type#All Device Types#TEST_GROUP_EDITED',
                'newValue': 'Device Type#All Device Types#TEST_GROUP_EDITED'
            },
            {
                'field': 'description',
                'oldValue': 'Edited Test Group',
                'newValue': 'Edited Test Group'
            }
        ]
    }}
]
```

You must provide the full payload when using PUT. If you only want to update one value you can make use of PATCH which only takes the values you want to change. For networkdevicegroups PATCH is only supported in Cisco ISE >= 3.2. Remember to always check the API documentation provided by Cisco (https://developer.cisco.com/docs/identity-services-engine/latest).

Let's delete the network device group:

```
from asyncio import run
from NDCiscoISE import NDCiscoISE

async def main():
    ISE = NDCiscoISE("username", "password", "ise_ip_address")
    DeleteNetworkGroup = await ISE.ISE_DELETE_api_ids("networkdevicegroup", ["4d2943f0-add6-11ed-bb08-ee2842faf84b"])
    print(DeleteNetworkGroup) # Will print True if successful

if __name__ == "__main__":
    run(main())
```

You can add as many ids as you like in the list. The program will delete all of them sending 30 delete requests per second.

This should cover how to use this module.

## Author

2023 Developed by [Rune Johannesen](https://github.com/cowm00) @ NetDesign A/S

----
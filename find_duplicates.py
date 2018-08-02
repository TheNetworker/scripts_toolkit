#!/usr/bin/python
# Author: Bassem Aly
# Juniper Networks

# Assumptions
# 1- I'm searching for vrf instances only, not virtual-switch or any other instance-type
# 2- VRF Interface has only one address, other addresses are automatically ignored (fixed in commit #5ac3ab1)
# 3- Use python 2.7.x not 3.x (it should work on both but I didn't test it on 3 train)
# 4- remove "class-of-services{}" entire section from configuration
# 5- remove " routing-instances " from descriptions


from ciscoconfparse import CiscoConfParse
from pprint import pprint
import collections
from sys import argv
import subprocess
import time
import re

parse = CiscoConfParse(argv[1], syntax='junos', comment='!')

try:
    debug = argv[2]
    pprint("Script Debug is {0}".format(debug))
except:
    pprint("You didn't configure any logging verbose, default will be False")
    debug = "false"

# f = open("/media/bassim/DATA/cisco-config",'w')
#
# data = ""
# for line in parse.ioscfg:
#     data = data + "\n" + line
#
# f.write(data)
# f.close()

# exit()


# cos = parse.find_all_children(r"^class-of-service ")
# pprint(cos)

welcome_text = '''
 _____                                                 __  __          __                               __                
/\___ \                  __                           /\ \/\ \        /\ \__                           /\ \               
\/__/\ \  __  __    ___ /\_\  _____      __   _ __    \ \ `\\ \     __\ \ ,_\  __  __  __    ___   _ __\ \ \/'\     ____  
   _\ \ \/\ \/\ \ /' _ `\/\ \/\ '__`\  /'__`\/\`'__\   \ \ , ` \  /'__`\ \ \/ /\ \/\ \/\ \  / __`\/\`'__\ \ , <    /',__\ 
  /\ \_\ \ \ \_\ \/\ \/\ \ \ \ \ \L\ \/\  __/\ \ \/     \ \ \`\ \/\  __/\ \ \_\ \ \_/ \_/ \/\ \L\ \ \ \/ \ \ \\`\ /\__, `\
  \ \____/\ \____/\ \_\ \_\ \_\ \ ,__/\ \____\\ \_\      \ \_\ \_\ \____\\ \__\\ \___x___/'\ \____/\ \_\  \ \_\ \_\/\____/
   \/___/  \/___/  \/_/\/_/\/_/\ \ \/  \/____/ \/_/       \/_/\/_/\/____/ \/__/ \/__//__/   \/___/  \/_/   \/_/\/_/\/___/ 
                                \ \_\                                                                                     
                                 \/_/                                                                                                                    
'''

print(welcome_text)


def script_logger(data="", message="", debug="false", indent=0):
    # pprint(debug)
    if debug.lower() == "true":
        pprint("LoggingMessage: " + " " * indent + message + data)


def get_address(num, IFD_CONFIG):
    intf_address = []
    counter = num + 1

    if "10.41.104.203" in IFD_CONFIG:
        script_logger(data=IFD_CONFIG, debug=True)

    while " unit " not in IFD_CONFIG[counter]:
        # print("LIST: {0}        counter:{1}".format(len(IFD_CONFIG),counter))
        # pprint(IFD_CONFIG[counter])
        if " address " in IFD_CONFIG[counter] and IFD_CONFIG[counter].split()[1] != "address":
            intf_address.append(IFD_CONFIG[counter].split()[1])
            # break #

        if counter == len(IFD_CONFIG) - 1:  # no address configured under the unit
            intf_address.append("NO_ADDRESS")
            break
        else:
            counter = counter + 1

    return intf_address


def get_all_addresses(interfaces):
    all_addresses = []
    unit_re = re.compile('\s+unit \d+')

    for intf in interfaces:
        IFD = intf.strip()
        IFD_CONFIG = parse.find_all_children("^\s+{0}".format(IFD))

        for num, line in enumerate(IFD_CONFIG):
            if unit_re.search(line):
                all_addresses = all_addresses + get_address(num, IFD_CONFIG)

    return all_addresses


def get_and_compare(instance, interfaces, type, all_addresses):
    global debug
    addresses = []
    for intf in interfaces:
        if type == 'vrf':
            IFD = intf.split(".")[0]
            IFL = intf.split(".")[1]
            unit_string = '\s+unit {0} '.format(IFL)
            unit_re = re.compile(unit_string)

        IFD_CONFIG = parse.find_all_children(r"^\s+{0} ".format(IFD), exactmatch=True)

        if "address" not in IFD.lower():
            for num, line in enumerate(IFD_CONFIG):
                if unit_re.search(line):
                    new_addresses = get_address(num, IFD_CONFIG)
                    addresses = addresses + new_addresses
                    if "vpnmonitor" in instance and "5.119.81.205/30" in new_addresses:
                        script_logger(data="{0} {1}: {2}".format(IFD, line.strip(), new_addresses), debug=debug,
                                      indent=2)
                        script_logger(message="interface: ", data=intf, debug=debug, indent=2)
                        script_logger(message="IFD: ", data=IFD, debug=debug, indent=2)
                        script_logger(message="IFL: ", data=IFL, debug=debug, indent=2)

    if addresses:

        script_logger(message="*Removing the VRF addresses from global", debug=debug, indent=2)
        script_logger(message="*Number of addresses before removing: {0}".format(len(all_addresses)), debug=debug,
                      indent=2)

        all_addresses = [x for x in all_addresses if x not in addresses and x != ""]
        vrf_duplicate = [item for item, count in collections.Counter(addresses).items() if count > 1]

        script_logger(message="*Number of VRF addresses: {0}".format(len(addresses)), debug=debug, indent=2)
        script_logger(message="*Number of duplicate addresses: {0}".format(len(vrf_duplicate)), debug=debug, indent=2)
        script_logger(message="*Number of addresses after removing: {0}".format(len(all_addresses)), debug=debug,
                      indent=2)

        # if "vpnmonitor" in instance:
        #     script_logger(data=interfaces, debug=debug)
        #     script_logger(data=addresses, debug=debug)
        #     script_logger(data=vrf_duplicate, debug=debug)

        if vrf_duplicate:
            return all_addresses, vrf_duplicate
        else:
            return all_addresses, "NO_DUPLICATES"


interfaces = parse.find_children(r"^interfaces ")[1:]

print("**Getting All addresses from the configuration")
all_addresses = get_all_addresses(interfaces)

routing_instances = parse.find_children('^routing-instances')
# pprint(routing_instances)


ri_vrfs = []
for ri in routing_instances:
    ri_config = parse.find_children(ri)

    if "instance-type vrf" in ri_config[1]:
        ri_vrfs.append(ri)

last_instance = ri_vrfs[-1]

script_logger(message="*Last Instances is {0}".format(last_instance), debug=debug,
              indent=1)

vrf_interfaces = []
for index, instance in enumerate(ri_vrfs):
    print("\n")
    script_logger(message="*Processing Instance:{0}".format(instance), debug=debug)
    if debug.lower() == 'false':
        pprint("Processing instance #{0} out of {1}".format(index + 1, len(ri_vrfs)))
        # time.sleep(0.5)
        # subprocess.call("clear")

    instance_config = parse.find_all_children(instance)
    for line in instance_config:
        if "interface " in line:
            vrf_interfaces.append(line.split()[1])

    script_logger(message="*VRF interfaces are {0}".format(vrf_interfaces), debug=debug,
                  indent=2)
    vrf_interfaces = list(set(vrf_interfaces))
    clean_intfs = []
    for intf in vrf_interfaces:
        if ";" not in intf:
            clean_intfs.append(intf)

    vrf_interfaces = clean_intfs

    if len(vrf_interfaces) >= 1:
        try:
            all_addresses, vrf_duplicates = get_and_compare(instance, vrf_interfaces, 'vrf', all_addresses)
            script_logger(message="*All_Addresses: {0}".format(all_addresses), debug=debug,
                          indent=2)
        except:
            pass

        if vrf_duplicates != "NO_DUPLICATES":
            pprint("{0}: {1}".format(instance.strip(), vrf_duplicates))

        vrf_interfaces = []
        script_logger(message="*Last Instances is {0}".format(last_instance), debug=debug,
                      indent=0)
        script_logger(message="*Current Instances is {0}".format(instance), debug=debug,
                      indent=0)

    if instance == last_instance:
        script_logger(message="*Current Instances is {0}".format(instance), debug=debug,
                      indent=2)
        pprint("Global Duplicates: {0}".format(
            [item for item, count in collections.Counter(all_addresses).items() if count > 1]))

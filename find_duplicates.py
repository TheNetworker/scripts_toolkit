#!/usr/bin/python
#Author: Bassem Aly
#Juniper Networks

#Assumptions
# 1- I'm searching for vrf instances only, not virtual-switch or any other instance-type
# 2- VRF Interface has only one address, other addresses are automatically ignored
# 3- Use python 2.7.x not 3.x (it should work on both but I don't test it on 3 train)

from ciscoconfparse import CiscoConfParse
from pprint import pprint
import collections
from sys import argv

import re

parse = CiscoConfParse("/media/bassim/DATA/DOKKI-config", syntax='junos', comment='#')


def get_address(num,IFD_CONFIG):
    intf_address = []
    counter = num + 1
    while " unit" not in IFD_CONFIG[counter]:
        # print("LIST: {0}        counter:{1}".format(len(IFD_CONFIG),counter))
        # pprint(IFD_CONFIG[counter])
        if "address" in IFD_CONFIG[counter]:
            intf_address.append(IFD_CONFIG[counter].split()[1])
            break #

        if counter == len(IFD_CONFIG)-1: #no address configured under the unit
            break
        else:
            counter = counter + 1
    return intf_address



def get_and_compare(interfaces,type='vrf'):
    unit_re = re.compile('\s+unit \d+')
    if type == 'global':
        all_addresses = []
    addresses = []
    for intf in interfaces:
        if type == 'vrf':
            IFD = intf.split(".")[0]
            IFL = intf.split(".")[1]

        elif type == 'global':
            IFD = intf.strip()

        IFD_CONFIG = parse.find_all_children("^\s+{0}".format(IFD))

        # if type == 'global':
        #     pprint(IFD_CONFIG)
        # pprint(IFD_CONFIG)
        for num,line in enumerate(IFD_CONFIG):
            if type == "vrf" and " unit {0}".format(IFL) in line:
                addresses = addresses + get_address(num,IFD_CONFIG)

            elif type =="global" and unit_re.search(line):
                # print IFD_CONFIG
                all_addresses = all_addresses + get_address(num,IFD_CONFIG)


    vrf_duplicate = [item for item, count in collections.Counter(addresses).items() if count > 1]

    if type == "global" and all_addresses:
        return all_addresses
    if type == "vrf" and vrf_duplicate:
        return vrf_duplicate


interfaces = parse.find_children(r"^interfaces ")[1:]
cos_intf = interfaces.index("interfaces ")
interfaces = interfaces[:cos_intf]
all_addresses = get_and_compare(interfaces, "global")


routing_instances = parse.find_children("^routing-instances")[1:]

ri_vrfs = []
for ri in routing_instances:
    ri_config = parse.find_children(ri)

    if "instance-type vrf" in ri_config[1]:
        ri_vrfs.append(ri)

vrf_interfaces = []
for instance in ri_vrfs:
    print instance
    instance_config = parse.find_all_children(instance)
    for line in instance_config:
        if "interface " in line:
            vrf_interfaces.append(line.split()[1])

    if len(vrf_interfaces) > 1:
        vrf_duplicates = get_and_compare(vrf_interfaces,'vrf')
        print("==========================")
        pprint(vrf_duplicates)
        if vrf_duplicates:
            all_addresses = [ x for x in all_addresses if x not in vrf_duplicates and x != "" ]
            pprint("{0}: {1}".format(instance.strip(),vrf_duplicates))
    # pprint(interfaces)
    vrf_interfaces = []

if all_addresses:
    pprint("Global Duplicates: {0}".format([item for item, count in collections.Counter(all_addresses).items() if count > 1]))

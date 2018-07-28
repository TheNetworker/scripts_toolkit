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

# parse = CiscoConfParse(argv[1], syntax='junos', comment='!')
parse = CiscoConfParse("/media/bassim/DATA/DOKKI-config", syntax='junos', comment='!')
f = open("/media/bassim/DATA/cisco-config",'w')

# data = ""
# for line in parse.ioscfg:
#     data = data + "\n" + line
#
# f.write(data)
# exit()


# cos = parse.find_all_children(r"^class-of-service ")
# pprint(cos)

def get_address(num,IFD_CONFIG):
    intf_address = []
    counter = num + 1
    while " unit " not in IFD_CONFIG[counter]:
        # print("LIST: {0}        counter:{1}".format(len(IFD_CONFIG),counter))
        # pprint(IFD_CONFIG[counter])
        if " address " in IFD_CONFIG[counter]:
            intf_address.append(IFD_CONFIG[counter].split()[1])
            # break #

        if counter == len(IFD_CONFIG)-1: #no address configured under the unit
            intf_address.append("NO_ADDRESS")
            break
        else:
            counter = counter + 1

    # if "5.119.50.21/30" in intf_address:
    #     pprint(intf_address)
    #     pprint (IFD_CONFIG)

    return intf_address








def get_all_addresses(interfaces):
    all_addresses = []
    unit_re = re.compile('\s+unit \d+')

    for intf in interfaces:
        IFD = intf.strip()
        IFD_CONFIG = parse.find_all_children("^\s+{0}".format(IFD))

        for num,line in enumerate(IFD_CONFIG):
            if unit_re.search(line):
                all_addresses = all_addresses + get_address(num,IFD_CONFIG)


    return all_addresses



def get_and_compare(instance,interfaces,type,all_addresses):
    addresses = []

    for intf in interfaces:
        if type == 'vrf':
            IFD = intf.split(".")[0]
            IFL = intf.split(".")[1]

            if "vpnmonitor" in instance:
                pprint(intf)

        IFD_CONFIG = parse.find_all_children("^\s+{0}".format(IFD))

        if "address" not in IFD.lower():
            for num,line in enumerate(IFD_CONFIG):
                if type == "vrf" and " unit {0}".format(IFL) in line:
                    addresses = addresses + get_address(num,IFD_CONFIG)



    if addresses:
        # pprint(addresses)
        # pprint(all_addresses)
        all_addresses = [x for x in all_addresses if x not in addresses and x != ""]
        vrf_duplicate = [item for item, count in collections.Counter(addresses).items() if count > 1]

        if "vpnmonitor" in instance:
            pprint(interfaces)
            pprint(addresses)
            pprint(vrf_duplicate)

        if vrf_duplicate:

            # pprint(vrf_duplicate)
            return all_addresses,vrf_duplicate
        else:
            return all_addresses,"NO_DUPLICATES"


interfaces = parse.find_children(r"^interfaces ")[1:]
# cos_intf = interfaces.index("interfaces ")
# interfaces = interfaces[:cos_intf]

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
vrf_interfaces = []
for instance in ri_vrfs:
    print("**Processing Instance:{0}".format(instance))
    instance_config = parse.find_all_children(instance)
    for line in instance_config:
        if "interface " in line:
            vrf_interfaces.append(line.split()[1])

    vrf_interfaces = list(set(vrf_interfaces))
    clean_intfs = []
    for intf in vrf_interfaces:
        if ";" not in intf:
            clean_intfs.append(intf)

    vrf_interfaces = clean_intfs
    # pprint(vrf_interfaces)
    if len(vrf_interfaces) >= 1:
        try:
            all_addresses,vrf_duplicates = get_and_compare(instance,vrf_interfaces,'vrf',all_addresses)
        except:
            pass

        if vrf_duplicates != "NO_DUPLICATES":
            pprint("{0}: {1}".format(instance.strip(),vrf_duplicates))
    # pprint(interfaces)
        vrf_interfaces = []
        if instance == last_instance:
            pprint("Global Duplicates: {0}".format(
            [item for item, count in collections.Counter(all_addresses).items() if count > 1]))

#
# if all_addresses:
#     pprint("Global Duplicates: {0}".format([item for item, count in collections.Counter(all_addresses).items() if count > 1]))


#
# def test(x,y):
#     return x,y
#
#
#
# m,n = test([10,11],[13,14])
#
# pprint(m)
# pprint(n)
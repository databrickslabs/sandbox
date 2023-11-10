import argparse
from typing import List
import copy
import itertools
import json
import logging

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.settings import IpAccessListInfo, ListType

import ipaddress


def check_for_subnet_inclusion(ip_addresses: List[str], oip: str, cond: bool, to_remove: List[str]):
    if oip.find("/") == -1:
        return

    oip_net = ipaddress.ip_network(oip, False)
    for ip in ip_addresses:
        if ip == oip:
            continue
        if ip.find("/") == -1:
            if ipaddress.ip_address(ip) in oip_net and cond:
                logging.debug(f"\t{ip} is part of {oip}, removing...")
                to_remove.append(ip)
        elif oip_net.supernet_of(ipaddress.ip_network(ip, False)) and cond:
            logging.debug(f"\t{ip} is subnet of {oip}, removing...")
            to_remove.append(ip)


def analyze_lists(orig: List[IpAccessListInfo]) -> List[IpAccessListInfo]:
    """Analyze and modify the IP Access Lits if problems are found

    :param orig: source list of IP Access List structures
    :return: new, potentially modified list of IP Access List structures
    """
    lsts = copy.deepcopy(orig)

    all_ips = list(itertools.chain(*[l.ip_addresses for l in lsts]))
    uniq_ips = set(all_ips)
    if len(all_ips) != len(uniq_ips):
        logging.info(f"There are duplicates in the IP Access lists! len(all_ips)={len(all_ips)}, len(uniq_ips)={len(uniq_ips)}")

    for i in range(len(lsts)):
        l = lsts[i]
        if not l.enabled:
            logging.debug(f"Skipping not enabled list {l.label} ({l.list_id})")
            continue
        logging.debug(f"Processing list '{l.label}' ({l.list_id})")
        to_remove = []
        ip_addresses = l.ip_addresses
        # find duplicates inside the list
        if len(set(ip_addresses)) != len(ip_addresses):
            logging.debug("\tThere are duplicates in IP list, removing")
            #logging.debug(f"\tOld list: {ip_addresses}")
            ip_addresses = list(set(ip_addresses))
            #logging.debug(f"\tNew list: {ip_addresses}")

        # find duplicates & overlaps with other lists
        for l2 in lsts:
            # skip current list or if another list isn't enabled
            if l2.list_id == l.list_id or not l2.enabled:
                continue
            dups = set(ip_addresses).intersection(l2.ip_addresses)
            if len(dups) > 0:
                logging.debug(f"\tFound intersection with list {l2.label}")
                if l2.list_type == ListType.BLOCK or (l.list_type == ListType.ALLOW):
                    logging.debug("\tModifying current list...")
                    to_remove.extend(dups)

            # finding subranges
            for oip in l2.ip_addresses:
                try:
                    check_for_subnet_inclusion(ip_addresses, oip,
                                               l2.list_type == l.list_type, to_remove)
                except ValueError as ex:
                    logging.warn(f"\tWarn: Incorrect IP Address or Network: '{ex}'")

        # Find private & local IPs
        for ip in ip_addresses:
            try:
                if ip.find("/") == -1:
                    ip_addr = ipaddress.ip_address(ip)
                else:
                    ip_addr = ipaddress.ip_network(ip, False)
                if ip_addr.is_loopback or ip_addr.is_private:
                    logging.debug(f"\tWe can ignore {ip} because it's local or private...")
                    to_remove.append(ip)
            except ValueError as ex:
                logging.warn(f"\tWarn: Incorrect IP Address or Network: '{ip}': {ex}")

        # find subranges, in the current list as well...
        for oip in ip_addresses:
            try:
                check_for_subnet_inclusion(ip_addresses, oip, True, to_remove)
            except ValueError as ex:
                logging.warn(f"\tWarn: Incorrect IP Address or Network: '{ex}'")

        if len(to_remove) > 0:
            logging.debug(f"\tRemoving from {l.label}: {list(set(to_remove))}")
            for ip in set(to_remove):
                ip_addresses.remove(ip)

        lsts[i] = IpAccessListInfo(address_count=len(ip_addresses), list_type=l.list_type,
                                   list_id=l.list_id, label=l.label,
                                   ip_addresses=ip_addresses, enabled=l.enabled)

    return lsts


def apply_modifications(w: WorkspaceClient, make_changes: bool, orig: List[IpAccessListInfo],
                        new: List[IpAccessListInfo]):
    """Apply modifications to the specific IP Access Lists if there are changes
    in a specific IP Access List.  Delete a list if it's empty

    :param w: WorkspaceClient
    :param make_changes: if we should apply changes to workspace
    :param orig: original list of IP Access Lists
    :param new: potentially modified list of IP Access Lists
    :return:
    """
    ol = dict([(l.list_id, l) for l in orig])
    for l in new:
        if len(l.ip_addresses) == 0:
            logging.info(f"Going to remove list '{l.label}' ({l.list_id}) as it's empty")
            if w and make_changes:
                w.ip_access_lists.delete(l.list_id)
            continue
        old = ol[l.list_id]
        if len(l.ip_addresses) == len(old.ip_addresses) or not l.enabled:
            logging.info(f"List '{l.label}' ({l.list_id}) isn't modified or not enabled")
        else:
            diff = list(set(old.ip_addresses).difference(set(l.ip_addresses)))
            logging.info(f"Going to modify list '{l.label}' ({l.list_id}). Entries to remove: {diff}")
            logging.debug(f"\tfrom: {old}")
            logging.debug(f"\tto  : {l}")
            if w and make_changes:
                w.ip_access_lists.update(ip_access_list_id=l.list_id,
                    label=l.label, list_id=l.list_id, list_type=l.list_type,
                    enabled=l.enabled, ip_addresses=l.ip_addresses)


def main():
    parser = argparse.ArgumentParser(description='Analyze and fix Databricks IP Access Lists')
    parser.add_argument('--apply', help="Do analysis and apply changes",
                        action='store_true', default=False)
    parser.add_argument('--debug', help="Allow debug output",
                        action='store_true', default=False)
    parser.add_argument('--json-file', nargs=1,
                        help="Load IP Access Lists from a JSON file that is output of lists API")
    args = parser.parse_args()
    log_level = logging.INFO
    if args.debug:
        log_level = logging.DEBUG
    logging.basicConfig(level=log_level)
    if args.apply:
        logging.debug("Performing analysis & fixing issues...")
    else:
        logging.debug("Performing only analysis...")

    w = None

    if args.json_file:
        logging.debug(f"Going to load IP Access Lists from JSON file: {args.json_file[0]}")
        with open(args.json_file[0]) as f:
            d = json.load(f)
            ipls = [IpAccessListInfo.from_dict(l) for l in d['ip_access_lists']]
    else:
        logging.debug("Getting IP Access Lists from workspace")
        w = WorkspaceClient()
        logging.debug(f"Processing IP Access Lists for host {w.config.host}")
        ipls = list(w.ip_access_lists.list())

    new_ipls = analyze_lists(ipls)

    apply_modifications(w, args.apply, ipls, new_ipls)


if __name__ == '__main__':
    main()

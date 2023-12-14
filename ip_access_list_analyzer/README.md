---
title: "Analyzer/fix tool for Databricks IP Access Lists"
language: python
author: "Alex Ott"
date: 2022-10-15

tags: 
- workspaces
- security
- ip-access-lists
- script
- installable
---

# Analyzer/fix tool for Databricks IP Access Lists

This tool is used to perform analysis of the [Databricks IP Access Lists for Workspaces](https://docs.databricks.com/security/network/ip-access-list-workspace.html) to identify problems, like:

* specification of private & local IP addresses: `10.x.x.x`, `192.168.x.x`, `127.0.0.x`, ...
* having duplicate entries in the list(s)
* having overlapping entries in the list(s) when big network is included together with smaller networks/IPs covered by a bigger network.

Besides identification of the problems, the tool could be also used to fix the problems found by calling REST API to update lists.

Only enabled IP Access Lists are analyzed (and fixed).


## Installation

* You need to have Python 3.8+ installed
* The code and dependencies are installed as part of the `databricks labs install sandbox` command.

## Usage

To run the tool just execute:

```sh
databricks labs sandbox ip-access-list-analyzer [options]
```

Pass `--help` command-line flag to obtain built-in help.  Specify `--debug` option to get detailed log output.

This tool works in two modes:

1. Analysis (and optional fix) of IP Access Lists obtained directly from workspace via [REST API](https://docs.databricks.com/api/workspace/ipaccesslists/list).  To work in this mode you need to configure authentication via environment variables as described in [documentation](https://docs.databricks.com/dev-tools/auth.html).  To apply fixes for problems found, add `--apply` command line flag - in this case tool will remove empty lists and modify lists that were modified.

1. Analysis (without fixing) of IP Access Lists stored in the files by using the `--json_file` command line flag. The format of the file must be the same as output of the [Get IP Acces Lists REST API](https://docs.databricks.com/api/workspace/ipaccesslists/list). See `test.json` for example. 

### Example

If you execute following command:

```sh
databricks labs sandbox ip-access-list-analyzer --json_file=test.json
```

Then you will receive following output:

```
INFO:root:There are duplicates in the IP Access lists! len(all_ips)=241, len(uniq_ips)=237
INFO:root:Going to remove list 'list1' (0f209622-ca20-455a-bdc4-4de3bed8a1ed) as it's empty
INFO:root:Going to modify list 'list1 dup' (1f209622-ca20-455a-bdc4-4de3bed8a1ed). Entries to remove: ['52.55.144.63']
INFO:root:Going to modify list 'list2' (1f209623-ca20-455a-bdc4-4de3bed8a1ed). Entries to remove: ['10.1.2.0/24', '192.168.10.11', '52.55.144.63', '10.0.1.0']
INFO:root:List 'github_actions' (d798c5f5-3b53-4dc7-85b7-75dd67056512) isn't modified or not enabled
INFO:root:List 'Disabled list' (fc594781-60cb-4b46-b0f7-ee9d951e3c3f) isn't modified or not enabled
```

Based on the output we can see that following changes will be done:

* List `list1` will be removed because it had full overlap with `list1 dup`, and became empty.
* List `list1 dup` will be modified because it had intersection with the `list2`, plus one of the IP addresses is subset of another network
* List `list2` will be modified because it had some overlapping IP addresses, and few IPs were from the private IP ranges.

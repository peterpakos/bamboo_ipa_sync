# bamboo_ipa_sync
Bamboo HR to FreeIPA Synchronisation Tool

## Usage
```
$ ./usage: bamboo_ipa_sync [-h] [--version] [-l] [-b] [-s] [-n]
                       [-f [UID [UID ...]]]

A tool to synchronise FreeIPA with Bamboo HR

optional arguments:
  -h, --help            show this help message and exit
  --version             show program's version number and exit
  -l, --ldap            print LDAP data and exit
  -b, --bamboo          print Bamboo data and exit
  -s, --sync            synchronise LDAP with Bamboo
  -n, --notification    send New Starter Notification (requires -s)
  -f [UID [UID ...]], --force [UID [UID ...]]
                        force changes for given UIDs (or all if none provided)
```

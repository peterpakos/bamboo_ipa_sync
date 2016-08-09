# bamboo_ipa_sync
Bamboo HR to FreeIPA Synchronisation Tool

## Usage
```
$ ./bamboo_ipa_sync -h
usage: bamboo_ipa_sync [-h] [--version] [-l] [-b] [-s] [-n]

A tool to synchronise FreeIPA with Bamboo HR

optional arguments:
  -h, --help          show this help message and exit
  --version           show program's version number and exit
  -l, --ldap          print LDAP data and exit
  -b, --bamboo        print Bamboo data and exit
  -s, --sync          synchronise LDAP with Bamboo
  -n, --notification  send New Starter Notification (requires -s)
```

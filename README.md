# bamboo_ipa_sync
Bamboo HR to FreeIPA Synchronisation Tool

## Python modules
Run the following command to install required Python modules:
~~~
$ pip install -r requirements.txt
~~~

## Configuration
Edit and save the sample config file `CONFIG_SAMPLE.py` as `CONFIG.py`.

## Usage
```
$ ./bamboo_ipa_sync -h
usage: bamboo_ipa_sync [-h] [--version] [-l] [-b] [-s] [-n]
                       [-f [UID [UID ...]]] [-N]

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
  -N, --noop            dry-run mode
```

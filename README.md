# bamboo_ipa_sync
Bamboo to FreeIPA synchronisation tool

## Usage
```
$ ./bamboo_ipa_sync.py -h
bamboo_ipa_sync.py version 16.3.3
Usage: bamboo_ipa_sync.py [OPTIONS]
AVAILABLE OPTIONS:
-u  Bamboo API URL
-U  Bamboo API URL file (default: bamboo_ipa_sync.url)
-a  Bamboo API key (prompt for one if not supplied with -a/-A)
-A  Bamboo API key file (default: bamboo_ipa_sync.key)
-e  Bamboo exclude list
-E  Bamboo exclude list file (default: bamboo_ipa_sync.exclude)
-b  Print Bamboo data and exit (can be combined with -l)
-l  Print IPA LDAP data and exit (can be combined with -b)
-H  List of IPA servers (e.g.: 'shdc01 shdc02')
-d  IPA domain (e.g.: 'ipa.wandisco.com')
-D  BIND DN (default: 'cn=Directory Manager')
-p  BIND PW (prompt for one if not supplied with -p/-P)
-P  BIND PW file (default: bamboo_ipa_sync.passwd)
-h  Print this help summary page
-v  Print version number
```

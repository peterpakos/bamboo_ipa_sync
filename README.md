# bamboo_ipa_sync
Tool to synchronise FreeIPA with BambooHR

PyPI package: [bamboo_ipa_sync](https://pypi.python.org/pypi/bamboo_ipa_sync)

If you spot any problems or have any improvement ideas then feel free to open
an issue and I will be glad to look into it for you.

## Installation
A recommended way of installing the tool is pip install.

Once installed, a command line tool `bamboo_ipa_sync` should be available in your
system's PATH.

### pip install
The tool is available in PyPI and can be installed using pip:
```
$ pip install --user bamboo_ipa_sync
$ bamboo_ipa_sync --help
```

## Configuration
Edit and save the sample config file `SAMPLE_CONFIG` as `~/.config/bamboo_ipa_sync`.

The tool uses `ppmail` module for sending Email/Slack notifications, please check
[ppmail home page](https://github.com/peterpakos/ppmail) for more information on
how to configure it.

## Usage
```
$ bamboo_ipa_sync --help
usage: bamboo_ipa_sync [--version] [-l] [-b] [-s] [-n] [-f [UID [UID ...]]]
                       [-N] [--help] [--debug] [--quiet]

Tool to synchronise FreeIPA with Bamboo HR

optional arguments:
  --version             show program's version number and exit
  -l, --ldap            print LDAP data and exit
  -b, --bamboo          print Bamboo data and exit
  -s, --sync            synchronise LDAP with Bamboo
  -n, --notification    send New Starter Notification (requires -s)
  -f [UID [UID ...]], --force [UID [UID ...]]
                        force changes for given UIDs (or all if none provided)
  -N, --noop            dry-run mode
  --help                show this help message and exit
  --debug               debugging mode
  --quiet               no console output
```

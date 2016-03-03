#!/usr/bin/env python
#
# The script fetches data from Bamboo and compares it with data in FreeIPA's LDAP directory.
# Any changes to Bamboo records are synced to LDAP directory.
# Any accounts that do not exist in LDAP are created as FreeIPA stage accounts.
#
# Author: Peter Pakos <peter.pakos@wandisco.com>

from __future__ import print_function
from sys import stderr, exit, argv
from os import path
from getopt import getopt, GetoptError
from urllib2 import Request, urlopen, HTTPError, URLError
from base64 import encodestring
from xml.etree import ElementTree
from ldap import initialize, SERVER_DOWN, NO_SUCH_OBJECT, INVALID_CREDENTIALS, SCOPE_SUBTREE, LDAPError, modlist
from getpass import getpass


class Bamboo(object):
    __url = None
    __api_key = None
    __employees = {}

    def __init__(self, url, api_key):
        self.__url = url
        self.__api_key = api_key
        self.fetch_employees()

    def get_employees(self):
        return self.__employees

    def fetch_employees(self):
        request = Request(self.__url)
        base64string = encodestring('%s:x' % (
             self.__api_key
         )).replace('\n', '')
        request.add_header('Authorization', 'Basic %s' % base64string)
        result = None
        try:
            result = urlopen(request)
        except HTTPError as err:
            Main.die('Failed to fetch Bamboo data (HTTP Error Code %s)' % err.code)
        except URLError as err:
            Main.die('Failed to fetch Bamboo data (URL Error %s)' % err.reason)
        except ValueError:
            Main.die('Failed to fetch Bamboo data (Incorrect API URL)')

        directory = ElementTree.fromstring(result.read())
        for employee in directory.iter('employee'):
            fields = {}
            for field in employee.iter('field'):
                fields[field.attrib['id']] = field.text
            self.__employees.update({employee.attrib['id']: fields})
        if len(self.__employees) == 0:
            app.die('Bamboo data set is empty')

    def display_data(self):
        for fields in self.__employees.itervalues():
            print('B: %s|%s|%s|%s|%s' % (
                fields['firstName'],
                fields['lastName'],
                fields['jobTitle'],
                fields['mobilePhone'],
                fields['workEmail'],
            ))


class Ldap(object):
    __url = None
    __bind_dn = None
    __bind_pw = None
    __suffix = None
    __active_user_base = None
    __stage_user_base = None
    __preserved_user_base = None
    __con = None
    __employees = {}

    def __init__(self, ldap_server, bind_dn, bind_pw):
        self.__url = 'ldap://' + ldap_server
        self.__bind_dn = bind_dn
        self.__bind_pw = bind_pw
        self.__suffix = 'dc=' + ldap_server.partition('.')[2].replace('.', ',dc=')
        self.__active_user_base = 'cn=users,cn=accounts,' + self.__suffix
        self.__stage_user_base = 'cn=staged users,cn=accounts,cn=provisioning,' + self.__suffix
        self.__preserved_user_base = 'cn=deleted users,cn=accounts,cn=provisioning,' + self.__suffix
        self.bind()
        self.fetch_employees()

    def __del__(self):
        self.__con.unbind()

    def bind(self):
        self.__con = initialize(self.__url)
        try:
            self.__con.simple_bind_s(self.__bind_dn, self.__bind_pw)
        except (
            SERVER_DOWN,
            NO_SUCH_OBJECT,
            INVALID_CREDENTIALS
        ) as err:
            Main.die('Bind error: %s' % err.message['desc'])

    def search(self, base, scope, fltr, attrs):
        return self.__con.search_s(base, scope, fltr, attrs)

    def fetch_employees(self):
        for dn, attrs in self.search(
                self.__active_user_base,
                SCOPE_SUBTREE,
                '(uid=*)',
                ['*']
        ):
            self.__employees.update({dn: attrs})

    def get_employees(self):
        return self.__employees

    def display_data(self):
        for dn, attrs in self.get_employees().iteritems():
            given_name = attrs.get('givenName')
            sn = attrs.get('sn')
            title = attrs.get('title')
            mobile = attrs.get('mobile')
            mail = attrs.get('mail')
            if type(given_name) in [list]:
                given_name = ','.join(given_name)
            if type(sn) in [list]:
                sn = ','.join(sn)
            if type(title) in [list]:
                title = ','.join(title)
            if type(mobile) in [list]:
                mobile = ','.join(mobile)
            if type(mail) in [list]:
                mail = ','.join(mail)

            print('L: %s|%s|%s|%s|%s' % (
                given_name,
                sn,
                title,
                mobile,
                mail,
            ))

    def mail_exists(self, mail):
        result = {}
        for dn, attrs in self.get_employees().iteritems():
            mail_list = attrs.get('mail')
            if mail_list is not None:
                mail_list = [e.lower() for e in mail_list]
                if str(mail).lower() in mail_list:
                    result.update({dn: attrs})
        return result

    def user_exists(self, uid, category='active'):
        if category == 'stage':
            base = self.__stage_user_base
        elif category == 'preserved':
            base = self.__preserved_user_base
        else:
            base = self.__active_user_base
        result = self.search(
            base,
            SCOPE_SUBTREE,
            '(uid=%s)' % uid,
            ['dn']
        )
        result = len(result)
        if result == 0:
            return False
        elif result == 1:
            return True

    def add_user(self, uid, first, last, title, mobile, mail):
        dn = 'uid=%s,%s' % (uid, self.__stage_user_base)

        attrs = dict()
        attrs['objectclass'] = ['top', 'posixaccount', 'person', 'inetorgperson', 'organizationalperson']
        attrs['cn'] = first + ' ' + last
        attrs['givenName'] = first
        attrs['sn'] = last
        attrs['uid'] = uid
        attrs['uidNumber'] = '-1'
        attrs['gidNumber'] = '707'
        attrs['title'] = title
        attrs['mobile'] = mobile
        attrs['mail'] = mail
        attrs['homeDirectory'] = '/home/' + uid
        attrs['loginShell'] = '/usr/sbin/nologin'
        ldif = modlist.addModlist(attrs)

        try:
            self.__con.add_s(dn, ldif)
        except LDAPError:
            return False
        return True

    def modify(self, dn, attr, old_value, new_value):
        old = {attr: old_value}
        new = {attr: new_value}
        ldif = modlist.modifyModlist(old, new)

        try:
            self.__con.modify_s(dn, ldif)
        except LDAPError:
            return False

        return True


class Main(object):
    __version = '16.3.3'
    __name = path.basename(argv[0])
    __cwd = path.dirname(path.abspath(argv[0]))
    __bamboo_url = None
    __bamboo_url_file = __cwd + '/' + path.splitext(__name)[0] + '.url'
    __bamboo_api_file = __cwd + '/' + path.splitext(__name)[0] + '.key'
    __bamboo_api_key = None
    __bamboo_exclude_list = []
    __bamboo_exclude_list_file = __cwd + '/' + path.splitext(__name)[0] + '.exclude'
    __bind_pw_file = __cwd + '/' + path.splitext(__name)[0] + '.passwd'
    __bind_dn = 'cn=Directory Manager'
    __bind_pw = None
    __ipa_servers = []
    __ipa_domain = None
    __ldap_server = None
    __bamboo_data_mode = False
    __ldap_data_mode = False

    def __init__(self):
        self.get_opts()
        self.vet_opts()

        self.bamboo = Bamboo(self.__bamboo_url, self.__bamboo_api_key)
        self.ipa = Ldap(self.__ldap_server, self.__bind_dn, self.__bind_pw)

        if self.__bamboo_data_mode:
            self.bamboo.display_data()
        if self.__ldap_data_mode:
            self.ipa.display_data()
        if self.__bamboo_data_mode or self.__ldap_data_mode:
            exit()

        self.sync_data()

    def get_opts(self):
        options = None

        try:
            options, args = getopt(argv[1:], 'hvu:U:a:A:e:E:blH:d:D:p:P:', [
                'help',
                'version'
            ])
        except GetoptError as err:
            self.die(err)

        for opt, arg in options:
            if opt in ('-v', '--version'):
                self.display_version()
                exit()
            if opt in ('-h', '--help'):
                self.display_usage()
                exit()
            if opt in '-u':
                self.__bamboo_url = arg
            if opt in '-U':
                self.__bamboo_url_file = arg
            if opt in '-a':
                self.__bamboo_api_key = arg
            if opt in '-A':
                self.__bamboo_api_file = arg
            if opt in '-e':
                self.__bamboo_exclude_list = arg.split()
            if opt in '-E':
                self.__bamboo_exclude_list_file = arg
            if opt in '-b':
                self.__bamboo_data_mode = True
            if opt in '-l':
                self.__ldap_data_mode = True
            if opt in '-H':
                self.__ipa_servers = arg.split()
            if opt in '-d':
                self.__ipa_domain = arg
            if opt in '-D':
                self.__bind_dn = arg
            if opt in '-p':
                self.__bind_pw = arg
            if opt in '-P':
                self.__bind_pw_file = arg

    def vet_opts(self):
        if self.__bamboo_url is None:
            if path.isfile(self.__bamboo_url_file):
                self.__bamboo_url = open(self.__bamboo_url_file).readline().strip()
        if self.__bamboo_url is None:
            self.die('Bamboo URL not specified (-u/-U)')
        if self.__bamboo_api_key is None:
            if path.isfile(self.__bamboo_api_file):
                self.__bamboo_api_key = open(self.__bamboo_api_file).readline().strip()
        if self.__bamboo_api_key is None:
            self.__bamboo_api_key = raw_input('Bamboo API key: ')

        if len(self.__bamboo_exclude_list) == 0:
            if path.isfile(self.__bamboo_exclude_list_file):
                with open(self.__bamboo_exclude_list_file) as f:
                    for line in f:
                        self.__bamboo_exclude_list.append(line.strip())

        if self.__bind_pw is None:
            if path.isfile(self.__bind_pw_file):
                self.__bind_pw = open(self.__bind_pw_file).readline().strip()
        if self.__bind_pw is None:
            self.__bind_pw = getpass('BIND PW: ')

        if len(self.__ipa_servers) == 0:
            self.die('No IPA servers specified (-H)')

        if self.__ipa_domain is None:
            self.die('No domain specified (-d)')

        self.__ldap_server = self.__ipa_servers[0] + '.' + self.__ipa_domain

    def display_version(self):
        print('%s version %s' % (self.__name, self.__version))

    def display_usage(self):
        self.display_version()
        print('''Usage: %s [OPTIONS]
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
-v  Print version number''' % self.__name)

    @staticmethod
    def die(message=None, code=1):
        if message is not None:
            print(message, file=stderr)
        exit(code)

    def sync_data(self):
        for bamboo_fields in self.bamboo.get_employees().itervalues():
            bamboo_mail = bamboo_fields['workEmail']
            if bamboo_mail is not None and bamboo_mail not in self.__bamboo_exclude_list:
                bamboo_first_name = bamboo_fields['firstName']
                bamboo_last_name = bamboo_fields['lastName']
                bamboo_uid = bamboo_first_name.lower() + '.' + bamboo_last_name.lower()
                bamboo_job_title = bamboo_fields['jobTitle']
                bamboo_mobile_phone = bamboo_fields['mobilePhone']
                result = self.ipa.mail_exists(bamboo_mail)
                exists = False
                if len(result) == 0:
                    mail_uid = bamboo_mail.partition('@')[0]
                    print('%s: email found in Bamboo but not in LDAP:' % bamboo_mail)
                    print('- Checking if active user %s exists: ' % bamboo_uid, end='')
                    if self.ipa.user_exists(bamboo_uid):
                        print('YES')
                        exists = True
                    else:
                        print('NO')
                    print('- Checking if stage user %s exists: ' % bamboo_uid, end='')
                    if self.ipa.user_exists(bamboo_uid, 'stage'):
                        print('YES')
                        exists = True
                    else:
                        print('NO')
                    print('- Checking if preserved user %s exists: ' % bamboo_uid, end='')
                    if self.ipa.user_exists(bamboo_uid, 'preserved'):
                        print('YES')
                        exists = True
                    else:
                        print('NO')
                    if bamboo_uid != mail_uid:
                        print('- Checking if active user %s exists: ' % mail_uid, end='')
                        if self.ipa.user_exists(mail_uid):
                            print('YES')
                            exists = True
                        else:
                            print('NO')
                        print('- Checking if stage user %s exists: ' % mail_uid, end='')
                        if self.ipa.user_exists(mail_uid, 'stage'):
                            print('YES')
                            exists = True
                        else:
                            print('NO')
                        print('- Checking if preserved user %s exists: ' % mail_uid, end='')
                        if self.ipa.user_exists(mail_uid, 'preserved'):
                            print('YES')
                            exists = True
                        else:
                            print('NO')
                    if exists:
                        print('Account already exists, skipping account creation.')
                        continue
                    else:
                        print('Creating stage account %s: ' % bamboo_uid, end='')
                        if self.ipa.add_user(
                            bamboo_uid,
                            bamboo_first_name,
                            bamboo_last_name,
                            bamboo_job_title,
                            bamboo_mobile_phone,
                            bamboo_mail,
                        ):
                            print('OK')
                        else:
                            print('FAIL')
                elif len(result) == 1:
                    for dn, attrs in result.iteritems():
                        uid = attrs.get('uid')
                        mobile = attrs.get('mobile')
                        title = attrs.get('title')
                        if type(uid) in [list]:
                            uid = uid[0]
                        if type(title) in [list]:
                            title = title[0]
                        if type(mobile) in [list]:
                            mobile = mobile[0]
                            if bamboo_mobile_phone != mobile:
                                print('%s: updating mobile from \'%s\' to \'%s\': '
                                      % (uid, mobile, bamboo_mobile_phone), end='')
                                if self.ipa.modify(dn, 'mobile', mobile, bamboo_mobile_phone):
                                    print('OK')
                                else:
                                    print('FAIL')
                            if bamboo_job_title != title:
                                print('%s: updating title from \'%s\' to \'%s\': '
                                      % (uid, title, bamboo_job_title), end='')
                                if self.ipa.modify(dn, 'title', title, bamboo_job_title):
                                    print('OK')
                                else:
                                    print('FAIL')

                else:
                    print('More than one entry found in LDAP for email %s' % bamboo_mail, file=stderr)


if __name__ == '__main__':
    app = Main()

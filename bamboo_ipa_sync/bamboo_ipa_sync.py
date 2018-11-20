# -*- coding: utf-8 -*-
"""Tool to synchronise FreeIPA with BambooHR

The script compares data in Bamboo HR with data in FreeIPA's LDAP directory.
Any changes to Bamboo records are synced to LDAP directory.
Any accounts that do not exist in LDAP are created as stage accounts in FreeIPA.

Author: Peter Pakos <peter.pakos@wandisco.com>

Copyright (C) 2018 WANdisco
"""

from __future__ import print_function
from .__version__ import __version__

from pplogger import get_logger
from ppipa import FreeIPAServer
from ppmail import Mailer
from ppconfig import Config
from ppbamboo import BambooHR

import os
import sys

import argparse
import datetime
import tzlocal
import prettytable


class Main(object):
    def __init__(self):
        self._app_name = os.path.splitext(__name__)[0].lower()
        self._parser, self._args = self._parse_args()
        self._log = get_logger(name=__name__, debug=self._args.debug, quiet=self._args.quiet)
        self._log.debug(self._args)

        try:
            self._config = Config(self._app_name)
        except IOError as e:
            self._log.critical(e)
            exit(1)

        try:
            self._bamboo_url = self._config.get('bamboo_url')
            self._bamboo_api_key = self._config.get('bamboo_api_key')
            self._bamboo_exclude_list = self._config.get('bamboo_exclude_list').replace(',', ' ').split()
            self._bind_dn = self._config.get('bind_dn')
            self._bind_pw = self._config.get('bind_pw')
            self._ipa_server = self._config.get('ipa_server')
            self._ipa_domain = self._config.get('ipa_domain')
            self._notification_to = self._config.get('notification_to')
            self._default_gid = self._config.get('default_gid')
        except NameError as e:
            self._log.critical(e)
            exit(1)

        self._force_all = False

        if isinstance(self._args.uid, list):
            self._force_uid = self._args.uid
            if len(self._args.uid) == 0:
                self._force_all = True
        else:
            self._force_uid = []

        if self._args.bamboo:
            self._bamboo = BambooHR(self._bamboo_url, self._bamboo_api_key)
            self._display_bamboo_data()

        if self._args.ldap:
            self._ldap = FreeIPAServer(host=self._ipa_server, bindpw=self._bind_pw)
            self._display_ldap_data()

        if self._args.bamboo or self._args.ldap:
            exit()

        if self._args.sync:
            self._mailer = Mailer()
            self._bamboo = BambooHR(self._bamboo_url, self._bamboo_api_key)
            self._ldap = FreeIPAServer(host=self._ipa_server, bindpw=self._bind_pw)
            self.sync_data()
            exit()

        self._parser.print_help()

    def _parse_args(self):
        parser = argparse.ArgumentParser(description='Tool to synchronise FreeIPA with BambooHR', add_help=False)
        parser.add_argument('--version', action='version', version='%s %s' % (self._app_name, __version__))
        parser.add_argument('-l', '--ldap', help='print LDAP data and exit', dest='ldap', action='store_true')
        parser.add_argument('-b', '--bamboo', help='print Bamboo data and exit', dest='bamboo', action='store_true')
        parser.add_argument('-s', '--sync', help='synchronise LDAP with Bamboo', dest='sync', action='store_true')
        parser.add_argument('-n', '--notification', help='send New Starter Notification (requires -s)', dest='notify',
                            action='store_true')
        parser.add_argument('-f', '--force', help='force changes for given UIDs (or all if none provided)', dest='uid',
                            nargs='*', action='store')
        parser.add_argument('-N', '--noop', help='dry-run mode', dest='noop',
                            action='store_true')
        parser.add_argument('--help', action='help', help='show this help message and exit')
        parser.add_argument('--debug', action='store_true', dest='debug', help='debugging mode')
        parser.add_argument('--quiet', action='store_true', dest='quiet', help="no console output")
        return parser, parser.parse_args()

    def _display_bamboo_data(self):
        table = prettytable.PrettyTable(['ID', 'First', 'Last', 'Preferred', 'Department', 'Job title', 'Mobile',
                                         'Email', 'Division'], sortby='Last')
        table.align = 'l'
        for bamboo_id, bamboo_fields in self._bamboo.get_directory().items():
            table.add_row([
                bamboo_id,
                bamboo_fields.get('firstName'),
                bamboo_fields.get('lastName'),
                bamboo_fields.get('preferredName'),
                bamboo_fields.get('department'),
                bamboo_fields.get('jobTitle'),
                bamboo_fields.get('mobilePhone'),
                bamboo_fields.get('workEmail'),
                bamboo_fields.get('division')
            ])
        print(table)

    def _display_ldap_data(self):
        table = prettytable.PrettyTable(['ID', 'First', 'Last', 'EMail', 'Department', 'Job title', 'Division', 'UID'],
                                        sortby='Last')
        table.align = 'l'
        for uid, user in self._ldap.users().items():
            table.add_row([
                user.employee_number if user.employee_number else '',
                user.given_name if user.given_name else '',
                user.sn if user.sn else '',
                ','.join(user.mail),
                user.department_number if user.department_number else '',
                user.title if user.title else '',
                user.ou if user.ou else '',
                uid
            ])
        print(table)

    @staticmethod
    def _capitalize(string):
        return ' '.join(w[:1].upper() + w[1:] for w in string.split(' '))

    def sync_data(self):
        directory = self._bamboo.get_directory()
        local_tz = tzlocal.get_localzone()
        now = local_tz.localize(datetime.datetime.now()).date()

        printed = False
        for bamboo_id, bamboo_fields in directory.items():

            bamboo_email = str(bamboo_fields.get('workEmail')).lower()
            bamboo_email_uid = bamboo_email.partition('@')[0]

            if not bamboo_email or bamboo_email in self._bamboo_exclude_list:
                continue

            pref_first_name = bamboo_fields['firstName']
            pref_last_name = bamboo_fields['lastName']

            if bamboo_fields.get('preferredName'):
                pref_name_split = bamboo_fields['preferredName'].split()
                n = len(pref_name_split)
                if n == 1:
                    pref_first_name = pref_name_split[0]
                elif n > 1:
                    pref_first_name = pref_name_split[0]
                    pref_last_name = pref_name_split[1]

            pref_first_name = self._capitalize(pref_first_name)
            pref_last_name = self._capitalize(pref_last_name)

            result = self._ldap.find_users_by_email(email=bamboo_email)

            if len(result) == 0:
                fields = self._bamboo.fetch_field(bamboo_id, [
                    'hireDate',
                    'terminationDate',
                    'homeEmail',
                    'homePhone',
                    'supervisor',
                    'supervisorEid',
                    'customonboardingNotes',
                    'customrequestedPhone',
                    'customrequestedLaptop',
                    'customrequestedMonitor',
                    'location',
                    'customTeams',
                    'customSystems'
                ])

                if self._ldap.users().get(bamboo_email_uid):
                    exists = 'Active'
                elif self._ldap.users(user_base='stage').get(bamboo_email_uid):
                    exists = 'Stage'
                elif self._ldap.users(user_base='preserved').get(bamboo_email_uid):
                    exists = 'Preserved'
                else:
                    exists = False

                if fields['hireDate'] and fields['hireDate'] != '0000-00-00' and exists == 'Stage' \
                        and not self._force_all and bamboo_email_uid not in self._force_uid and not self._args.noop:
                    hire_date = local_tz.localize(datetime.datetime.strptime(fields['hireDate'], '%Y-%m-%d')).date()
                    if hire_date > now:
                        continue

                if printed:
                    print()
                print('New Bamboo account: %s %s (%s)' % (
                    pref_first_name,
                    pref_last_name,
                    bamboo_email))
                print('- Job Title: %s' % bamboo_fields['jobTitle'])
                print('- Department: %s' % bamboo_fields['department'])
                print('- Location: %s' % fields['location'])
                print('- Division: %s' % bamboo_fields['division'])
                print('- Manager: %s' % fields['supervisor'])
                print('- Start date: %s' % fields['hireDate'])
                printed = True

                if exists:
                    print('%s LDAP account %s already exists' % (exists, bamboo_email_uid))
                    continue

                if fields['terminationDate'] and fields['terminationDate'] != '0000-00-00':
                    print('User leaving on %s, skipping account creation' % fields['terminationDate'])
                    continue

                if fields['hireDate'] and fields['hireDate'] != '0000-00-00' and not self._force_all \
                        and bamboo_email_uid not in self._force_uid:
                    hire_date = local_tz.localize(datetime.datetime.strptime(fields['hireDate'], '%Y-%m-%d')).date()
                    if hire_date < now:
                        print('Start date is in the past, skipping account creation (use -f to force)')
                        continue

                if fields['supervisorEid']:
                    supervisor_email = self._bamboo.fetch_field(fields['supervisorEid'], ['workEmail'])
                else:
                    supervisor_email = None
                print('Creating stage LDAP account %s: ' % bamboo_email_uid, end='')
                if self._args.noop:
                    print('DRY-RUN')
                    user_created = False
                else:
                    if self._ldap.add_user(
                        uid=bamboo_email_uid,
                        employee_number=bamboo_id,
                        given_name=pref_first_name,
                        sn=pref_last_name,
                        department_number=bamboo_fields['department'],
                        title=bamboo_fields['jobTitle'],
                        mobile=bamboo_fields['mobilePhone'],
                        mail=bamboo_fields['workEmail'],
                        ou=bamboo_fields['division'],
                        gid=self._default_gid
                    ):
                        print('OK')
                        user_created = True
                    else:
                        print('FAIL')
                        user_created = False

                print('Sending New Starter Notification: ', end='')
                if not self._args.notify or self._args.noop:
                    print('NO')
                    continue
                message = '''*Personal Information*
Name: %s %s
Job Title: %s
Work Email: %s
Start Date: %s

*Department Information*
Department: %s
Location: %s
Division: %s
Manager Name: %s
Manager Email: %s

*Requirements*
Phone: %s
Laptop: %s
Monitor: %s
Teams: %s
Systems: %s

*Onboarding Notes*
%s

*LDAP uid:* %s

*Stage LDAP user created:* %s
''' % (
                    pref_first_name,
                    pref_last_name,
                    bamboo_fields['jobTitle'],
                    bamboo_email,
                    fields['hireDate'],
                    bamboo_fields['department'],
                    fields['location'],
                    bamboo_fields['division'],
                    fields['supervisor'],
                    supervisor_email,
                    fields['customrequestedPhone'],
                    fields['customrequestedLaptop'],
                    fields['customrequestedMonitor'],
                    fields['customTeams'],
                    fields['customSystems'],
                    fields['customonboardingNotes'],
                    bamboo_email_uid,
                    'Yes' if user_created else 'No'
                )

                if not supervisor_email:
                    supervisor_email = self._notification_to
                if self._mailer.send(
                        sender=supervisor_email,
                        recipients=[self._notification_to],
                        cc=[supervisor_email],
                        subject='New Starter Notification: %s %s' % (pref_first_name, pref_last_name),
                        message=message,
                        code=True
                ):
                    print('OK')
                else:
                    print('FAIL')

            elif len(result) == 1:
                for user in result:
                    user_printed = False
                    mobile = user.mobile[0] if len(user.mobile) > 0 else ''
                    phone = user.telephone_number[0] if len(user.telephone_number) > 0 else ''

                    if pref_first_name != user.given_name:
                        if printed and not user_printed:
                            print()
                            user_printed = True
                        print('%s: updating givenName from \'%s\' to \'%s\': '
                              % (user.uid, user.given_name, pref_first_name), end='')
                        if self._args.noop:
                            print('DRY-RUN')
                        else:
                            if self._ldap.modify(user.dn, 'givenName', user.given_name, pref_first_name):
                                print('OK')
                            else:
                                print('FAIL')

                    if pref_last_name != user.sn:
                        if printed and not user_printed:
                            print()
                            user_printed = True
                        print('%s: updating sn from \'%s\' to \'%s\': '
                              % (user.uid, user.sn, pref_last_name), end='')
                        if self._args.noop:
                            print('DRY-RUN')
                        else:
                            if self._ldap.modify(user.dn, 'sn', user.sn, pref_last_name):
                                print('OK')
                            else:
                                print('FAIL')

                    cn = '%s %s' % (pref_first_name, pref_last_name)
                    if cn != user.cn:
                        if printed and not user_printed:
                            print()
                            user_printed = True
                        print('%s: updating cn from \'%s\' to \'%s\': '
                              % (user.uid, user.cn, cn), end='')
                        if self._args.noop:
                            print('DRY-RUN')
                        else:
                            if self._ldap.modify(user.dn, 'cn', user.cn, cn):
                                print('OK')
                            else:
                                print('FAIL')

                    if bamboo_fields['mobilePhone'] != mobile and bamboo_fields['mobilePhone'] != 'None':
                        if printed and not user_printed:
                            print()
                            user_printed = True
                        print('%s: updating mobile from \'%s\' to \'%s\': '
                              % (user.uid, mobile, bamboo_fields['mobilePhone']), end='')
                        if self._args.noop:
                            print('DRY-RUN')
                        else:
                            if self._ldap.modify(user.dn, 'mobile', mobile, bamboo_fields['mobilePhone']):
                                print('OK')
                            else:
                                print('FAIL')

                    if bamboo_fields['mobilePhone'] != phone:
                        if printed and not user_printed:
                            print()
                            user_printed = True
                        print('%s: updating telephoneNumber from \'%s\' to \'%s\': '
                              % (user.uid, phone, bamboo_fields['mobilePhone']), end='')
                        if self._args.noop:
                            print('DRY-RUN')
                        else:
                            if self._ldap.modify(user.dn, 'telephoneNumber', phone, bamboo_fields['mobilePhone']):
                                print('OK')
                            else:
                                print('FAIL')

                    if bamboo_fields['jobTitle'] != user.title:
                        if printed and not user_printed:
                            print()
                            user_printed = True
                        print('%s: updating title from \'%s\' to \'%s\': '
                              % (user.uid, user.title, bamboo_fields['jobTitle']), end='')
                        if self._args.noop:
                            print('DRY-RUN')
                        else:
                            if self._ldap.modify(user.dn, 'title', user.title, bamboo_fields['jobTitle']):
                                print('OK')
                            else:
                                print('FAIL')

                    if bamboo_id != user.employee_number:
                        if printed and not user_printed:
                            print()
                            user_printed = True
                        print('%s: updating employeeNumber from \'%s\' to \'%s\': '
                              % (user.uid, user.employee_number, bamboo_id), end='')
                        if self._args.noop:
                            print('DRY-RUN')
                        else:
                            if self._ldap.modify(user.dn, 'employeeNumber', user.employee_number, bamboo_id):
                                print('OK')
                            else:
                                print('FAIL')

                    if bamboo_fields['department'] != user.department_number:
                        if printed and not user_printed:
                            print()
                            user_printed = True
                        print('%s: updating departmentNumber from \'%s\' to \'%s\': '
                              % (user.uid, user.department_number, bamboo_fields['department']), end='')
                        if self._args.noop:
                            print('DRY-RUN')
                        else:
                            if self._ldap.modify(user.dn, 'departmentNumber', user.department_number,
                                                 bamboo_fields['department']):
                                print('OK')
                            else:
                                print('FAIL')

                    if bamboo_fields['division'] != user.ou:
                        if printed and not user_printed:
                            print()
                            user_printed = True
                        print('%s: updating ou from \'%s\' to \'%s\': '
                              % (user.uid, user.ou, bamboo_fields['division']), end='')
                        if self._args.noop:
                            print('DRY-RUN')
                        else:
                            if self._ldap.modify(user.dn, 'ou', user.ou, bamboo_fields['division']):
                                print('OK')
                            else:
                                print('FAIL')

                    if user_printed:
                        printed = True

            else:
                print('More than one LDAP account found with email address: %s' % bamboo_fields['workEmail'],
                      file=sys.stderr)
                printed = True


def main():
    try:
        Main()
    except KeyboardInterrupt:
        print('\nTerminating...')
        exit(130)

# -*- coding: utf-8 -*-
"""This module implements communication with FreeIPA server.

Copyright (C) 2017 Peter Pakos <peter.pakos@wandisco.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from __future__ import print_function
import sys
import ldap.modlist
import prettytable
import re


class WDLdap(object):
    def __init__(self, ipa_server, bind_dn, bind_pw):
        self._ipa_server = ipa_server
        self._bind_dn = bind_dn
        self._bind_pw = bind_pw
        self._directory = {}
        self._url = 'ldaps://' + ipa_server
        self._base_dn = 'dc=' + ipa_server.partition('.')[2].replace('.', ',dc=')
        self._active_user_base = 'cn=users,cn=accounts,' + self._base_dn
        self._stage_user_base = 'cn=staged users,cn=accounts,cn=provisioning,' + self._base_dn
        self._preserved_user_base = 'cn=deleted users,cn=accounts,cn=provisioning,' + self._base_dn
        self._con = None
        self._fetch_directory()

    def __del__(self):
        self._con.unbind()

    def _bind(self):
        self._con = ldap.initialize(self._url)
        try:
            self._con.simple_bind_s(self._bind_dn, self._bind_pw)
        except (
            ldap.SERVER_DOWN,
            ldap.NO_SUCH_OBJECT,
            ldap.INVALID_CREDENTIALS
        ) as err:
            print('Bind error: %s' % err.message['desc'], file=sys.stderr)

    def _search(self, base, scope, fltr, attrs):
        return self._con.search_s(base, scope, fltr, attrs)

    def _fetch_directory(self):
        self._bind()
        for dn, attrs in self._search(
                self._active_user_base,
                ldap.SCOPE_SUBTREE,
                '(uid=*)',
                ['*']
        ):
            self._directory.update({dn: attrs})

    def get_directory(self):
        return self._directory

    def display_data(self):
        table = prettytable.PrettyTable(['ID', 'First', 'Last', 'Department', 'Job title', 'Mobile', 'Email',
                                         'Division', 'uid'], sortby='Last')
        table.align = 'l'
        for dn, attrs in self.get_directory().items():
            eid = attrs.get('employeeNumber')
            given_name = attrs.get('givenName')
            sn = attrs.get('sn')
            ou = attrs.get('ou')
            title = attrs.get('title')
            mobile = attrs.get('mobile')
            mail = attrs.get('mail')
            dept = attrs.get('departmentNumber')
            if type(eid) is list:
                eid = ','.join(eid)
            if type(given_name) is list:
                given_name = ','.join(given_name)
            if type(sn) is list:
                sn = ','.join(sn)
            if type(dept) is list:
                dept = ','.join(dept)
            if type(ou) is list:
                ou = ','.join(ou)
            if type(title) is list:
                title = ','.join(title)
            if type(mobile) is list:
                mobile = ','.join(mobile)
            if type(mail) is list:
                mail = ','.join(mail)
            table.add_row([
                eid,
                given_name,
                sn,
                dept,
                str(title)[0:40],
                mobile,
                mail,
                ou,
                re.search('uid=(.*?),', dn).group(1)
            ])
        print(table)

    def mail_exists(self, mail):
        result = {}
        for dn, attrs in self.get_directory().items():
            mail_list = attrs.get('mail')
            if mail_list is not None:
                mail_list = [e.lower() for e in mail_list]
                if str(mail).lower() in mail_list:
                    result.update({dn: attrs})
        return result

    def user_exists(self, uid, category='active'):
        if category == 'stage':
            base = self._stage_user_base
        elif category == 'preserved':
            base = self._preserved_user_base
        else:
            base = self._active_user_base
        result = self._search(
            base,
            ldap.SCOPE_SUBTREE,
            '(uid=%s)' % uid,
            ['dn']
        )
        result = len(result)
        if result == 0:
            return False
        elif result == 1:
            return True

    def add_user(self, uid, bamboo_id, first, last, dept, title, mobile, mail, division):
        dn = 'uid=%s,%s' % (uid, self._stage_user_base)
        attrs = dict()
        attrs['objectclass'] = ['top', 'posixaccount', 'person', 'inetorgperson', 'organizationalperson']
        attrs['cn'] = str(first).capitalize() + ' ' + str(last).capitalize()
        attrs['givenName'] = str(first).capitalize()
        attrs['sn'] = str(last).capitalize()
        attrs['uid'] = uid
        attrs['uidNumber'] = '-1'
        attrs['gidNumber'] = '707'
        attrs['title'] = title if title else ''
        attrs['mobile'] = mobile if mobile else ''
        attrs['telephoneNumber'] = mobile if mobile else ''
        attrs['mail'] = mail if mail else ''
        attrs['homeDirectory'] = '/home/' + uid
        attrs['loginShell'] = '/usr/sbin/nologin'
        attrs['employeeNumber'] = bamboo_id if bamboo_id else ''
        attrs['departmentNumber'] = dept if dept else ''
        attrs['ou'] = division if division else ''
        ldif = ldap.modlist.addModlist(attrs)
        try:
            self._con.add_s(dn, ldif)
        except ldap.LDAPError:
            return False
        return True

    def modify(self, dn, attr, old_value, new_value):
        old_value = '' if not old_value else [old_value]
        new_value = '' if not new_value else [new_value]
        old = {attr: old_value}
        new = {attr: new_value}
        ldif = ldap.modlist.modifyModlist(old, new)

        try:
            self._con.modify_s(dn, ldif)
        except ldap.LDAPError:
            return False

        return True

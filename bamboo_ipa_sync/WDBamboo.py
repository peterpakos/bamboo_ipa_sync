# -*- coding: utf-8 -*-
"""
This module implements communication with Bamboo HR.

Author: Peter Pakos <peter.pakos@wandisco.com>

Copyright (C) 2018 WANdisco
"""

from __future__ import print_function
import sys
import base64
import urllib2
import xml.etree.ElementTree
import prettytable


class WDBamboo(object):
    def __init__(self, url, api_key):
        self._directory = {}
        self._url = url
        self._api_key = api_key
        self._fetch_directory()

    def get_directory(self):
        return self._directory

    def _fetch(self, url):
        request = urllib2.Request(self._url + url)
        base64string = base64.encodestring('%s:x' % (
            self._api_key
        )).replace('\n', '')
        request.add_header('Authorization', 'Basic %s' % base64string)
        result = None
        try:
            result = urllib2.urlopen(request)
        except urllib2.HTTPError as err:
            print('Failed to fetch Bamboo data (HTTP Error Code %s)' % err.code, file=sys.stderr)
        except urllib2.URLError as err:
            print('Failed to fetch Bamboo data (URL Error %s)' % err.reason, file=sys.stderr)
        except ValueError:
            print('Failed to fetch Bamboo data (Incorrect API URL)', file=sys.stderr)
        return xml.etree.ElementTree.fromstring(result.read())

    def _fetch_directory(self):
        directory = self._fetch("/directory/")
        for employee in directory.iter('employee'):
            fields = {}
            for field in employee.iter('field'):
                fields[field.attrib['id']] = field.text.encode('utf8').strip() if field.text else ''
            self._directory.update({employee.attrib['id']: fields})
        if len(self._directory) == 0:
            print('Bamboo data set is empty', file=sys.stderr)

    def display_data(self):
        table = prettytable.PrettyTable(['ID', 'First', 'Last', 'Preferred', 'Department', 'Job title', 'Mobile',
                                         'Email', 'Division'], sortby='Last')
        table.align = 'l'
        number = 0
        for bamboo_id, bamboo_fields in self._directory.items():
            number += 1
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

    def fetch_field(self, bamboo_id, bamboo_fields):
        if type(bamboo_fields) is not list:
            bamboo_fields = [bamboo_fields]
        result = {}
        fields = self._fetch("/%s?fields=%s" % (bamboo_id, ','.join(bamboo_fields)))
        for f in fields.iter('field'):
            field_id = f.attrib['id']
            field_text = f.text.encode('utf8').strip() if f.text else None
            result[field_id] = field_text
        if len(bamboo_fields) == 1 and len(result) == 1:
            return result[bamboo_fields[0]]
        else:
            return result

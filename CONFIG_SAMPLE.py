# -*- coding: utf-8 -*-
"""Sample config file. Edit and save it as CONFIG.py."""


class CONFIG(object):
    # See https://www.bamboohr.com/api/documentation/ for more details on Bamboo HR setup
    BAMBOO_URL = 'https://api.bamboohr.com/api/gateway.php/company/v1/employees'
    BAMBOO_API_KEY = 'xxx'

    # Bamboo accounts to ignore
    BAMBOO_EXCLUDE_LIST = [
        'first.last@company.com'
    ]

    # FreeIPA details
    BIND_DN = 'cn=Directory Manager'
    BIND_PW = 'xxx'
    IPA_SERVER = 'ipa01.company.com'
    IPA_DOMAIN = 'ipa.company.com'

    # New accounts notification recipient
    NOTIFICATION_TO = 'it@company.com'

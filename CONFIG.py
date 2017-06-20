class CONFIG():
  # See https://www.bamboohr.com/api/documentation/ for detail on below two fields
  BAMBOO_URL = 'https://api.bamboohr.com/api/gateway.php/{yourbamboosubdomain}/v1/employees'
  BAMBOO_API_KEY = "{yourAPIkey}"
  IPA_SERVER = "ipaserver.yourdomain.com"
  # Example bind details for conventional freeipa account granted user admin role
  BIND_DN = 'uid=bamboosync,cn=users,cn=accounts,dc=example,dc=net'
  BIND_PW = ''
  BAMBOO_EXCLUDE_LIST = "somevalue"
  NOTIFICATION_TO = "someaddress"

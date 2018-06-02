import hcpsdk
import hcpsdk.namespace
from xml.etree import ElementTree as ET
from pprint import pprint
import pymysql
import datetime
import re

'''This 'python 3' script is built to collect the capacity information from all namespaces in all the tenants on a specific HCP that is
being referenced to. The hcp name along with the domain name has to be mentioned against the very first variable called "url". This way
you will tell the script which HCP does it have to talk to to fetch the information. The next important step is to have the right 
credentials updated against the very first "auth" variable(in this case at line 31). The credentials being provided must have monitor 
access to all the tenants. You need not have access to the namespaces underneath. Still we will be able to fetch the capacity information
of the namespaces. All content written with <> must be replaced with actual values. We will collect the following information in this
script: `TenantName`, `NamespaceName`, `TotalCapacity or the hard quota set for the namespace`, `Current Used Capacity of the namespace`,
`total current Object count in that namespace`, `todays Date`. All of this information is dropped into a mysql database. 
Any analysis can be done from the data in the database at a future point '''

url = '<hcpname>.hcp.<domain>.com'
tenantshortnamelist = []
tenantfullnamelist = []
namespacenamelist = []
nscapacityinfolist = []
nsquotainfolist = []

adminportal = 'admin.'+url

today = datetime.date.today()
datestr = str(today.year)+"/"+str(today.month)+"/"+str(today.day)

auth = hcpsdk.NativeAuthorization('<monitoring user>', '<password>')
tgt = hcpsdk.Target( adminportal, auth, port=hcpsdk.P_MAPI)
alltenants = hcpsdk.mapi.listtenants(tgt)

for atenant in alltenants:
    tenantshortnamelist.append(atenant.name)

for btenant in alltenants:
    tgttnts = hcpsdk.Target(btenant.name+'.'+url, auth, port=443)
    tenantfullnamelist.append(tgttnts._Target__fqdn)

for tenantfullname in tenantfullnamelist:
    tgttnt = hcpsdk.Target(tenantfullname, auth, port=hcpsdk.P_MAPI)
    c = hcpsdk.Connection(tgttnt)

for tenantsn in tenantshortnamelist:
    c.GET('/mapi/tenants/'+tenantsn+'/namespaces')
    c.response_status
    source = c.read()


    if source == "b''":
        pass
    else:
        try:
            namespacelistpertenant = ET.fromstring(source)
            namespaceinfopertenant = namespacelistpertenant.findall('name')
            for q, value in enumerate(namespaceinfopertenant):
                namespacenamelist.append(value.text)
                namespacename = str(value.text)
                cona = hcpsdk.Connection(tgt)
                conb = hcpsdk.Connection(tgt)
                cona.GET('/mapi/tenants/'+tenantsn+'/namespaces/'+value.text)
                conb.GET('/mapi/tenants/'+tenantsn+'/namespaces/'+value.text+'/statistics')
                quotasource = cona.read()
                capacitysource = conb.read()

                if quotasource == "b''":
                    pass
                else:
                    try:
                        #nsquotainfopertnt = etree.fromstring(quotasource)
                        nsquotainfopertnt = ET.fromstring(quotasource)
                        nsquotainfo = nsquotainfopertnt.findall('hardQuota')
                        for l, quota in enumerate(nsquotainfo):
                            quotarawvalue = str(quota.text)
                            #print(quotarawvalue)
                            pattern = re.compile(r'(?:\d*\.\d+)')
                            matches = pattern.finditer(quotarawvalue)
                            for match in matches:
                                if 'GB' in quotarawvalue:
                                    quotavalue = match.group()
                                    quotavaluefloat = float(quotavalue)
                                    quotavalueinbytes = (quotavaluefloat*1024*1024*1024)
                                else:
                                    quotavalue = match.group()
                                    quotavaluefloat = float(quotavalue)
                                    quotavalueinbytes = (quotavaluefloat*1024*1024*1024*1024)
                            
                    except ET.ParseError:
                        pass
                if capacitysource == "b''":
                    pass
                else:
                    try:
                        nscapacityinfopertnt = ET.fromstring(capacitysource)
                        nscapacityinfo = nscapacityinfopertnt.findall('storageCapacityUsed')
                        for l, cap in enumerate(nscapacityinfo):
                            capacityrawvalue = str(cap.text)
                            


                    except ET.ParseError:
                        pass
                if capacitysource == "b''":
                    pass
                else:
                    try:
                        nscapacityinfopertnt = ET.fromstring(capacitysource)
                        nsobjectinfo = nscapacityinfopertnt.findall('objectCount')
                        for l, obj in enumerate(nsobjectinfo):
                            objectrawvalue = str(obj.text)
                            # nscapacityinfolist.append(cap.text)

                    except ET.ParseError:
                        pass

                #print(tenantsn, namespacename, quotavalueinbytes, capacityrawvalue, objectrawvalue, datestr)
                #Use this print to test if the script is really working fine. Then you can troubleshoot the database if there are no issues here

                dbconnection = pymysql.connect(host='localhost', user='root', password='', db='SAN')
                data = (tenantsn, namespacename, quotavalueinbytes, capacityrawvalue, objectrawvalue, url, datestr)
                cursor = dbconnection.cursor()
                sql = 'INSERT INTO SAN.HCP (`TenantName`, `NamespaceName`, `TotalCapacity`, `UsedCapacity`, `Objectcount`, `HCPName`, `Date`) VALUES (%s, %s, %s, %s, %s, %s, %s)'
                cursor.execute(sql, data)
                dbconnection.commit()

            dbconnection.close()


        except ET.ParseError:
            pass

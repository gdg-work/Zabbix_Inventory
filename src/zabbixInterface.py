#!/usr/bin/env python3

from logging import getLogger
from pyzabbix.api import ZabbixAPI, ZabbixAPIException
from pyzabbix.sender import ZabbixSender, ZabbixMetric
import re

oLog = getLogger(__name__)

# Constants
RE_DISK = re.compile('^Drive Disk \d{2,3}$')
RE_ENCLOSURE = re.compile('^DiskShelf Disk Enclosure \d{1,2}$')


# THE simplest function, can take any number of arguments
def _NullFunction(*args): return None


# exceptions
class ZabInterfaceException(Exception):
    def __init__(self, sData):
        self.sData = sData

    def __str__(self): return self.sData


class GeneralZabbix:
    def __init__(self, sArrayName, sZabbixIP, iZabbixPort, sZabUser, sZabPwd):
        """
        sArrayName is a name of array (HOST.HOST) IN ZABBIX
        *Zab* are parameters for Zabbix connection.
        """
        oLog.debug("Entered DisksToZabbix.__init__")
        self.sZabbixURL = 'http://' + sZabbixIP + "/zabbix"
        self.sZabbixIP = sZabbixIP
        self.iZabbixPort = iZabbixPort
        self.dApplicationNamesToIds = {}
        self.sArrayName = sArrayName
        self.sHostID = ''
        try:
            self.oZapi = ZabbixAPI(url=self.sZabbixURL, user=sZabUser, password=sZabPwd)
            self.oZSend = ZabbixSender(zabbix_server=self.sZabbixIP, zabbix_port=self.iZabbixPort)
            lsHosts = self.oZapi.host.get(filter={"host": sArrayName})
            if len(lsHosts) > 0:
                # Just use the first host
                self.sHostID = str(lsHosts[0]['hostid'])
                oLog.debug("host ID of array: {}".format(self.sHostID))
            else:
                oLog.error("Invalid or non-existent host in Zabbix")
                raise ZabInterfaceException("This host isn't known to Zabbix")
        except ZabbixAPIException as e:
            oLog.error("Cannot connect to Zabbix API")
            oLog.error(str(e))
            raise ZabInterfaceException
        return

    def __fillApplications__(self):
        # receive the list of applications
        ldApplications = self.oZapi.do_request('application.get', {'hostids': self.sHostID})
        if len(ldApplications['result']) == 0:
            # the host exists but didn't return anything, just continue
            oLog.info("Array with ID {0} and name {1} doesn't answer".format(self.sHostID, self.sArrayName))
        else:
            # oLog.debug("Applications on host {0}: {1}".format(self.sHostID, ldApplications['result']))
            # now filter the apps list for disks
            for dApp in ldApplications['result']:
                self.dApplicationNamesToIds[dApp['name']] = dApp['applicationid']
            oLog.debug("Application IDs from array: \n{}".format(",\n".join([str(n) for n in self.dApplicationNamesToIds.keys()])))
        return

    def _oPrepareZabMetric(self, sAppName, sParameter, iValue):
        """Prepare ZabbixMetric instance for sending to a Zabbix server"""
        dFilter = {'name': sAppName + ' ' + sParameter}
        try:
            iAppID = self.dApplicationNamesToIds[sAppName]
            dItem2Get = {'hostids': self.sHostID,
                         'applicationids': iAppID,
                         'filter': dFilter,
                         'sort': 'name'}
            dResult = self.oZapi.do_request('item.get', dItem2Get)
            try:
                oLog.debug("_oPrepareZabMetric -- result of item.get(): {}".format(dResult['result']))
                sKey = dResult['result'][0]['key_']
                # now we have key, so we can prepare data to Zabbix
                oRet = ZabbixMetric(host=self.sArrayName, key=sKey, value=iValue)
            except IndexError:
                oLog.info("Can't receive item named '{}' from array".format(dFilter['name']))
                oRet = None
        except KeyError:
            oLog.info('Unknown application name "{}"'.format(sAppName))
            oRet = None
        return oRet

    def _SendMetrics(self, loMetrics):
        """Send only non-empty metrics to Zabbix"""
        if loMetrics:
            # skip empty objects from loMetrics
            loMetrics = [o for o in loMetrics if o is not None]
            self.oZSend.send(loMetrics)
        else:
            pass   # dont send empty metrics
        return


class DisksToZabbix(GeneralZabbix):
    def __init__(self, sArrayName, sZabbixIP, iZabbixPort, sZabUser, sZabPwd):
        """
        sArrayName is a name of array (HOST.HOST) IN ZABBIX
        *Zab* are parameters for Zabbix connection.
        """
        oLog.debug("Entered DisksToZabbix.__init__")
        super().__init__(sArrayName, sZabbixIP, iZabbixPort, sZabUser, sZabPwd)
        self.dOperations = {'type': self._oPrepareDiskType,
                            'name': _NullFunction,
                            'model': self._oPrepareDiskModel,
                            'SN': self._oPrepareDiskSN,
                            'position': self._oPrepareDiskPosition,
                            'RPM': self._oPrepareDiskRPM,
                            'size': self._oPrepareDiskSize}
        return

    def __fillApplications__(self):
        # receive the list of applications
        super().__fillApplications__()
        dBuf = {}
        for sName, sID in self.dApplicationNamesToIds.items():
            if RE_DISK.match(sName):
                dBuf[sName] = sID
        self.dApplicationNamesToIds = dBuf
        return

    def _oPrepareDiskRPM(self, sAppName, iValue):
        return self._oPrepareZabMetric(sAppName, 'RPM', iValue)

    def _oPrepareDiskSize(self, sAppName, iValue):
        return self._oPrepareZabMetric(sAppName, 'Size', iValue)

    def _oPrepareDiskType(self, sAppName, sValue):
        return self._oPrepareZabMetric(sAppName, 'Type', sValue)

    def _oPrepareDiskModel(self, sAppName, sValue):
        return self._oPrepareZabMetric(sAppName, 'Model', sValue)

    def _oPrepareDiskSN(self, sAppName, sValue):
        return self._oPrepareZabMetric(sAppName, 'Serial Number', sValue)

    def _oPrepareDiskPosition(self, sAppName, sValue):
        return self._oPrepareZabMetric(sAppName, 'Position', sValue)

    def sendDiskInfoToZabbix(self, sArrayName, ldDisksInfo):
        """send data to Zabbix via API"""
        loMetrics = []
        oLog.debug('sendDiskInfoToZabbix: data to send: {}'.format(str(ldDisksInfo)))
        for dDiskInfo in ldDisksInfo:
            sAppName = 'Drive ' + dDiskInfo['name']
            for sName, oValue in dDiskInfo.items():
                try:
                    loMetrics.append(self.dOperations[sName](sAppName, oValue))
                except KeyError:
                    # unknown names passed
                    oLog.info('Skipped unknown disk information item named {} with value {}'.format(sName, str(oValue)))
                    pass
        self._SendMetrics(loMetrics)
        return



class EnclosureToZabbix(GeneralZabbix):
    def __init__(self, sArrayName, sZabbixIP, iZabbixPort, sZabUser, sZabPwd):
        super().__init__(sArrayName, sZabbixIP, iZabbixPort, sZabUser, sZabPwd)
        self.dOperations = {"name":         _NullFunction,
                            "sn":           self._oPrepareEnclSN,
                            "type":         self._oPrepareEnclType,
                            "model":        self._oPrepareEnclModel,
                            "disks":        self._oPrepareEnclDisksAmount,
                            "disk-slots":   self._oPrepareEnclSlotsAmount,
                            "ps-amount":    self._oPrepareEnclPSAmount}
        return

    def __fillApplications__(self):
        # receive the list of applications
        super().__fillApplications__()
        dBuf = {}
        for sName, sID in self.dApplicationNamesToIds.items():
            if RE_ENCLOSURE.match(sName):
                dBuf[sName] = sID
        self.dApplicationNamesToIds = dBuf
        return

    def _oPrepareEnclSN(self, sAppName, sValue):
        return self._oPrepareZabMetric(sAppName, 'Serial Number', sValue)

    def _oPrepareEnclType(self, sAppName, sValue):
        return self._oPrepareZabMetric(sAppName, 'Type', sValue)

    def _oPrepareEnclModel(self, sAppName, sValue):
        return self._oPrepareZabMetric(sAppName, 'Model', sValue)

    def _oPrepareEnclDisksAmount(self, sAppName, iValue):
        return self._oPrepareZabMetric(sAppName, 'Number of Occupied Slots', iValue)

    def _oPrepareEnclSlotsAmount(self, sAppName, iValue):
        return self._oPrepareZabMetric(sAppName, 'Number of Disk Slots', iValue)

    def _oPrepareEnclPSAmount(self, sAppName, sValue):
        return self._oPrepareZabMetric(sAppName, 'Number of Power Supplies', sValue)

    def _SendEnclInfoToZabbix(self, sArrayName, ldEnclosuresInfo):
        """send data to Zabbix via API"""
        loMetrics = []
        oLog.debug('sendDiskInfoToZabbix: data to send: {}'.format(str(ldEnclosuresInfo)))
        for dShelfInfo in ldEnclosuresInfo:
            oLog.debug('_SendEnclInfoToZabbix -- shelf info dict is {}'.format(dShelfInfo))
            sAppName = 'DiskShelf ' + dShelfInfo['name']
            for sName, oValue in dShelfInfo.items():
                try:
                    loMetrics.append(self.dOperations[sName](sAppName, oValue))
                except KeyError:
                    # unknown names passed
                    oLog.info('Skipped unknown DE information item named {} with value {}'.format(sName, str(oValue)))
                    pass
        self._SendMetrics(loMetrics)
        return
# --

if __name__ == "__main__":
    # set up logging
    # oLog.setLevel(logging.DEBUG)
    # oConHdr = logging.StreamHandler()
    # oConHdr.setLevel(logging.DEBUG)
    # oLog.addHandler(oConHdr)
    # testing
    pass

# vim: expandtab : softtabstop=4 : tabstop=4 : shiftwidth=4
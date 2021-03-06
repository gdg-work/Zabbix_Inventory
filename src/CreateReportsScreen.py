#!/usr/bin/env python3
# -*- coding: utf8 -*-
"""
A small program for creating an application in the host with several items like:
    - host name
    - host accounting number (инвентарный номер) from host.inventory
    - host S/N (from inventory)
    - a link to Jasper report
"""

import zabbixInterface as zi
import pyzabbix.api as zapi
import re
import json
from urllib.parse import quote
# from pyzabbix.sender import ZabbixSender
import subprocess as sp
import logging
import logging.config
import traceback
import yaml
from i18n import _
import locale

#
# Make you configuration here, but don't forget to backup the file first
#
dConfig = yaml.load("""
    version: 1
    ZabbixAPI:
        ip: 127.0.0.1
        user: zabbix
        password: A3hHr88man01
    ZabbixSender:
        ip: 127.0.0.1
        port: 10051
    Jasper:
        # http://10.1.96.163:8080/jasperserver/flow.html?_flowId=viewReportFlow&\
        #       ParentFolderUri=%2Freports&j_username=zabbix&j_password=Z@bbix123&\
        #       reportUnit=%2Freports%2FHOST_ITEMS&HOST_NAME=HOST-EVA-4400
        ip: zabbix.protek.ru
        port: 8080
        root: "/jasperserver"
        report_folder: "reports"
        user: zabbix
        password: "Z@bbix123"
        host_name: "HOST_NAME={}"
        flow_id: viewReportFlow
        CFG_Report:
            report_name: host_by_name
            report_unit: "/reports/host_by_name"
        DIFF_Report:
            report_name: host_changes_by_date
            report_unit: "/reports/host_changes_by_date"
    Logs:
        version: 1
        formatters:
            simple:
                format: '%(asctime)s: %(name)s - %(levelname)s - %(message)s'
            brief:
                format: '%(name)s:  %(levelname)s - %(message)s'
        handlers:
          console:
            class : logging.StreamHandler
            formatter: brief
            level   : WARNING
            stream  : ext://sys.stderr
          logfile:
            class : logging.handlers.RotatingFileHandler
            formatter: simple
            encoding: utf8
            level: DEBUG
            filename: /tmp/CreatePropsScreen.log
            # Max log file size: 1 MB, then the file will be rotated
            maxBytes: 1048576
            backupCount: 1
        root:
            level: INFO
        loggers:
            __main__:
                level: INFO
                handlers: [ console, logfile ]
            zabbixInterface:
                level: INFO
                handlers: [ console, logfile ]
            Create_Properties_Screen:
                level: DEBUG
                handlers: [ console, logfile ]
    """)


# CONST
ZABBIX_ENCODING = 'utf-8'
ZABBIX_SENDER = '/usr/bin/zabbix_sender'
ZBX_SENDER_TIMEOUT = 120


def s_make_url(d_config, sRepName, s_host_name):
    """dCfg is a dictionary of configuration data for Jasper URL"""
    if 'flow_id' in d_config:
        s_flow = "flow.html?_flowId={}".format(d_config['flow_id'])
        s_base = 'http://{0}:{1}/{2}/{3}'.format(d_config['ip'], d_config['port'], d_config['root'], s_flow)
        s_base = re.sub(r'//+', '/', s_base)
        l_parts = ['ParentFolderUri=/{0}'.format(quote(d_config['report_folder']))]
        l_parts.append('j_username={}'.format(quote(d_config['user'])))
        l_parts.append('j_password={}'.format(quote(d_config['password'])))
        l_parts.append('reportUnit={}'.format(quote(d_config[sRepName]['report_unit'])))
        l_parts.append('HOST_NAME={}'.format(s_host_name))
        s_parts = '&'.join([(s) for s in l_parts])
        s_url = s_base + '&' + s_parts
        s_url = s_url
    else:
        raise(Exception)
    return(s_url)


class InventoryHost:
    def __init__(self, s_name, s_desc, s_ip, s_inv, s_sn, s_site):
        """constructor of an object, parameters:
        s_name: Zabbix name,
        s_desc: human-readable description
        s_inv: accet tag (inventory number)
        s_sn: serial number (if present)
        s_site: address as a string
        """
        self.s_name = s_name
        self.s_desc = s_desc
        self.s_inv = s_inv
        self.s_sn = s_sn
        self.s_site = s_site
        self.s_netaccess = s_ip
        self.s_url = ''
        self.d_config = {}
        return

    def set_cfg(self, dCfg):
        self.d_config = dCfg
        return

    def make_app_items(self, o_api, o_sender):
        APP_NAME = 'Properties'
        """transfer data to Zabbix"""
        # oLog.debug('*DBG* API object for host {0}: {1}'.format(self.s_name, str(o_api)))
        try:
            o_zbx_host = zi.ZabbixHost(self.s_name, o_api)
            if not o_zbx_host._bHasApplication(APP_NAME):
                o_zbx_host._oAddApp(APP_NAME)
            # make items
            # oNameItem = o_zbx_host._oAddItem(
            #     'Host name', APP_NAME, dParams={'key': zi._sMkKey(APP_NAME, "HostName"),
            #                                     'value_type': 1})
            # o_sender.add_item_value(oNameItem, self.s_name)
            oDescItem = o_zbx_host._oAddItem(
                '1_Description', APP_NAME, dParams={'key': zi._sMkKey(APP_NAME, 'Description'),
                                                  'description': _('Short description'),
                                                  'value_type': 1})
            o_sender.add_item_value(oDescItem, self.s_desc)
            oIP_Item = o_zbx_host._oAddItem(
                '2_Controlling IP', APP_NAME,
                dParams={'key': zi._sMkKey(APP_NAME, 'IP'),
                         'description': _('Internet Protocol address'),
                         'value_type': 1})
            o_sender.add_item_value(oIP_Item, self.s_netaccess)
            oInvItem = o_zbx_host._oAddItem(
                '3_Inventory #', APP_NAME,
                dParams={'key': zi._sMkKey(APP_NAME, 'Inventory Number'),
                         'description': _('Asset tag'),
                         'value_type': 1})
            o_sender.add_item_value(oInvItem, self.s_inv)
            oSN_Item = o_zbx_host._oAddItem('4_Serial Number', APP_NAME,
                dParams={'value_type': 1,
                         'description': _('System Serial Number'),
                         'key': zi._sMkKey(APP_NAME, 'Serial Num')})
            if oSN_Item:
                o_sender.add_item_value(oSN_Item, self.s_sn)
            oSiteItem = o_zbx_host._oAddItem('5_Site address', APP_NAME,
                dParams={'value_type': 1,
                         'description': _('Physical placement'),
                         'key': zi._sMkKey(APP_NAME, 'Site')})
            o_sender.add_item_value(oSiteItem, self.s_site)

            s_cfg_url = s_make_url(self.d_config['Jasper'], 'CFG_Report', self.s_name)
            oCfgRepItem = o_zbx_host._oAddItem('6_CFG Report URL', APP_NAME,
                    dParams={'value_type': 1,
                    'description': _('Configuration report URL'),
                    'key': zi._sMkKey(APP_NAME, 'CFG Rep URL')})
            o_sender.add_item_value(oCfgRepItem, s_cfg_url)

            s_diff_url = s_make_url(self.d_config['Jasper'], 'DIFF_Report', self.s_name)
            oDiffRepItem = o_zbx_host._oAddItem('7_DIFF Report URL', APP_NAME, dParams={'value_type': 1,
                    'description': _('Differential report URL'),
                    'key': zi._sMkKey(APP_NAME, 'DIFF Rep URL')})
            o_sender.add_item_value(oDiffRepItem, s_diff_url)
        except zi.MyZabbixException as e:
            oLog.error('Error communicating with Zabbix, host is ' + self.s_name)
        except Exception as e:
            oLog.error('Unhandled exception in make_app_items: ' + str(e))
            traceback.print_exc()
            raise(e)
        return


class BufferedSender:
    """Bufferized interface to 'zabbix_sender' program to make a list of items and send all the data at once
    """
    def __init__(self, s_zbx_svr_name='127.0.0.1', i_zbx_port=10051):
        """s_zbx_svr_name = Zabbix server name or IP
        i_zbx_port = Zabbix proxy port
        """
        self.s_zbx_srv = s_zbx_svr_name
        self.i_zbx_port = i_zbx_port
        self.s_sender_prog = ZABBIX_SENDER
        self.ls_sendlist = []
        return

    def add_item_value(self, o_item, s_value):
        """Add an line to senf buffer. Parameters: o_item: Zabbix item object
        (zabbixItem from zabbixInterface.py), s_value is a value as string or integer
        """
        s_tmpl = '"{0}"\t{1}\t"{2}"'
        if str(s_value) != '':
            # Escape of quotes and backslash in the s_value
            if ('\\' in s_value):
                s_value = s_value.replace('\\', r'\\')
            if ('"' in s_value):
                s_value = s_value.replace('"', r'\"')
            if o_item:
                s_ln = s_tmpl.format(o_item.host.name, o_item.key, str(s_value))
                self.ls_sendlist.append(s_ln)
            # oLog.debug('*DBG* Stored line: {}'.format(s_ln))
        return

    def send_values(self):
        l_args = [ZABBIX_SENDER, '-z', self.s_zbx_srv, '-p', str(self.i_zbx_port), '-i', '-']
        o_proc = sp.Popen(l_args, stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE, universal_newlines=False)
        s_data = '\n'.join(self.ls_sendlist)
        b_data = s_data.encode(ZABBIX_ENCODING)
        # oLog.debug('*DBG* Data to send:')
        # oLog.debug('*CONT*' + s_data)
        with open('/tmp/zbx_send.bin', 'wb') as f_out:
            f_out.write(b_data)
        try:
            locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8')
            (b_stdout, b_stderr) = o_proc.communicate(b_data, timeout=ZBX_SENDER_TIMEOUT)
        except sp.TimeoutExpired as e:
            o_proc.kill()
            oLog.error('Error calling zabbix_sender, Timeout expired')
        if o_proc.returncode != 0:
            oLog.error('*ERR* Non-zero return code from subprocess\n' +
                       '*        stdout is ' +  b_stdout.decode(ZABBIX_ENCODING) + '\n' +
                       '*        stderr is ' + b_stderr.decode(ZABBIX_ENCODING))
        return


def fi_do_the_work():
    sURL = 'http://' + dConfig['ZabbixAPI']['ip'] + '/zabbix'
    oAPI = zapi.ZabbixAPI(url=sURL,
                          user=dConfig['ZabbixAPI']['user'],
                          password=dConfig['ZabbixAPI']['password'])
    oNewSend = BufferedSender(dConfig['ZabbixSender']['ip'], dConfig['ZabbixSender']['port'])
    lsHosts = oAPI.host.get(filter={'withInventory': 1, 'status': 0})
    lHostIDs = []
    lHosts = []
    for dHost in lsHosts:
        iID = int(dHost['hostid'])
        # oLog.debug('Host ID is {}'.format(iID))
        lHostIDs.append(iID)
        dCfg = oAPI.do_request('configuration.export',
                           {'options': {'hosts': iID}, 'format': 'json'})
        dData = json.loads(dCfg['result'])
        if dData['zabbix_export']['hosts'] is not None:
            lHosts.append(dData['zabbix_export']['hosts'][0])
    lHostData = []

    for dHost in lHosts:
        # lets access host configuration host-by-host
        # oLog.debug('*DBG* dHost is ' + str(dHost))
        # oLog.debug("Host fields are" +  ', '.join('{0}={1}'.format(a, b) for a, b in dHost.items()))
        # sName = dHost['name']
        sIP = 'IP.AD.RE.SS'
        sName = dHost['host']
        lInterfaces = dHost['interfaces']
        for dInt in lInterfaces:
            if dInt['default'] == '1':
                if dInt['useip'] == '1':
                    sIP = dInt['ip']
                else:
                    sIP = dInt['dns']
                break
        dInv = dHost.get('inventory', {})
        if len(dInv) > 0:
            sDesc = dInv['type_full']
            oLog.debug('Host is {} ({}) at IP'.format(sName, sDesc, sIP))
            sInvNo = dInv['asset_tag']
            if sInvNo != '':
                sSN = dInv['serialno_a']
                lAddrList = [
                    dInv['site_country'], dInv['site_zip'], dInv['site_state'], dInv['site_city'],
                    dInv['site_address_a'], dInv['site_address_b'], dInv['site_address_c'],
                    dInv['site_notes']]
                sAddr = ', '.join([s for s in lAddrList if s != ''])
                o_inv_host = InventoryHost(sName, sDesc, sIP, sInvNo, sSN, sAddr)
                o_inv_host.set_cfg(dConfig)
                o_inv_host.make_app_items(oAPI, oNewSend)
                lHostData.append(o_inv_host)
    oNewSend.send_values()
    return lHostData

if __name__ == '__main__':
    # main section
    # locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8')
    oLog = logging.getLogger('Create_Properties_Screen')
    logging.config.dictConfig(dConfig['Logs'])
    iRetCode = fi_do_the_work()

    exit()

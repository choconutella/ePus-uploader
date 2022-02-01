import cx_Oracle
import logging
import os
import configparser
from datetime import date
from hclab.uploader import Uploader

logging.basicConfig(filename=os.path.join(os.getcwd(),f"log\\log_result.log"),
                    level=logging.WARNING, 
                    format="%(asctime)s - %(levelname)s : %(message)s")

class Result(Uploader):
    def __init__(self,user,pswd,host,file):
        try:
            self.conn = cx_Oracle.connect(user,pswd,host)
            self.cursor = self.conn.cursor()
            logging.debug("Database connection successfully")  
        except:
            logging.warning("Cannot connect HCLAB Database")


        lines = configparser.ConfigParser(interpolation=None)
        lines.read(file)
        
        #OBR section
        obr = lines['OBR']
        self.pid  = obr['pid']
        self.apid = obr['apid'] if lines.has_option('OBR','apid') else ''
        self.pname = obr['pname']
        self.ptype = obr['ptype'] if lines.has_option('OBR','ptype') else ''
        self.birth_dt = obr['birth_dt'] if lines.has_option('OBR','birth_dt') else ''
        self.sex = obr['sex'] if lines.has_option('OBR','sex') else ''
        self.ono = obr['ono']
        self.lno = obr['lno']
        self.request_dt = obr['request_dt']
        self.specimen_dt = obr['specimen_dt'] if lines.has_option('OBR','specimen_dt') else ''
        self.specimen = obr['specimen'] if lines.has_option('OBR','specimen') else ''
        self.source = obr['source']
        self.clinician = obr['clinician']
        self.priority = obr['priority'] if lines.has_option('OBR','priority') else ''
        self.pstatus = obr['pstatus'] if lines.has_option('OBR','pstatus') else ''
        self.visitno = obr['visitno'] if lines.has_option('OBR','visitno') else ''
        self.site_id = obr['site_id'] if lines.has_option('OBR','site_id') else ''
        self.order_testid = obr['order_testid'].split('^')[0]
        self.order_testnm = obr['order_testid'].split('^')[1]
        self.obx = lines['OBX']


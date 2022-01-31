#!venv/scripts/pythonw.exe
import json
import threading
import logging
import os
import time
import configparser
from shutil import copy
from datetime import datetime
from tkinter import *
from hclab.result import Result
from hclab.test_detail import TestDetail

# setup logging environment
logging.basicConfig(filename=os.path.join(os.getcwd(),f"log\\log_result.log"),
                    level=logging.WARNING, 
                    format="%(asctime)s - %(levelname)s : %(message)s")


# ini variable from .ini file
config = configparser.ConfigParser()
config.read('application.ini')
api_dbuser = config['api']['user']
api_dbpass = config['api']['pass']
api_dbhost = config['api']['host']
api_dbname = config['api']['db']


class Process(Result):

    def __init__(self):
        super(Result,self).__init__("HIS Uploader - Result")
        self.__start_thread = True

        try:
            self.__thread = threading.Thread(target=self.check_result)
            self.__thread.start()

            super().run()

            self.__start_thread = False
        except:
            logging.warning("Cannot start Thread")


    def check_result(self):
        """
        Check file result at HL7_OUT folder
        if file .R01 exists, then process the file
        if other extension, file will be deleted
        """
        while True:
            self.label.config(text="Wait for Result...")
            for filename in os.listdir(self.resultdir):
                file = os.path.join(self.resultdir,filename)
                if os.path.isdir(file):
                    pass
                else:
                    if file.endswith('.R01'):
                        self.label.config(text=f"Processing {filename}")
                        self.post_result(file)
                    else:
                        os.remove(file)
            
            time.sleep(1)

            if self.__start_thread == False:
                break  


    def post_result(self,file:str):
        """
        File result will be inserted to HIS Result table
        :param file: Path of result file
        """

        result = Result(self.lis_user, self.lis_pswd, self.lis_host, file)

        ono = result.ono
        lno = result.lno

        counter = 1
        while 'obx'+str(counter) in result.obx:
            res = result.obx['obx'+str(counter)].split('|')
            test_cd = res[0]
            test_nm = res[1]
            data_type = res[2]
            status = res[7]
            result_value = ''

            # handle result MB
            if test_cd == 'MBFTR':
                test_cd = result.order_testid
                test_nm = result.order_testnm

            detail = TestDetail(self.lis_user, self.lis_pswd, self.lis_host, lno, test_cd)

            if status == 'I':
                #SET BLANK VALUE IF CURRENT TESTCODE ONLY CHECK-IN PROCESS
                unit = flag = ref_range = test_comment =  ''

            elif status == 'F':
                
                if detail.is_profile() :
                    #SET BLANK VALUE IF CURRENT TESTCODE IS PROFILE TEST
                    unit = flag = ref_range = test_comment =  ''
                
                else:
                    #ASSIGN RESULT PARAMETER VALUE 

                    result_value = res[3]                        
                    unit = res[4]
                    flag = res[5]
                    ref_range = res[6]
                    test_comment = res[8]

            disp_seq = detail.sequence + '_' + ('000'+str(counter))[-3:]

            specimen_cd = detail.checkin_code 
            specimen_nm = detail.checkin_name
            specimen_by_cd = detail.checkin_by_code
            specimen_by_nm = detail.checkin_by_name
            specimen_dt = result.specimen_dt
            release_by_cd = detail.release_by_code
            release_by_nm = detail.release_by_name
            release_on = detail.release_on
            authorise_by_cd = detail.authorise_by_code
            authorise_by_nm = detail.authorise_by_name
            authorise_on = detail.authorise_on
            phoned_by_cd = ""
            phoned_by_nm = ""
            phoned_on = ""

            counter += 1

        if os.path.exists(file):
            copy(file,os.path.join(self.temp_result,os.path.basename(file)))
            os.remove(file)
        else:
            logging.warning("RESULTEND-The file does not exist")
        

                    
process = Process()

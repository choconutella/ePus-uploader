#!venv/scripts/pythonw.exe
import json
import threading
import logging
import os
import time
import configparser
import http.client
import ssl
from shutil import copy
from datetime import datetime
from tkinter import *
from hclab.result import Result
from hclab.test_detail import TestDetail

# setup logging environment
logging.basicConfig(filename=os.path.join(os.getcwd(),f"log\\log_result.log"),
                    level=logging.WARNING, 
                    format="%(asctime)s - %(levelname)s : %(message)s")

class Process(Result):

    def __init__(self):
        super(Result,self).__init__("HIS Uploader - Result")
        self.__start_thread = True

        self.config = configparser.ConfigParser()
        self.config.read('application.ini')
        
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
                        self.get_data_result(file)
                    else:
                        os.remove(file)
            
            time.sleep(1)

            if self.__start_thread == False:
                break  
    

    def post_result(self, ono, results:dict):
        conn = http.client.HTTPSConnection(self.config['api']['host'], context = ssl._create_unverified_context())
        payload = {
            'penanggung_jawab' : {
                'penanggung_jawab_id' : self.config['person_in_charge']['expertise'],
                'pemeriksa_id' : self.config['person_in_charge']['validator']
            },
            'content' : {}
        }
        payload['content'].update(results)

        print(payload)

        headers = {
            'x-token': f'{self.config["token"]["key"]}',
            'x-username': f'{self.config["api"]["user"]}'
        }
        conn.request("POST", f"/v1/pemeriksaanlab/{ono}", json.dumps(payload), headers)
        res = conn.getresponse()
        data = res.read() 
        data_as_json = json.loads(data.decode("utf-8"))
        print(json.dumps(data_as_json,indent=3,sort_keys=True))
        

    def get_data_result(self,file:str):

        result = Result(self.lis_user, self.lis_pswd, self.lis_host, file)

        dict_results = {}

        counter = 1
        while 'obx'+str(counter) in result.obx:
            res = result.obx['obx'+str(counter)].split('|')
            test_cd = res[0]
            test_nm = res[1]
            data_type = res[2]
            status = res[7]
            result_value = unit = flag = ref_range = test_comment =  ''

            # handle result MB
            if test_cd == 'MBFTR':
                test_cd = result.order_testid
                test_nm = result.order_testnm

            detail = TestDetail(self.lis_user, self.lis_pswd, self.lis_host, result.lno, test_cd)


            if status == 'F':
                
                if not detail.is_profile() :
                    
                    #ASSIGN RESULT PARAMETER VALUE 
                    result_value = res[3]                        
                    unit = res[4]
                    flag = res[5]
                    ref_range = res[6]
                    test_comment = res[8]


                dict_result = {counter-1 : {'tarif' : '0', 'hasil' : result_value, 'nilai_normal' : ref_range, 'pemeriksaan' : detail.his_code}}

            counter += 1

        
        dict_results.update(dict_result)
        self.post_result(result.ono, dict_results)

        
        if os.path.exists(file):
            copy(file,os.path.join(self.temp_result,os.path.basename(file)))
            os.remove(file)
        else:
            logging.warning("RESULTEND-The file does not exist")
    
                    
process = Process()
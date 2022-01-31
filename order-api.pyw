#!.venv\scripts\python.exe
import logging
import configparser
import http.client
import ssl
import json
import os
from datetime import date, datetime
from hclab.order import Order

logging.basicConfig(filename=os.path.join(os.getcwd(),f"log\\log_order.log"),
                    level=logging.WARNING, 
                    format="%(asctime)s - %(levelname)s : %(message)s")


class Process(Order):

    def __init__(self):

        self.config = configparser.ConfigParser()
        self.config.read('application.ini')
        self.get_order()


    # get token
    def get_token(self):

        conn = http.client.HTTPSConnection(self.config['api']['host'], context = ssl._create_unverified_context())
        payload = ''
        headers = {
            'x-username': f'{self.config["api"]["user"]}',
            'x-password': f'{self.config["api"]["pass"]}'
        }
        conn.request("GET", "/v1/auth", payload, headers)
        res = conn.getresponse()
        data = res.read()
        data_as_json = json.loads(data.decode("utf-8"))

        key = data_as_json['content']['token']
        refresh = data_as_json['content']['token_refresh']
        expire = data_as_json['content']['token_expire']
        self.save_token_detail(key, refresh, expire) # save token
        

    # save token detail
    def save_token_detail(self, key, refresh, expire):

        self.config['token']['key'] = key
        self.config['token']['refresh'] = refresh
        self.config['token']['expire'] = expire
        with open('application.ini','w') as f:
            self.config.write(f)


    def is_get_new_token(self):
        
        if self.config['token']['key']=='' or self.config['token']['refresh']=='' or self.config['token']['expire']=='':
            return True
        
        today_time = datetime.now()
        refresh_time = datetime.strptime(self.config['token']['refresh'], '%Y-%m-%d %H:%M:%S')
        expire_time = datetime.strptime(self.config['token']['expire'], '%Y-%m-%d %H:%M:%S')
        if today_time > refresh_time or today_time > expire_time:
            return True

        return False

    
    def update_status(self,ono):

        conn = http.client.HTTPSConnection(self.config['api']['host'], context = ssl._create_unverified_context())
        payload = {
            "proses_flag" : "1"
        }
        headers = {
            'x-token': f'{self.config["token"]["key"]}',
            'x-username': f'{self.config["api"]["user"]}'
        }
        conn.request("PUT", f"/v1/orderlab/{ono}", payload, headers)
        res = conn.getresponse()
        data = res.read() 
        data_as_json = json.loads(data.decode("utf-8"))
        print(json.dumps(data_as_json,indent=3,sort_keys=True))


    # retrieve order
    def get_order(self):
        today = date.today().strftime('%d%m%Y')
        today = '27012022'
        
        if self.is_get_new_token():
            self.get_token()

        conn = http.client.HTTPSConnection(self.config['api']['host'], context = ssl._create_unverified_context())
        payload = ''
        headers = {
            'x-token': f'{self.config["token"]["key"]}',
            'x-username': f'{self.config["api"]["user"]}'
        }
        conn.request("GET", f"/v1/orderlabby/{today}/0", payload, headers)
        res = conn.getresponse()
        data = res.read()
        data_as_json = json.loads(data.decode("utf-8"))
        print(json.dumps(data_as_json,indent=3,sort_keys=True))

        if data_as_json['content']['total'] > 0:

            records = data_as_json['content']['data']
            for record in records:

                try:
                    
                    order = Order(user=self.config['lis']['user'],
                                pswd=self.config['lis']['pass'],
                                host=self.config['lis']['host'])
                    
                    order.ono = record['id_Order']
                    order.order_control = record['order_control']
                    order.pid = record['pasien']['id_Pasien'].lstrip('0')
                    order.apid = record['pasien']['nik'].lstrip('0')
                    order.pname = record['pasien']['nama'].replace("'","`").strip()
                    order.address1 = record['pasien']['alamat'].replace("'","`").strip()[:50]
                    order.address2 = (record['pasien']['kelurahan'] + '-' + record['pasien']['kecamatan']).replace("'","`").strip()[:50]
                    order.address3 = ''
                    order.address4 = ''
                    order.ptype = record['tipe_pasien']
                    birth_dt = record['pasien']['tanggal_lahir']
                    order.birth_dt = birth_dt[-4:] + birth_dt[3:5] + birth_dt[:2] # yyyymmdd
                    order.sex = record['pasien']['jenis_kelamin']
                    order.lno = ''
                    order_dt = record['trx_dt']
                    order.message_dt = order_dt[6:10] + order_dt[3:5] + order_dt[:2] + order_dt[11:13] + order_dt[14:16] + order_dt[17:19] # yyyymmddhh24miss
                    order.source = record['ruangan_pengirim']['id_ruangan'][:15] + '^' + record['ruangan_pengirim']['nama_ruangan'][:50]
                    order.clinician = record['dokter_pengirim']['id_dokter'][:15] + '^' + record['dokter_pengirim']['nama_dokter'][:50]
                    order.room_no = ''
                    order.priority = record['priority']
                    order.pstatus = ''
                    order.comment = record['diagnosa_klinis']
                    order.visitno = record['id_kunjungan']
                    order.his_testid = record['order_test']
                    order.test_mapping(record['order_test'],'~')
                    order.save()

                    self.update_status(record['id_Order'])

                except Exception as e:
                    logging.warning(e)
        print(f'\n\nProcessing {data_as_json["content"]["total"]}')

process = Process()
input('Press any key for continue...')

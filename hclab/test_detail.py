import os
import cx_Oracle
import logging
from hclab.uploader import Uploader

logging.basicConfig(filename=os.path.join(os.getcwd(),f"log\\log_result.log"),
                    level=logging.WARNING, 
                    format="%(asctime)s - %(levelname)s : %(message)s")

class TestDetail(Uploader):
    def __init__(self,user,pswd,host, lno, test_cd):
        try:
            self.conn = cx_Oracle.connect(user,pswd,host)
            self.cursor = self.conn.cursor()
            logging.debug("Database connection successfully")  
        except:
            logging.warning("Cannot connect HCLAB Database")

        self.test_cd = test_cd
        self.lno = lno
        self.get_item_parent()
        self.get_test_group()
        self.get_test_sequence()
        self.get_checkin_data()
        self.get_release_data()
        self.get_authorise_data()
        self.get_test_method()

    def is_profile(self):
        category = 'U'
        sql = f"""
            select ti_category from test_item where ti_code = '{self.test_cd}'
        """
        try:
            self.cursor.execute(sql)
            data = self.cursor.fetchone()
            if data is not None:
                category = data[0]

        except cx_Oracle.DatabaseError as e:
            logging.warning(f"RESULT004-Error while item category. {e}")

        if category == 'P':
            return True
        return False

    def get_item_parent(self):
        self.parent = ''
        sql = f"""
            select od_item_parent from ord_dtl where od_testcode = '{self.test_cd}' and od_tno = '{self.lno}'
        """
        try:
            self.cursor.execute(sql)
            data = self.cursor.fetchone()
            if data is not None:
                self.parent = data[0]
            
        except cx_Oracle.DatabaseError as e:
            logging.warning(f"RESULT002-Error while check item parent. {e}")
        

    def get_test_group(self):
        self.group_code = ''
        self.group_name = ''
        sql = f"""
            select tg_code, tg_name 
            from test_group where 
            tg_code in(select ti_test_grp from test_item where ti_code = '{self.test_cd}')
        """
        try:
            self.cursor.execute(sql)
            data = self.cursor.fetchone()
            if data is not None:
                self.group_code = data[0]
                self.group_name = data[1]
            else:
                self.group_code = None
                self.group_name = None
        except cx_Oracle.DatabaseError as e:
            logging.warning(f"RESULT001-Cannot get test group. {e}")


    def get_test_sequence(self):
        sql = f"""
            select tg_ls_code, ti_disp_seq 
            from test_item 
            join test_group on ti_test_grp = tg_code
            where ti_code = '{self.test_cd}'
        """
        try:
            self.cursor.execute(sql)
            data = self.cursor.fetchone()
            if data is not None:
                self.sequence = ('000'+str(data[0]))[-3:] + '_' + ('000'+str(data[1]))[-3:] 
            else:
                self.sequence = '000_000'
            
        except cx_Oracle.DatabaseError as e:
            logging.warning(f"RESULT001-Cannot get sequence. {e}")


    def get_checkin_data(self, sp_on='', sp_code='', sp_name=''):
        self.checkin_code = ''
        self.checkin_name = ''
        self.checkin_on = ''
        self.checkin_by_code = ''
        self.checkin_by_name = ''
        sql = f"""
            select os_spl_type, st_name, to_char(os_spl_rcvdt,'yyyymmddhh24miss'), os_update_by, user_name
            from ord_spl
            join ord_dtl on os_tno = od_tno and os_spl_type = od_spl_type
            join user_account on os_update_by = user_id
            join sample_type on st_code = os_spl_type
            where os_tno = '{self.lno}'
            and od_testcode = '{self.test_cd}'
        """
        print(sql)
        try:
            self.cursor.execute(sql)
            data = self.cursor.fetchone()
            if data is not None:
                self.checkin_code = sp_code if sp_code != '' else data[0]
                self.checkin_name = sp_name if sp_name != '' else data[1]
                self.checkin_on = sp_on if sp_on != '' else data[2]
                self.checkin_by_code = data[3]
                self.checkin_by_name = data[4]  

        except cx_Oracle.DatabaseError as e:
            logging.warning(f"RESULT001-Cannot get check-in data. {e}")

    def get_release_data(self):
        self.release_by_code = ''
        self.release_by_name = ''
        self.release_on = ''

        sql = f"""
            select el_userid, user_name, max(to_char(el_datetime,'yyyymmddhh24miss'))
            from eventlog
            join user_account on user_id = el_userid 
            where el_tno = '{self.lno}' 
            and el_ev_code = 'L06' 
            and substr(el_comment,0,length('{self.test_cd}')) = '{self.test_cd}'
            group by el_userid, user_name
        """
        print(sql)
        try:
            self.cursor.execute(sql)
            data = self.cursor.fetchone()
            if data is not None:
                self.release_by_code = data[0]
                self.release_by_name = data[1]
                self.release_on = data[2]


        except cx_Oracle.DatabaseError as e:
            logging.warning(f"RESULT001-Cannot get check-in data. {e}")

    def get_authorise_data(self):
        self.authorise_by_code = ''
        self.authorise_by_name = ''
        self.authorise_on = ''
        
        sql = f"""
            select el_userid, user_name, max(to_char(el_datetime,'yyyymmddhh24miss'))
            from eventlog
            join user_account on user_id = el_userid 
            where el_tno = '{self.lno}' 
            and el_ev_code = 'L20' 
            and substr(el_comment,0,length('{self.test_cd}')) = '{self.test_cd}'
            group by el_userid, user_name
        """
        print(sql)
        try:
            self.cursor.execute(sql)
            data = self.cursor.fetchone()
            if data is not None:
                self.authorise_by_code = data[0]
                self.authorise_by_name = data[1]
                self.authorise_on = data[2]
            
        except cx_Oracle.DatabaseError as e:
            logging.warning(f"RESULT001-Cannot get check-in data. {e}")

    def get_test_method(self):
        self.method = ''
        
        sql = f"""
            select tm_desc
            from test_item 
            join test_method on tm_code = ti_tm_code
            where ti_code = '{self.test_cd}'
        """
        try:
            self.cursor.execute(sql)
            data = self.cursor.fetchone()
            if data is not None:
                self.method = data[0]
            
        except cx_Oracle.DatabaseError as e:
            logging.warning(f"RESULT001-Cannot get test method data. {e}")
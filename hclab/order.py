import cx_Oracle
import logging
import os
from datetime import date
from hclab.uploader import Uploader

logging.basicConfig(filename=os.path.join(os.getcwd(),f"log\\log_order.log"),
                    level=logging.WARNING, 
                    format="%(asctime)s - %(levelname)s : %(message)s")

class Order(Uploader):
    def __init__(self,user,pswd,host):
        try:
            self.conn = cx_Oracle.connect(user,pswd,host)
            self.cursor = self.conn.cursor()
            logging.debug("Database connection successfully")  
        except:
            logging.debug("Cannot connect HCLAB Database")


    def save(self):
        self.insert_lisorders()
        self.create_hl7file()

    
    def is_exists(self): 
        """
        Check order whether exists in LIS_ORDER On HCLAB database
        based on ONO parameter
        """
        try:
            self.cursor.execute(f"""
                SELECT * FROM LISORDERS WHERE ONO = {self.ono}
            """)
            data = self.cursor.fetchone()

            if not data is None:
                return True
            else:
                return False
        except:
            logging.debug(f"Cannot check ONO : {self.ono} existed or not!")
            return False


    
    def test_mapping(self,testid,delimiter):
        """
        Process mapping test from HIS Code 
        and assign value mapped test to Order.order_testid

        :param testid: List of test that will be mapped on test_mapping
        :param delimiter: Delimiter each test 
        """
        his_tests = testid.split("~")

        #TRUNCATE EVERY TEMP TABLE EACH PROCESSING TRANSACTION
        try:
            self.cursor.execute("truncate table tmp_his_code")
            self.cursor.execute("truncate table tmp_ti_code")
            self.cursor.execute("truncate table tmp_ti_code1")
            self.cursor.execute("truncate table tmp_ti_code2")
            self.conn.commit()
        except cx_Oracle.DatabaseError as e:
            logging.error(f"Cannot trucate tmp table. {e}")


        #REPLACE TEST WITH HIS CODE INTO HCLAB CODE
        #1. INSERT HIS CODE INTO TMP_HIS_CODE TABLE
        #2. MAPPED HIS CODE WITH HCLAB CODE BASED ON TEST_MAPPING TABLE
        #3. CHECK DUPLICATE HCLAB CODE IN PROFILE OR PACKAGE ORDER
        for test in his_tests:
            try:
                self.cursor.execute("insert into tmp_his_code values (:test)",[test])
                self.conn.commit()
            except cx_Oracle.DatabaseError as e:
                logging.warning(f"Cannot insert into tmp_his_code. {e}")
        
        try:
            self.cursor.execute("""
                insert into tmp_ti_code select a.tm_ti_code
                from test_mapping a
                join tmp_his_code b on a.tm_his_code = b.tm_his_code
                where a.active_fl = 'Y'
            """)

            #INSERT ONO, HIS_CODE, LIS_CODE IN LISHISORDERS TABLE
            #FOR RETURN HIS CODE VALUE FOR RESULT PROCESS
            self.cursor.execute(f"""
                insert into lishisorders select
                '{self.ono}',a.tm_his_code,a.tm_ti_code
                from test_mapping a
                join tmp_his_code b on a.tm_his_code = b.tm_his_code
                where a.active_fl = 'Y'
            """)

            self.cursor.execute("insert into tmp_ti_code1 select tm_ti_code from tmp_ti_code")
            self.cursor.execute("insert into tmp_ti_code2 select tp_ti_code from test_profile where tp_code in (select tm_ti_code from tmp_ti_code1)")
            self.cursor.execute("insert into tmp_ti_code2 select imd_pkg_item from item_masterd where imd_pkg_code in (select tm_ti_code from tmp_ti_code1)")
            self.cursor.execute("insert into tmp_ti_code2 select tp_ti_code from test_profile where tp_code in (select tm_ti_code from tmp_ti_code2)")
            self.cursor.execute("insert into tmp_ti_code2 select tp_ti_code from test_profile where tp_code in (select tm_ti_code from tmp_ti_code2)")
            self.conn.commit()
            self.cursor.execute("select distinct tm_ti_code from tmp_ti_code1 where tm_ti_code not in(select tm_ti_code from tmp_ti_code2) order by tm_ti_code")
            
            records = self.cursor.fetchall()
            lis_tests = []
            for record in records:
                lis_tests.append(record[0])

            #ASSIGN MAPPED HCLAB TESTCODE INTO ORDER_TESTID VARIABLE
            self.order_testid = "~".join(lis_tests)

        except cx_Oracle.DatabaseError as e:
            logging.warning(f"Test mapping failed. {e}")


        #PROVIDE LOG FOR UNMAPPED HIS CODE
        try:
            self.cursor.execute("""
                select distinct tm_his_code 
                from tmp_his_code 
                where tm_his_code not in(select tm_his_code from test_mapping where active_fl = 'Y')
            """)
            tests = self.cursor.fetchall()
            if len(tests) > 0:
                for test in tests:
                    logging.warning(f"HIS Code {test[0]} not yet mapped")
                    self.cursor.execute(f"""
                        insert into sine_log_testmapping(his_code,trx_dt)
                        values('{test[0]}',sysdate)
                    """)
                self.conn.commit()
        except cx_Oracle.DatabaseError as e:
            logging.warning(f"Cannot check unmapping test. {e}")


    #INSERT INTO LISORDERS TABLE IN HCLAB DATABASE
    #PURPOSE : BACKUP DATA ORDER FROM HIS TABLE LIS_ORDER
    def insert_lisorders(self):
        try:
            self.cursor.execute("""
                SELECT * FROM LISORDERS WHERE ono = :ono
            """,[self.ono])
            data = self.cursor.fetchone()
            if not data is None:
                self.cursor.execute("""
                    DELETE FROM LISORDERS WHERE ono = :ono
                """,[self.ono])
            self.cursor.execute("""
                INSERT INTO LISORDERS (
                    id, MESSAGE_DT, ORDER_CONTROL, PID, APID, PNAME, ADDRESS1, ADDRESS2, ADDRESS3, ADDRESS4, 
                    PTYPE, BIRTH_DT, SEX, ONO, REQUEST_DT, SOURCE, CLINICIAN, ROOM_NO, PRIORITY, CMT, VISITNO, ORDER_TESTID 
                )VALUES(
                    :id, :message_dt, :order_control, :pid, :apid, :pname, :address1, :address2, :address3, :address4,
                    :pytpe, :birth_dt, :sex, :ono, :request_dt, :source, :clinician, :room_no, :priority, :cmt, :visitno, :order_testid
                )
            """,[
                None, self.message_dt, self.order_control, self.pid, self.apid, self.pname, self.address1, self.address2, self.address3, self.address4,
                self.ptype, self.birth_dt, self.sex, self.ono, self.message_dt, self.source, self.clinician, self.room_no, self.priority, self.comment, self.visitno, self.his_testid
            ])

        except cx_Oracle.DatabaseError as error:
            logging.error(error)
        
        self.conn.commit()
    

    #CREATE HL7 ORDER FILE AT TMP_MSG FOLDER (BACKUP FOLDER)
    #THEN COPIED TO HL7_IN FOLDER
    def create_hl7file(self):
        line = "[MSH]\n"
        line = line + "message_id=O01\n"
        line = line + f"message_dt={self.message_dt}\n"
        line = line + "version=2.3\n"
        line = line + "[OBR]\n"
        line = line + f"order_control={self.order_control}\n"
        line = line + f"pid={self.pid}\n"
        line = line + f"apid={self.apid}\n"
        line = line + f"pname={self.pname}\n"
        line = line + f"address={self.address1}^{self.address2}^{self.address3}^{self.address4}\n"
        line = line + f"ptype={self.ptype}\n"
        line = line + f"birth_dt={self.birth_dt}\n"
        line = line + f"sex={self.sex}\n"
        line = line + f"ono={self.ono}\n"
        line = line + f"lno={self.lno}\n"
        line = line + f"request_dt={self.message_dt}\n"
        line = line + f"source={self.source}\n"
        line = line + f"clinician={self.clinician}\n"
        line = line + f"room_no={self.room_no}\n"
        line = line + f"priority={self.priority}\n"
        line = line + f"pstatus={self.pstatus}\n"
        line = line + f"comment={self.comment}\n"
        line = line + f"visitno={self.visitno}\n"
        line = line + f"order_testid={self.order_testid}\n"
        
        try:
            dest = os.path.join(self.destdir,f"{self.ono[8:]}_{self.message_dt}.txt")
            temp_msg = os.path.join(self.temp_order,f"{self.ono[8:]}_{self.message_dt}.txt")

            with open(temp_msg,"w") as f:
                f.writelines(line)

            logging.debug(f"Create file order ONO : {self.ono} successfully")

            try:
                os.popen(f"copy {temp_msg} {dest}")
            except:
                logging.error(f"Cannot copy ONO : {self.ono}")

        except:
            logging.error(f"Cannot create file order ONO : {self.ono}")


if __name__ == "__main__" :
    order = Order("hclab","hclab","localhost/hclab")
    order.message_dt = '20210126144210'
    order.order_control = 'NW'
    order.pid = '12345'
    order.apid = ''
    order.pname = 'TESTING'
    order.address1 = 'Jl. Jankes AD No. 1'
    order.address2 = ''
    order.address3 = ''
    order.address4 = ''
    order.ptype = 'IP'
    order.birth_dt = '19891108'
    order.sex = '1'
    order.ono = '9911234'
    order.lno = ''
    order.request_dt = '20210126144210'
    order.source = 'IGD^IGD'
    order.clinician = 'C0001^dr. Elsa'
    order.room_no = ''
    order.priority = 'R'
    order.pstatus = ''
    order.comment = ''
    order.visitno = '1000023'
    order.order_testid = 'AST~ALT~'
    order.create_hl7file()


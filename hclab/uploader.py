import configparser
from tkinter import *
import json

class Uploader:
    def __init__(self,title):
        self.getApplication()
        
        self.root = Tk()
        self.root.title(title)
        self.root.geometry("570x200")
        self.root.resizable(0,0)

        self.label = Label(self.root,anchor="e",font=("Courier",11))
        self.label.grid(row=1,column=1,padx=2,pady=5,sticky=W+E)
        self.label.config(text="Starting...")
    
    def run(self):
        self.root.mainloop()

    def showMessage(self,msg):
        self.label.config(text=msg)

    def getApplication(self):
        #GET SETTING FROM APPLICATION.JSON FILE
        config = configparser.ConfigParser()
        config.read('application.ini')

        #HCLAB DATABASE CONFIGURATION
        self.lis_user = config["lis"]["user"]
        self.lis_pswd = config["lis"]["pass"]
        self.lis_host = config["lis"]["host"]

        #API CONFIGURATION
        self.his_user = config["api"]["user"]
        self.his_pswd = config["api"]["pass"]
        self.his_host = config["api"]["host"]

        #FILE PATH CONFIGURATION
        self.destdir = config["file"]["order"]
        self.temp_order = config["file"]["temp_order"]
        self.resultdir= config["file"]["result"]
        self.temp_result = config["file"]["temp_result"]
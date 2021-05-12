# model class for setting and getting configuration
class Model:
    def __init__(self):
        pass

    # configuration default values
    __appEUI = ""
    __appKey = ""
    __devEUI = ""
    __accessKey = ""
    __appId = ""

    __raspberryIP = ""
    __username = ""
    __password = ""
    __noOfRuns = 0
    __ul_interval = 0
    __dl_interval = 0
    __adapt_int = 0
    __error_flag = 0
    __db_host = ""
    __db_name = ""

    # Getters
    def get_appeui(self):
        return self.__appEUI

    def get_appkey(self):
        return self.__appKey

    def get_deveui(self):
        return self.__devEUI

    def get_acceskey(self):
        return self.__accessKey

    def get_appid(self):
        return self.__appId

    def get_rasperryip(self):
        return self.__raspberryIP

    def get_username(self):
        return self.__username

    def get_password(self):
        return self.__password

    def get_noofruns(self):
        return self.__noOfRuns

    def get_ul_interval(self):
        return self.__ul_interval

    def get_dl_interval(self):
        return self.__dl_interval

    def get_error_flag(self):
        return self.__error_flag

    def get_db_host(self):
        return self.__db_host

    def get_db_name(self):
        return self.__db_name

    def get_adapt_int(self):
        return self.__adapt_int


    # Setters
    def set_appeui(self, param):
        self.__appEUI = param

    def set_appkey(self, param):
        self.__appKey = param

    def set_deveui(self, param):
        self.__devEUI = param

    def set_acceskey(self, param):
        self.__accessKey = param

    def set_appid(self, param):
        self.__appId = param

    def set_rasperryip(self, param):
        self.__raspberryIP = param

    def set_username(self, param):
        self.__username = param

    def set_password(self, param):
        self.__password = param

    def set_noofruns(self, param):
        self.__noOfRuns = param

    def set_ul_interval(self, param):
        self.__ul_interval = param

    def set_dl_interval(self, param):
        self.__dl_interval = param

    def set_error_flag(self, param):
        self.__error_flag = param

    def set_db_host(self, param):
        self.__db_host = param

    def set_db_name(self, param):
        self.__db_name = param

    def set_adapt_int(self, param):
        self.__adapt_int = param

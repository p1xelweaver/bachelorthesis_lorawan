from model import Model
from view import View
import paramiko
import threading

# open SSH client
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())


class Controller:
    def __init__(self):
        self.__model = Model()
        self.__view = View(self, self.__model)

    def main(self):
        # start view
        self.__view.main()

    def start_framework(self):
        self.__view.ssh_window()

    # method to fetch ssh credentials from GUI
    def fetch_ssh_data(self, entries):
        raspberry_ip = entries[0][1].get()
        username = entries[1][1].get()
        password = entries[2][1].get()

        self.__model.set_rasperryip(raspberry_ip)
        self.__model.set_username(username)
        self.__model.set_password(password)

        # start thread for ssh connection in background
        threading.Thread(target=self.infobox_connect_to_rpi()).start()

    # method to fetch device credentials from GUI
    def fetch_device_data(self, entries):
        appeui = entries[0][1].get()
        appkey = entries[1][1].get()
        deviceeui = entries[2][1].get()
        accesskey = entries[3][1].get()
        appid = entries[4][1].get()

        # check if entries match required length
        if len(appeui) != 16 or len(appkey) != 32 or len(deviceeui) != 16:
            self.__view.open_warning_message("otaa")
        else:
            self.__model.set_appeui(appeui)
            self.__model.set_appkey(appkey)
            self.__model.set_deveui(deviceeui)
            self.__model.set_acceskey(accesskey)
            self.__model.set_appid(appid)
            threading.Thread(target=self.infobox_activate_otaa()).start()

    # method to fetch configuration for measurement from GUI
    def fetch_measurement(self, entries, adapt_int):
        for entry in entries:
            field = entry[0]
            text = entry[1].get()
            print('%s: "%s"' % (field, text))

        no_of_runs = entries[0][1].get()
        ul_interval = entries[1][1].get()
        dl_interval = entries[2][1].get()
        adapt_interval = adapt_int.get()

        self.__model.set_noofruns(no_of_runs)
        self.__model.set_dl_interval(dl_interval)
        self.__model.set_ul_interval(ul_interval)
        self.__model.set_db_host(entries[3][1].get())
        self.__model.set_db_name(entries[4][1].get())
        self.__model.set_adapt_int(adapt_interval)

        # start thread to start measurement
        threading.Thread(target=self.infobox_start_measurement()).start()

    def infobox_connect_to_rpi(self):
        self.__view.open_infobox("ssh")
        chk = self.__model.get_error_flag()
        if chk == 0:
            self.__view.device_window()

    def infobox_activate_otaa(self):
        self.__view.open_infobox("otaa")
        chk = self.__model.get_error_flag()
        if chk == 0:
            self.__view.measurement_window()

    def infobox_start_measurement(self):
        self.__view.open_infobox("measure")


if __name__ == '__main__':
    c = Model()
    controller = Controller()
    # this main call, calls the main of view and starts gui
    controller.main()
    raise SystemExit

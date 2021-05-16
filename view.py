# GUI for LoRaWAN framework
# Author Gudrun Huszar
# Jan. 2021

import tkinter as tk
from tkinter import ttk
import time
import threading
import pysftp
import paramiko
import logging

# define fields for configuration form
ssh_fields = 'Raspberry Pi IP:', 'Username:', 'Password:'
device_fields = 'App EUI:', 'App Key:', 'Device EUI:', 'Access Key:', 'App ID: '
measurement_fields = 'No. of runs:', 'Uplink Interval:', 'Downlink Interval: ', 'Database Host: ', 'Database Name: '

# initialize SSH client for connection to RPI
PORT = 22
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

# set up logger
rpi_logger = logging.getLogger('Communication RPi')
nwserver_logger = logging.getLogger('Communication NW Server')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh = logging.FileHandler('framework.log')
fh.setFormatter(formatter)
fh.setLevel(logging.INFO)
rpi_logger.addHandler(fh)
nwserver_logger.addHandler(fh)

# detailed ssh logger
paramiko.util.log_to_file('paramiko.log')


class SSHThread(threading.Thread):
    """
    thread class for executing SSH connection to RPi
    """
    def __init__(self, model, view):
        super().__init__()
        self.model = model
        self.view = view

    def run(self):
        self.model.set_error_flag(0)
        try:
            raspberry_ip = self.model.get_rasperryip()
            username = self.model.get_username()
            password = self.model.get_password()
            ssh.connect(raspberry_ip, PORT, username, password)
            cnopts = pysftp.CnOpts()
            cnopts.hostkeys = None

            stdin, stdout, stderr = ssh.exec_command("sudo reboot")

            time.sleep(60)

            # Make connection to sFTP
            with pysftp.Connection(raspberry_ip,
                                   username=username,
                                   password=password,
                                   cnopts=cnopts
                                   ) as sftp:
                sftp.put('connect_stick_otaa.py')
                sftp.put('monitor_parameters.py')
                sftp.put('mqtt_grafana.py')

            # sftp.close()
            print("done with SSH")
        except Exception as e:
            rpi_logger.error("SSH connection failed")
            rpi_logger.error(e)
            self.model.set_error_flag(-1)


class OTAAThread(threading.Thread):
    """
    thread class for executing OTAA script
    """
    def __init__(self, model, view):
        super().__init__()
        self.model = model
        self.view = view

    def run(self):
        self.model.set_error_flag(0)
        raspberry_ip = self.model.get_rasperryip()
        username = self.model.get_username()
        password = self.model.get_password()
        dev_eui = self.model.get_deveui()
        app_eui = self.model.get_appeui()
        app_key = self.model.get_appkey()

        try:
            self.model.set_error_flag(0)
            ssh.connect(raspberry_ip, PORT, username, password)
            cnopts = pysftp.CnOpts()
            cnopts.hostkeys = None

            # execute connection via OTAA
            stdin, stdout, stderr = ssh.exec_command(
                "nohup python connect_stick_otaa.py --appeui " + app_eui + " --appkey " + app_key + " --deveui " + dev_eui + "&> connection.log &")

            time.sleep(60)

            # look if connection script is still running. otherwise it is expected to be done
            stdin, stdout, stderr = ssh.exec_command("ps -aef | grep connect_stick_OTAA.py")
            tmp = stdout.readlines()
            connecting = len(tmp)
            i = 0
            while (connecting > 2) and (i <= 2):
                time.sleep(30)
                stdin, stdout, stderr = ssh.exec_command("ps -aef | grep connect_stick_OTAA.py")
                tmp = stdout.readlines()
                connecting = len(tmp)
                i += 1
            if i > 2:
                rpi_logger.error("OTAA failed")
                self.model.set_error_flag(-1)
        except Exception as e:
            nwserver_logger.error("OTAA failed")
            nwserver_logger.error(e)
            self.model.set_error_flag(-1)
        rpi_logger.info("OTAA successful")


class MeasurementThread(threading.Thread):
    """
    thread class for executing measurement script on RPI
    """
    def __init__(self, model, view):
        super().__init__()
        self.model = model
        self.view = view

    def run(self):
        self.model.set_error_flag(0)
        raspberry_ip = self.model.get_rasperryip()
        username = self.model.get_username()
        password = self.model.get_password()
        no_of_runs = self.model.get_noofruns()
        ul_interval = self.model.get_ul_interval()
        dl_interval = self.model.get_dl_interval()
        adapt_int = self.model.get_adapt_int()
        device_eui = self.model.get_deveui()
        db_host = self.model.get_db_host()
        db_name = self.model.get_db_name()
        app_id = self.model.get_appid()
        access_key = self.model.get_acceskey()

        try:
            ssh.connect(raspberry_ip, PORT, username, password)
            cnopts = pysftp.CnOpts()
            cnopts.hostkeys = None

            # execute measurement script
            ssh.exec_command(
                "nohup python monitor_parameters.py --runs " + no_of_runs + " --ul_interval " + ul_interval +
                " --dl_interval " + dl_interval + " --deveui " + device_eui + " --adapt_int " + str(adapt_int) +
                " --db_host " + db_host + " --db_name " + db_name + " &> monitoring.log &")

            # execute mqtt measurement script
            if db_name is not "" and db_host is not "":
                ssh.exec_command("nohup python mqtt_grafana.py  --appid " + app_id +
                                 " --accesskey " + access_key + " --deveui " + device_eui +
                                 " --db_host " + db_host + " --db_name " + db_name +
                                 " &> mqttLog_" + db_name + ".log &")
            else:
                nwserver_logger.error("No data base specified")
                self.model.set_error_flag(-1)

            time.sleep(120)

            # check if mqtt script was started
            stdin, stdout, stderr = ssh.exec_command("ps -aef | grep mqtt_grafana")
            chk = stdout.readlines()
            if len(chk) < 3:
                nwserver_logger.error("MQTT connection failed")
                self.model.set_error_flag(-1)
        except Exception as e:
            nwserver_logger.error(e)
            nwserver_logger.error("Measurement failed")
        nwserver_logger.info("Measurement started")


class View(tk.Tk):
    """
    class for starting Graphical User Interface
    """
    def __init__(self, clean_controller, model):
        super().__init__()
        self.controller = clean_controller
        self.model = model

        self.title("LoRa Test Framework")
        self._make_main_frame()
        self._make_start_button()

    def main(self):
        self.mainloop()

    def _make_main_frame(self):
        self.main_frm = ttk.Frame(self)
        self.main_frm.pack(padx=10, pady=10)

    def _make_start_button(self):
        frm = ttk.Frame(self.main_frm)
        frm.pack()

        header_var = tk.StringVar()
        text_var = tk.StringVar()
        header = tk.Label(frm, textvariable=header_var, font="Verdana 10 bold")
        header_var.set("Welcome to the LoRaWAN Test Framework")
        header.pack()

        welcome_text = tk.Label(frm, textvariable=text_var, font="Veranda 10")
        text_var.set(
            "Before starting the framework make sure you have installed your hardware like specified "
            "and prepare your credentials. \n ")
        welcome_text.pack()

        ttk.Button(frm, text="Start Framework", command=lambda: self.controller.start_framework()).pack()

    def ssh_window(self):
        """
            open window for SSH configuration
        """
        self.destroy()
        root = tk.Tk()
        root.title("SSH Configuration")
        root.conf_frame = ttk.Frame(root)
        root.conf_frame.pack(padx=10, pady=10)
        config_inputs = self._make_ssh_data_inputs(root)
        root.bind('<Return>', (lambda event, e=config_inputs: self.controller.fetch_ssh_data(e)))
        button_ssh = tk.Button(root.conf_frame, text='Configure SSH',
                               command=(lambda e=config_inputs: self.controller.fetch_ssh_data(e)))
        button_ssh.pack(side=tk.LEFT, padx=5, pady=5)
        button_quit = tk.Button(root.conf_frame, text='Quit', command=root.conf_frame.quit)
        button_quit.pack(side=tk.RIGHT, padx=5, pady=5)

    @staticmethod
    def _make_ssh_data_inputs(root):
        """
         built ssh data input GUI
        """
        outer_frm = ttk.Frame(root.conf_frame)
        outer_frm.pack()

        frm = ttk.Frame(outer_frm)
        frm.pack()

        entries = []
        for field in ssh_fields:
            row = tk.Frame(frm)
            lab = tk.Label(row, width=15, text=field, anchor='w', font="Verdana 10 bold")
            ent = tk.Entry(row)
            row.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
            lab.pack(side=tk.LEFT)
            ent.pack(side=tk.RIGHT, expand=tk.YES, fill=tk.X)
            entries.append((field, ent))
        return entries

    def open_infobox(self, initiator):
        """
        initiate thread while showing an infobox
        """
        global t
        if initiator == "ssh":
            t = SSHThread(self.model, self)
            t.start()
        elif initiator == "otaa":
            t = OTAAThread(self.model, self)
            t.start()
        elif initiator == "measure":
            t = MeasurementThread(self.model, self)
            t.start()
        infobox = tk.Tk()
        infobox.title('Information')
        infobox.geometry("300x100")
        tk.Message(infobox, text="Configuring... \n Please wait \n ", padx=20, pady=20, font="Verdana 10 bold",
                   anchor='center').pack()
        while t.isAlive():
            infobox.update()
        infobox.destroy()
        # show warning or error if something went wrong
        chk = self.model.get_error_flag()
        if chk != 0:
            if initiator == "ssh":
                self.open_warning_message("ssh")
            else:
                self.open_error_messagebox()
        # all configurations are done. Close program
        elif initiator == "measure" and chk == 0:
            closing_window = tk.Tk()
            closing_window.title("Done")

            closing_window.button_frame = ttk.Frame(closing_window)
            closing_window.button_frame.pack(padx=10, pady=10)

            label_end = tk.Label(closing_window.button_frame,
                                 text='Your measurement was started. \n  '
                                      'Depending on your configuration this takes some time. '
                                      '\n Your measurments will be stored to your data base \n'
                                      'You can close the application now.')
            label_end.pack(side=tk.TOP, padx=5, pady=5)
            button_end = tk.Button(closing_window.button_frame, text='Quit', command=closing_window.button_frame.quit)
            button_end.pack(side=tk.LEFT, padx=5, pady=5)

    def device_window(self):
        """
        open window for device configuration
        """
        print("Opening device window")
        dev_window = tk.Tk()
        dev_window.title("Device Configuration")
        dev_window.device_frame = ttk.Frame(dev_window)
        dev_window.device_frame.pack(padx=10, pady=10)

        config_inputs = self._make_device_config_inputs(dev_window)
        b1 = tk.Button(dev_window.device_frame, text='Configure device',
                       command=(lambda e=config_inputs: self.controller.fetch_device_data(e)))
        b1.pack(side=tk.LEFT, padx=5, pady=5)
        b2 = tk.Button(dev_window.device_frame, text='Quit', command=dev_window.destroy)
        b2.pack(side=tk.RIGHT, padx=5, pady=5)

    @staticmethod
    def _make_device_config_inputs(dev_window):
        """
        built device data input GUI
        """
        outer_frm = ttk.Frame(dev_window.device_frame)
        outer_frm.pack()
        frm = ttk.Frame(outer_frm)
        frm.pack()
        entries = []
        for field in device_fields:
            if field == "Raspberry Pi IP:":
                separator = ttk.Separator(frm, orient=tk.HORIZONTAL)
                separator.pack(side='top', fill='x', padx=10, pady=10)

                ttk.Label(frm, text="Configure SSH connection").pack()
            elif field == "Access Key:":
                separator = ttk.Separator(frm, orient=tk.HORIZONTAL)
                separator.pack(side='top', fill='x', padx=10, pady=10)

                ttk.Label(frm, text="If you are using TTN to collect gateway data, \n"
                                    "please enter the credentials of your application", font="Verdana 10 bold",
                          anchor='c').pack()
            row = tk.Frame(frm)
            lab = tk.Label(row, width=15, text=field, font="Verdana 10 bold", anchor='w')
            ent = tk.Entry(row)
            row.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
            lab.pack(side=tk.LEFT)
            ent.pack(side=tk.RIGHT, expand=tk.YES, fill=tk.X)
            entries.append((field, ent))
        return entries

    def measurement_window(self):
        """
        open window for measurement configuration
        """
        measurement_window = tk.Toplevel()
        measurement_window.title("Measurement Configuration")
        measurement_window.measurement_frame = ttk.Frame(measurement_window)
        measurement_window.measurement_frame.pack(padx=10, pady=10)
        outer_frm = ttk.Frame(measurement_window.measurement_frame)
        outer_frm.pack()

        frm = ttk.Frame(outer_frm)
        frm.pack()
        config_inputs = self._make_measurement_config_inputs(outer_frm)

        adapt_int = tk.IntVar()
        tk.Checkbutton(outer_frm, text="Decrease Interval", variable=adapt_int, font="Verdana 10").pack()
        b1 = tk.Button(outer_frm, text='Configure run',
                       command=(lambda e=config_inputs: self.controller.fetch_measurement(e, adapt_int)))
        b1.pack(side=tk.LEFT, padx=5, pady=5)
        b2 = tk.Button(outer_frm, text='Quit', command=measurement_window.destroy)
        b2.pack(side=tk.RIGHT, padx=5, pady=5)

    @staticmethod
    def _make_measurement_config_inputs(frm):
        """
        built measurement data input GUI
        """
        entries = []
        for field in measurement_fields:
            row = tk.Frame(frm)
            lab = tk.Label(row, width=15, text=field, anchor='w', font="Verdana 10 bold")
            ent = tk.Entry(row)
            row.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
            lab.pack(side=tk.LEFT)
            ent.pack(side=tk.RIGHT, expand=tk.YES, fill=tk.X)
            entries.append((field, ent))
        return entries

    @staticmethod
    def open_error_messagebox():
        """
        built GUI with error information
        """
        error_window = tk.Toplevel()
        error_window.title("Error")
        error_window.geometry("300x100")
        error_window.measurement_frame = ttk.Frame(error_window)
        error_window.measurement_frame.pack(padx=10, pady=10)
        outer_frm = ttk.Frame(error_window.measurement_frame)
        outer_frm.pack()

        frm = ttk.Frame(outer_frm)
        frm.pack()
        text_var = tk.StringVar()
        info_text = tk.Label(frm, textvariable=text_var, font="Veranda 10 bold")
        text_var.set("An error occured. \n Please check logs. \n ")
        info_text.pack()
        button_end = tk.Button(error_window.measurement_frame, text='Quit', command=error_window.measurement_frame.quit)
        button_end.pack(side=tk.BOTTOM, padx=5, pady=5)

    @staticmethod
    def open_warning_message(initiator):
        """
        built GUI with warning
        """
        warning_window = tk.Toplevel()
        warning_window.title("Error")
        warning_window.geometry("300x100")
        warning_window.info_frm = ttk.Frame(warning_window)
        warning_window.info_frm.pack(padx=10, pady=10)
        outer_frm = ttk.Frame(warning_window.info_frm)
        outer_frm.pack()

        frm = ttk.Frame(outer_frm)
        frm.pack()
        text_var = tk.StringVar()
        info_text = tk.Label(frm, textvariable=text_var, font="Veranda 10 bold")

        if initiator == "ssh":
            text_var.set("SSH failed. \n Please check credentials and connection.")
        elif initiator == "otaa":
            text_var.set("Your keys do not match the required length. \n Please check them again. \n ")
        elif initiator == "interval":
            text_var.set("Uplink message interval \n has to be >= downlink message interval.")
        info_text.pack()
        button_end = tk.Button(warning_window.info_frm, text='Go Back', command=warning_window.destroy)
        button_end.pack(side=tk.BOTTOM, padx=5, pady=5)

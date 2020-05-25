import tkinter
from tkinter import ttk
import tkinter.messagebox
import subprocess
from threading import Thread
import os, glob
import time
import json
import requests
import re

class LabelEntry(tkinter.Frame):
    def __init__(self, label, var, validatetype = 'float', *args, **kwargs):
        tkinter.Frame.__init__(self, *args, **kwargs)
        self.label = label
        self.var = var
        self.columnconfigure(0, weight = 1)

        if validatetype == 'float':
            self.vcmd = (self.master.register(self.validate_float), '%P')
        elif validatetype == 'int':
            self.vcmd = (self.master.register(self.validate_int), '%P')
        elif validatetype == None:
            self.vcmd = None
        elif validatetype == 'basic':
            self.vcmd =  (self.master.register(self.validate_basic), '%P')
        else:
            raise ValueError('validatetype needs to be "float", "int", "basic" or None')

        self.TKLabel = tkinter.Label(self, text = label + '\t')
        self.TKEntry = tkinter.Entry(self, textvariable = self.var)
        if self.vcmd != None:
            self.TKEntry.configure(validate = 'key', validatecommand = self.vcmd)

        self.TKLabel.grid(row = 0, column = 0, sticky=tkinter.W)
        self.TKEntry.grid(row = 0, column = 1, sticky=tkinter.E)

        self.pack(fill = tkinter.BOTH, expand = True)

    def validate_float(self, new_value):
        try:
            float(new_value)
            return True
        except:
            return False

    def validate_int(self, new_value):
        try:
            int(new_value)
            if int(new_value) == new_value:
                return True
            else:
                return False
        except:
            return False

    def validate_basic(self, new_value):
        if re.match("^[\w\d_-]*$", new_value):
            return True
        else:
            return False

class GUI (tkinter.Frame):
    port_api = '7377'
    localhost_api = 'http://localhost:'+ port_api + '/api/'
    serverlist_filename = 'phantom.json'
    buffer_read_time = 500 #ms
    serverlist_filename = 'phantom.json'
    server_json = {"servers" : {}, "settings": {"apiPort" : port_api}}
    def __init__(self, *args, **kwargs):
        tkinter.Frame.__init__(self,*args,**kwargs)
        self.bindPort = 0
        self.path_to_phantom = self.search_phantom_exe()
        self.server_list = []
        self.linebuffer = []
        self.api_process = None
        self.server_var = tkinter.StringVar()
        self.server_var.set('000.000.00.00:0000')
        self.server_name_var = tkinter.StringVar()
        self.server_name_var.set('Server1')
        self.connect_button = tkinter.Button(text = 'connect!', command = self.spawn_new_phantom)
        self.connect_button.pack(fill = tkinter.BOTH, expand = True)
        self.server_ip_entry =  LabelEntry(label = 'server address:', var = self.server_var, validatetype = None, master = self)
        self.server_name_entry =  LabelEntry(label = 'server name:', var = self.server_name_var, validatetype = 'basic', master = self)
        self.tree = ttk.Treeview(self, columns =2, show = ['headings'])
        self.tree['columns'] = ['#1', '#2']
        self.tree.column('#1',width = 100)
        self.tree.column('#2', width = 20)
        self.tree.heading('#1',text='server IP',anchor = tkinter.W)
        self.tree.heading('#2',text='name',anchor = tkinter.W)
        self.tree.pack(fill = tkinter.BOTH, expand = True)

        self.remove_button =  tkinter.Button(text = 'remove selected server(s)', command = self.remove_selected)
        self.remove_button.pack(fill = tkinter.BOTH, expand = True)

        self.pack(fill = tkinter.BOTH, expand = True)
        self.start_phantom_api()
        self.get_serverlist()
        self.after(self.buffer_read_time, self.print_buffers)

        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)

    def spawn_new_phantom(self):
        if self.validate_servername():
            server_json = {
              "name": self.server_name_var.get(),
              "prefs": {
                "bindAddress": "0.0.0.0",
                "bindPort": 0,
                "remoteServer": self.server_var.get(),
                "idleTimeout": 0,
                "ipv6": False
              }
            }
            ans = requests.post(self.localhost_api + 'servers/' + self.server_name_var.get(), json = server_json)
            print(ans)
            if str(ans) == '<Response [201]>':
                requests.post(self.localhost_api + 'servers/' + self.server_name_var.get() + '/start')
                self.tree.insert("","end",text=self.server_name_var.get(), values = (self.server_var.get(), self.server_name_var.get()))
                self.server_list.append(server_json)
                self.server_json['servers'][server_json['name'].lower()] = server_json
            else:
                self.error_message('Server creation failed', 'Something went wrong creating the Server! Make sure your PC is connected to the internet and the server address is correct.\
                                    \n Hint: for URL formatted servers, try adding ":19132" to the end (that is a common port for minecraft servers)')

    def validate_servername(self):
        names = [server['name'] for server in self.server_list]
        if self.server_name_var.get() in names:
            self.error_message('Error', 'Please choose an unique servername!')
            return 0
        else:
            return 1

    def search_phantom_exe(self):
        cwd = os.path.dirname(os.path.realpath(__file__))
        os.chdir(cwd)
        path = ''
        for file in glob.glob("*.exe"):
            if "phantom" in file:
                path =  cwd + '\\' + file
                break
        if path == '':
            self.error_message('missing Phantom executable', "couldn't find Phantom executable! Please put it in the same directory as this program.")
            exit()
        return path

    def error_message(self,title,message):
        '''generates an error message-popup with generic title and message'''
        tkinter.messagebox.showerror(title,message)

    def start_phantom_api(self):
        process = subprocess.Popen([self.path_to_phantom, '-api'], stdout = subprocess.PIPE, stdin = subprocess.PIPE)
        self.api_process = process
        t=Thread(target=self.reader,args=(process.stdout,self.linebuffer))
        t.daemon=True
        t.start()
        time.sleep(1)
        while True:
            line = self.linebuffer.pop(0).decode('utf-8')
            print(line)
            if 'live' in line:
                break

    def print_buffers(self):
        self.after(self.buffer_read_time, self.print_buffers)
        while True:
            if self.linebuffer:
                line = self.linebuffer.pop(0).decode('utf-8')
                print(line)
            else:
                break

    def remove_selected(self):
        selection = self.tree.selection()
        for idx in selection:
            id = self.tree.index(idx)
            self.stop_phantom(self.server_list[id])
            self.tree.delete(idx)
            del self.server_json['servers'][self.server_list[id]['name'].lower()]
            del self.server_list[id]
            with open (self.serverlist_filename, 'w') as file:
                json.dump(self.server_json, file)



    def stop_phantom(self,server):
        servername = server['name']
        requests.delete(self.localhost_api + 'servers/' + servername)

    def get_serverlist(self):
        if os.path.isfile(self.serverlist_filename):
            with open(self.serverlist_filename, 'rb') as file:
                s_list = json.load(file)
                self.server_json = s_list
                self.server_list = [server for name,server in s_list['servers'].items()]

        for server in self.server_list:
            self.start_phantom(server)
            self.tree.insert("","end",text=server['name'], values = (server['prefs']['remoteServer'], server['name']))

    def start_phantom(self,server):
        servername = server['name']
        requests.post(self.localhost_api + 'servers/' + servername + '/start')

    @staticmethod
    def reader(f,buffer):
        while True:
            line=f.readline()
            if line:
                buffer.append(line)
            else:
                break

    def on_closing(self):
        self.api_process.terminate()
        self.master.quit()





if __name__ == '__main__':
    root = tkinter.Tk()
    root.title('Phantom for Minecraft')
    GUI(master = root)
    root.mainloop()

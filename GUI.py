import tkinter
from tkinter import ttk
import tkinter.messagebox
import subprocess
from threading import Thread
import os, glob
import time

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
        else:
            raise ValueError('validatetype needs to be "float", "int" or None')

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

class GUI (tkinter.Frame):
    def __init__(self, *args, **kwargs):
        tkinter.Frame.__init__(self,*args,**kwargs)

        columns = ['#0']
        column_names = ['server ip']

        self.path_to_phantom = self.search_phantom_exe()
        self.process_list = []
        self.server_list = []
        self.server_var = tkinter.StringVar()
        self.server_var.set('185.223.28.35:5060')
        self.connect_button = tkinter.Button(text = 'connect!', command = self.spawn_new_phantom)
        self.connect_button.pack(fill = tkinter.BOTH, expand = True)
        self.server_ip_entry =  LabelEntry(label = 'server address:', var = self.server_var, validatetype = None, master = self)
        self.tree = ttk.Treeview(self)
        self.tree.column('#0')
        self.tree.heading('#0',text='server IP',anchor = tkinter.W)
        self.tree.pack(fill = tkinter.BOTH, expand = True)

        self.remove_button =  tkinter.Button(text = 'remove selected server(s)', command = self.remove_selected)
        self.remove_button.pack(fill = tkinter.BOTH, expand = True)
        self.pack(fill = tkinter.BOTH, expand = True)
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)

    @staticmethod
    def reader(f,buffer):
        while True:
            line=f.readline()
            if line:
                buffer.append(line)
            else:
                break

    def spawn_new_phantom(self):
        linebuffer = []

        if self.server_var.get() in self.server_list:
            self.error_message('Error','server already in list!')
            return
        self.process_list.append(subprocess.Popen([self.path_to_phantom, '-server', str(self.server_var.get())], stdout = subprocess.PIPE))
        t=Thread(target=self.reader,args=(self.process_list[-1].stdout,linebuffer))
        t.daemon=True
        t.start()
        time.sleep(.1)
        log = ''
        while True:
            if linebuffer:
                line = linebuffer.pop(0).decode('utf-8')
                print(line)
                log = log + line
                if "failed" in line or "Failed" in line:
                    self.error_message('something went wrong', log)
                    self.process_list.pop(-1)
                    return
            else:
                break
        if log == '':
            self.error_message('error!', 'Phantom executable didnt respond in time, please restart the GUI')
        self.tree.insert("","end",text=self.server_var.get())
        self.server_list.append(self.server_var.get())

    def kill_phantom(self, id):
        self.process_list[id].kill()
        self.process_list.pop(id)
        self.server_list.pop(id)

    def search_phantom_exe(self):
        cwd = os.path.dirname(os.path.realpath(__file__))
        os.chdir(cwd)
        path = ''
        for file in glob.glob("*.exe"):
            if "phantom" in file:
                path =  cwd + '\\' + file
                break
        if path == '':
            self.error_message('missing Phantom executable', "couldn't find phantom executable! Please put it in the same directory as this program.")
            exit()
        return path

    def remove_selected(self):
        selection = self.tree.selection()
        for idx in selection:
            id = self.tree.index(idx)
            self.kill_phantom((id))
            self.tree.delete(idx)
        pass

    def error_message(self,title,message):
        '''generates an error message-popup with generic title and message'''
        tkinter.messagebox.showerror(title,message)

    def on_closing(self):
        for p in self.process_list:
            p.kill()
        self.master.destroy()



if __name__ == '__main__':
    root = tkinter.Tk()
    root.title('Phantom for Minecraft')
    GUI(master = root)
    root.mainloop()

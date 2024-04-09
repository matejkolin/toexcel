import re
import pandas as pd

import paramiko

import tkinter as tk
from tkinter import filedialog,messagebox
from datetime import date

from tqdm import tqdm
import time
import variables


class GetLog:
    def __init__(self):
        self.sshclient=self.sshConnect()
        self.sftp_client = self.sshclient.open_sftp()
        self.remote_file = None

    def sshConnect(self):
            client = paramiko.SSHClient()
            # client.load_system_host_keys()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            try:
                pubkey=variables.keypath
                private_key = paramiko.RSAKey(filename=pubkey)
            except Exception as e:
                messagebox.showerror("Public key error:",e)
                pubkey = filedialog.askopenfilename(title="Select public key", filetypes=[("Public keys", "*.pub")])
                private_key = paramiko.RSAKey(filename=pubkey)
                
            client.connect(variables.domain, port=variables.port, username=variables.user,pkey=private_key)
            return client

    def extract_resources(self,file, output_path):
        
        resource_dicts = []

        for line in file:
            if not line.strip():
                continue
            timestamp, orderNo, resource_data = line.strip().split("|")
            timestamp = timestamp.strip()

            resources = re.findall(r'Resources:{([^}]*(?:(?!Resources:).)*)}', resource_data)
            if resources:
                for resource in resources:
                    try:
                        resource_dict = {}
                        
                        resource_dict['Timestamp'] = timestamp
                        resource_dict['OrderNo'] = orderNo
                        resource_dict['ID'] = re.search(r'ID:(\d+)', resource).group(1)
                        resource_dict['CPU'] = re.search(r'CPU:units:<val:"([^"]+)"', resource).group(1)
                        resource_dict['Memory'] = re.search(r'Memory:quantity:<val:"([^"]+)"', resource).group(1)

                        dictionary_pattern = r'\{Name:(\w+) Quantity:{Val:(\d+)} Attributes:(\[\s*(?:\{(?:Key:\w+ Value:\w+)\}\s*)*\])\}'
                        storage_items = re.findall(dictionary_pattern, resource)
                        
                        gpus=re.search(r'GPU:units:<val:"([^"]+)"', resource)
                        gpuatr=re.search(r'GPU:units:<val:"[^"]+" > (attributes:<key:"[^"]+" value:"[^"]+" >)', resource)

                        if gpus:
                            resource_dict['GPUs'] = gpus.group(1)
                        else:
                            resource_dict['GPUs']=None
                        if gpuatr:
                            resource_dict['GPU type'] =  gpuatr.group(1)
                        else:
                            resource_dict['GPU type'] =None
                                                    
                        
                        for idx,storage_item in enumerate(storage_items,1):
                            name, quantity, attributes = storage_item

                            attributes_data = re.findall(r'\{Key:(\w+) Value:(\w+)\}', attributes)

                            resource_dict[f'Stor_name_{idx}'] = name
                            resource_dict[f'Stor_qty_{idx}'] = quantity
                            
                            if not attributes_data:
                                resource_dict[f'Stor_attr_{idx}']=None
                            else:
                                resource_dict[f'Stor_attr_{idx}'] = attributes_data


                        resource_dicts.append(resource_dict)

                    except Exception as e:
                        print(f'Exception2: ', e)
                        break


                df = pd.DataFrame(resource_dicts)

                df.to_csv(output_path, index=False)
            else:
                messagebox.showerror("Log file empty")


    def browse_files(self):
        root = tk.Tk()
        root.withdraw()  # hide main window

        file_source = tk.messagebox.askquestion("File Source", "Pull file from remote server?", icon='question')
        if file_source == 'yes':  
            try:
                file = self.pullFromScp()
            except Exception as e:
                messagebox.showerror("Error:",e)
                return None

        else:  # Local file
            file_path = filedialog.askopenfilename(title="Select Input Text File (Local file)", filetypes=[("Text files", "*.txt")])
            try:
                file=open(file_path,'r')
            except Exception as e:
                messagebox.showerror("Error:",e)
                return None

        if not file:
            messagebox.showerror("No input file selected. Exiting.")
            return

        # Prompt user to select output file
        today=date.today()
        output_path = filedialog.asksaveasfilename(title="Select Output CSV File", initialfile=f"{today}_akash-log.csv",defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if not output_path:
            messagebox.showerror("Error","No output file selected. Exiting.")
            return
        
        self.extract_resources(file, output_path)
        messagebox.showinfo("Extraction completed and saved to", output_path)

    def pullFromScp(self):
        try:
            self.remote_file = self.sftp_client.open(variables.logpath, 'r')
            return self.remote_file

        except Exception as e:
            messagebox.showerror("Error:", e)
        return None, None

    def close(self):
        if self.remote_file is not None:
            self.remote_file.close()  
        if self.sftp_client is not None:
            self.sftp_client.close()  
        if self.sshclient is not None:
            self.sshclient.close()  

def main():
   
    try:
        log=GetLog()
        log.browse_files()
        log.close()      

        exit()
    except Exception as e:
        messagebox.showerror("Error:", e)
        
    
if __name__ == "__main__":
    main()



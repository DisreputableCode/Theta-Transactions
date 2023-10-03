import datetime, requests, webbrowser
import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading

class ThetaExporter:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title('Theta Explorer')
        self.window.geometry('600x250')
        self.create_widgets()

    def create_widgets(self):
        wallet_label = tk.Label(self.window, text='Wallet Address:')
        wallet_label.pack()

        self.wallet_entry = tk.Entry(self.window, width=40)
        self.wallet_entry.pack()

        start_label = tk.Label(self.window, text='Start Date (dd/mm/yyyy):')
        start_label.pack()

        self.start_entry = tk.Entry(self.window)
        self.start_entry.insert(0, '01/07/2022')
        self.start_entry.pack()

        weeks_label = tk.Label(self.window, text='Weeks:')
        weeks_label.pack()

        self.weeks_var = tk.StringVar()
        validate_cmd = self.window.register(self.validate_integer)
        self.weeks_entry = tk.Entry(self.window, textvariable=self.weeks_var, validate='key', validatecommand=(validate_cmd, '%S'))
        self.weeks_entry.insert(0, '52')
        self.weeks_entry.pack()

        project_label = tk.Label(self.window, text='Project by Dane Lewis (https://github.com/disreputablecode)', font=('Arial', 12), fg='gray')
        project_label.pack(side=tk.BOTTOM, pady=5)
        project_label.bind('<Button-1>', self.open_link)

        start_button = tk.Button(self.window, text='Start', command=self.validate_and_run)
        start_button.pack()

    def show_working_dialog(self):
        self.working_dialog = tk.Toplevel(self.window)
        self.working_dialog.title('Working')
        self.working_dialog.geometry('600x500')

        self.progress_label = tk.Label(self.working_dialog, text='00/00 weeks retrieved')
        self.progress_label.pack(pady=10)

        self.progress = ttk.Progressbar(self.working_dialog, orient='horizontal', length=500, mode='determinate')
        self.progress.pack(pady=10)

        self.log_text = tk.Text(self.working_dialog, width=80, height=30, state='disabled')
        self.log_text.pack(pady=10)

        self.working_dialog.transient(self.window)
        self.working_dialog.grab_set()

    def update_progress(self, count, total):
        self.progress['value'] = (count / total) * 100
        self.progress_label.config(text=f'{count}/{total} weeks retrieved')
        self.working_dialog.update_idletasks()

    def log_message(self, message):
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, message + '\n')
        self.log_text.config(state='disabled')
        self.log_text.see(tk.END)

    def validate_integer(self, var):
        if var.isdigit():
            return True
        else:
            return False

    def open_link(self, event):
        webbrowser.open_new('https://github.com/disreputablecode')

    def main_enabled(self, action):
        if action:
            for widget in self.window.winfo_children():
                widget.configure(state='normal')
        else:
            for widget in self.window.winfo_children():
                widget.configure(state='disabled')

    def validate_and_run(self):
        wallet = self.wallet_entry.get()
        start_date = self.start_entry.get()
        weeks = self.weeks_entry.get()

        try:
            start = int(datetime.datetime.strptime(start_date, '%d/%m/%Y').timestamp())
        except ValueError:
            messagebox.showerror('Error', 'Please check the Start field and ensure date is in dd/mm/yyyy format.')
            return None

        weeks = int(weeks)
        if weeks < 1 or weeks > 52:
            messagebox.showerror('Error', 'Invalid week range. Weeks must be between 1 and 52.')
            return None

        if wallet == '':
            messagebox.showerror('Error', 'Please enter wallet address.')
            return None

        r = requests.get(f'https://explorer.thetatoken.org:8443/api/accountTx/history/{wallet}')
        if r.status_code != 200:
            messagebox.showerror('Error', 'Wallet does not exist. Please check the wallet address.')
            return None

        file_path = filedialog.asksaveasfilename(defaultextension='.csv', initialfile='theta.csv')
        if file_path == '':
            return None

        self.get_data(wallet, start, weeks, file_path)

    def get_data(self, wallet, start, weeks, file_path):
        self.main_enabled(False)
        self.show_working_dialog()
        self.update_progress(0, weeks)
        self.data_thread = threading.Thread(target=self.fetch_data, args=(wallet, start, weeks, file_path))
        self.data_thread.start()

    def fetch_data(self, wallet, start, weeks, file_path):
        dates = []

        for i in range(weeks):
            end = start + 604800
            dates.append((start, end))
            start = end

        with open(file_path, 'w', newline='') as csv_file:
            writer = None

            for idx, date in enumerate(dates):
                self.log_message(f'Getting week {idx+1} of {len(dates)}')
                data = self.get_csv(date, wallet)
                df = pd.DataFrame(data)
                df['timestamp'] = df['timestamp'].str.replace('"', '')

                if writer is None:
                    df.to_csv(csv_file, mode='a', header=True, index=False)
                    writer = True
                else:
                    df.to_csv(csv_file, mode='a', header=False, index=False)

                self.update_progress(idx+1, len(dates))

        self.working_dialog.destroy()
        messagebox.showinfo('Complete', 'Transaction retrieval complete!')
        self.main_enabled(True)

    def get_csv(self, date, wallet):
        url = f'https://explorer.thetatoken.org:8443/api/accountTx/history/{wallet}?startDate={date[0]}&endDate={date[1]}'
        count = 0
        while count < 10:
            count += 1
            try:
                response = requests.get(url)
                response.raise_for_status()
                data = response.json()
                self.log_message(f'Attempt {count} succeeded to get week {datetime.datetime.fromtimestamp(date[0])} - {datetime.datetime.fromtimestamp(date[1])}.')
                return data['body']
            except Exception as e:
                if count < 10:
                    self.log_message(f'Attempt {count} failed to get week {datetime.datetime.fromtimestamp(date[0])} - {datetime.datetime.fromtimestamp(date[1])}. Retrying...')
                else:
                    self.log_message(f'Attempt {count} failed to get week {datetime.datetime.fromtimestamp(date[0])} - {datetime.datetime.fromtimestamp(date[1])}. Failed to get data.')
                    exit()

    def run_tasks(self, dates, wallet):
        txns = []
        for idx, date in enumerate(dates):
            self.log_message(f'Getting week {idx+1} of {len(dates)}')
            data = self.get_csv(date, wallet)
            txns += data
            self.update_progress(idx+1, len(dates))
        return txns

app = ThetaExporter()
app.window.mainloop()

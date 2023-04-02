import datetime, asyncio, requests, aiohttp, webbrowser
import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox


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

        project_label = tk.Label(self.window, text='Project by Dane Lewis (https://github.com/danelewis)', font=('Arial', 12), fg='gray')
        project_label.pack(side=tk.BOTTOM, pady=5)
        project_label.bind('<Button-1>', self.open_link)

        start_button = tk.Button(self.window, text='Start', command=self.validate_and_run)
        start_button.pack()

    def validate_integer(self, var):
        if var.isdigit():
            return True
        else:
            return False
        
    def open_link(self, event):
        webbrowser.open_new('https://github.com/danelewis')

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
        self.window.update()

        dates = []
        txns = []

        # Generate start and end times 7 days at a time, as the API only allows 7 days max per request
        for i in range(weeks):
            end = start + 604800
            dates.append((start, end))
            start = end

        # get 7 day increments async
        loop = asyncio.get_event_loop()
        txns = loop.run_until_complete(self.run_tasks_async(dates, wallet))

        # convert to dataframe
        df = pd.DataFrame(txns)

        # timestamp column has extra double quotes in the field
        df['timestamp'] = df['timestamp'].str.replace('"', '')

        # export dataframe to sigle CSV
        df.to_csv(file_path, index=False)

        # close working dialog and re-enable main window
        self.working_dialog.destroy()
        messagebox.showinfo('Complete', 'Transaction retreival complete!')
        self.main_enabled(True)

    def show_working_dialog(self):
        self.working_dialog = tk.Toplevel(self.window)
        self.working_dialog.title('Working')
        self.working_dialog.geometry('200x50')
        
        working_label = tk.Label(self.working_dialog, text='Working on it…')
        working_label.pack()

        self.working_dialog.transient(self.window)
        self.working_dialog.grab_set()

    async def get_csv(self, date, wallet):
        async with aiohttp.ClientSession() as session:
            async with session.get(f'https://explorer.thetatoken.org:8443/api/accountTx/history/{wallet}?startDate={date[0]}&endDate={date[1]}') as response:
                data = await response.json()
                return data['body']

    async def run_tasks_async(self, dates, wallet):
        tasks = []
        for date in dates:
            task = asyncio.create_task(self.get_csv(date, wallet))
            tasks.append(task)

        txns = []
        for task in asyncio.as_completed(tasks):
            data = await task
            txns += data

        return txns
           

if __name__ == '__main__':
    app = ThetaExporter()
    app.window.mainloop()
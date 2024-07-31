###########################################################################################
#                                                                                         #
# ██████╗    ██████╗   ███╗   ███╗   ██████╗   ██████╗    ██████╗   ██████╗    ██████╗    #
# ██╔══██╗  ██╔═══██╗  ████╗ ████║  ██╔═══██╗  ██╔══██╗  ██╔═══██╗  ██╔══██╗  ██╔═══██╗   #
# ██████╔╝  ██║   ██║  ██╔████╔██║  ██║   ██║  ██║  ██║  ██║   ██║  ██████╔╝  ██║   ██║   #
# ██╔═══╝   ██║   ██║  ██║╚██╔╝██║  ██║   ██║  ██║  ██║  ██║   ██║  ██╔══██╗  ██║   ██║   #
# ██║       ╚██████╔╝  ██║ ╚═╝ ██║  ╚██████╔╝  ██████╔╝  ╚██████╔╝  ██║  ██║  ╚██████╔╝   #
# ╚═╝        ╚═════╝   ╚═╝     ╚═╝   ╚═════╝   ╚═════╝    ╚═════╝   ╚═╝  ╚═╝   ╚═════╝    #
#                                                                                         #
#                                         V 1.0.1                                         #
#                                         *******                                         #
#                                                                                         #
# This script logs Pomodoro sessions to help track productivity. Each session's start     #
# time, end time, and activity description are recorded, enabling users to monitor and    #
# analyze their work patterns effectively.                                                #
#                                                                                         #
###########################################################################################


import tkinter as tk
from tkinter import messagebox, ttk
import sqlite3
import datetime
import logging
import re
import os


# Configure logging
logging.basicConfig(
    filename='pomodoro.csv',
    level=logging.INFO,
    format='%(asctime)s, %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        if self.tooltip:
            self.tooltip.destroy()
        self.tooltip = tk.Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{self.widget.winfo_rootx()+20}+{self.widget.winfo_rooty()+20}")
        label = tk.Label(self.tooltip, text=self.text, background="lightyellow", relief="solid", borderwidth=1)
        label.pack()

    def hide_tooltip(self, event=None):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

class Row:
    def __init__(self, initial_row):
        self.initial_row = initial_row - 1
        self.row = self.initial_row

    def next(self):
        self.row += 1
        return self.row
    
    def reset(self):
        self.row = self.initial_row


class PomodoroTimer:
    def __init__(self, master):
        self.master              = master
        self.master.title("Pomodoro Timer")
        self.master.geometry("270x400")  # Adjusted to accommodate activity input
        self.has_encourted_error = False
        self.timer_type          = tk.StringVar(value="duration")
        self.timer_started       = False
        self.remaining_time      = 0
        self.status              = tk.StringVar(value="initial")
        self.activity_name       = tk.StringVar()
        self.db_name             = 'activities.db'

        self.create_widgets()
        self.create_db()
        try:
            self.check_and_fix_records()
        except:
            # Get the current working directory
            current_working_directory = os.getcwd()

            # Error message
            messagebox.showerror("DB error!", f"error with db. You should erase it.\ndb path : {current_working_directory}/{self.db_name}")
            self.has_encourted_error = True
        
    def has_error(self):
        return self.has_encourted_error
    
    def create_widgets(self):
        row = Row(0)

        pady = 0
        # Timer type selection
        ttk.Radiobutton(self.master, text="Duration ", variable=self.timer_type, value="duration").grid(row=row.next(), column=0, sticky=tk.E)
        ttk.Radiobutton(self.master, text="End Time",  variable=self.timer_type, value="endtime"). grid(row=row.next(), column=0, sticky=tk.E)

        # Activity input
        self.activity_frame = ttk.Frame(self.master)
        self.activity_frame.grid(row=row.next(), column=0, pady=pady, sticky=tk.E)
        
        # Label and Entry for activity
        ttk.Label(self.activity_frame, text="Activity:").grid(row=0, column=0, sticky=tk.W)
        self.activity_entry = ttk.Entry(self.activity_frame, textvariable=self.activity_name, width=23)
        self.activity_entry.grid(row=0, column=1, sticky=tk.W)
        self.activity_entry.bind("<KeyRelease>", self.on_key_release)
        self.activity_entry.bind("<Control-Tab>", self.on_ctrl_tab)

        # Tooltip for activity entry
        self.activity_tooltip_init_val = "Enter the activity name here"
        self.activity_tooltip = Tooltip(self.activity_entry, self.activity_tooltip_init_val)

        # Create default combobox for search suggestions
        self.suggestion_combobox = ttk.Combobox(self.activity_frame, state="readonly", width=20)
        self.suggestion_combobox.grid(row=1, column=1, sticky=tk.W)
        self.suggestion_combobox.bind("<<ComboboxSelected>>", self.on_combobox_select)

        # Tooltip for combobox
        self.suggestion_tooltip_init_val = "Select a suggested activity"
        self.suggestion_tooltip = Tooltip(self.suggestion_combobox, self.suggestion_tooltip_init_val)

        # Duration input
        self.duration_frame = ttk.Frame(self.master)
        self.duration_frame.grid(row=row.next(), column=0, pady=pady, sticky=tk.E)
        ttk.Label(self.duration_frame, text="Duration (minutes):").pack(side=tk.LEFT)
        self.duration_entry = ttk.Entry(self.duration_frame, width=10)
        self.duration_entry.pack(side=tk.LEFT)

        # End time input
        self.endtime_frame = ttk.Frame(self.master)
        self.endtime_frame.grid(row=row.next(), column=0, pady=pady, sticky=tk.E)
        ttk.Label(self.endtime_frame, text="End Time (HH:MM):").pack(side=tk.LEFT)
        self.endtime_entry = ttk.Entry(self.endtime_frame, width=10)
        self.endtime_entry.pack(side=tk.LEFT)

        # Notification time input
        self.notify_frame = ttk.Frame(self.master)
        self.notify_frame.grid(row=row.next(), column=0, pady=pady, sticky=tk.E)
        ttk.Label(self.notify_frame, text="Notify before (minutes):").pack(side=tk.LEFT)
        self.notify_entry = ttk.Entry(self.notify_frame, width=10)
        self.notify_entry.pack(side=tk.LEFT)
        self.notify_entry.insert(0, "0")  # Set default value to 0

        # Start button
        self.start_button = tk.Button(self.master, text="Start Timer", command=self.toggle_timer)
        self.start_button.grid(row=row.next(), column=0, pady=pady, sticky=tk.E)

        # Display labels
        self.time_left_text = "Time Left: "
        self.duration_text  = "Total Duration: "
        self.time_left_label = ttk.Label(self.master, text=self.time_left_text + "00:00:00")
        self.time_left_label.grid(row=row.next(), column=0, sticky=tk.E)
        self.duration_label = ttk.Label(self.master, text=self.duration_text + "00:00:00")
        self.duration_label.grid(row=row.next(), column=0, sticky=tk.E)

        # Status label
        self.status_label = ttk.Label(self.master, text=f"Status: {self.status.get()}")
        self.status_label.grid(row=row.next(), column=0, pady=10, sticky=tk.E)

        # Get today's date and format it as dd.MM.YYYY
        today = datetime.date.today()
        default_date = today.strftime('%d.%m.%Y')

        # Summary input
        tk.Label(self.master, text="Enter date (dd.MM.YYYY):").grid(row=row.next(), column=0, pady=10, sticky=tk.W+tk.E)
        self.summary_frame = ttk.Frame(self.master)
        self.summary_frame.grid(row=row.next(), column=0, pady=pady, sticky=tk.W+tk.E)
        self.summary_date_entry = tk.Entry(self.summary_frame, width=10) # Changed parent to self.summary_frame
        self.summary_date_entry.grid(row=1, column=0, pady=pady, sticky=tk.W+tk.E)
        self.summary_date_entry.insert(0, default_date)  # Set the default date in the entry field

        # Summary button
        self.summary_button = tk.Button(self.summary_frame, text="Show Summary", command=self.show_summary)
        self.summary_button.grid(row=1, column=1, pady=pady, padx=(10, 0), sticky=tk.E)

        # Erase missing records button
        # self.erase_missing_button = tk.Button(self.master, text="Erase Missing Records", command=self.erase_missing_records)
        # self.erase_missing_button.grid(row=row.next(), column=0, pady=pady, sticky=tk.E)

        row.reset()
        # Vertical delay status bar
        self.progress_bar = ttk.Progressbar(self.master, orient='vertical', length=300, mode='determinate')
        self.progress_bar.grid(row=row.next(), column=1, rowspan=10, padx=20, pady=pady, sticky=tk.N+tk.S)


    def create_db(self):
        self.conn    = sqlite3.connect(self.db_name)
        self.cursor  = self.conn.cursor()
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS activities (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE NOT NULL
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS timer_logs (
                id INTEGER PRIMARY KEY,
                activity_name TEXT NOT NULL,
                start_time TEXT NULL,
                end_time TEXT,
                status TEXT NOT NULL,
                date_time TEXT NOT NULL
            )
        ''')
        self.conn.commit()

    def add_activity_to_db(self, activity):
        try:
            self.cursor.execute('INSERT INTO activities (name) VALUES (?)', (activity,))
            self.conn.commit()
        except sqlite3.IntegrityError:
            pass  # Activity already exists

    def add_timer_log(self, activity_name, start_time, end_time, status):
        if start_time:
            date_time = start_time
        else:
            date_time = end_time
        self.cursor.execute('INSERT INTO timer_logs (activity_name, start_time, end_time, status, date_time) VALUES (?, ?, ?, ?, ?)', (activity_name, start_time, end_time, status, date_time))
        self.conn.commit()

    def search_activities(self, query):
        self.cursor.execute('SELECT name FROM activities WHERE name LIKE ?', (f'%{query}%',))
        return [row[0] for row in self.cursor.fetchall()]

    def check_and_fix_records(self):
        # Fetch all records sorted by their IDs
        self.cursor.execute('SELECT * FROM timer_logs ORDER BY date_time ASC')
        records = self.cursor.fetchall()

        # To store new records to insert
        new_records = []

        for i in range(len(records)):
            current = records[i]
            if i < len(records) - 1:
                next_record = records[i + 1]
            else:
                next_record = None

            if next_record:
                next_rec = next_record[1] 

            if (next_record == None   or   next_record[3] is None)  \
               and current[4] == "started"                         \
               and ( next_record == None   or   current[1] != next_record[1]):
                # If the next record has no end time
                end_time = current[2]
                new_record = (current[1], None, end_time, 'missing')
                new_records.append(new_record)

        # Insert missing records into the database
        for record in new_records:
            self.add_timer_log(record[0], record[1], record[2], record[3])

    def erase_missing_records(self):
        # Delete records with status 'missing'
        self.cursor.execute('DELETE FROM timer_logs WHERE status = ?', ('missing',))
        self.conn.commit()
        messagebox.showinfo("Info", "All missing records have been deleted.")

    def on_key_release(self, event):
        query = self.activity_name.get()
        if query:
            suggestions = self.search_activities(query)
            self.suggestion_combobox['values'] = suggestions
            if suggestions:
                self.suggestion_combobox.current(0)
        else:
            self.suggestion_combobox['values'] = []
            self.suggestion_combobox.set('')

        # Update tooltip for activity entry
        if self.activity_tooltip.text:
            self.activity_tooltip.text = self.activity_name.get()
        else:
            self.activity_tooltip.text = self.activity_tooltip_init_val

        # Update tooltip for combobox
        if self.suggestion_combobox['values']:
            self.suggestion_tooltip.text = self.suggestion_combobox.get()
        else:
            self.suggestion_tooltip.text = self.suggestion_tooltip_init_val

    def on_combobox_select(self, event):
        self.activity_name.set(self.suggestion_combobox.get())

    def on_ctrl_tab(self, event):
        # Autocomplete using the selected item in the combobox
        if self.suggestion_combobox['values']:
            self.activity_name.set(self.suggestion_combobox.get())
        return "break"  # Prevent the default behavior of Ctrl+Tab

    def update_status(self, new_status):
        self.status.set(new_status)
        self.status_label.config(text=f"Status: {self.status.get()}")
        
        # Log status changes
        if new_status in ["started", "cancelled", "finished"]:
            self.log_event(new_status)

    def log_event(self, status):
        activity = self.activity_name.get() if self.activity_name.get() else "No activity"
        logging.info(f"{status}, {activity}")

    def toggle_timer(self):
        if self.timer_started:
            self.stop_timer()
        else:
            self.start_timer()

    def start_timer(self):
        try:
            # Add activity to database when timer starts
            activity = self.activity_name.get().strip()
            if activity:
                self.add_activity_to_db(activity)

            notify_before = int(self.notify_entry.get()) * 60  # Convert to seconds
            if self.endtime_entry.get() != "":
                self.timer_type.set("endtime")
            elif self.duration_entry.get() != "":
                self.timer_type.set("duration")

            if self.timer_type.get() == "duration":
                duration  = int(self.duration_entry.get()) * 60  # Convert to seconds
                end_time  = datetime.datetime.now() + datetime.timedelta(seconds=duration)
            else:
                end_time  = datetime.datetime.strptime(self.endtime_entry.get(), "%H:%M").replace(
                    year  = datetime.datetime.now().year,
                    month = datetime.datetime.now().month,
                    day   = datetime.datetime.now().day)
                if end_time <= datetime.datetime.now():
                    end_time += datetime.timedelta(days=1)
                duration = (end_time - datetime.datetime.now()).total_seconds()

            # Log the timer activity
            self.add_timer_log(activity, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), None, "started")

            self.remaining_time = int(duration)
            self.total_duration = int(duration)
            self.notify_time    = notify_before
            self.timer_started  = True
            self.update_status("started")
            self.start_button.config(text="Stop Timer", bg="green")
            self.progress_bar['maximum'] = self.total_duration
            self.countdown()
        except ValueError:
            messagebox.showerror("Invalid input", "Please enter valid values.")

    def stop_timer(self):
        self.timer_started = False
        end_time           = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.update_status("cancelled")
        self.add_timer_log(self.activity_name.get().strip(), None, end_time, "cancelled")
        self.start_button.config(bg="red")
        self.master.after(1000, self.reset_button_color)

    def reset_button_color(self):
        self.start_button.config(text="Start Timer", bg=self.master.cget("bg"))

    def countdown(self):
        if self.remaining_time > 0 and self.timer_started:
            mins, secs  = divmod(self.remaining_time, 60)
            hours, mins = divmod(mins, 60)
            time_str    = f"{hours:02d}:{mins:02d}:{secs:02d}"
            self.time_left_label.config(text=f"{self.time_left_text}{time_str}")

            total_mins, total_secs  = divmod(self.total_duration, 60)
            total_hours, total_mins = divmod(total_mins, 60)
            total_time_str          = f"{total_hours:02d}:{total_mins:02d}:{total_secs:02d}"
            self.duration_label.config(text=f"{self.duration_text}{total_time_str}")

            if self.remaining_time == self.notify_time:
                self.notify()

            self.progress_bar['value'] = self.total_duration - self.remaining_time

            self.remaining_time -= 1
            self.master.after(1000, self.countdown)
        elif self.remaining_time <= 0:
            self.timer_started = False
            self.update_status("finished")
            self.add_timer_log(self.activity_name.get().strip(), None, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "finished")
            self.start_button.config(text="Start Timer", bg=self.master.cget("bg"))
            self.progress_bar['value'] = 0
            messagebox.showinfo("Time's up!", "Your Pomodoro session has ended!")

    def notify(self):
        messagebox.showinfo("Reminder", f"{self.notify_time // 60} minutes left!")

    def parse_date(self, date_str):
        # Define regex patterns for different date formats
        patterns = [
            (r'^(\d{2})\.(\d{2})\.(\d{4})$', '%d.%m.%Y'),  # dd.MM.YYYY
            (r'^(\d{2})\.(\d{2})$', '%d.%m'),              # dd.MM
            (r'^(\d{2})\.(\d{2})\.(\d{2})$', '%d.%m.%y')   # dd.MM.YY
        ]
        
        today = datetime.date.today()
        
        for pattern, date_format in patterns:
            match = re.match(pattern, date_str)
            if match:
                day, month, year = match.groups()
                # Handle year format (YYYY or YY)
                if len(year) == 2:
                    year = '20' + year
                # Use current year if not provided
                if not year:
                    year = today.year
                if not month:
                    month = today.month
                if not day:
                    day  = today.day
                # Create a datetime object and return the date part
                try:
                    dt = datetime.datetime.strptime(f'{day}.{month}.{year}', date_format)
                    return dt.date()
                except ValueError:
                    messagebox.showerror("Error", "Invalid date format.")
                    return None
        messagebox.showerror("Error", "Date does not match any known format.")
        return None


# SUMMARY
    def show_summary(self):
        date_str          = self.summary_date_entry.get()
        self.summary_date = self.parse_date(date_str)

        if not self.summary_date:
            return

        summary_window = tk.Toplevel(self.master)
        summary_window.title("Activity Summary")

        self.tree = ttk.Treeview(summary_window, columns=("Activity", "Cumulative Time", "Start Time", "End Time"), show="headings")
        self.tree.heading("Activity",        text="Activity",        command=lambda: self.sort_by("Activity"))
        self.tree.heading("Cumulative Time", text="Cumulative Time", command=lambda: self.sort_by("Cumulative Time"))
        self.tree.heading("Start Time",      text="Start Time",      command=lambda: self.sort_by("Start Time"))
        self.tree.heading("End Time",        text="End Time",        command=lambda: self.sort_by("End Time"))

        start_of_day = datetime.datetime.combine(self.summary_date, datetime.time.min)
        end_of_day   = datetime.datetime.combine(self.summary_date, datetime.time.max)

        self.cursor.execute('''
            SELECT activity_name,
                MIN(start_time) AS first_start_time,
                SUM(strftime('%s', start_time)) AS sum_starts,
                SUM(strftime('%s', end_time)) AS sum_ends
            FROM timer_logs
            WHERE (start_time BETWEEN ? AND ?)
            OR (end_time   BETWEEN ? AND ?)
            GROUP BY activity_name
        ''', (
            start_of_day.strftime("%Y-%m-%d %H:%M:%S"),
            end_of_day.  strftime("%Y-%m-%d %H:%M:%S"),
            start_of_day.strftime("%Y-%m-%d %H:%M:%S"),
            end_of_day.  strftime("%Y-%m-%d %H:%M:%S")
        ))

        nb_act     = 0
        start_time = None
        duration   = None
        end_time   = None
        for activity_name, first_start, sum_starts, sum_ends in self.cursor.fetchall():
            nb_act += 1

            # Prepare for treeview
            start_time = datetime.datetime.strptime(first_start, "%Y-%m-%d %H:%M:%S")
            duration   = datetime.timedelta(milliseconds=((sum_ends-sum_starts) * 1000))
            end_time   = start_time + duration

            # Populate treeview
            self.tree.insert("", "end", values=(
                activity_name,
                str(duration),
                start_time.strftime("%Y-%m-%d %H:%M:%S"),
                end_time  .strftime("%Y-%m-%d %H:%M:%S")
            ))

        # Set default sort
        self.sort_by("Start Time")
        self.tree.pack(expand=True, fill="both")
        

    def sort_by(self, column):
        # Determine the sort order (ascending or descending)
        if self.tree.heading(column, 'text')[-1] == "▼":
            order = 'asc'
        else:
            order = 'desc'

        # Change the sort indicator
        for col in self.tree["columns"]:
            self.tree.heading(col, text=col, command=lambda c=col: self.sort_by(c))

        if order == 'asc':
            self.tree.heading(column, text=column + " ▲", command=lambda: self.sort_by(column))
        else:
            self.tree.heading(column, text=column + " ▼", command=lambda: self.sort_by(column))

        # Retrieve data from the Treeview and sort it
        data = [(self.tree.item(item)["values"], item) for item in self.tree.get_children()]
        if column == "Cumulative Time":
            data.sort(key=lambda x: self.parse_duration(x[0][1]),             reverse=(order == 'desc'))
        else:
            data.sort(key=lambda x: x[0][self.tree["columns"].index(column)], reverse=(order == 'desc'))

        # Re-insert sorted data into the Treeview
        for item in self.tree.get_children():
            self.tree.delete(item)
        for values, item in data:
            self.tree.insert("", "end", iid=item, values=values)

    def parse_duration(self, duration_str):
        # Helper function to parse duration string and return total milliseconds
        try:
            td = datetime.datetime.strptime(duration_str, "%H:%M:%S").time()
            return td.hour * 3600 * 1000 + td.minute * 60 * 1000 + td.second * 1000
        except ValueError:
            return 0

if __name__ == "__main__":
    root = tk.Tk()
    app = PomodoroTimer(root)
    if not app.has_error():
        root.mainloop()

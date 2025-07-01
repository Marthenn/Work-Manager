# Work Manager

A simple, powerful command-line tool for Ubuntu to track your work hours and manage a to-do list directly from the terminal.

Designed for developers, freelancers, and anyone who wants a fast and efficient way to stay organized without leaving the command line. The key feature is its robust, automatic time logging that captures your work hours even if you forget to stop the timer before a system shutdown or reboot.

---

## Features

- **Automatic Time Logging**  
  Uses a `systemd` service to automatically run the stop command on shutdown/reboot, ensuring you never lose track of your work hours.

- **Weekly Reports**  
  View your total work hours on a weekly basis.

- **Task Management**  
  A comprehensive to-do list system.

- **Task Grouping**  
  Organize your tasks into custom groups (e.g., `Project X`, `Personal`, `Admin`).

- **Deadline Tracking**  
  Assign deadlines to tasks and get automatic notifications.

- **Proactive Notifications**  
  Get alerts for overdue tasks and upcoming deadlines automatically when starting a session.

- **Purely CLI**  
  Fast, lightweight, and keyboard-driven. All data is stored locally in your home directory.

## Setup

1. **Save the Script**  
   Place the `work.py` script in a memorable location (e.g., inside a Git repository).

2. **Make it Executable**
   ```bash
   chmod +x /path/to/your/work.py
   ```
3. **Create an Alias (Recommended)**
For the best experience, create an alias in your `~/.bashrc` to run the script with python3. This solves potential execution issues.
```bash
# Add this line to your ~/.bashrc. Use the absolute path to your script.
alias work='python3 /path/to/your/work.py'
```
Then run source ~/.bashrc to apply the changes to your current terminal

4. **Install the service:**:
- Modify the `work-manager.service` file to include the absolute path to your `work.py` script in the `ExecStop` line
- **Important**: The `ExecStop` command must also explicitly use `python3`, just like your alias. For example: `ExecStop=/usr/bin/python3 /path/to/you/work.py stop`
- Save the service file to `~/.config/systemd/user/work-manager.service`
- Reload the systemd daemon with `systemctl --user daemon-reload`

## Usage
Below is a complete list of all available commands, assuming you have set up an alias named `work`.

### Work Hours Management
These commands are for starting, stopping, and reviewing your work sessions.

`start`<br>
Start a new work session timer. It also enables the automatic shutdown-catcher service and runs a check for task deadlines.
```bash
work start
```
<br>

`stop`<br>
Stops the current work session, calculates the duration, and logs it. This also disables the shutdown-catcher service.
```bash
work stop
```
<br>

`status`<br>
Shows if a work session is currently active and displays the elapsed time since it started.
```bash
work status
```
<br>

`log show`<br>
Displays a summary of logged work hours for a specific week
```bash
# Show hours for the current week (Monday to Sunday)
work log show

# Show hours for last week
work log show last
```
<br>

`log prune`<br>
Manually removes old log entries
```bash
# Prune logs older than the default 6 months
work log prune

# Prune logs older than 3 months
work log prune --months 3
```
<br>

### To-Do List Management
These commands help you manage your tasks

`todo list`<br>
Displays all your to-do items, neatly organized by group. Each item is given a temporary ID that can be used with the `rm` command.
```bash
work todo list
```
<br>

`todo add`<br>
Adds a new task to your to-do list. You can optionally assign it to a group and give it a deadline.
```bash
# Add a simple task to the 'General' group
work todo add "Send the weekly report"

# Add a task to a specific group
work todo add "Design the new logo" --group "Project-Y"

# Add a task with a group and a deadline
work todo add "Book flight tickets" --group "Travel" --deadline "2025-07-10"
```
*Note: The deadline must be in `YYYY-MM-DD` format.*
<br>

`todo rm`<br>
Removes a task from your list using the ID shown by the `todo list` command.
```bash
# First, find the ID of the task you want to remove
work todo list

# Then, remove the task with that ID (e.g., ID 3)
work todo rm 3
```
<br>

`todo edit`<br>
Modifies an existing task. You can change its text, group, or deadline.
```bash
# Change the task description for ID 5
work todo edit 5 --task "Submit the final project report"

# Move task 2 to a new group
work todo edit 2 --group "Archive"

# Add a deadline to task 7
work todo edit 7 --deadline "2025-09-01"

# Remove the deadline from task 7
work todo edit 7 --deadline "none"

# Change multiple fields at once for task 4
work todo edit 4 --task "Follow up with client" --group "Urgent"
```
<br>

`todo check`<br>
Manually runs a check for tasks that are overdue or have a deadline within the next two days. This same check is run automatically every time you use the `start` command.
```bash
work todo check
```

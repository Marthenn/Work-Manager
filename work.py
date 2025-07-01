import os
import sys
import json
import argparse
import subprocess
from datetime import datetime, timedelta, date

# --- CONFIGURATION ---
# The directory where your data files will be stored.
DATA_DIR = os.path.expanduser("~/.work_manager")
# Path for the main work log file.
WORK_LOG_FILE = os.path.join(DATA_DIR, "work_log.json")
# Path for the to-do list file.
TODOS_FILE = os.path.join(DATA_DIR, "todos.json")
# A temporary file to track the current active session. This is crucial for the auto-stop feature.
ACTIVE_SESSION_FILE = os.path.join(DATA_DIR, "active_session.json")
# The name of the systemd service file.
SYSTEMD_SERVICE_NAME = "work-manager.service"
# Default number of months to keep logs for automatic pruning.
DEFAULT_MONTHS_TO_KEEP = 6

# --- HELPER FUNCTIONS ---

def setup_environment():
    """Creates the data directory if it doesn't exist."""
    os.makedirs(DATA_DIR, exist_ok=True)

def read_json_file(file_path, default_data=None):
    """Reads a JSON file and returns its content. Returns default_data if file doesn't exist."""
    if default_data is None:
        default_data = []
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default_data

def write_json_file(file_path, data):
    """Writes data to a JSON file."""
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)

def get_active_session():
    """Checks for and returns the currently active work session."""
    return read_json_file(ACTIVE_SESSION_FILE, default_data=None)

def manage_systemd_service(action):
    """Starts or stops the systemd service for auto-shutdown handling."""
    try:
        if action == "start":
            subprocess.run(["systemctl", "--user", "enable", "--now", SYSTEMD_SERVICE_NAME], check=True, capture_output=True)
        elif action == "stop":
            subprocess.run(["systemctl", "--user", "stop", SYSTEMD_SERVICE_NAME], check=True, capture_output=True)
            subprocess.run(["systemctl", "--user", "disable", SYSTEMD_SERVICE_NAME], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(f"Warning: Could not manage systemd service '{SYSTEMD_SERVICE_NAME}'.")
        print("The automatic stop-on-shutdown feature may not work.")

# --- CORE WORK LOGIC ---

def start_work():
    """Starts a new work session."""
    if get_active_session():
        print("Error: A work session is already active. Use 'stop' to end it first.")
        sys.exit(1)

    check_deadlines()

    session = {"start_time": datetime.now().isoformat()}
    write_json_file(ACTIVE_SESSION_FILE, session)
    manage_systemd_service("start")
    print(f"Work session started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("The system will now automatically log your hours on shutdown/reboot.")

def stop_work():
    """Stops the current work session."""
    session = get_active_session()
    if not session:
        print("No active work session to stop.")
        manage_systemd_service("stop")
        sys.exit(0)

    start_time = datetime.fromisoformat(session["start_time"])
    end_time = datetime.now()

    work_log = read_json_file(WORK_LOG_FILE)
    work_log.append({"start": start_time.isoformat(), "end": end_time.isoformat()})
    write_json_file(WORK_LOG_FILE, work_log)

    os.remove(ACTIVE_SESSION_FILE)
    manage_systemd_service("stop")
    
    duration = end_time - start_time
    hours, remainder = divmod(duration.total_seconds(), 3600)
    minutes, _ = divmod(remainder, 60)

    print(f"Work session stopped at {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Session duration: {int(hours)} hours, {int(minutes)} minutes.")

    # Automatically prune old logs after stopping.
    prune_old_logs(DEFAULT_MONTHS_TO_KEEP, silent=True)

def show_status():
    """Shows the status of the current work session."""
    session = get_active_session()
    if not session:
        print("You are not currently working.")
        return

    start_time = datetime.fromisoformat(session["start_time"])
    duration = datetime.now() - start_time
    hours, remainder = divmod(duration.total_seconds(), 3600)
    minutes, _ = divmod(remainder, 60)
    
    print(f"Currently working. Session started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Elapsed time: {int(hours)} hours, {int(minutes)} minutes.")

def show_log(week_offset=0):
    """Displays the work log for a specific week."""
    work_log = read_json_file(WORK_LOG_FILE)
    if not work_log:
        print("Work log is empty.")
        return

    today = datetime.now()
    start_of_current_week = today - timedelta(days=today.weekday())
    start_of_week = start_of_current_week + timedelta(weeks=week_offset)
    end_of_week = start_of_week + timedelta(days=7)

    print(f"\n--- Work Log for Week of {start_of_week.strftime('%Y-%m-%d')} ---\n")

    weekly_total = timedelta()
    week_sessions = []

    for entry in work_log:
        start_time = datetime.fromisoformat(entry["start"])
        if start_of_week <= start_time < end_of_week:
            end_time = datetime.fromisoformat(entry["end"])
            duration = end_time - start_time
            weekly_total += duration
            week_sessions.append((start_time, duration))
    
    if not week_sessions:
        print("No work sessions recorded for this week.")
        return

    week_sessions.sort(key=lambda x: x[0])

    for start, duration in week_sessions:
        h, rem = divmod(duration.total_seconds(), 3600)
        m, _ = divmod(rem, 60)
        print(f"  - {start.strftime('%A, %b %d')}: {int(h):02d}h {int(m):02d}m")

    total_h, rem = divmod(weekly_total.total_seconds(), 3600)
    total_m, _ = divmod(rem, 60)
    print("\n-------------------------------------")
    print(f"Weekly Total: {int(total_h)} hours, {int(total_m)} minutes")
    print("-------------------------------------\n")

def prune_old_logs(months_to_keep, silent=False):
    """Removes log entries older than a specified number of months."""
    work_log = read_json_file(WORK_LOG_FILE)
    if not work_log:
        if not silent:
            print("Work log is empty. Nothing to prune.")
        return

    # Using 30.5 as an average month length for better accuracy over a year.
    cutoff_date = datetime.now() - timedelta(days=months_to_keep * 30.5)
    
    original_count = len(work_log)
    logs_to_keep = [
        entry for entry in work_log 
        if datetime.fromisoformat(entry["end"]) >= cutoff_date
    ]
    new_count = len(logs_to_keep)
    
    pruned_count = original_count - new_count

    if pruned_count > 0:
        write_json_file(WORK_LOG_FILE, logs_to_keep)
        if not silent:
            print(f"🗑️  Pruned {pruned_count} log entries older than {months_to_keep} months.")
    elif not silent:
        print("No old log entries found to prune.")


# --- TODO LIST LOGIC ---

def check_deadlines():
    """Checks for overdue and upcoming deadlines and prints a summary."""
    todos = read_json_file(TODOS_FILE)
    if not any(todo.get("deadline") for todo in todos):
        return

    overdue_tasks, upcoming_tasks = [], []
    today = date.today()
    soon_threshold = today + timedelta(days=2)

    for todo in todos:
        if "deadline" in todo:
            try:
                deadline_date = datetime.strptime(todo["deadline"], "%Y-%m-%d").date()
                if deadline_date < today:
                    overdue_tasks.append(todo)
                elif today <= deadline_date <= soon_threshold:
                    upcoming_tasks.append(todo)
            except (ValueError, TypeError):
                continue
    
    if not overdue_tasks and not upcoming_tasks:
        return

    print("\n🔔 Deadline Notifications 🔔")
    print("----------------------------")
    if overdue_tasks:
        print("🔥 OVERDUE TASKS:")
        for task in overdue_tasks:
            group = f"[{task.get('group', 'General')}] "
            print(f"  - {group}{task['task']} (Due: {task['deadline']})")

    if upcoming_tasks:
        print("\n✨ UPCOMING TASKS (Next 2 Days):")
        for task in upcoming_tasks:
            group = f"[{task.get('group', 'General')}] "
            print(f"  - {group}{task['task']} (Due: {task['deadline']})")
    
    print("----------------------------\n")

def list_todos():
    """Lists all to-do items, grouped by their category."""
    todos = read_json_file(TODOS_FILE)
    if not todos:
        print("Your to-do list is empty. Add one with 'todo add'.")
        return
    
    for i, todo in enumerate(todos):
        todo['id'] = i + 1

    grouped_todos = {}
    for todo in todos:
        group = todo.get("group", "General")
        if group not in grouped_todos:
            grouped_todos[group] = []
        grouped_todos[group].append(todo)

    for group, items in sorted(grouped_todos.items()):
        print(f"\n[{group}]")
        print("-" * (len(group) + 2))
        for item in items:
            deadline_str = f" (Due: {item['deadline']})" if item.get("deadline") else ""
            print(f"  {item['id']}: {item['task']}{deadline_str}")
    print()

def add_todo(task, group, deadline):
    """Adds a new item to the to-do list."""
    todos = read_json_file(TODOS_FILE)
    new_todo = {"task": task, "group": group}
    if deadline:
        try:
            datetime.strptime(deadline, "%Y-%m-%d")
            new_todo["deadline"] = deadline
        except ValueError:
            print(f"Error: Invalid deadline format for '{deadline}'. Please use YYYY-MM-DD.")
            sys.exit(1)
    
    todos.append(new_todo)
    write_json_file(TODOS_FILE, todos)
    print(f"Added to-do: '{task}' to group '{group}'.")
    list_todos()

def remove_todo(todo_id):
    """Removes a to-do item by its ID."""
    todos = read_json_file(TODOS_FILE)
    if not 0 < todo_id <= len(todos):
        print(f"Error: Invalid ID '{todo_id}'. Use 'todo list' to see available IDs.")
        sys.exit(1)
    
    removed_todo = todos.pop(todo_id - 1)
    write_json_file(TODOS_FILE, todos)
    print(f"Removed to-do: '{removed_todo['task']}'")
    list_todos()

# --- MAIN EXECUTION & ARGUMENT PARSING ---

def main():
    """Main function to parse arguments and call the appropriate function."""
    setup_environment()

    parser = argparse.ArgumentParser(description="A command-line tool to manage your work hours and to-do list.")
    subparsers = parser.add_subparsers(dest="command", help="Available commands", required=True)

    subparsers.add_parser("start", help="Start a new work session.")
    subparsers.add_parser("stop", help="Stop the current work session.")
    subparsers.add_parser("status", help="Show current work session status.")

    # 'log' command and its subcommands
    log_parser = subparsers.add_parser("log", help="Manage the work log.")
    log_subparsers = log_parser.add_subparsers(dest="log_command", help="Log actions", required=True)

    show_parser = log_subparsers.add_parser("show", help="Display the work log for a given week.")
    show_parser.add_argument("week", nargs="?", default="current", choices=["current", "last"], help="Which week to display (default: current).")

    prune_parser = log_subparsers.add_parser("prune", help="Remove old log entries.")
    prune_parser.add_argument("-m", "--months", type=int, default=DEFAULT_MONTHS_TO_KEEP, help=f"Prune logs older than this many months (default: {DEFAULT_MONTHS_TO_KEEP}).")

    # 'todo' command and its subcommands
    todo_parser = subparsers.add_parser("todo", help="Manage your to-do list.")
    todo_subparsers = todo_parser.add_subparsers(dest="todo_command", help="To-do actions", required=True)

    todo_subparsers.add_parser("list", help="List all to-do items.")
    todo_subparsers.add_parser("check", help="Check for overdue and upcoming deadlines.")
    add_parser = todo_subparsers.add_parser("add", help="Add a new to-do item.")
    add_parser.add_argument("task", type=str, help="The description of the task.")
    add_parser.add_argument("-g", "--group", type=str, default="General", help="An optional group for the task.")
    add_parser.add_argument("-d", "--deadline", type=str, help="An optional deadline in YYYY-MM-DD format.")
    rm_parser = todo_subparsers.add_parser("rm", help="Remove a to-do item by its ID.")
    rm_parser.add_argument("id", type=int, help="The ID of the to-do to remove (from 'todo list').")

    args = parser.parse_args()

    # --- Command Dispatcher ---
    if args.command == "start":
        start_work()
    elif args.command == "stop":
        stop_work()
    elif args.command == "status":
        show_status()
    elif args.command == "log":
        if args.log_command == "show":
            offset = 0 if args.week == "current" else -1
            show_log(week_offset=offset)
        elif args.log_command == "prune":
            prune_old_logs(args.months)
    elif args.command == "todo":
        if args.todo_command == "list":
            list_todos()
        elif args.todo_command == "check":
            check_deadlines()
        elif args.todo_command == "add":
            add_todo(args.task, args.group, args.deadline)
        elif args.todo_command == "rm":
            remove_todo(args.id)

if __name__ == "__main__":
    main()

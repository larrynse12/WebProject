import re
from datetime import datetime

# ============================================================
# DATA
# ============================================================
# Each record: [subject, section, instructor, room, day, start_str, end_str, start_float, end_float]
schedule_records = []

# Index positions inside a record (avoids "magic numbers" like record[7])
SUBJECT, SECTION, INSTRUCTOR, ROOM, DAY, START_STR, END_STR, START_NUM, END_NUM = range(9)

VALID_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DAY_LOOKUP = {}
for _day in VALID_DAYS:
    DAY_LOOKUP[_day.lower()] = _day          # "monday"  -> "Monday"
    DAY_LOOKUP[_day[:3].lower()] = _day      # "mon"     -> "Monday"

TIME_FORMAT = "%I:%M %p"
TABLE_HEADER = (
    f"{'ID':<3} | {'SUBJECT':<30} | {'SECTION':<10} | {'ROOM':<10} | "
    f"{'DAY':<10} | {'START':<8} | {'END':<8}"
)
TABLE_WIDTH = len(TABLE_HEADER)


# ============================================================
# VALIDATION (each parser returns a clean value or raises ValueError)
# ============================================================
def make_text_parser(label, max_len, allowed_pattern, require_letter=True):
    """Builds a parser that checks a text field for emptiness, length, and characters."""
    def parse(raw):
        value = " ".join(raw.split())  # trims and collapses extra spaces
        if not value:
            raise ValueError(f"{label} cannot be empty.")
        if len(value) > max_len:
            raise ValueError(f"{label} must not exceed {max_len} characters.")
        if not re.fullmatch(allowed_pattern, value):
            raise ValueError(f"{label} contains invalid characters.")
        if require_letter and not re.search(r"[A-Za-z]", value):
            raise ValueError(f"{label} must contain at least one letter.")
        return value
    return parse


parse_subject = make_text_parser("Subject name", 30, r"[A-Za-z0-9 .,'&()\-]+")
parse_section = make_text_parser("Section", 10, r"[A-Za-z0-9 \-]+", require_letter=False)
parse_instructor = make_text_parser("Instructor", 30, r"[A-Za-z .,'\-]+")
parse_room = make_text_parser("Classroom", 10, r"[A-Za-z0-9 \-]+", require_letter=False)


def parse_day(raw):
    """Accepts a full day name or 3-letter abbreviation (any capitalization)."""
    day = DAY_LOOKUP.get(raw.strip().lower())
    if day is None:
        raise ValueError(f"Invalid day! Choose one of: {', '.join(VALID_DAYS)}.")
    return day


def parse_time(raw):
    """Returns (clean_time_string, time_as_float) or raises ValueError."""
    cleaned = " ".join(raw.upper().replace("AM", " AM").replace("PM", " PM").split())
    try:
        parsed = datetime.strptime(cleaned, TIME_FORMAT)
    except ValueError:
        raise ValueError("Invalid time format! Use HH:MM AM/PM (e.g., 8:30 AM or 01:15 PM).")
    return parsed.strftime(TIME_FORMAT), parsed.hour + parsed.minute / 60.0


def make_end_time_parser(start_float):
    """Builds a time parser that also makes sure the end time is after the start time."""
    def parse(raw):
        display, value = parse_time(raw)
        if value <= start_float:
            raise ValueError("End time must be later than the start time.")
        return display, value
    return parse


def ask(prompt, parser, default=None):
    """Keeps asking until the input passes the parser. Blank input keeps `default` if given."""
    shown_prompt = f"{prompt} [{default}]: " if default is not None else f"{prompt}: "
    while True:
        raw = input(shown_prompt).strip()
        if not raw and default is not None:
            raw = str(default)
        try:
            return parser(raw)
        except ValueError as error:
            print(f"[ERROR] {error} Please try again.")


# ============================================================
# HELPERS
# ============================================================
def find_conflict(day, room, start_float, end_float, ignore_index=None):
    """Returns the first record that overlaps in the same room and day, or None."""
    for i, record in enumerate(schedule_records):
        if i == ignore_index:
            continue
        same_slot = record[DAY].lower() == day.lower() and record[ROOM].lower() == room.lower()
        overlaps = start_float < record[END_NUM] and end_float > record[START_NUM]
        if same_slot and overlaps:
            return record
    return None


def print_row(number, record):
    print(
        f"{number:<3} | {record[SUBJECT]:<30} | {record[SECTION]:<10} | {record[ROOM]:<10} | "
        f"{record[DAY]:<10} | {record[START_STR]:<8} | {record[END_STR]:<8}"
    )


def print_table(rows):
    """rows: list of (id_number, record)."""
    print("\n" + "=" * TABLE_WIDTH)
    print(TABLE_HEADER)
    print("-" * TABLE_WIDTH)
    for number, record in rows:
        print_row(number, record)
    print("=" * TABLE_WIDTH)


def show_day_examples():
    print(f"  Valid days : {', '.join(VALID_DAYS)}")
    print("  Short forms: Mon, Tue, Wed, Thu, Fri, Sat, Sun")


# ============================================================
# FEATURES
# ============================================================
def add_schedule():
    """Collects validated details and adds a new schedule if there is no conflict."""
    print("\n--- Add Class Schedule ---")
    subject = ask("Subject Name", parse_subject)
    section = ask("Section", parse_section)
    instructor = ask("Instructor", parse_instructor)
    room = ask("Classroom", parse_room)

    print("\nDay examples:")
    show_day_examples()
    day = ask("Day", parse_day)

    start_str, start_float = ask("Start Time (e.g. 8:30 AM)", parse_time)
    end_str, end_float = ask("End Time (e.g. 10:00 AM)", make_end_time_parser(start_float))

    clash = find_conflict(day, room, start_float, end_float)
    if clash:
        print(f"\n[ERROR] Schedule conflict detected in {room} on {day}!")
        print(f"        It overlaps with {clash[SUBJECT]} ({clash[START_STR]} - {clash[END_STR]}).")
        return

    schedule_records.append(
        [subject, section, instructor, room, day, start_str, end_str, start_float, end_float]
    )
    print(f"\n[SUCCESS] Class '{subject}' successfully added to your schedule!")


def view_schedules():
    """Displays all current schedules in a table. Returns False if empty."""
    if not schedule_records:
        print("\n[INFO] Your schedule is currently empty.")
        return False
    print_table(list(enumerate(schedule_records, start=1)))
    return True


def search_schedule():
    """Searches the schedule by Subject Name or Day."""
    if not schedule_records:
        print("\n[INFO] Your schedule is empty. Nothing to search.")
        return

    keyword = input("\nEnter Subject Name or Day to search: ").strip().lower()
    if not keyword:
        print("\n[ERROR] Search keyword cannot be empty.")
        return

    matches = [
        (i, record)
        for i, record in enumerate(schedule_records, start=1)
        if keyword in record[SUBJECT].lower() or keyword in record[DAY].lower()
    ]

    if matches:
        print_table(matches)
    else:
        print(f"\n[INFO] No schedules found matching '{keyword}'.")


def ask_for_id(action):
    """Asks for a schedule ID. Returns a zero-based index, or None if invalid."""
    try:
        index = int(input(f"\nEnter the ID number of the schedule to {action}: ")) - 1
    except ValueError:
        print("\n[ERROR] Please enter a valid number.")
        return None
    if not 0 <= index < len(schedule_records):
        print("\n[ERROR] Invalid ID number.")
        return None
    return index


def edit_schedule():
    """Allows the user to modify an existing schedule (ENTER keeps the current value)."""
    if not view_schedules():
        return

    index = ask_for_id("edit")
    if index is None:
        return

    old = schedule_records[index]
    print("\nEnter new details (Press ENTER to keep the current value):")

    subject = ask("Subject Name", parse_subject, default=old[SUBJECT])
    section = ask("Section", parse_section, default=old[SECTION])
    instructor = ask("Instructor", parse_instructor, default=old[INSTRUCTOR])
    room = ask("Classroom", parse_room, default=old[ROOM])

    print("\nDay examples:")
    show_day_examples()
    day = ask("Day", parse_day, default=old[DAY])

    start_str, start_float = ask("Start Time", parse_time, default=old[START_STR])
    end_str, end_float = ask(
        "End Time", make_end_time_parser(start_float), default=old[END_STR]
    )

    clash = find_conflict(day, room, start_float, end_float, ignore_index=index)
    if clash:
        print(f"\n[ERROR] Update failed! Conflict detected in {room} on {day}!")
        print(f"        It overlaps with {clash[SUBJECT]} ({clash[START_STR]} - {clash[END_STR]}).")
        return

    schedule_records[index] = [
        subject, section, instructor, room, day, start_str, end_str, start_float, end_float
    ]
    print("\n[SUCCESS] Schedule updated successfully!")


def delete_schedule():
    """Allows the user to remove a schedule."""
    if not view_schedules():
        return

    index = ask_for_id("delete")
    if index is None:
        return

    deleted = schedule_records.pop(index)
    print(f"\n[SUCCESS] Deleted '{deleted[SUBJECT]}' from your schedule.")


def check_next_class():
    """Alerts the user of their next upcoming class today."""
    now = datetime.now()
    current_day = now.strftime("%A")
    current_time = now.hour + now.minute / 60.0

    upcoming = [
        record for record in schedule_records
        if record[DAY].lower() == current_day.lower() and record[START_NUM] >= current_time
    ]

    if not upcoming:
        print(f"\n[INFO] You have no more classes scheduled for today ({current_day}).")
        return

    next_class = min(upcoming, key=lambda record: record[START_NUM])
    print(
        f"\n[ALERT] Your next class today ({current_day}) is {next_class[SUBJECT]} "
        f"in {next_class[ROOM]} starting at {next_class[START_STR]}."
    )


# ============================================================
# MAIN MENU
# ============================================================
def print_menu():
    print("\n=================================================")
    print("          BSIT FRESHMAN CLASS SCHEDULER          ")
    print("=================================================")
    print("1. Add Class Schedule")
    print("2. View Class Schedules")
    print("3. Search Schedule")
    print("4. Edit Class Schedule")
    print("5. Delete Class Schedule")
    print("6. Check Next Class (Updates)")
    print("7. Exit")


def main():
    actions = {
        "1": add_schedule,
        "2": view_schedules,
        "3": search_schedule,
        "4": edit_schedule,
        "5": delete_schedule,
        "6": check_next_class,
    }

    while True:
        print_menu()
        choice = input("\nEnter your choice: ").strip()

        if choice == "7":
            print("\nExiting program. Have a great semester!")
            break

        action = actions.get(choice)
        if action:
            action()
        else:
            print("\n[ERROR] Invalid input. Please select a number from 1 to 7.")


if __name__ == "__main__":
    main()

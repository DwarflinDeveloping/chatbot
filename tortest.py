import time
from datetime import datetime

# Get the current time and save it as a string
old_time_str = datetime.now().strftime('%H:%M:%S')
print(f"Old time: {old_time_str}")

# Wait for 10 seconds
time.sleep(1)

# Get the new current time
new_time_str = datetime.now().strftime('%H:%M:%S')
print(f"New time: {new_time_str}")

# Compare the times
print(f"Difference in seconds: {int(new_time_str[-2:]) - int(old_time_str[-2:])}")

with open(r"e:\hermes\agentic-course-loop\src\agents\core.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

# Line 417 is index 416. Line 718 is index 717.
for i in range(416, 718):
    lines[i] = "# " + lines[i]

with open(r"e:\hermes\agentic-course-loop\src\agents\core.py", "w", encoding="utf-8") as f:
    f.writelines(lines)
print("Commented out lines 417-718 in core.py")

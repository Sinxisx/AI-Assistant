import requests
import json
from pathlib import Path
import re
import os
import psycopg2

script_dir = Path.cwd()
print(script_dir)
# # Navigate to the parent directory and then into the Context folder
# context_dir = script_dir.parent / "Context"

# Construct the full path to the file
file_path = script_dir / "Context" / "MASTER_FUNDING.txt"
print(file_path)
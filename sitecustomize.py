# Render startup compatibility: main.py calls init_db() while importing only
# selected helpers from db.py. Python loads sitecustomize automatically, so expose
# the existing initializer without changing application behavior.
import builtins

from db import init_db as _init_db

builtins.init_db = _init_db

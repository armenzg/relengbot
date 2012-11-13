import sys, os.path

class Monitor(object):
    def __init__(self):
        self._file_ages = {}

    def check_ages(self):
        "Return True if something has changed"
        for module in sys.modules.values():
            if not hasattr(module, '__file__'):
                continue

            # Get the age of the file
            filename = module.__file__
            mtime = os.path.getmtime(filename)

            if filename.endswith(".pyc"):
                # Check the .py file too
                sourcefile = filename[:-4] + ".py"
                if os.path.exists(sourcefile):
                    mtime = os.path.getmtime(sourcefile)
                    filename = sourcefile

            old_mtime = self._file_ages.get(filename)
            if old_mtime and mtime > old_mtime:
                # Something has changed, restart!
                return True

            self._file_ages[filename] = mtime

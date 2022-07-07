class Node():
    def __init__(self, process_id):

        self.process_id     = process_id

        self.x              = 0 # variable to be replicated
        self.wait_list      = [] # stores the processes waiting to write
        self.is_writing     = False # True if the thread is currently writing
        self.has_rights     = (process_id == 1) # True if the process has the primary copy
        self.change_history = {} # Stores the changes made to the primary copy
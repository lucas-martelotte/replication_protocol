#==================================#
#======= EDITABLE VARIABLES =======#
#==================================#

BASE_PORT = 1000
NUMBER_OF_PROCESSES = 2
SLEEP_TIME = 0.1

#==================================#
#========= NO TOUCH AREA ==========#
#==================================#

def get_port_by_process_id(process_id):
    global BASE_PORT
    return BASE_PORT + process_id

from config import get_port_by_process_id, NUMBER_OF_PROCESSES, SLEEP_TIME
from rpyc.utils.server import ThreadedServer
from node import Node
import threading
import rpyc
import time
import os

#====================================#
#============== SETUP ===============#
#====================================#

print('Please type the process id.')
node = Node(int(input()))
port = get_port_by_process_id(node.process_id)

#====================================#
#============ INTERFACE =============#
#====================================#

def input_loop():
    global node

    print('\nPlease type a number. (Type \"q\" to quit.)')
    print('1) Read X.\n2) Read change history.\n3) Change X.\n')

    while True:

        input_action = input()
        if input_action == 'q':
            print('Quitting...')
            os._exit(1)

        if not input_action.isdigit():
            print('Invalid input. Please try again.')
            continue
        input_action = int(input_action)
        if not input_action in [1,2,3]:
            print('Input must be between 1 and 3. Please try again.')
            continue

        if input_action == 1:
            print(f'X = {node.x}.')
        elif input_action == 2:
            print(f'Change history: {node.change_history}.')
        elif input_action == 3:
            # Checking if the node has the writing rights.
            # If not, it'll enter the wait_list.
            if node.has_rights:
                node.is_writing = True
            else:
                # Updating the wait_list
                node.wait_list.append(node.process_id)
                for i in range(NUMBER_OF_PROCESSES):
                        if node.process_id == i+1:
                            continue
                        try:
                            conn = rpyc.connect('localhost', get_port_by_process_id(i+1))
                            current_wait_list = conn.root.exposed_get_wait_list()
                            node.wait_list.extend(current_wait_list)
                            conn.close()
                        except:
                            print(f'ERROR: Failed to get the wait_list of node {i+1}. Aborting...')
                            exit()
                node.wait_list = list(dict.fromkeys(node.wait_list))

                # Continuously checking who has right and waiting for its turn
                while True:
                    time.sleep(SLEEP_TIME) # Delay
                    rights_process_id = None # The ID of the process who currently has the rights
                    rights_process_is_writing = None # A boolean indicating if that process is
                                                     # currently writing

                    for i in range(NUMBER_OF_PROCESSES):
                        # Getting the node that currently has rights and
                        # checking if it is currently writing.
                        if i+1 == node.process_id:
                            continue

                        try:
                            conn = rpyc.connect('localhost',
                                                get_port_by_process_id(i+1))

                            if conn.root.exposed_has_rights():
                                conn = rpyc.connect('localhost',
                                                    get_port_by_process_id(i+1))

                                rights_process_id = i+1
                                rights_process_is_writing = conn.root.exposed_is_writing()

                                conn.close()
                                break

                            conn.close()
                        except:
                            print(f'ERROR: Failed to check if node {i+1} has rights ' +\
                                   'and is writing. Aborting...')
                            exit()

                    if (rights_process_id is None) or (rights_process_is_writing is None):
                        print('ERROR: Couldn\'t determina which node has the rights. Aborting...')
                        exit()

                    # When there is no one writing, this node can get the rights
                    if not rights_process_is_writing and len(node.wait_list) == 1:

                        node_rpc.exposed_gain_rights(node_rpc, rights_process_id)
                        node.is_writing = True
                        node.wait_list.remove(node.process_id)

                        for i in range(NUMBER_OF_PROCESSES):
                            # Updating the wait_list of the other nodes
                            if i+1 == node.process_id:
                                continue

                            conn = rpyc.connect('localhost',get_port_by_process_id(i+1))
                            conn.root.exposed_update_wait_list(node.process_id)
                            conn.close()
                        break

            print('Starting the writing process. (Type \"q\" to finish writing)')
            while True:
                c = input('New value for X: ')

                if c == 'q':
                    print('Updating the other nodes...')
                    for i in range (NUMBER_OF_PROCESSES):
                        if i+1 == node.process_id:
                            continue

                        try:
                            conn = rpyc.connect('localhost',get_port_by_process_id(i+1))
                            conn.root.exposed_write_by_other_node(node.process_id,node.x)
                            conn.close()
                        except:
                            print(f'ERROR: Could not update {i+1}. Aborting...')
                            exit()

                    node.is_writing = False
                    print('Writing process finished successfully.')
                    break
                else:
                    if not c.isdigit():
                        print('Invalid value for X. Please try again.')
                        continue
                    node_rpc.exposed_write_by_this_node(node_rpc,int(c))

#====================================#
#============== CLIENT ==============#
#====================================#

class node_rpc(rpyc.Service):

    def exposed_update_wait_list(self, process_id_to_remove):
        '''
            Removes one process id from this node's wait list. If the id
            is not in the wait list, the function does nothing.

            Parameters:
                process_id_to_remove (int): the node id that will be removed from the wait list.

            Returns:
                --
        '''
        global node
        try:
            node.wait_list.remove(process_id_to_remove)
        except:
            pass

    def exposed_gain_rights(self, rights_process_id):
        '''
            Removes the right from the input node and
            this node gains the rights.

            Parameters:
                rights_process_id (int): the ID of the node with the rights

            Retruns:
                --

        '''
        global node
        conn = rpyc.connect('localhost',get_port_by_process_id(rights_process_id))
        conn.root.exposed_lose_rights()
        conn.close()
        node.has_rights = True

    def exposed_write_by_other_node(self, writer_process_id, new_x):
        '''
            Modifies the value of X when the modification was made
            by another node.

            Parameters:
                writer_process_id (int): the ID of the node that did the writing
                new_x             (int): the new value for X

            Returns:
                --
        '''
        global node
        node.x = new_x

        if writer_process_id in node.change_history:
            node.change_history[writer_process_id].append(node.x)
        else:
            node.change_history[writer_process_id] = [node.x]

    def exposed_write_by_this_node(self, new_x):
        '''
            Modifies the value of X in this node when the writing is
            being done by this node.

            Parameters:
                new_x (int): the new value for X

            Returns:
                --
        '''
        global node
        exposed_write_by_other_node(node.process_id, new_x)

    def exposed_lose_rights(self):
        '''
            Removes the rights from this node.
        '''
        global node
        node.has_rights = False

    def exposed_has_rights(self):
        '''
            Returns if this node has rights.
        '''
        global node
        return node.has_rights

    def exposed_is_writing(self):
        '''
            Returns if this node is currently writing.
        '''
        global node
        return node.is_writing

    def exposed_get_wait_list(self):
        '''
            Gets this node's wait_list.
        '''
        global node
        return node.wait_list

#====================================#
#============ MAIN CODE =============#
#====================================#

if __name__=='__main__':
    thread = threading.Thread(target=input_loop, args=())
    server = ThreadedServer(node_rpc, port=port)
    thread.start()
    server.start()



import os
import sys
import click
from termcolor import colored
import traceback
import subprocess
import queue
import threading
import multiprocessing

worker_data=["BloodHoundAD/BloodHound",
        "GhostPack/Seatbelt",
        "GhostPack/SharpUp",
        "yeyintminthuhtut/Awesome-Red-Teaming",
        "byt3bl33d3r/DeathStar",
        "byt3bl33d3r/CrackMapExec",
        "Cn33liz/p0wnedShell",
        "EmpireProject/Empire",
        "danielmiessler/SecLists",
        "laramies/theHarvester",
        "s0md3v/Photon",
        "commixproject/commix",
        "emtunc/SlackPirate",
        "bwall/ExtractHosts",
        "Grunny/zap-cli",
        "tevora-threat/PowerView3-Aggressor",
        "vysecurity/ANGRYPUPPY",
        #"harleyQu1nn/AggressorScripts",
        "bluscreenofjeff/AggressorScripts",
        "pavanw3b/sh00t",
        "evyatarmeged/Raccoon",
        "1N3/IntruderPayloads",
        "1N3/BlackWidow",
        "trustedsec/ptf",
        "swisskyrepo/PayloadsAllTheThings",
        "robertdavidgraham/masscan",
        "bitsadmin/wesng",
        "needmorecowbell/Hamburglar"
        "Yara-Rules/rules"]
        #"codingo/Interlace"]

#test initial list

def threadCount(thread):
    # The command below kicks off thread dependent on how many CPU cores your system has available 
    #thread = multiprocessing.cpu_count() #Detect the available cores on system , similar to nproc
    # Reading CPU threads is no longer performed as this value is being privided by the user
    # Convert user supplied thread value (String) to integer for consuption
    cpus = int(thread)
    print("\nCreating %d threads...\n" % cpus)
    #cpus = 10
    #print("\nPulling git repos with %d threads...\n" % cpus))
    for i in range(cpus):
      t = threading.Thread(target=worker)
      t.daemon = True
      t.start()

    q.join() # Blocks everything until all tasks in the queue have completed, then it print the messages below
    print("Program has successfully completed execution ...")
    print('[%s]' % ', '.join(map(str, worker_data)))
    print(colored("Please check output ...", 'yellow'))

# Load up a queue with the data from the worker_data list, this will handle locking
# q = queue.Queue()
# for git_repo in worker_data2:
#     q.put(git_repo)

# When acquired by a thread it locks other threads from printing
lock = threading.Lock()
stop = 0

# Function to handle processing of commands
def subprocess_cmd(command):

    name = command[2].split("/")[-1].replace(".git", "")

    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = process.communicate()

    lock.acquire()
    if "fatal".encode("utf-8") not in err:
        print (colored("[**] Successfully cloned {}\n".format(name), 'green'))
    else:
        try:
            error = str(err, 'utf-8').strip().replace("\n", " ")
        except TypeError:
            error = err.strip().replace("\n", " ")
        print ("[***] Problem occurred while cloning {}: {}\n".format(name, error))
    lock.release()

# Worker function is defined below which will perform the work on the worker_data list


def intro():
     # Display ASCII art from text file below
    with open('ascii.txt', 'r') as f:
        for line in f:
            print(line.rstrip())
        return

@click.command()
@click.option('--verbose', '-v', multiple=True, is_flag=True, help="Will print verbose messages.")
# Interesting note below, the multiple option lets you changethe values of the option to a tuple if its true
# If it is not true, then the value is a single value
@click.option('--file', '-f', multiple=False,  default='' , help='a text file with a list of users favorite Github repos')
@click.option('--thread', '-t', multiple=False, default='' , help='Number of CPU threads to use')
def cli(verbose, file, thread):
    worker_data2 = []
    if verbose:
        click.echo("We are in the verbose mode.")
    if thread:
        click.echo("Aquired thread count value to use from user input...")
        click.echo('The thread count to use is ... {0}'.format(thread))
    if file:
        click.echo('The filename which contains user defined repos is called {}'.format(file))
        #Open user suppplied text file and append it to our existing worker_data list (array)
        # f = open(file,'r')
        # for line in f:
        #     # Print lines in user supplied text file for testing
        #     print(line.rstrip())
        #     worker_data2.append(line)
        #     worker_data2.save()
        #     # print updated worker_data list to see its contents with added repos
        #     print('[%s]' % ', '.join(map(str, worker_data2)))
        #     # The print statement above proves that worker_data is now updated with the two additional repos
        #test initial list
        # Open text file provided by user which includes a list of user specified Github repos line by line
        with open(file) as repofile:
            for line in repofile:
                line = line.strip()
                worker_data2.append(line)
                print(worker_data2)

        q = queue.Queue()
        for git_repo in worker_data2:
            q.put(git_repo)

        def worker2():
          while not stop: 
            item = q.get()
            subprocess_cmd(["/usr/bin/git", "clone", "https://github.com/{}.git".format(item)])
            q.task_done()

        cpus = int(thread)
        print("\nCreating %d threads...\n" % cpus)
        #cpus = 10
        #print("\nPulling git repos with %d threads...\n" % cpus))
        for i in range(cpus):
            t = threading.Thread(target=worker2)
            t.daemon = True
            t.start()

        q.join() # Blocks everything until all tasks in the queue have completed, then it print the messages below
        print("Program has successfully completed execution ...")
        print('[%s]' % ', '.join(map(str, worker_data2)))
        print(colored("Please check output ...", 'yellow'))

        
                


    
    #Show intro ASCII Art (Step1)
    intro()    
    # The goal is to read the filename below if it were given 
    
    # The multiprocessing libary below is ready to be called at this point
    # We want to make sure it takes in the "thread" parameter from the click cli function input from the user
    
    # Initial main part of program below
    # The part below installs all built in repos consumed by the program
    threadCount(thread)

if __name__ == "__main__":
    # The cli function calls all other functions when it is executed 
    cli()
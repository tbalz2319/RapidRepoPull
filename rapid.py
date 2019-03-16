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
        "Yara-Rules/rules",
        "codingo/Interlace"]

def threadCount(thread):
    # The command below kicks off thread dependent on how many CPU cores your system has available 
    thread = multiprocessing.cpu_count() #Detect the available cores on system , similar to nproc
    print("\nCreating %d threads...\n" % thread)
    #cpus = 10
    #print("\nPulling git repos with %d threads...\n" % cpus))
    for i in range(thread):
      t = threading.Thread(target=worker)
      t.daemon = True
      t.start()

    q.join() # Blocks everything until all tasks in the queue have completed, then it print the messages below
    print("Program has successfully completed execution ...")
    print(colored("Please check output ...", 'yellow'))

# Load up a queue with the data from the worker_data list, this will handle locking
q = queue.Queue()
for git_repo in worker_data:
    q.put(git_repo)

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
def worker():
    while not stop: 
        item = q.get()
        subprocess_cmd(["/usr/bin/git", "clone", "https://github.com/{}.git".format(item)])
        q.task_done()

def intro():
     # Display ASCII art from text file below
    with open('ascii.txt', 'r') as f:
        for line in f:
            print(line.rstrip())
        return

@click.command()
@click.option('--verbose', '-v', multiple=True, is_flag=True, help="Will print verbose messages.")
@click.option('--file', '-f', multiple=True,  default='' , help='a text file with a list of users favorite Github repos')
@click.option('--thread', '-t', multiple=True, default='' , help='Number of CPU threads to use')
def cli(verbose, file, thread):
    if verbose:
        click.echo("We are in the verbose mode.")
    click.echo("Aquired thread count value to use from user input...")
    click.echo('The thread count to use is ... {0}'.format(thread))
    click.echo('The filename which contains user defined repos is called {}'.format(file))
    file = file.replace(',','')
    print('The value for file is now {}'.format(file))

if __name__ == "__main__":
    cli()
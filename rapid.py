import os
import sys
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
        "paranoidninja/CarbonCopy",
        "Frint0/email-enum",
        "needmorecowbell/Hamburglar"
        "codingo/Interlace"]

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

if __name__ == "__main__":

    # Display ASCII art from text file below
    with open('ascii.txt', 'r') as f:
        for line in f:
            print(line.rstrip())

    # The command below kicks off thread dependent on how many CPU cores your system has available 
    cpus = multiprocessing.cpu_count() #Detect the available cores on system , similar to nproc
    print("\nCreating %d threads...\n" % cpus)
    #cpus = 10
    #print("\nPulling git repos with %d threads...\n" % cpus)

    for i in range(cpus):
      t = threading.Thread(target=worker)
      t.daemon = True
      t.start()

    q.join() # Blocks everything until all tasks in the queue have completed, then it print the messages below
    print("Program has successfully completed execution ...")
    print(colored("Please check output ...", 'yellow'))

#This script has been tested with Python 3.7.2
import os
import sys
import shlex
import traceback
import subprocess
import queue 
from queue import Empty
import threading
import multiprocessing

worker_data=["BloodHoundAD/BloodHound.git", 
        "GhostPack/Seatbelt.git", 
        "GhostPack/SharpUp.git", 
        "yeyintminthuhtut/Awesome-Red-Teaming.git",
        "byt3bl33d3r/DeathStar.git", 
        "byt3bl33d3r/CrackMapExec.git", 
        "Cn33liz/p0wnedShell.git", 
        "EmpireProject/Empire.git",
        "danielmiessler/SecLists.git", 
        "laramies/theHarvester.git", 
        "s0md3v/Photon.git", 
        "commixproject/commix.git", 
        "emtunc/SlackPirate",
        "bwall/ExtractHosts.git", 
        "Grunny/zap-cli.git", 
        "tevora-threat/PowerView3-Aggressor.git", 
        "vysecurity/ANGRYPUPPY.git", 
        "harleyQu1nn/AggressorScripts.git",
        "bluscreenofjeff/AggressorScripts.git", 
        "pavanw3b/sh00t.git",
        "evyatarmeged/Raccoon.git",
        "1N3/IntruderPayloads.git",
        "1N3/BlackWidow.git",
        "trustedsec/ptf.git",
        "codingo/Interlace.git"]

#Function to handle processing of commands        
def subprocess_cmd(command):
    process = subprocess.Popen(command,stdout=subprocess.PIPE, shell=False)
    proc_stdout = process.communicate()[0].strip()
    print (proc_stdout)

#load up a queue with the data from the worker_data list, this will handle locking
q = queue.Queue()
for git_repo in worker_data:
    q.put(git_repo)

#worker function is defined blow which will perform the work on the worker_data list
def worker():
    while True:
      item = q.get()
      #subprocess.Popen(cmd.format(item), shell = True)
      subprocess_cmd(["/usr/bin/git", "clone", "https://github.com/{}".format(item)])
      q.task_done()
    
cpus = multiprocessing.cpu_count() #Detect the available cores on system , similar to nproc
print("Creating %d threads" % cpus)
for i in range(cpus):
  t = threading.Thread(target=worker)
  t.daemon = True
  t.start()
 
q.join() #Blocks everything until all tasks in the queue have completed, then it print the messages below
print("Program has successfully completed execution ...")
print("Please check output ...")

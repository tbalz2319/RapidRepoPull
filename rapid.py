#This script has been tested with Python 3.7
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
# def subprocess_cmd(command):
#    #process = subprocess.Popen(command,stdout=subprocess.PIPE, shell=False)
#     process = subprocess.Popen(command, shell=False)
#     proc_stdout = process.communicate()[0].strip()
#     print (proc_stdout)

#load up a queue with your data, this will handle locking
q = queue.Queue()
for git_repo in worker_data:
    q.put(git_repo)

#command to run inside of while loop
cmd = "git clone https://github.com/{} &"    
#define a worker function
def worker():
    while True:
      item = q.get()
      #subprocess.Popen(cmd.format(item), shell = True)
      subprocess.Popen(["/usr/bin/git", "clone", "https://github.com/{}".format(item)])
      q.task_done()
    
cpus = multiprocessing.cpu_count() #Detect the number of CPU cores
print("Creating %d threads" % cpus)
for i in range(cpus):
  t = threading.Thread(target=worker)
  t.daemon = True
  t.start()
 
q.join() #Block everything until all tasks in queue have completed
print("Program has successfully completed execution")

# Python3 libraries required for the successful setup of this script
import os
import sys
import click
from termcolor import colored
import traceback
import subprocess
import queue
import threading
import multiprocessing
import giturlparse
import urllib3
from bs4 import BeautifulSoup
import re
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from huepy import *

# When acquired by a thread it locks other threads from printing
lock = threading.Lock()
stop = 0

# Function to handle processing of commands
def subprocess_cmd(command):
    # The actual name of the repo is pulled from the url in order to display it to the user
    name = command[2].split("/")[-1].replace(".git", "")

    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = process.communicate()

    lock.acquire()
    if "fatal".encode("utf-8") not in err:
        print (good(colored("[**] Successfully cloned {}\n".format(name), 'green')))

    else:
        try:
            error = str(err, 'utf-8').strip().replace("\n", " ")
        except TypeError:
            error = err.strip().replace("\n", " ")
        print (bad(colored("[ERROR] Problem occurred while cloning {}: {}\n".format(name, error),'red')))
    lock.release()

def intro():
    # Display ASCII art from text file below
    with open('ascii.txt', 'r') as f:
        for line in f:
            print(line.rstrip())
        return

@click.command()
@click.option('--verbose', '-v', multiple=True, is_flag=True, help="Will print verbose messages.")
@click.option('--fileinput', '-f', default='default.txt', multiple=False, help='Specify a text file with a list of user selected Github repos')
@click.option('--thread', '-t', multiple=False, default=multiprocessing.cpu_count(), help='Specify the number of CPU threads to use')
@click.option('--url', '-u', multiple=False, help='Specify a url to scrape containing Github repos to clone')

def cli(verbose, fileinput, thread, url):
    worker_data = []
    # The second array will only be utilized if a user specifies a url to scrape with the -u option
    worker_data2 = []

    if thread < 1:
        thread = multiprocessing.cpu_count()

    if verbose:
        click.echo("\nWe are in the verbose mode.")
        if thread:
            click.echo("Aquired thread count value to use from user input")
            click.echo("The thread count was 0 or negative, so the number of cores will be used".format(thread))
        else:
            click.echo('The thread count will be the number of cores')
        click.echo('The thread count to use is: {0}'.format(thread))

    if fileinput:
        if verbose:
            click.echo('The filename which contains user defined repos is called {}'.format(fileinput))
        # Open either supplied text file or default file
        # It includes a list of user specified Github repos line by line
        with open(fileinput) as repofile:
            for line in repofile:
                # .strip() removes the whitespace from the beginning and end of the string
                line = line.strip()
                p = giturlparse.parse(line)
                p_new = p.owner + '/' + p.repo
                worker_data.append(p_new)

        if verbose:
            print('Installed: [%s]' % ', '.join(map(str, worker_data)))

        q = queue.Queue()
        for git_repo in worker_data:
            q.put(git_repo)

        # Worker function is defined below which will perform the work on the worker_data list
        def worker():
          while not stop:
            item = q.get()
            subprocess_cmd(["/usr/bin/git", "clone", "https://github.com/{}.git".format(item)])
            q.task_done()

        print("\nCreating %d threads...\n" % thread)
        for i in range(thread):
            t = threading.Thread(target=worker)
            t.daemon = True
            t.start()

        q.join() # Blocks everything until all tasks in the queue have completed, then it print the messages below
        print("Program has successfully completed execution...")
        print(colored("Please check output...", 'yellow'))
        print (lightblue(info("All default options were used")))

    if url:
        if verbose:
            click.echo('The url which will be scraped for repos is ... {}'.format(url))
        # Open either supplied text file or default file
        # It includes a list of user specified Github repos line by line
        http = urllib3.PoolManager(num_pools=20)
        response = http.request('GET', url)
        soup = BeautifulSoup(response.data.decode('utf-8'), "html.parser")
        links = soup.find_all('a', {'href': re.compile(r'github\.com/([^\/]+)/([^\/]+$)')})


        file1 = open('red.txt', 'wb')
        print('Collecting the links...')
        for link in links:
            href = link.get('href') + '\n'
            file1.write(href.encode())
        file1.close()
        print('Saved to %s' % 'red.txt')
        print("New file input being called")
        
        with open('red.txt') as repofile:
             for line in repofile:
        #         # .strip() removes the whitespace from the beginning and end of the string
                 line = line.strip()
                 g = giturlparse.parse(line)
                 g_new = g.owner + '/' + g.repo
                 worker_data2.append(g_new)
        
        # if verbose:
        #     print('Installed: [%s]' % ', '.join(map(str, worker_data2)))

        q = queue.Queue()
        for git_repo in worker_data2:
            q.put(git_repo)

        # Worker function is defined below which will perform the work on the worker_data list
        def worker2():
          while not stop:
            item = q.get()
            subprocess_cmd(["/usr/bin/git", "clone", "https://github.com/{}.git".format(item)])
            q.task_done()

        print("\nCreating %d threads...\n" % thread)
        for i in range(thread):
            t = threading.Thread(target=worker2)
            t.daemon = True
            t.start()

        q.join() # Blocks everything until all tasks in the queue have completed, then it print the messages below
        print("Program has successfully completed execution...")
        print(colored("Please check output...", 'yellow'))
        print (info(lightblue('A url was scraped')))

 # Main part of program below
if __name__ == "__main__":
    #Show intro ASCII Art (Step1)
    intro()
    # The cli function calls all other functions when it is executed
    cli()

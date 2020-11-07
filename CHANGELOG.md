# 3.2.1

- Update to license file date
- Clean up of install.sh script (removed un-needed comments)
- Adding the https://github.com/21y4d/nmapAutomator repo to the default install list of tools

# 3.2.0

- Adding the Linux threat emulation framework "Chain Reactor" to the default
clone list

## 3.1.9

- Update of boot.sh file to increase thread execution of program inside of
Docker container from 75 to 85

## 3.1.8

- Cleanup and maintenance of various comments and spacing issues in various scripts and files

## 3.1.7

- Adding web app recon tools created by @TomNomNom to the default clone list

- The tools are assetfinder and httprobe

## 3.1.6

- Adding John Hammond's CTF Kitana repo to the default clone list

## 3.1.5

- Increasing repo pull threads to 75 from 35 when running the container to pull
  repos

## 3.1.4

- Adding the SpiderLabs Scavenger tool to the default clone list

## 3.1.3

- Adding RapidScan and the foospidy payloads repo for a nice quick
  dir of payloads to have for web application security testing and CTFs

## 3.1.2

- Adding ldapdomaindump tool to default list

## 3.1.1

- Upgrade of all pip packages in requirements.txt

- Added the gobuster tool to the default.txt clone list

- Addressed potential security vulnerability in urllib3

## 3.1.0

- Adding LinEnum, and joomscan to .gitignore

## 3.0.9

- Fixed comment typo in rapid.py and increased the num of pools in the url parser

## 3.0.8

- Adding Joomscan and LinEnum to the default.txt repos to clone

## 3.0.7

- Update to install.sh to use the Cyan color in the script

- Update to install.sh to replace backticks with $() per codefactor

## 3.0.6

- Removed bob.txt and added useful repos to demo.txt

## 3.0.5

- Bash script fixups implemented and testing recommended by codefactor

## 3.0.4

- Removed demo.txt file

- Added rm -f red.txt in clean.sh

## 3.0.3

- Fixed typos in main rapid.py file

- Created a demo.txt file

- Updated dockerfile to specify python3 instead of python

- Updated boot.sh for Docker container to run a minimal number of repositories for demo purposes

## 3.0.2

- Cleaned up @click section comments based on input provided by Codefactor

- Provided comment on second worker_data=[] list purpose

## 3.0.1

- Updated readme file "Use case" section

## 3.0.0

- Updated master branch with new features

- Added the ability to scrape a given url with the -u flag and clone any Github repos which are existing as links

- Added the pip huepy library to the program to help with user cli notifications with colors

## 2.1.4

- Adding rvrsh3ll/FindFrontableDomains to the clone list

## 2.1.3

- Rapid.py file is cleaned up with useful comments on what specific lines of code are doing

## 2.1.2

- Updates to contribute section of readme

## 2.1.1

- Adding the chompscan repo to the default.txt file to be cloned

## 2.1.0

- Externalised repos to text file called default.txt

- Code refacotring optimizations thanks to diego95root!

## 2.0.3

- Adding patator and girurlparse repos to .gitignore file

## 2.0.2

- Uncommented the mass scan repo which was taken out during dev testing

## 2.0.1

- Adding in minor Linter code fixes

## 2.0.0

- New 2.0.0 release includes the following new features

- New CLI based help menu with multiple options

- Ability to Specify user defined text file with custom repos for RapidRepoPull to clone

- Ability to specify how many threads the script takes advantage of

- Code refactored and additional comments added for clarity

- New use option script (option4.sh) created to install dependencies and get script ready for user

- specified text file and the specification for the number of threads to use

## 1.8.5

- Adding the hlldz/Invoke-Phant0m repo to the clone list

## 1.8.4

- Adding jondonas/ in front of broken repo pull for linux-exploit-suggester-2

- Adding the following dirs to .gitignore linux-exploit-suggester-2, CarbonCopy

- Hamburglar email-enum added to .gitignore as well

## 1.8.3

- Adding the "linux-exploit-suggester-2" repo to the clone list

## 1.8.2

- Minor issue fix in repo related to missing ','

## 1.8.1

- Added the Hamburgler tool to the clone list

## 1.8.0

- Added the email-enum tool to the clone list

## 1.7.9

- Added the CarbonCopy tool to the clone list

## 1.7.8

- Install script updated to detect OS and install specific dependencies

- So far, this only works for Kali/Ubuntu/Debian Linux distros

## 1.7.7

- Added image of running program in readme file

## 1.7.6

- Added support for green colored echo statements in update_repos.sh

## 1.7.5

- Green colored text added to echo statements in install.sh

## 1.7.4

- Added support to mass update all repos already cloned instead of re-cloning

## 1.7.3

- Adding support for terminal colors

## 1.7.2

- Added an install.sh to install all dependencies and run script

## 1.7.1

- Added an update.sh script to keep the program updated via Github

## 1.7.0

- Created docker-compose file to build dockerfile

- Cleaned up print statement outputs

- Various updates to readme for clarity

## 1.6.0

- Created a dockerfile for the script

- Created a cleanup bash script

## 1.5.0

- Megreged pull request that fixed up code : "Removed git output, added controlled output with locks"

## 1.4.1

- The repo for Windows Exploit Suggester NG has been added

## 1.4.0

- Cleaned up readme instructions

- Added Massscn to repo list

- Removed un-needed import library

## 1.3.2

- Multiple code fixes and adding in missing ","

- Added a new ASCII text for "RapidRepoPull" displayed after program execution completes

## 1.3.1

- First release version of codebase

## 1.2.1

- code cleanup, removing .git from every entry in list and adding to loop

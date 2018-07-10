*** OSINT TOOL ***

Tool for extracting data and knowledge from public available sources like Twitter,Pastebin,Telegram and Forocoches.


-- Installation --

Recommended to clone with git, so versions are automatically updated

git clone https://github.com/aperezdev/OsintTool.git

-- Execution enviroments (Linux,Centos) --

Open a terminal
Run the command setup.sh

-- Command Line --

See tool basic info:
	python3.6 modosint.py

Run tool as simple execution:
	python3.6 modosint.py -c /etc/modosint/modosint.conf

Run,stop and restart tool as daemon service:
	python3.6 modosint.py -c /etc/modosint/modosint.conf -D {start,stop,restart}

See help for using tool:
	python3.6 modosint.py -h
	python3.6 modosint.py -help

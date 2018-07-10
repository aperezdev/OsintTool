#!/bin/bash

### START SETUP INFO
#
#  Modulable OSINT Tool (ModOSINT)
#
### END SETUP INFO

# files location
sudo cp -R etc/modosint /etc/
echo "workplace: /etc/modosint/... OK"
sudo cp etc/init.d/modosintd /etc/init.d/
echo "initd: /etc/init.d/modosintd... OK"
sudo cp modosint.py /usr/local/bin/modosint.py
echo "tool: /usr/local/bin/modosint.py... OK"
if [ ! -d /var/log/modosint/ ]; then
	sudo mkdir /var/log/modosint/;
fi

# python requirements
pip=$(which pip3.6)
if [ -z "$pip" ];
then
	echo "[WARNING] python pip cannot be found... what user is installing?"
	echo "[WARNING] python requirements have not been installed... you must install them manually if it is necessary"
else
	$pip install python-daemon
	$pip install daemon-runner
	$pip install twitter
	$pip install emoji
	$pip install graypy
	$pip install matplotlib
	$pip install numpy
	$pip install datetime
	$pip install wordcloud
	$pip install stop_words
	$pip install twarc
	$pip install pandas
	$pip install seaborn
	$pip install logging
	$pip install multiprocessing
	$pip install telethon
	$pip install request
	$pip install beautifulsoup4
	$pip install shodan
	$pip install googletrans
fi

echo ""
echo "ModOSINT-Tool successfully installed!"
echo "Usage (daemon): /etc/init.d/modosintd start"
echo "Usage (simple): /etc/modosint/modosint.py -c /etc/modosint/modosint.conf"

exit 0;

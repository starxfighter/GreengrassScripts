#!/bin/bash

homeDir='/home/ec2-user'
cd ${homeDir}
sudo adduser --system ggc_user
sudo groupadd --system ggc_group
cd /etc/sysctl.d
if [ ! -f 00-defaults.conf ]; then
    echo "Got No file"
    sudo touch 00-defaults.conf
fi
grepOutput=`grep protected_hardlinks 00-defaults.conf|wc -l`
if [ $grepOutput == 0 ]; then
    echo "Got No Match"
    echo 'fs.protected_hardlinks = 1' | sudo tee --append 00-defaults.conf
    echo 'fs.protected_symlinks = 1' | sudo tee --append 00-defaults.conf
fi
cd ${homeDir}
curl https://raw.githubusercontent.com/tianon/cgroupfs-mount/951c38ee8d802330454bdede20d85ec1c0f8d312/cgroupfs-mount > cgroupfs-mount.sh
chmod +x cgroupfs-mount.sh 
sudo bash ./cgroupfs-mount.sh
wget https://s3.amazonaws.com/ggfiles123/greengrass-linux-x86-64-1.6.0.tar.gz -O gg.tar.gz
sudo tar xvzf gg.tar.gz -C /
sudo yum -y install git
git clone https://github.com/aws-samples/aws-greengrass-samples.git 
sudo yum -y install python-pip
pip install awscli --upgrade --user
pip install pandas --user
pip install boto3 --user
wget https://s3.amazonaws.com/ggtestfiles/createFullGG.py -O createFullGG.py
sudo cd /
sudo mkdir /Tmp
cd /greengrass/certs/ 
sudo wget -O root.ca.pem http://www.symantec.com/content/en/us/enterprise/verisign/roots/VeriSign-Class%203-Public-Primary-Certification-Authority-G5.pem
cd ${homeDir}
python createFullGG.py >& $homeDir/outputlog.txt
sudo cp config.json /greengrass/config/config.json
sudo cp iot-pem-crt /greengrass/certs/iot-pem-crt
sudo cp iot-pem-key /greengrass/certs/iot-pem-key
cd /greengrass/ggc/core/ 
sudo ./greengrassd start


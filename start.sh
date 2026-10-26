if [ -z $UPSTREAM_REPO ]
then
  echo "Cloning main Repository"
  git clone https://github.com/MAX-COPYCODE-TG/Charlie_Film_BoT /Charlie_Film_BoT
else
  echo "Cloning Custom Repo from $UPSTREAM_REPO "
  git clone $UPSTREAM_REPO /Charlie_Film_BoT
fi
cd /Charlie_Film_BoT
pip3 install -U -r requirements.txt
echo "Starting Bot....✅"
python3 bot.py

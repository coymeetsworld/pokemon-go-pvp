# pokemon-go-pvp
App that will be used to create a custom search string for Pokemon Go to filter out pokemon that are used in the current meta for PVP. The search string will include the pokemon, then also appropriate IVs when necessary. Generally speaking low attack IVs and high defense and hp are ideal (although not always, sometimes 100% IVs are the ideal).


# How to Run App
```
cd app/
python3 -m venv .pgo
source .pgo/bin/activate
pip install -r requirements.txt
python main.py
```

# How to Setup the Control Node Fresh
```
cd ansible/
python3 -m venv .ansible_control
source .ansible_control/bin/activate
pip install -r requirements.txt
ansible-galaxy collection install -r requirements.yml
```

Note that the ansible playbooks depend on .ansible_control being the location of the python version to use which will include the dependencies needed (via the pip install command).

# Configure Secrets
Create ansible/.env file and add following line:
`export DIGITALOCEAN_TOKEN="dop_v1_..."`

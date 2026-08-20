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

# Installing the app onto a DigitalOcean droplet

## Setting up the Control Node
```
cd ansible/
python3 -m venv .ansible_control
source .ansible_control/bin/activate
pip install -r requirements.txt
ansible-galaxy collection install -r requirements.yml
```

Note that the ansible playbooks depend on .ansible_control being the location of the python version to use which will include the dependencies needed (via the pip install command).

## Configure Secrets
Create ansible/.env file and add following line:
`export DIGITALOCEAN_TOKEN="dop_v1_..."`
`export EMAIL_ADDRESS=""`
email address needed when Certbot tasks are run to generate certs for the app.

Create user to be used for admin on droplet:
`ssh-keygen -t ed25519 -f ~/.ssh/pokemongopvp_admin -C "pvpokedeployer@pokemongopvp.com"`
This file should be picked up as a variable `admin_ssh_public_key` under `group_vars/all.yml`

Then run following:
```
set -a
source .env
set +a
echo $DIGITALOCEAN_TOKEN
echo $EMAIL_ADDRESS
```
Confirm token works:
`curl -s -X GET -H "Authorization: Bearer $DIGITALOCEAN_TOKEN" "https://api.digitalocean.com/v2/sizes"`

### Scopes needed for token:
* Fully Scoped Access
  * actions (1): read
  * regions (1): read
  * sizes (1): read
  * domain (4): create, read, update, delete
* Create Access
  * droplet
  * ssh_key
* Read Access
  * droplet
  * image
  * snapshot
  * ssh_key
  * vpc
* Delete Access
  * droplet
  * ssh_key


## Deploy onto droplet
Note: Droplet will be provisioned during this step along with DNS records

```
cd ansible/
ansible-playbook -i inventory/production.ini site.yml
```

## Destroy
Note: Droplet and DNS records will be removed (but not nameserver records, just A and PTR records)
```
cd ansible/
ansible-playbook -i inventory/production.ini destroydroplet.yml
```
# Polymarekit

## Start the project

1. Run:

   ```bash
   ./start.sh
   ```

### Note: if python3, node, or npm fail to install you must verify that it is running on a Ubuntu-based distribution or install the tools manually to work with your OS

2. Open <http://127.0.0.1:8000/>.

`start.sh` installs dependencies, creates the SQLite database tables, builds the CSS, and starts the Django development server. It is safe to run again.

## Deploy to EC2

Install AWS EC2 Ubuntu server access and an SSH key first. Then run the one-time server setup:

```bash
scp -i ~/keys/mykey.pem -r deploy ubuntu@<PUBLIC-IP>:~
ssh -i ~/keys/mykey.pem ubuntu@<PUBLIC-IP>
sudo bash deploy/setup-ec2.sh
```

From your laptop, deploy updates with:

```bash
./deploy/deploy.sh -h <PUBLIC-IP> -i ~/keys/mykey.pem
```

If the browser cannot connect, check these items on the EC2 server:

```bash
sudo systemctl status polymarekit nginx --no-pager
sudo journalctl -u polymarekit -n 50 --no-pager
sudo ss -ltnp | grep -E ':80 |:8000 '
curl -i http://127.0.0.1/api/health
```

The EC2 security group must allow inbound **TCP 80** from your IP (or `0.0.0.0/0` for a public demo). The server must have a public IPv4 address, and the browser URL must be `http://<PUBLIC-IP>/`, not HTTPS. If the local curl succeeds but the browser times out, the security group or an EC2/network firewall is blocking port 80. If local curl fails, inspect the service and nginx logs above.

## Checkpoint 1:

Deliverables:
- Complete the EC2 setup and app configuration scripts
- Install dependencies, initialize SQLite, and verify the deployed app is reachable

All deliverables have been addressed in assignment 7.02 and are currently running in the EC2 instance.

## Checkpoint 2:

Deliverables:
- Set up the Django project templates, Tailwind styling, and shared header/footer
- Display available markets on the Home Page

Setting up Django project deliverable has been addressed in assignment 7.02 and are currently running in the EC2 instance.

Display available markets on the Home Page deliverable has been addressed in this checkpoint by adding a homepage with placeholder markets.

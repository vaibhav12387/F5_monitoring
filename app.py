import requests
from flask import Flask, render_template
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Suppress only the single InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

app = Flask(__name__)

# Define your F5 devices with their respective IP addresses and ports
F5_DEVICES = {
   ##   "AWS PROD": [
   ##       {'ip': '192.168.0.46', 'port': 8443},
   ##       {'ip': '192.168.0.115', 'port': 8443},
   ##       {'ip': '192.168.0.22', 'port': 8443},
   ##       {'ip': '192.168.0.112', 'port': 8443}
   ##   ],
    "INSIDE ": [
        {'ip': '192.168.0.21', 'port': 443},
   ##        {'ip': '192.168.0.22', 'port': 443}
    ]
}

USERNAME = 'f5admin'
PASSWORD = 'YOUR_PASS'
EMAIL_FROM = 'YOUR_EMAIL@DOMAIN.COM'
EMAIL_TO = 'YOUR_EMAIL@DOMAIN.COM'
EMAIL_SUBJECT = 'F5 Failover Notification'
SMTP_SERVER = 'smtp.office365.com'
SMTP_PORT = 587
SMTP_USER = 'YOUR_EMAIL@DOMAIN.COM'
SMTP_PASS = 'YOUR_PASS'

def get_f5_status(host, port):
    try:
        url = f"https://{host}:{port}/mgmt/tm/cm/device"
        response = requests.get(url, auth=(USERNAME, PASSWORD), verify=False)
        response.raise_for_status()
        return response.json().get('items', [])
    except requests.exceptions.RequestException as e:
        print(f"Error fetching F5 status from {host}:{port}: {e}")
        return []

def send_email(subject, body):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_FROM
    msg['To'] = EMAIL_TO
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html'))
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
        server.quit()
        print("Email sent successfully")
    except Exception as e:
        print(f"Failed to send email: {e}")

app = Flask(__name__)

@app.route('/')
def home():
    all_devices = []
    for group, hosts in F5_DEVICES.items():
        for host_info in hosts:
            devices = get_f5_status(host_info['ip'], host_info['port'])
            for device in devices:
                device['group'] = group  # Add group info to each device
            all_devices.extend(devices)
    
    # Check for failover events and send email notifications
    active_devices = [device for device in all_devices if device.get('failoverState') == 'active']
    
    # Check if there are any devices in failover state
    if any(device.get('failoverState') != 'active' for device in all_devices):
        failover_devices = [device for device in all_devices if device.get('failoverState') != 'active']
        email_body = f"""
        <h2>F5 Failover Notification</h2>
        <p>Failover has occurred. Below are the details:</p>
        <h3>Failover Devices</h3>
        <table border="1">
            <tr>
                <th>Host Name</th>
                <th>IP Address</th>
                <th>State</th>
                <th>Group</th>
            </tr>
            {''.join([f"<tr><td>{device.get('hostname')}</td><td>{device.get('managementIp')}</td><td>{device.get('failoverState')}</td><td>{device['group']}</td></tr>" for device in failover_devices])}
        </table>
        <h3>Active Devices</h3>
        <table border="1">
            <tr>
                <th>Host Name</th>
                <th>IP Address</th>
                <th>State</th>
                <th>Group</th>
            </tr>
            {''.join([f"<tr><td>{device.get('hostname')}</td><td>{device.get('managementIp')}</td><td>{device.get('failoverState')}</td><td>{device['group']}</td></tr>" for device in active_devices])}
        </table>
        """
        send_email(EMAIL_SUBJECT, email_body)
    
    return render_template('index.html', devices=all_devices)

if __name__ == '__main__':
    app.run(debug=True)


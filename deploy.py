import argparse
from paramiko import SSHClient


parser = argparse.ArgumentParser()
parser.add_argument("username")
parser.add_argument("hostname")
parser.add_argument("server_dir")
parser.add_argument("release_candidate_dir")
parser.add_argument("project_prefix")
args = parser.parse_args()

host = args.hostname
user = args.username
server_dir = args.server_dir
release_candidate_dir = args.release_candidate_dir
project_prefix = args.project_prefix

if not project_prefix:
    raise Exception('The PREFIX environment variable is not set')

client = SSHClient()
client.load_system_host_keys()
client.connect(host, username=user)

commands_list = [
    f'chmod +x {server_dir}/releases/{release_candidate_dir}/deploy.sh',
    f'{server_dir}/releases/{release_candidate_dir}/deploy.sh {server_dir} {release_candidate_dir} {project_prefix}'
]
for command in commands_list:
    stdin, stdout, stderr = client.exec_command(command)
    print("stderr: ", stderr.readlines())
    for line in stdout.readlines():
        print(line)
    del stdin, stdout, stderr
del client
print("commands completed")

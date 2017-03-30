# Configuration file for jupyterhub.

import os

import jupyterhub
jh_ver = [int(v) for v in jupyterhub.__version__.split(".")]

c = get_config()

# Setup some variables
network_name               = os.environ["DOCKER_NETWORK_NAME"]
ff_data_dir                = os.environ["FF_DATA_DIR"]
ff_image_name              = os.environ["FF_IMAGE_NAME"]
ff_container_name          = os.environ["FF_CONTAINER_NAME"]
hub_container_name         = os.environ["HUB_CONTAINER_NAME"]
mysql_container_name       = os.environ["MYSQL_CONTAINER_NAME"]

jupyterhub_config_dir      = os.path.join(ff_data_dir, "config", "jupyterhub")

# Spawned containers
c.JupyterHub.spawner_class          = "dockerspawner.SystemUserSpawner"
c.SystemUserSpawner.container_image = ff_image_name
c.DockerSpawner.container_prefix    = ff_container_name
c.DockerSpawner.remove_containers   = True
if jh_ver[0] >= 0 and jh_ver[1] >= 7:
    c.Spawner.mem_limit             = os.environ["FF_CONTAINER_MEMLIMIT"]

# Networking
c.JupyterHub.port                 = 443
c.JupyterHub.hub_ip               = hub_container_name
c.JupyterHub.hub_port             = 8080
c.DockerSpawner.use_internal_ip   = True
c.DockerSpawner.network_name      = network_name
c.DockerSpawner.extra_host_config = {
    "network_mode" : network_name,
}
c.Spawner.environment             = {
    "MYSQL_CONTAINER_NAME" : mysql_container_name,
}

# Security
c.JupyterHub.ssl_key = os.environ["SSL_KEY"]
c.JupyterHub.ssl_cert = os.environ["SSL_CERT"]
# c.Authenticator.whitelist = {""}

# Data/directories
c.JupyterHub.db_url                            = os.path.join("sqlite:///", jupyterhub_config_dir, "jupyterhub.sqlite")
c.JupyterHub.cookie_secret_file                = os.path.join(jupyterhub_config_dir, "jupyterhub_cookie_secret")
c.JupyterHub.extra_log_file                    = os.path.join(jupyterhub_config_dir, "jupyterhub.log")
c.Spawner.notebook_dir                         = "~/notebooks"
c.DockerSpawner.read_only_volumes              = { os.path.join(ff_data_dir, "data") : "/data" }
c.SystemUserSpawner.host_homedir_format_string = os.path.join(ff_data_dir, "users", "{username}")

# Services - setup
cull_idle_filename = os.path.join(jupyterhub_config_dir, "cull_idle_servers.py")
if "FF_IDLE_SERVER_TIMEOUT" in os.environ:
    cull_idle_timeout = os.environ["FF_IDLE_SERVER_TIMEOUT"]
else:
    cull_idle_timeout = 3600

evaluation_server_filename = os.path.join(jupyterhub_config_dir, "server.py")

# Services - definitions
c.JupyterHub.services = [
    {
        "name": "cull-idle",
        "admin": True,
        "command": ["python", cull_idle_filename,
                    "--timeout="+cull_idle_timeout,
                    "--cull_every=300"],
    },
    {
        "name": "evaluation-server",
        "url": "http://127.0.0.1:10101",
        "command": ["flask", "run", "--port=10101"],
        "environment": {
            "FLASK_APP": evaluation_server_filename,
            "FLASK_DEBUG": "1",
        }
    }
]

# Whitelist users and admins
c.Authenticator.whitelist = whitelist = set()
c.Authenticator.admin_users = admin = set()
c.JupyterHub.admin_access = True

whitelist.add("root")
admin.add("root")

userlist_filename = os.path.join(jupyterhub_config_dir, "userlist")
if os.path.isfile(userlist_filename):
    with open(userlist_filename, "r") as f:
        for line in f:
            if not line:
                continue
            parts = line.split()
            name = parts[0]
            whitelist.add(name)
            if len(parts) > 1 and parts[1] == "admin":
                admin.add(name)

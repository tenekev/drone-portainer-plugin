# Drone-Portainer Plugin

[![Docker Pulls](https://img.shields.io/docker/pulls/tenekev/drone-portainer-plugin?style=for-the-badge&logo=docker)](https://hub.docker.com/r/tenekev/drone-portainer-plugin)
![Python](https://img.shields.io/badge/Python-v3.10-f7cb40?style=for-the-badge&logo=python)
![Portainer](https://img.shields.io/badge/Portainer-v2.18-13bef9?style=for-the-badge&logo=portainer)

## Why?
Portainer is great for management of docker at a glance but it locks you into using the UI. Docker-compose, aka "Stacks", created outside Portainer cannot be managed fully. This plugin bridges the gap.
* It allows you to write plain `YAML` files and incorporate them into an existing Portainer instance for easy management.
* It watches the repo for changes and applies updated docker-compose files into Portainer.

## How it works

By default the drone-portainer-plugin check recursively for changed `docker-compose.yml` files in the workspace and applies them to the provided Portainer instance.

Simply put, when you push a changed docker-compose to the repo, Drone detects it and updates the corresponding Portainer Stack, based on name.

The name is taken either from the directory of the docker-compose.yml file OR from the top-level element `name`, if it's defined in the docker-compose.yml

```yml
- name: "Test Deploy Compose"
  image: tenekev/drone-portainer-plugin
  settings: 
    portainer_instance: https://my.portainer.lan 
    
    # usually named local or Primary
    portainer_endpoint_name: local

    portainer_username:
      from_secret: portainer_username
    portainer_password:
      from_secret: portainer_password

    # optional -> ⚠️#1
    global_env:
      from_secret: compose_environment
    
    # optional -> ⚠️#2
    docker_compose_file: ./test_files/docker-compose.yml

    # optional -> ⚠️#3
    docker_compose_skip: stack_init
```

⚠️#1 When setting the `compose_environment` from a secret, use json notation in the secret:
```json
{
    "key1": "value1",
    "key2": "value2"
}
```

⚠️#2 Defining `docker_compose_file` will prevent the plugin from scanning recursively the whole workspace for `docker-compose.yml` and `.env` files. It will use only the specified file, regardless of change status.

## ⚠️#3 Crucial infrastructure. The importaince of `stack_init`
```
{Code Editor} --> [Reverse Proxy] --> [Gitea] --> [Drone] --> [Portainer] --> {Deploy}
```

In order to deploy changes to the Docker environment, you need a working infrastructure. If you try to update a stack that contains parts of this crucial infrastructure, the process will break and you will have to recover it manually. 
That's why it's advised to define these crucial services in an **"initializing"** stack. A stack that goes up before anything else is started in your Docker environment. I name this stack `stack_init`. A stack that contains `stack_init` in the name will be ignored by the drone-portainer-plugin. You can override the name and use your own by defining `docker_compose_skip` argument.

Here is an exmaple: My `stack_init` contains Portainer, Gitea, Drone and RP of choice - Traefik. Changes to this stack are ignored by the drone-portainer-plugin. It's the only stack that requires you to use `docker compose up` command. There is no other rational way to do it.

## Inspired by
* [robkaandorp/drone-portainer](https://github.com/robkaandorp/drone-portainer) 
* [Deploy docker-compose.yml automatically with drone.io and gitea](https://www.reddit.com/r/homelab/comments/yghttb/deploy_dockercomposeyml_automatically_with/)
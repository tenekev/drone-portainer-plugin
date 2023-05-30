import json, yaml, dotenv 
import os, subprocess
import requests, logging
import uuid

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
indent = list()
def logger(log_message):
  def decorator(func):
    def wrapper(*args, **kwargs):
      global indent
  
      formatted_message = f"{''.join(indent)}{log_message.format(*args, **kwargs)}"
      logging.info(formatted_message)  # Log the custom message
      
      if len(indent) == 0:
        indent.append('└───')
      else:
        indent.insert(0,'│   ')

      try:
        result = func(*args, **kwargs)
        log_message_success = f"{''.join(indent)}[SUCCESS] {func.__name__} function completed successfully"
        logging.info(log_message_success)  # Log the successful completion
        return result

      except Exception as e:
        log_message_exception = f"{''.join(indent)}[ERROR] {func.__name__} function raised an exception: {str(e)}"
        logging.exception(log_message_exception)  # Log the exception with traceback
        raise e

      finally:
        indent.pop(0)

    return wrapper
  return decorator


@logger('Getting Git Changes')
def get_git_gitchanges() -> list: 
  if os.environ.get("DRONE_PULL_REQUEST"):
    command = 'git --no-pager diff --name-only --diff-filter=d FETCH_HEAD FETCH_HEAD~1'
  else: 
    command = 'git --no-pager diff --name-only --diff-filter=d HEAD~1'
  
  output = subprocess.check_output(command, shell=True).decode('utf-8').split('\n')

  output = [i for i in output if "docker-compose" in i]


  return output


@logger('Defining Portainer Instance')
class Portainer:
  def __init__(self, instance: str):
    self.instance = instance
    self.endpoint_name = str
    self.endpoint_id = int
    self.headers = {
      'Accept': 'application/json',
      'Content-Type': 'application/json',
    } 
  

  @logger('Authenticating @ {0.instance}...')
  def auth(self, username: str, password: str) -> None:
    request = requests.post( 
      f'{self.instance}/api/auth', 
      headers=self.headers, 
      data=json.dumps({
        "Username": username,
        "Password": password
      })
    )
    if request.status_code != 200: raise RuntimeError(request.json())

    self.headers['Authorization'] = f'Bearer {request.json()["jwt"]}'


  def select_endpoint(self, name: str) -> None:
    self.endpoint_name = name
    self.endpoint_id = self.get_id('endpoints', self.endpoint_name)


  @logger('Identifying [{2}] in [{1}] @ {0.instance}...')
  def get_id(self, haystack: str, needle: str) -> int:
    request = requests.get(
      f'{self.instance}/api/{haystack}', 
      headers=self.headers
    )
    if request.status_code != 200: raise RuntimeError(request.json())
    
    results = [i['Id'] for i in request.json() if needle in i['Name']]
    
    if len(results) != 1:
      if haystack == 'stacks':
        logger(f'    Stack {needle} is missing and will be created.')
        return None
      
      else:
        raise RuntimeError(f'{len(results)} {haystack} found.')
      
    else:
      return results[0]


  @logger('Stopping "{1.stack_name}" @ {0.instance}...')
  def stack_stop(self, stack: 'Stack') -> None:
    request = requests.post(
      f'{self.instance}/api/stacks/{stack.stack_id}/stop?endpointId={self.endpoint_id}',
      headers=self.headers
    )
    if request.status_code != 200: raise RuntimeError(request.json())


  @logger('Starting "{1.stack_name}" @ {0.instance}...')
  def stack_start(self, stack: 'Stack') -> None:
    request = requests.post(
      f'{self.instance}/api/stacks/{stack.stack_id}/start?endpointId={self.endpoint_id}',
      headers=self.headers
    )
    if request.status_code != 200: raise RuntimeError(request.json())


  @logger('Updating "{1.stack_name}" @ {0.instance}...')
  def stack_update(self, stack: 'Stack') -> None:
    request = requests.put(
      f'{self.instance}/api/stacks/{stack.stack_id}?endpointId={self.endpoint_id}',
      headers=self.headers,
      data=json.dumps({
        "stackFileContent": stack.stack_body,
        "env": stack.stack_env,
        "prune": True,
        "pullImage": True,
      })
    )
    if request.status_code != 200: raise RuntimeError(request.json())


  @logger('Creating "{1.stack_name}" @ {0.instance}...')
  def stack_create(self, stack: 'Stack') -> None:
    request = requests.post(
      f'{self.instance}/api/stacks?type=2&method=string&endpointId={self.endpoint_id}',
      headers=self.headers,
      data=json.dumps({
        "Name": stack.stack_name,
        "stackFileContent": stack.stack_body,
        "env": stack.stack_env,
        "prune": True,
      })
    )
    if request.status_code != 200: raise RuntimeError(request.json())


@logger('Defining Stack')
class Stack:
  def __init__(self, portainer: 'Portainer', compose_file_path: str, global_env: str) -> None:
    self.stack_name = self.handle_naming(os.path.abspath(compose_file_path))
    self.stack_id   = portainer.get_id('stacks', self.stack_name)
    self.stack_body = self.compose_file(os.path.abspath(compose_file_path))
    self.global_env = json.loads(global_env)
    self.stack_env  = self.environment(os.path.abspath(compose_file_path))  


  @logger('Determining stack name for {1}')
  def handle_naming(self, filename: str) -> str:
    def from_file(fn: str) -> str:
      n = str
      try:
        with open(fn, "r") as f:
          n = yaml.safe_load(f)['name']
        return n

      except:
        return None

    name = from_file(filename)
    unname = f'unnamed-{uuid.uuid4()}'
    default = os.path.basename(os.path.dirname(filename))

    if os.getcwd() == os.path.dirname(filename):
      logger(f'{os.path.basename(filename)} is in root...   ')

      if name:
        logger(f'  Stack name set: {name}')
        return name

      else:
        logger(f'  Stack name unknown: {unname}')
        return unname

    else:
      logger(f'{os.path.basename(filename)} is in {os.path.dirname(filename)}...   ')

      if name:
        logger(f'  Stack name set: {name}')
        return name

      else:
        logger(f'  Stack name default: {default}')
        return default


  @logger('Reading compose from {1}')
  def compose_file(self, compose_file_path: str) -> str:
    with open(compose_file_path, 'r') as f:
      return f.read() 
  

  @logger('Combining ENV variables')
  def environment(self, compose_file_path: str) -> list:
    env_from_file = dotenv.dotenv_values(
      os.path.join(os.path.dirname(compose_file_path),'.env')
    )
    env_from_file = [
      {"name": k, "value": v} for k, v in env_from_file.items()
    ]

    env_from_drone = [
      {"name": k, "value": v} for k, v in self.global_env.items()
    ]

    return env_from_drone + env_from_file


@logger('======================== Starting ========================')
def main() -> None:
  portainer = Portainer(
    instance = os.environ["PLUGIN_PORTAINER_INSTANCE"],
  ) 

  portainer.auth(
    username = os.environ["PLUGIN_PORTAINER_USERNAME"],
    password = os.environ["PLUGIN_PORTAINER_PASSWORD"]
  )
  portainer.select_endpoint(
    name = os.environ["PLUGIN_PORTAINER_ENDPOINT_NAME"],
  )

  if os.environ.get("PLUGIN_GLOBAL_ENV"):
    env_var = os.environ["PLUGIN_GLOBAL_ENV"]
  else:
    env_var = {}

  if os.environ.get("PLUGIN_DOCKER_COMPOSE_FILE"):
    stack = Stack(
      portainer = portainer,
      compose_file_path = os.environ["PLUGIN_DOCKER_COMPOSE_FILE"],
      global_env = env_var
    )

    if stack.stack_id:
      portainer.stack_stop(stack)
      portainer.stack_update(stack)

    else:
      portainer.stack_create(stack)

  else: 
    for o in get_git_gitchanges():
      stack = Stack(
        portainer = portainer,
        compose_file_path = o,
        global_env = env_var
      )

      if stack.stack_id:
        portainer.stack_stop(stack)
        portainer.stack_update(stack)
      
      else:
        portainer.stack_create(stack)

if __name__ == '__main__': main()
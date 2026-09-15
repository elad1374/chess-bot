import os
from common.utils import repo_path

filepath = repo_path("src/main/config.yaml")

print(repr(filepath))
print(os.path.exists(filepath))
print(os.path.isfile(filepath))
print(os.path.dirname(filepath))
print(os.listdir(repo_path("src/main")))
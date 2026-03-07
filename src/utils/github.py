import git
from pathlib import Path

class GithubUtils:
    
  def clone_repo(self, target_dir: Path, repo_url: str) -> str | None:
    try:
      print(f"Cloning into {target_dir}...")
      repo = git.Repo.clone_from(repo_url, target_dir)
      return repo.head.commit.hexsha
    except Exception as e:
      print(f"Error during clone: {e}")
      return None

  def get_repo_hash(self, path: Path) -> str | None:
    try:
      repo = git.Repo(path)
      head_commit = repo.head.commit
      return head_commit.hexsha
    except Exception as e:
      print(f"Error getting repo hash: {e}")
      return None
import git
from pathlib import Path
import shutil
import stat
import os
from git.exc import GitCommandError

class GithubUtils:
  def __init__(self):
    pass
    
  def _force_remove(self, func, path, _):
    """ Error handler for shutil.rmtree — clears read-only flag then retries """
    os.chmod(path, stat.S_IWRITE)
    func(path)

  def clone_repo(self, target_dir: Path, repo_url: str, hash: str | None = None) -> str | None:
    try:
      # TODO: Don't force remove, instead use a temp folder library handler?
      if target_dir.exists():
        shutil.rmtree(target_dir, onexc=self._force_remove)

      print(f"Cloning into {target_dir}...")
      repo = git.Repo.clone_from(repo_url, target_dir, multi_options=["--recurse-submodules"])

      if hash:
        print(f"Checking out commit {hash}...")
        repo.git.checkout(hash)

        # Update submodules to match the state at this commit
        repo.git.submodule("update", "--init", "--recursive")

      return repo.head.object.hexsha

    except GitCommandError as e:
      print(f"Git error during clone: {e}")
      return None
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
# Learning Git by building it.

## Commands

◻️ `init`
- ✅ `init`
- ◻️ Missing files in hooks

◻️ `add`
- ✅ `add <file> [<file>...]`
- ✅ `add <dir> [...]`
- ◻️ make it so that index is a binary file (currently just a JSON)
- ◻️ `add .`
- ◻️ `add --all`

◻️ `commit`
- ✅ `commit`
- ✅ `commit -m "message"`
- ◻️ Don't commit if nothing is staged
- ◻️ `commit --amend`

◻️ `status`

◻️ `branch`
- ◻️ `branch <branch name>`
- ◻️ `branch -d <branch name>`

◻️ `switch`
- ◻️ `switch <branch name>`
- ◻️ `switch -c <branch name>`


◻️ `merge`

◻️ `log`

- ◻️ `--oneline`
- ◻️ `--graph`

◻️ `rebase`

◻️ `remote`

◻️ `push`

◻️ `pull`

◻️ `fetch`




## Classes

✅ Objects:

- ✅ Blob
- ✅ Tree
- ✅ Commit
- ✅ Tag

## Steps:

	0. Quick tour of Git
	1. init (no hooks)
		- main.py (bare bones)
		- repo.py
			- just REPO_DIR
		- init.py
	2. add
		- main.py
			- add commands=[]
		- objects.py (just Blob)
		- add.py
		- repo.find_repo_root()
	3. commit


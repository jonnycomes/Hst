# Hst: Learning Git by Rebuilding It (slower, smaller, in Python)

**Hst** (pronounced Hist -- short for History) is a personal project to help me learn about Git internals by implementing a simplified version of Git in Python. This project is for educational purposes and is not intended to be a fully-featured Git alternative.

## Installation

To get started with **Hst**, follow these steps:

1. Clone the repository:

   ```bash
   git clone https://github.com/jonnycomes/Hst.git
   cd hst
   ```

2. Install the package in editable mode:

   ```bash
   pip install -e .
   ```

## Usage

Once installed, you can create a Hst repo with the command:

```bash
hst init
```
Then you can `add` and `commit` files to your Hst repo by mimicking Git commands:

```bash
hst add <file>
hst commit -m "commit message"
```

## Commands That Either Work (✅) or Are Coming Soon (◻️)

### `init`
- ✅ `hst init` (missing files in hooks)

### `add`
- ✅ `hst add <file> [<file>...]`
- ✅ `hst add <dir> [...]`
- ✅ `hst add .`
- ✅ `hst add --all`
- ✅ `hst add -A`
- **Note:** Currently, the index is just a JSON. Making it a binary file will come later. 

### `commit`
- ✅ `hst commit`
- ✅ `hst commit -m "message"`
- ✅ `hst commit --amend`

### `status`
- ✅ `hst status`
- ✅ `hst status <path> [<path> ...]`

### `branch`
- ✅ `hst branch`
- ✅ `hst branch <branch name>`
- ✅ `hst branch -D <branch name>`
- ✅ `hst branch -d <branch name>`

### `switch`
- ✅ `hst switch <branch name>`
- ✅ `hst switch -c <branch name>`

### `restore`
- ✅ `hst restore <file>`
- ✅ `hst restore --staged <file>`

### `merge`
- ◻️ `hst merge`

### `log`
- ◻️ `hst log`
- ◻️ `hst log --oneline`
- ◻️ `hst log --graph`

### `rebase`
- ◻️ `hst rebase -i <commit-ish>`

### `remote`
- ◻️ `hst remote -v`
- ◻️ `hst remote add origin <repo>`

### `push`
- ◻️ (comming soon)

### `pull`
- ◻️ (comming soon)

### `fetch`
- ◻️ (comming soon)



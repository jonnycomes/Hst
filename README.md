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



## Commands That Either Work or Are Coming Soon

### `init`
- ✅ `init` (missing files in hooks)

### `add`
- ✅ `add <file> [<file>...]`
- ✅ `add <dir> [...]`
- ◻️ `add .`
- ◻️ `add --all`
- **Note:** Currently, the index is just a JSON. Making it a binary file will come later. 

### `commit`
- ✅ `commit`
- ✅ `commit -m "message"`
- ◻️ `commit --amend`
- **Note:** Currently, you can commit if nothing new is staged. This should be fixed later.

### `status`
- ◻️ `status`

### `branch`
- ✅ `branch`
- ✅ `branch <branch name>`
- ✅ `branch -D <branch name>`
- ◻️ `branch -d <branch name>`

### `switch`
- ✅ `switch <branch name>`
- ✅ `switch -c <branch name>`
- **Note:** Currently, you can switch to the branch you are currently on. This should be fixed later.

### `merge`
- ◻️ `merge`

### `log`
- ◻️ `log`
- ◻️ `--oneline`
- ◻️ `--graph`

### `rebase`
- ◻️ `rebase -i <commit-ish>`

### `remote`
- ◻️ `remote -v`
- ◻️ `remote add origin <repo>`

### `push`
- ◻️ (comming soon)

### `pull`
- ◻️ (comming soon)

### `fetch`
- ◻️ (comming soon)



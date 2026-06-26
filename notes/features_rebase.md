# Standard Deluxe

## Workflow for Interactive Rebase Feature Extraction

### Phase 1: Prepare dev-features

1. Ensure being on dev-features and up to date:

```bash
 git checkout dev-features
 git fetch origin
 git pull origin dev-features
```

2. Verify all work is committed (should show clean)
3. View full commit history to plan your features, identify which commits
   belong to which feature.

    ```bash
    git log --oneline --graph main..dev-features
    ```

### Phase 2: Extract Feature (Repeat for each feature)

Example for Feature `availability` (commits A, B, C).

1. Create a feature branch from dev-features:

    ```bash
    git checkout -b feature/availability dev-features
    ```

2. Start interactive rebase:

    > Identify the commit BEFORE your first feature commit.
    Let's say this feature starts at commit B (after A).
    A is the "base" commit that is NOT part the feature.

    ```bash
    git rebase -i main

    # OR if you need to start from a specific point:

    git rebase -i <commit-hash-of-A>

    # In the editor that opens:
    # pick Acommithash Feature: add X
    # pick Bcommithash Feature: add Y
    # pick Ccommithash Feature: add Z
    # pick Dcommithash WIP: unfinished
    # pick Ecommithash WIP: unfinished

    # Change to:
    # pick Acommithash Feature: add X
    # pick Bcommithash Feature: add Y
    # pick Ccommithash Feature: add Z
    # drop Dcommithash WIP: unfinished
    # drop Ecommithash WIP: unfinished
    ```

3. Save and close editor
4. If conflicts, resolve them, then:

    ```bash
    git add .
    git rebase --continue
    ```

5. Verify the branch has only your feature commits:
    git log --oneline
6. Push to remote (first time, -u sets upstream):
    git push -u origin feature/availability

### Phase 3: Merge to Main

Option A: PR via GitHub (recommended)

> Push is already done above
Go to GitHub, create PR from feature/availability to main

Option B: Direct merge:

```bash
git checkout main
git merge feature/availability
git push origin main
git branch -d feature/availability  # delete local
git push origin --delete feature/availability  # delete remote
```

### Phase 4: Repeat for Each Feature

After Feature 1 is merged, repeat Phase 2 for Feature 2.

- Start again from dev-features (unchanged)
    git checkout dev-features
- Create a next feature branch
    git checkout -b feature/version dev-features
- Rebase, keeping only version-related commits

```bash
git rebase -i main
# ... select commits ...
git push -u origin feature/version
```

### Phase 5: Cleanup

After ALL features merged to main.

```bash
git checkout main
git pull origin main

```

Optionally keep dev-features as backup for a while Or delete when ready:

```bash
git branch -d dev-features
git push origin --delete dev-features
```

Summary Diagram
main:      A---B---C---D---E---F---G---H---I
               \     \     \     \
dev-features:   A-----B-----C-----D-----E-----F-----G-----H-----I
                     |     |     |
feature-1:          A-----B-----C
feature-2:                      D-----E
feature-3:                             F-----G

Questions Before Execution:

1. Should features be merged in order? (some may depend on others)
2. Do you want to keep the commit messages exactly as-is, or squash/reword?
3. Any commits that are shared across multiple features (e.g., a refactor
   used by several features)?

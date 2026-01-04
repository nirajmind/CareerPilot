# Branching Strategy

This project follows the GitFlow branching model, which provides a robust framework for managing a project with a scheduled release cycle. This model is designed to keep the `main` branch clean and stable, while allowing for parallel development of new features.

## Branches

### `main`

The `main` branch is the primary branch of the repository. It represents the production-ready code and should always be in a stable state. No direct commits should be made to this branch. Instead, changes should be merged into `main` from `release` or `hotfix` branches.

### `develop`

The `develop` branch is the integration branch for new features. It is created from the `main` branch and serves as the primary branch for development. All `feature` branches are created from `develop` and are merged back into it when they are complete. This branch should always be in a state that is ready for a new release.

### `feature`

`feature` branches are created for developing new features. Each feature should have its own branch, created from the `develop` branch. When a feature is complete, it is merged back into the `develop` branch. `feature` branches should never be merged directly into `main`.

- **Naming Convention:** `feature/<feature-name>`

### `release`

`release` branches are created from the `develop` branch when it is ready for a new release. These branches are used for final testing and bug fixes before a release. Once a `release` branch is stable, it is merged into both the `main` and `develop` branches. This ensures that the `main` branch is updated with the new release, and the `develop` branch is updated with any bug fixes that were made during the release process.

- **Naming Convention:** `release/<version-number>`

### `hotfix`

`hotfix` branches are created from the `main` branch to address critical bugs in production. These branches are used to make urgent fixes to the production code. Once a `hotfix` is complete, it is merged into both the `main` and `develop` branches. This ensures that the fix is applied to the production code and is also incorporated into future releases.

- **Naming Convention:** `hotfix/<issue-name>`

## Workflow

1. A `develop` branch is created from the `main` branch.
2. `feature` branches are created from the `develop` branch for new features.
3. When a feature is complete, it is merged back into the `develop` branch.
4. When the `develop` branch is ready for a release, a `release` branch is created.
5. The `release` branch is tested and any necessary bug fixes are made.
6. Once the `release` branch is stable, it is merged into both the `main` and `develop` branches.
7. If a critical bug is found in production, a `hotfix` branch is created from the `main` branch.
8. The `hotfix` is merged into both the `main` and `develop` branches.

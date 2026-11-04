# WRLD automated desktop updates

WRLD's built-in Update button installs a published Windows release; it does not generate new code.

## Publishing an updated app

1. Make the desired source changes in this repository.
2. Bump `APP_VERSION` in `app_version.py` (for example, 1.8.1 -> 1.8.2) and commit it to `main`.
3. GitHub Actions builds `WRLD.exe`, generates its SHA-256 checksum, creates the version tag automatically, and publishes a release. No separate tag or manual Release step is required.
4. In an already installed WRLD app, open **Updates -> Check Now -> Update & Restart**.

Assistant-side GitHub access can prepare and commit changed source directly, when connected and permitted.

## Notes

- Versions must be unique. A version with an existing published release is skipped.
- Windows compilation and automatic replacement need to succeed in GitHub Actions and on Windows, respectively.
- Avoid adding songs, music folders, build outputs, or personal files to this public repository.
- Existing local playlists and preferences are stored in `%APPDATA%\WRLDPlayer`; the updater must not delete them.
- Users remain in control of applying updates from the WRLD UI.

# Try the integration in Home Assistant

This starts a separate Home Assistant instance using the integration files in
this checkout. You need Docker with the Compose plugin (`docker compose version`).
The HA image is pinned to the release used by `requirements-dev.txt`; update the
two together when changing the supported test version.

Run the helper from the repository root (use `sudo ./dev/ha/run start` if your
user cannot access Docker):

```sh
./dev/ha/run start
```

For automatic first-time setup:

```sh
./dev/ha/run setup
```

Use `sudo` if needed. This starts HA, creates a local `tester` account with a
random password, completes onboarding, and adds Tøyenbadet. It prints the login
and dashboard URL. Credentials are saved with owner-only permissions inside the
Docker volume at `/config/.toyenbadet-dev-login.json`, never in the repo. Running
`setup` again reuses that login and does not add a duplicate integration. If the
public API is unavailable, fix connectivity and rerun `setup` to finish.

Open [the test dashboard](http://127.0.0.1:8124/lovelace/toyenbadet). You can also
set up manually: create a local test account, then go to **Settings → Devices &
services → Add integration → Tøyenbadet**. Use English during setup for the
example entity IDs, or adjust `dev/ha/ui-lovelace.yaml` to the IDs assigned by HA.
The helper leaves manually created accounts and their configuration untouched.
Your current manually configured instance therefore needs only `start`.

`start` never performs onboarding. The optional `setup` helper uses HA's local
onboarding APIs, so review it when updating the pinned HA version. To test the
integration's setup UI itself, use the manual route on a separate fresh volume.

HA may offer or create its usual onboarding integrations (such as weather).
These aren't needed for this test; skip them where offered, or remove them from
Devices & services. The YAML configuration loads the frontend and its built-in
dependencies, without `default_config` or network discovery.

The dashboard displays the visitor monitor from `main`. Feature branches can
edit the dashboard to display their additional entities. It uses real public
API data, so the instance needs internet access. No production HA credentials
or devices are needed. The web UI is bound to localhost only.

## While working

The integration directory is mounted read-only from this checkout. After Python
changes, restart HA to load them:

```sh
./dev/ha/run restart
```

HA configuration and dashboard files are mounted read-only too; edit them in
the repo, not in HA's UI. After changing these YAML files, recreate the container
to pick up file replacements made by your editor, then refresh the browser:

```sh
./dev/ha/run recreate
```

Use the same command after changing Compose settings or the pinned image.
Recreating the container preserves the named volume and your login.

View status and logs:

```sh
./dev/ha/run status
./dev/ha/run logs
```

The health check verifies the web server responds. Check the Tøyenbadet device
and logs as well to verify that the integration has loaded and fetched data.

## Stop and start again

```sh
./dev/ha/run stop
```

The named volume `toyenbadet-dev_ha-config` keeps your account, integration setup,
and other generated HA data outside Git. Run the start command again to reuse
it. To deliberately discard this test instance's data and repeat onboarding:

```sh
docker compose -f dev/ha/compose.yaml down --volumes
```

## Remember local settings

Copy the example once:

```sh
cp dev/ha/.env.example dev/ha/.env
```

Edit `dev/ha/.env` to choose a port, such as `HA_TEST_PORT=8125` if the temporary
server still uses 8124. Keep `COMPOSE_PROJECT_NAME=toyenbadet-dev` to reuse the
existing Docker instance and login. The file is ignored by Git, and the script
loads it consistently even when invoked from another directory or with `sudo`.
It prints the dashboard URL after starting or restarting HA.

To run two worktrees at once, set a different port **and** project name in each
checkout's `.env`. A different project name creates a separate volume and login.
The helper always mounts the integration from the checkout containing the script.

Run `./dev/ha/run --help` for the available commands. `restart` returns after the
container restarts; the UI can take a little longer to become available. `start`
and `recreate` wait for the web server health check.

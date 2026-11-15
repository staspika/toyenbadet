# Try the integration in Home Assistant

This starts a separate Home Assistant instance using the integration files in
this checkout. You need Docker with the Compose plugin (`docker compose version`).
The HA image is pinned to the release used by `requirements-dev.txt`; update the
two together when changing the supported test version.

Run these commands from the repository root:

```sh
docker compose -f dev/ha/compose.yaml up -d --wait --wait-timeout 300
```

Open [the test dashboard](http://127.0.0.1:8124/lovelace/toyenbadet). On the first
run, create a local test account, then go to **Settings → Devices & services →
Add integration → Tøyenbadet**. Use English during setup for the example entity
IDs, or adjust `dev/ha/ui-lovelace.yaml` to the IDs assigned by HA.

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
docker compose -f dev/ha/compose.yaml restart homeassistant
```

HA configuration and dashboard files are mounted read-only too; edit them in
the repo, not in HA's UI. After changing these YAML files, recreate the container
to pick up file replacements made by your editor, then refresh the browser:

```sh
docker compose -f dev/ha/compose.yaml up -d --force-recreate --wait --wait-timeout 300
```

Use the same command after changing Compose settings or the pinned image.
Recreating the container preserves the named volume and your login.

View status and logs:

```sh
docker compose -f dev/ha/compose.yaml ps
docker compose -f dev/ha/compose.yaml logs -f homeassistant
```

The health check verifies the web server responds. Check the Tøyenbadet device
and logs as well to verify that the integration has loaded and fetched data.

## Stop and start again

```sh
docker compose -f dev/ha/compose.yaml down
```

The named volume `toyenbadet-dev_ha-config` keeps your account, integration setup,
and other generated HA data outside Git. Run the start command again to reuse
it. To deliberately discard this test instance's data and repeat onboarding:

```sh
docker compose -f dev/ha/compose.yaml down --volumes
```

## Another instance or an occupied port

If the temporary HA server or another service is using port 8124, choose another
port. To test two worktrees at once, also give each one its own project name:

```sh
HA_TEST_PORT=8125 docker compose -p toyenbadet-feature -f dev/ha/compose.yaml up -d --wait --wait-timeout 300
```

Open `http://127.0.0.1:8125/lovelace/toyenbadet` for that instance. Use the same
`HA_TEST_PORT` and `-p` arguments for its subsequent commands. A different project
name creates a separate volume and login; the default name reuses the default
instance's data.

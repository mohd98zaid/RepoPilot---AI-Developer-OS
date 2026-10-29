# Desktop application

Run `build-desktop.bat` at the repository root. The build uses pinned Tauri CLI dependencies, the Rust lockfile, and PyInstaller to package the backend as a directory. Tauri starts that backend, waits for its health endpoint, opens the authenticated UI, and stops the child process on exit.

Output: `src-tauri/target/release/bundle/nsis/RepoPilot_0.1.0_x64-setup.exe`.

`../launch.bat --desktop` uses the development launcher with the release executable. `../scripts/smoke_packaged.py` verifies the bundled backend without installing the app.

The installer is unsigned. Authenticode signing requires the publisher's certificate and signing configuration. Git, Docker, model weights and provider credentials are not bundled.

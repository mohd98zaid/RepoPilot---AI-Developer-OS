use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};
use std::process::{Child, Command};
use std::sync::Mutex;
use std::time::Duration;
use tauri::{Manager, WebviewUrl, WebviewWindowBuilder};

struct Backend(Mutex<Option<Child>>);

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let application = tauri::Builder::default()
        .manage(Backend(Mutex::new(None)))
        .setup(|app| {
            let url = if let Ok(url) = std::env::var("REPOPILOT_URL") {
                // Development launcher already owns and authenticates the backend.
                url
            } else {
                let listener = TcpListener::bind("127.0.0.1:0")?;
                let port = listener.local_addr()?.port();
                drop(listener);
                let token = format!("{}{}", uuid::Uuid::new_v4(), uuid::Uuid::new_v4());
                let data = app.path().app_local_data_dir()?;
                std::fs::create_dir_all(&data)?;
                let executable = app.path().resource_dir()?.join("backend").join("repopilot-server.exe");
                let mut command = Command::new(executable);
                command.args(["--port", &port.to_string()]).current_dir(&data)
                    .env("REPOPILOT_SESSION_TOKEN", &token)
                    .env("REPOPILOT_DATABASE_PATH", data.join("repopilot.sqlite3"))
                    .env("LANGSMITH_TRACING", "false");
                #[cfg(windows)]
                {
                    use std::os::windows::process::CommandExt;
                    command.creation_flags(0x08000000);
                }
                let mut child = command.spawn()?;
                let mut ready = false;
                for _ in 0..240 {
                    if child.try_wait()?.is_some() {
                        return Err("RepoPilot backend stopped during startup".into());
                    }
                    if let Ok(mut stream) = TcpStream::connect(("127.0.0.1", port)) {
                        stream.set_read_timeout(Some(Duration::from_secs(1)))?;
                        let request = format!("GET /health HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nConnection: close\r\n\r\n");
                        let _ = stream.write_all(request.as_bytes());
                        let mut reply = [0u8; 256];
                        if let Ok(length) = stream.read(&mut reply) {
                            if String::from_utf8_lossy(&reply[..length]).contains("200 OK") {
                                ready = true;
                                break;
                            }
                        }
                    }
                    std::thread::sleep(Duration::from_millis(250));
                }
                if !ready {
                    let _ = child.kill();
                    let _ = child.wait();
                    return Err("RepoPilot backend readiness timed out".into());
                }
                *app.state::<Backend>().0.lock().unwrap() = Some(child);
                format!("http://127.0.0.1:{port}/#token={token}")
            };
            WebviewWindowBuilder::new(app, "main", WebviewUrl::External(url.parse()?))
                .title("RepoPilot").inner_size(1440.0, 960.0).min_inner_size(960.0, 640.0).build()?;
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("RepoPilot could not start");
    application.run(|handle, event| {
        if let tauri::RunEvent::Exit = event {
            if let Some(mut child) = handle.state::<Backend>().0.lock().unwrap().take() {
                let _ = child.kill();
                let _ = child.wait();
            }
        }
    });
}

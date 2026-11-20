//! Bounded IPC/menu capture and explicit direct-child deadlines. Never run a shell.
use std::io::{self, Read, Write};
use std::os::fd::AsRawFd;
use std::process::{Command, ExitStatus, Stdio};
use std::time::{Duration, Instant};

const LIMIT: usize = 4 * 1024 * 1024;

fn nonblocking(fd: &impl AsRawFd) -> io::Result<()> {
    // SAFETY: borrowed live pipe descriptor; only its status flags are changed.
    let flags = unsafe { libc::fcntl(fd.as_raw_fd(), libc::F_GETFL) };
    if flags < 0
        || unsafe { libc::fcntl(fd.as_raw_fd(), libc::F_SETFL, flags | libc::O_NONBLOCK) } < 0
    {
        return Err(io::Error::last_os_error());
    }
    Ok(())
}

fn drain(pipe: &mut impl Read, output: &mut Vec<u8>) -> Result<(), String> {
    let mut buffer = [0; 8192];
    for _ in 0..32 {
        match pipe.read(&mut buffer) {
            Ok(0) => break,
            Ok(n) => {
                if output.len() + n > LIMIT {
                    return Err("child output limit exceeded".into());
                }
                output.extend_from_slice(&buffer[..n]);
            }
            Err(e) if e.kind() == io::ErrorKind::WouldBlock => break,
            Err(e) if e.kind() == io::ErrorKind::Interrupted => continue,
            Err(e) => return Err(e.to_string()),
        }
    }
    Ok(())
}

#[derive(Debug)]
pub struct Output {
    pub status: ExitStatus,
    pub stdout: Vec<u8>,
}

pub fn run(
    command: &mut Command,
    input: Option<&[u8]>,
    capture: bool,
    timeout: Option<Duration>,
) -> Result<Output, String> {
    command.stdin(if input.is_some() {
        Stdio::piped()
    } else {
        Stdio::null()
    });
    command.stdout(if capture {
        Stdio::piped()
    } else {
        Stdio::inherit()
    });
    command.stderr(if capture {
        Stdio::piped()
    } else {
        Stdio::inherit()
    });
    let mut child = command
        .spawn()
        .map_err(|e| format!("cannot start child: {e}"))?;
    let started = Instant::now();
    let result = (|| {
        if let Some(pipe) = &child.stdin {
            nonblocking(pipe).map_err(|e| e.to_string())?;
        }
        if let Some(pipe) = &child.stdout {
            nonblocking(pipe).map_err(|e| e.to_string())?;
        }
        if let Some(pipe) = &child.stderr {
            nonblocking(pipe).map_err(|e| e.to_string())?;
        }
        let mut remaining = input.unwrap_or_default();
        let mut stdout = Vec::new();
        let mut stderr = Vec::new();
        loop {
            if let Some(pipe) = &mut child.stdout {
                drain(pipe, &mut stdout)?;
            }
            if let Some(pipe) = &mut child.stderr {
                drain(pipe, &mut stderr)?;
            }
            if let Some(pipe) = &mut child.stdin {
                match pipe.write(remaining) {
                    Ok(n) => remaining = &remaining[n..],
                    Err(e) if e.kind() == io::ErrorKind::BrokenPipe => remaining = &[],
                    Err(e)
                        if matches!(
                            e.kind(),
                            io::ErrorKind::WouldBlock | io::ErrorKind::Interrupted
                        ) => {}
                    Err(e) => return Err(e.to_string()),
                }
                if remaining.is_empty() {
                    child.stdin.take();
                }
            }
            if let Some(status) = child.try_wait().map_err(|e| e.to_string())? {
                // Do not wait forever for descendants retaining an inherited pipe.
                if let Some(pipe) = &mut child.stdout {
                    drain(pipe, &mut stdout)?;
                }
                if let Some(pipe) = &mut child.stderr {
                    drain(pipe, &mut stderr)?;
                }
                return Ok(Output { status, stdout });
            }
            if timeout.is_some_and(|limit| started.elapsed() >= limit) {
                return Err(
                    "child deadline exceeded; result may be uncertain; not retrying".into(),
                );
            }
            std::thread::sleep(Duration::from_millis(2));
        }
    })();
    if result.is_err() {
        // Kill/reap this helper only, never a process group or a launched application.
        let _ = child.kill();
        let _ = child.wait();
    }
    result
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn deadline_is_bounded() {
        let started = Instant::now();
        assert!(
            run(
                Command::new("sleep").arg("5"),
                None,
                true,
                Some(Duration::from_millis(20))
            )
            .is_err()
        );
        assert!(started.elapsed() < Duration::from_secs(2));
    }
    #[test]
    fn capture_and_stdin() {
        let result = run(
            &mut Command::new("cat"),
            Some(b"fixture"),
            true,
            Some(Duration::from_secs(2)),
        )
        .unwrap();
        assert!(result.status.success());
        assert_eq!(result.stdout, b"fixture");
    }
    #[test]
    fn output_is_bounded() {
        assert!(
            run(
                &mut Command::new("yes"),
                None,
                true,
                Some(Duration::from_secs(2))
            )
            .unwrap_err()
            .contains("limit")
        );
    }
}
